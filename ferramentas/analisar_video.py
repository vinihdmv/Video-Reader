"""
Prepara um vídeo (gravação de tela) para o Claude analisar.

Gera, em analises/<nome-do-video>/:
  frames/          telas únicas (frames repetidos são descartados), nomeadas pelo horário
  mosaicos/        grades 3x3 de frames com horário, para visão geral rápida
  transcricao.md   fala do vídeo com horários (se a transcrição estiver disponível)
  linha_do_tempo.md  fala + telas intercaladas por horário
  INDICE.md        resumo e ponto de partida da análise

Uso:
  .venv\\Scripts\\python.exe ferramentas\\analisar_video.py "C:\\caminho\\video.mp4"
  opções: --intervalo 2  --sensibilidade 0.004  --sem-transcricao  --modelo small
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import warnings
from pathlib import Path

# Avisos internos das bibliotecas poluem a janela; erros de verdade continuam aparecendo.
warnings.filterwarnings("ignore")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
RAIZ = Path(__file__).resolve().parent.parent


def hms(segundos: float, sep=":") -> str:
    s = int(round(segundos))
    h, m, s = s // 3600, (s % 3600) // 60, s % 60
    if sep == "arquivo":
        return f"{h:02d}h{m:02d}m{s:02d}s"
    return f"{h:02d}:{m:02d}:{s:02d}"


def duracao(video: Path) -> float:
    saida = subprocess.run([FFMPEG, "-i", str(video)], capture_output=True, text=True, errors="replace").stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", saida)
    if not m:
        sys.exit(f"Não consegui ler a duração de {video}. É um vídeo válido?")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def extrair_frames(video: Path, pasta_tmp: Path, intervalo: float):
    print(f"[1/4] Extraindo 1 frame a cada {intervalo}s...")
    subprocess.run(
        [FFMPEG, "-v", "error", "-i", str(video),
         "-vf", f"fps=1/{intervalo},scale='min(1600,iw)':-2",
         "-q:v", "3", str(pasta_tmp / "f_%06d.jpg")],
        check=True,
    )
    return sorted(pasta_tmp.glob("f_*.jpg"))


def assinatura(caminho: Path) -> np.ndarray:
    with Image.open(caminho) as im:
        return np.asarray(im.convert("L").resize((640, 360)), dtype=np.int16)


BLOCO = 20  # a webcam é procurada em blocos de 20x20 px da assinatura (640x360)


def detectar_webcam(frames):
    """Acha a área que continua mudando enquanto o resto da tela está parado (webcam no canto).
    Retorna (máscara 360x640, True = ignorar na comparação; descrição) ou None."""
    gy, gx = 360 // BLOCO, 640 // BLOCO
    mudou_sozinho, calmos, anterior = np.zeros((gy, gx)), 0, None
    for f in frames:
        sig = assinatura(f)
        if anterior is not None:
            blocos = (np.abs(sig - anterior) > 25).reshape(gy, BLOCO, gx, BLOCO).mean(axis=(1, 3)) > 0.02
            if blocos.mean() < 0.3:  # par "calmo": a tela em si não trocou
                mudou_sozinho += blocos
                calmos += 1
        anterior = sig
    if calmos < 10:
        return None
    candidatos = mudou_sozinho / calmos > 0.3

    # Regiões ligadas de blocos; cursor piscando, relógio etc. são pequenos demais para contar.
    mascara, visto, caixas = np.zeros((gy, gx), bool), np.zeros((gy, gx), bool), []
    for y0, x0 in zip(*np.nonzero(candidatos)):
        if visto[y0, x0]:
            continue
        regiao, fila = [], [(y0, x0)]
        visto[y0, x0] = True
        while fila:
            y, x = fila.pop()
            regiao.append((y, x))
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < gy and 0 <= nx < gx and candidatos[ny, nx] and not visto[ny, nx]:
                    visto[ny, nx] = True
                    fila.append((ny, nx))
        if len(regiao) >= 6:
            ys, xs = zip(*regiao)  # retângulo inteiro + 1 bloco de folga: rosto parado não vira "buraco"
            caixa = (max(min(ys) - 1, 0), min(max(ys) + 2, gy), max(min(xs) - 1, 0), min(max(xs) + 2, gx))
            mascara[caixa[0]:caixa[1], caixa[2]:caixa[3]] = True
            caixas.append(caixa)
    if not caixas or mascara.mean() > 0.25:  # nada achado, ou grande demais para ser uma webcam
        return None

    def posicao(y0, y1, x0, x1):
        cy, cx = (y0 + y1) / 2 / gy, (x0 + x1) / 2 / gx
        v = "superior" if cy < 1 / 3 else "inferior" if cy > 2 / 3 else "central"
        h = "esquerdo" if cx < 1 / 3 else "direito" if cx > 2 / 3 else "centro"
        return f"canto {v} {h}" if h != "centro" else f"parte {v} do centro"
    descricao = ", ".join(posicao(*c) for c in caixas) + f" ({mascara.mean():.0%} da tela)"
    return np.repeat(np.repeat(mascara, BLOCO, axis=0), BLOCO, axis=1), descricao


def frames_unicos(frames, intervalo: float, sensibilidade: float, pasta_frames: Path, ignorar=None):
    """Mantém só frames em que uma fração relevante dos pixels mudou desde o último mantido.
    `ignorar` (máscara da webcam) tira essa área da comparação."""
    print("[2/4] Removendo telas repetidas...")
    considerar = np.ones((360, 640), bool) if ignorar is None else ~ignorar
    mantidos, ultima = [], None
    for i, f in enumerate(frames):
        t = i * intervalo
        sig = assinatura(f)
        if ultima is None or (np.abs(sig - ultima) > 25)[considerar].mean() > sensibilidade:
            destino = pasta_frames / f"t_{hms(t, 'arquivo')}.jpg"
            shutil.move(str(f), destino)
            mantidos.append((t, destino))
            ultima = sig
    return mantidos


def montar_mosaicos(mantidos, pasta_mosaicos: Path, colunas=3, linhas=3, larg=640):
    print("[3/4] Montando mosaicos...")
    alt = larg * 9 // 16
    faixa = 34
    try:
        fonte = ImageFont.truetype("arialbd.ttf", 24)
    except OSError:
        fonte = ImageFont.load_default()
    por_mosaico = colunas * linhas
    gerados = []
    for n in range(0, len(mantidos), por_mosaico):
        grupo = mantidos[n:n + por_mosaico]
        tela = Image.new("RGB", (colunas * larg, linhas * (alt + faixa)), "white")
        d = ImageDraw.Draw(tela)
        for k, (t, caminho) in enumerate(grupo):
            x, y = (k % colunas) * larg, (k // colunas) * (alt + faixa)
            with Image.open(caminho) as im:
                im.thumbnail((larg, alt))
                tela.paste(im, (x, y + faixa))
            d.rectangle([x, y, x + larg, y + faixa], fill="black")
            d.text((x + 8, y + 4), f"{hms(t)}  ({caminho.name})", fill="yellow", font=fonte)
        destino = pasta_mosaicos / f"mosaico_{len(gerados) + 1:03d}_{hms(grupo[0][0], 'arquivo')}.jpg"
        tela.save(destino, quality=80)
        gerados.append((grupo[0][0], grupo[-1][0], destino))
    return gerados


# Mesma palavra/expressão (até 40 caracteres) repetida 4+ vezes seguidas: loop típico do Whisper.
REPETICAO = re.compile(r"(\b.{1,40}?)(?:[\s,.]*\1){3,}", re.IGNORECASE)


def energia_por_decimo(pcm: np.ndarray, sr=16000) -> np.ndarray:
    """Volume (RMS) de cada bloco de 0,1s."""
    passo = sr // 10
    return np.sqrt(np.add.reduceat(pcm.astype(np.float64) ** 2, np.arange(0, len(pcm), passo)) / passo)


def limiar_de_fala(pcm: np.ndarray) -> float:
    """Volume acima do qual consideramos que há som: bem acima do ruído de fundo da gravação."""
    return max(0.005, 4 * float(np.percentile(energia_por_decimo(pcm), 10)))


def cortar_nas_pausas(pcm: np.ndarray, sr=16000, minimo=20, maximo=29.5):
    """Divide o áudio em janelas de até `maximo` s, cortando no trecho mais silencioso após `minimo` s."""
    passo = sr // 10
    energia = energia_por_decimo(pcm, sr)
    cortes, ini = [], 0
    while len(pcm) - ini > maximo * sr:
        b0, b1 = (ini + minimo * sr) // passo, int(ini + maximo * sr) // passo
        fim = (b0 + int(np.argmin(energia[b0:b1]))) * passo
        cortes.append((ini, fim))
        ini = fim
    cortes.append((ini, len(pcm)))
    return cortes


def chave_assemblyai():
    """Lê a chave de chave_assemblyai.txt (na raiz) ou da variável ASSEMBLYAI_API_KEY."""
    arquivo = RAIZ / "chave_assemblyai.txt"
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8-sig").splitlines():
            if linha.strip() and not linha.lstrip().startswith("#"):
                return linha.strip()
    return os.environ.get("ASSEMBLYAI_API_KEY")


# A AssemblyAI não tem endpoint de saldo: estimamos somando a duração de tudo que já foi transcrito.
# Conta nova ganha US$ 50; o modelo usado (universal-3-5-pro) + separação de falantes ≈ US$ 0,23/hora.
CREDITO_INICIAL_USD = 50.0
PRECO_HORA_USD = 0.21 + 0.02
CACHE_USO = RAIZ / "analises" / ".uso_assemblyai.json"


def saldo_assemblyai():
    import json
    import urllib.request
    chave = chave_assemblyai()
    if not chave:
        return
    cabecalho = {"authorization": chave}
    obter = lambda url: json.loads(urllib.request.urlopen(
        urllib.request.Request(url, headers=cabecalho), timeout=60).read())
    try:
        duracoes = json.loads(CACHE_USO.read_text()) if CACHE_USO.exists() else {}
        url = "https://api.assemblyai.com/v2/transcript?limit=200&status=completed"
        while url:
            pagina = obter(url)
            for t in pagina["transcripts"]:
                if t["id"] not in duracoes:  # a lista não traz a duração: busca uma vez e guarda
                    duracoes[t["id"]] = obter(t["resource_url"]).get("audio_duration") or 0
            url = pagina["page_details"].get("prev_url") if pagina["transcripts"] else None
        CACHE_USO.parent.mkdir(exist_ok=True)
        CACHE_USO.write_text(json.dumps(duracoes))
    except Exception as e:
        print(f"  (não consegui consultar o uso da AssemblyAI: {type(e).__name__})")
        return
    usadas = sum(duracoes.values()) / 3600
    restantes = max(0.0, CREDITO_INICIAL_USD / PRECO_HORA_USD - usadas)
    print(f"  AssemblyAI: {usadas:.1f} h já transcritas -> restam ~{restantes:.0f} h de áudio grátis "
          f"(estimativa; saldo exato em assemblyai.com/dashboard)")


def limpar_analises_orfas():
    """Manda para a Lixeira as análises cujo vídeo de origem foi apagado."""
    pasta_analises = RAIZ / "analises"
    for pasta in sorted(p for p in pasta_analises.iterdir() if p.is_dir()) if pasta_analises.exists() else []:
        indice = pasta / "INDICE.md"
        if not indice.exists():
            continue
        m = re.search(r"- Arquivo: `(.+?)`", indice.read_text(encoding="utf-8"))
        if m and not Path(m.group(1)).exists():
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "Add-Type -AssemblyName Microsoft.VisualBasic; "
                                "[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($env:ALVO, "
                                "'OnlyErrorDialogs', 'SendToRecycleBin')"],
                               env={**os.environ, "ALVO": str(pasta)}, capture_output=True)
            if r.returncode == 0:
                print(f"  Vídeo apagado -> análise enviada para a Lixeira: {pasta.name}")


def transcrever_assemblyai(video: Path, pasta_tmp: Path, idioma: str, chave: str):
    """Transcrição na nuvem (AssemblyAI), separando quem fala. Retorna None se falhar."""
    import json
    import urllib.request
    print("[4/4] Transcrevendo áudio na AssemblyAI (separando quem fala)...")
    audio = pasta_tmp / "audio.mp3"  # só o áudio, mono e comprimido: sobe rápido
    r = subprocess.run([FFMPEG, "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-b:a", "48k", str(audio)])
    if r.returncode != 0 or not audio.exists():
        print("      Vídeo sem faixa de áudio.")
        return []

    def chamar(caminho, dados=None, json_=None):
        corpo = json.dumps(json_).encode() if json_ is not None else dados
        req = urllib.request.Request(f"https://api.assemblyai.com/v2/{caminho}", data=corpo,
                                     headers={"authorization": chave, "content-type": "application/json"
                                              if json_ is not None else "application/octet-stream"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            return json.loads(resp.read())

    try:
        print(f"      enviando áudio ({audio.stat().st_size // 1_000_000} MB)...", flush=True)
        url = chamar("upload", dados=audio.read_bytes())["upload_url"]
        tarefa = chamar("transcript", json_={"audio_url": url, "language_code": idioma,
                                             "speaker_labels": True, "punctuate": True, "format_text": True})
        print("      processando na nuvem...", flush=True)
        while tarefa["status"] not in ("completed", "error"):
            time.sleep(5)
            tarefa = chamar(f"transcript/{tarefa['id']}")
        if tarefa["status"] == "error":
            raise RuntimeError(tarefa.get("error"))
        return [(u["start"] / 1000, u["end"] / 1000, f"Pessoa {u['speaker']}: {u['text']}")
                for u in tarefa.get("utterances") or []]
    except Exception as e:
        detalhe = e.read().decode(errors="replace")[:200] if hasattr(e, "read") else str(e)[:200]
        print(f"      AssemblyAI falhou ({type(e).__name__}: {detalhe}) — usando a transcrição local")
        return None


def transcrever(video: Path, pasta_tmp: Path, modelo: str, idioma: str, parcial: Path):
    """Retorna lista de (inicio, fim, texto) ou None se não houver motor de transcrição disponível."""
    print("[4/4] Transcrevendo áudio...")
    audio = pasta_tmp / "audio.wav"
    r = subprocess.run([FFMPEG, "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(audio)])
    if r.returncode != 0 or not audio.exists():
        print("      Vídeo sem faixa de áudio.")
        return []

    import wave
    with wave.open(str(audio)) as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768

    # Motor 1: faster-whisper (mais rápido). O áudio é passado como array para não depender da lib "av".
    try:
        import ctranslate2  # noqa: F401 — falha cedo se a DLL estiver bloqueada, antes de mexer em sys.modules
        sys.modules.setdefault("av", type(sys)("av"))
        from faster_whisper import WhisperModel
        m = WhisperModel(modelo, device="auto", compute_type="int8")
        segs, _ = m.transcribe(pcm, language=idioma, vad_filter=False)
        return [(s.start, s.end, s.text.strip()) for s in segs]
    except Exception as e:
        if getattr(sys.modules.get("av"), "__spec__", True) is None:
            del sys.modules["av"]  # o módulo falso de "av" quebraria o transformers no motor 2
        print(f"      faster-whisper indisponível ({type(e).__name__}: {str(e)[:120]})")

    # Motor 2: transformers + PyTorch (o que funciona nesta máquina com Smart App Control).
    try:
        import torch
        from transformers import pipeline
        dispositivo = 0 if torch.cuda.is_available() else -1
        print(f"      usando transformers/PyTorch em {'GPU' if dispositivo == 0 else 'CPU'} (modelo {modelo})")
        asr = pipeline("automatic-speech-recognition", model=f"openai/whisper-{modelo}",
                       device=dispositivo,
                       torch_dtype=torch.float16 if dispositivo == 0 else torch.float32)
        # Cortamos nós mesmos em janelas <30s (nas pausas): o chunking interno perde os horários em áudios longos.
        # Em silêncio o Whisper "inventa" frases ("tchau", "obrigado"...): pulamos janelas sem som
        # e descartamos trechos cujo intervalo não tem som.
        energia, limiar = energia_por_decimo(pcm), limiar_de_fala(pcm)
        tem_som = lambda t0, t1: energia[int(t0 * 10):max(int(t1 * 10), int(t0 * 10) + 1)].max(initial=0) > limiar
        cortes = []
        for a, b in cortar_nas_pausas(pcm):
            blocos_com_som = np.flatnonzero(energia[a // 1600:b // 1600] > limiar)
            if len(blocos_com_som):  # começa a janela onde o som começa, senão o 1º horário sai adiantado
                cortes.append((max(a, a + (int(blocos_com_som[0]) - 3) * 1600), b))
        # Uma janela por vez: mandar todas juntas lota os 2 GB da GPU e o processo "trava" (lento demais).
        # O texto vai sendo gravado em transcricao_parcial.md, para não perder nada se parar no meio.
        falas = []
        with open(parcial, "w", encoding="utf-8") as arq:
            arq.write(f"# Transcrição parcial — {video.name}\n\n")
        inicio = time.time()
        for n, (a, b) in enumerate(cortes, 1):
            try:
                out = asr({"raw": pcm[a:b], "sampling_rate": 16000}, return_timestamps=True,
                          generate_kwargs={"language": idioma, "task": "transcribe", "max_new_tokens": 300})
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                print(f"      trecho {n}: memória da GPU cheia, pulando")
                continue
            antes = len(falas)
            base, fim_janela = a / 16000, b / 16000
            for c in out.get("chunks") or [{"timestamp": (0, None), "text": out["text"]}]:
                ini = base + (c["timestamp"][0] or 0)
                fim_bruto = base + c["timestamp"][1] if c["timestamp"][1] else None
                fim = min(fim_bruto, fim_janela) if fim_bruto else fim_janela
                # trecho que começa no fim da janela e "vaza" para o silêncio de preenchimento = invenção
                vazou = (fim_bruto is None or fim_bruto > fim_janela + 0.5) and ini > fim_janela - 2
                texto = REPETICAO.sub(r"\1", c["text"]).strip()
                if texto.strip(" .,") and not vazou and ini < fim_janela - 0.2 and tem_som(ini, fim):
                    falas.append((ini, fim, texto))
            with open(parcial, "a", encoding="utf-8") as arq:
                arq.writelines(f"[{hms(t)}] {txt}\n" for t, _, txt in falas[antes:])
            gasto = time.time() - inicio
            print(f"      trecho {n}/{len(cortes)} ({hms(base)}) — falta ~{int(gasto / n * (len(cortes) - n) / 60)} min",
                  flush=True)
        return falas
    except Exception as e:
        print(f"      transformers/torch indisponível ({type(e).__name__}: {str(e)[:120]})")

    print("      >> Transcrição pulada. Veja a seção 'Transcrição' no CLAUDE.md para habilitar.")
    return None


def escrever_saidas(pasta: Path, video: Path, dur: float, mantidos, mosaicos, falas, webcam=None):
    rel = lambda p: p.relative_to(pasta).as_posix()

    if falas:
        linhas = [f"# Transcrição — {video.name}\n"]
        linhas += [f"[{hms(a)}] {txt}" for a, b, txt in falas]
        (pasta / "transcricao.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")

    eventos = [(t, 1, f"[{hms(t)}] TELA  {rel(c)}") for t, c in mantidos]
    eventos += [(a, 0, f"[{hms(a)}] FALA  {txt}") for a, b, txt in (falas or [])]
    eventos.sort()
    (pasta / "linha_do_tempo.md").write_text(
        f"# Linha do tempo — {video.name}\n\n" + "\n".join(e[2] for e in eventos) + "\n", encoding="utf-8")

    status_fala = ("não transcrito" if falas is None
                   else "sem fala/áudio" if not falas else f"{len(falas)} trechos em transcricao.md")
    indice = [
        f"# Análise de vídeo — {video.name}",
        "",
        f"- Arquivo: `{video}`",
        f"- Duração: {hms(dur)}",
        f"- Telas únicas: {len(mantidos)} (em `frames/`)",
        f"- Mosaicos: {len(mosaicos)} (em `mosaicos/`, 9 telas cada)",
        f"- Fala: {status_fala}",
    ]
    if webcam:
        indice.append(f"- Webcam: {webcam}; essa área não contou para separar as telas")
    indice += [
        "",
        "## Mosaicos (comece por aqui)",
        "",
    ]
    indice += [f"- {hms(a)} → {hms(b)}: `{rel(p)}`" for a, b, p in mosaicos]
    (pasta / "INDICE.md").write_text("\n".join(indice) + "\n", encoding="utf-8")


PEDIDO_RESUMO = """Leia a análise do vídeo em "{pasta}": INDICE.md e, principalmente, transcricao.md \
(é ali que está a demanda falada). Use os mosaicos/frames só para esclarecer momentos específicos \
(nomes de telas, erros, valores) — no máximo uns 10 arquivos de imagem.

Escreva "{pasta}\\RESUMO.md" em português, para o usuário (quem gravou; veja CLAUDE.local.md, se existir) \
usar sem precisar conversar com você:
1. **Do que se trata** — 3 a 5 linhas: reunião/gravação de quem, sobre o quê.
2. **Participantes** — quem é "Pessoa A", "Pessoa B"... (deduza pelos nomes citados e pelo contexto).
3. **Demandas e tarefas para o usuário** — lista numerada, cada item com horário [hh:mm:ss], o que \
foi pedido, por quem, e detalhes técnicos necessários para executar.
4. **Combinados, prazos e próximos passos** (reuniões, entregas, quem vai fazer o quê), com horário.
5. **Informações técnicas importantes** — sistemas, ambientes, URLs, erros, números, regras de negócio citados.
6. **Lacunas e dúvidas** — o que ficou vago, contraditório ou sem resposta e deveria ser confirmado \
com quem pediu (perguntas prontas para enviar).
7. **Trechos em que a transcrição parece ter errado** palavras importantes (nomes, siglas), com a provável correção.

Seja completo: não deixe de fora nenhum pedido, mesmo pequeno ou dito de passagem. Cite sempre os horários."""


def gerar_resumo(pasta: Path):
    """Pede ao Claude Code (conta do usuário, sem custo extra) para escrever RESUMO.md na pasta da análise."""
    claude = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude.exe")
    if not Path(claude).exists():
        print("      Claude Code não encontrado (instale e faça login: veja o README); RESUMO.md não foi gerado.")
        return
    print("[5/5] Claude escrevendo RESUMO.md (demandas, combinados, lacunas)...", flush=True)
    # O pedido vai pela entrada padrão: argumentos com várias linhas quebram se o claude for um .cmd (npm).
    r = subprocess.run([claude, "-p", "--allowedTools", "Read,Glob,Grep,Write", "--max-turns", "40"],
                       input=PEDIDO_RESUMO.format(pasta=pasta), cwd=RAIZ,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if (pasta / "RESUMO.md").exists():
        print(f"      RESUMO.md pronto.")
    else:
        print(f"      Não consegui gerar o RESUMO.md: {(r.stderr or r.stdout).strip()[:300]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path, nargs="?")
    ap.add_argument("--intervalo", type=float, default=2, help="segundos entre frames amostrados (padrão 2)")
    ap.add_argument("--sensibilidade", type=float, default=0.0003,
                    help="fração de pixels que precisa mudar para contar como tela nova "
                         "(padrão 0.0003; aumente se vierem telas repetidas demais)")
    ap.add_argument("--manter-webcam", action="store_true",
                    help="não procurar webcam: a tela inteira conta para separar as telas")
    ap.add_argument("--sem-transcricao", action="store_true")
    ap.add_argument("--local", action="store_true",
                    help="não usar a AssemblyAI mesmo com chave (transcreve só neste PC)")
    ap.add_argument("--modelo", default="small", help="modelo Whisper: tiny, base, small, medium, large-v3")
    ap.add_argument("--idioma", default="pt")
    ap.add_argument("--saida", type=Path, default=RAIZ / "analises")
    ap.add_argument("--sem-resumo", action="store_true", help="não pedir ao Claude o RESUMO.md")
    ap.add_argument("--so-resumo", action="store_true",
                    help="só refaz o RESUMO.md de um vídeo já analisado (não reprocessa)")
    ap.add_argument("--limpar", action="store_true",
                    help="manda para a Lixeira as análises de vídeos que foram apagados")
    ap.add_argument("--saldo", action="store_true", help="mostra quantas horas grátis restam na AssemblyAI")
    a = ap.parse_args()

    if a.limpar:
        limpar_analises_orfas()
    if a.saldo:
        saldo_assemblyai()
    if a.video is None:
        if not (a.limpar or a.saldo):
            ap.error("informe o vídeo")
        return

    pasta = a.saida / a.video.stem
    if a.so_resumo:
        if not (pasta / "INDICE.md").exists():
            sys.exit(f"Ainda não há análise em {pasta}")
        (pasta / "RESUMO.md").unlink(missing_ok=True)
        gerar_resumo(pasta)
        return

    video = a.video.resolve()
    if not video.exists():
        sys.exit(f"Arquivo não encontrado: {video}")
    dur = duracao(video)
    if pasta.exists():
        shutil.rmtree(pasta)
    (pasta / "frames").mkdir(parents=True)
    (pasta / "mosaicos").mkdir()
    print(f"Vídeo: {video.name} ({hms(dur)}) -> {pasta}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        frames = extrair_frames(video, tmp, a.intervalo)
        webcam = None if a.manter_webcam else detectar_webcam(frames)
        if webcam:
            print(f"      Webcam detectada: {webcam[1]} - essa área não conta para separar as telas.")
        mantidos = frames_unicos(frames, a.intervalo, a.sensibilidade, pasta / "frames",
                                 webcam[0] if webcam else None)
        mosaicos = montar_mosaicos(mantidos, pasta / "mosaicos")
        parcial = pasta / "transcricao_parcial.md"
        falas = None
        chave = None if a.local else chave_assemblyai()
        if not a.sem_transcricao and chave:
            falas = transcrever_assemblyai(video, tmp, a.idioma, chave)
        if not a.sem_transcricao and falas is None:
            falas = transcrever(video, tmp, a.modelo, a.idioma, parcial)

    escrever_saidas(pasta, video, dur, mantidos, mosaicos, falas, webcam[1] if webcam else None)
    if falas is not None:
        parcial.unlink(missing_ok=True)
    if not a.sem_resumo:
        gerar_resumo(pasta)
    print(f"\nPronto: {len(frames)} frames amostrados -> {len(mantidos)} telas únicas, {len(mosaicos)} mosaicos.")
    print(f"Comece por: {pasta / ('RESUMO.md' if (pasta / 'RESUMO.md').exists() else 'INDICE.md')}")


if __name__ == "__main__":
    main()
