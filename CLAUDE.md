# Claude Trabalho — análise de gravações de tela

O usuário grava a tela (vídeos .mp4 de minutos até 1h+) com demandas de trabalho e pede ajuda para resolvê-las.
O Claude não assiste vídeo diretamente; esta pasta converte o vídeo em imagens + texto que o Claude lê.

## Contexto do usuário

Quem é o usuário, colegas, clientes e sistemas com que ele trabalha ficam em `CLAUDE.local.md` (fora do git,
cada pessoa cria o seu). Use esse contexto para identificar participantes e corrigir nomes na transcrição.
Sem esse arquivo, deduza tudo pela transcrição e pelas telas.

## Como responder quando ele pedir o resumo/análise de um vídeo

Falar APENAS do vídeo avaliado agora (o que ele nomear, ou a pasta de `analises/` mais recente):
transcrição + mosaicos desse vídeo — participantes, assunto, demandas com horário, final, conclusões.
Não misturar outros vídeos, histórico da conversa nem funcionamento das ferramentas.

## Instalação em outro computador

`git clone` + `INSTALAR.bat` (Python, .venv, dependências, chave, checagem do Claude Code) — ver README.md.
`chave_assemblyai.txt`, `CLAUDE.local.md`, `videos/` e `analises/` não vão para o git (.gitignore).
A transcrição local é opcional (`requirements-local.txt`).

## Estrutura

- `ANALISAR VIDEOS.bat` — o usuário roda sozinho: clique duplo processa os .mp4 novos de `videos/`
  (pula os que já têm `analises/<nome>/INDICE.md`); ou arrastar .mp4 sobre ele.
  Se o usuário pedir para "ler a análise" de um vídeo já processado, NÃO rodar de novo: ir direto ao INDICE.md.
  O usuário usa o VS Code, onde duplo clique só ABRE o .bat: lá ele roda com Ctrl+Shift+B
  (tarefa "Analisar videos" em `.vscode/tasks.json`) ou pelo Explorador de Arquivos do Windows.
  A tarefa faz `Start-Process` no .bat (igual a duplo clique): abre uma janela própria do Windows, não o
  terminal do VS Code, e ela fica aberta no `pause` final mostrando o saldo. Não usar `cmd /c "ANALISAR VIDEOS.bat" arg`:
  com mais um argumento o cmd tira as aspas e quebra no espaço do nome. O VS Code precisa estar com a pasta
  `Video-Reader` aberta (não a pasta de cima), senão o Ctrl+Shift+B não acha a tarefa.
  O .bat começa com `--limpar` (análise cujo vídeo de origem — linha "Arquivo:" do INDICE.md — não existe mais
  vai para a Lixeira) e termina com `--saldo` (horas grátis restantes na AssemblyAI; estimativa = US$ 50 /
  US$ 0,23 por hora − duração de tudo já transcrito, guardada em `analises/.uso_assemblyai.json`).
  ATENÇÃO: o .bat precisa ter quebras de linha CRLF. Com LF o cmd não acha os rótulos (:analisar) e não roda nada;
  depois de editar, reconverter para CRLF.
- `videos/` — onde o usuário coloca os .mp4 (pode também passar qualquer caminho)
- `ferramentas/analisar_video.py` — prepara o vídeo
- `analises/<nome-do-video>/` — resultado (gerado; pode ser apagado e refeito)
- `.venv/` — Python com as dependências (`requirements.txt`)

## Fluxo quando o usuário pedir para analisar um vídeo

1. Rodar (PowerShell, na raiz do projeto; vídeos longos levam alguns minutos, use timeout alto ou background):
   `.venv\Scripts\python.exe ferramentas\analisar_video.py "<caminho do .mp4>"`
2. Ler `analises/<nome>/INDICE.md`.
3. Se existir `transcricao.md`, ler — normalmente é onde está a demanda falada.
4. Ler os mosaicos em ordem (cada um = 9 telas com horário) para entender o fluxo do vídeo.
5. Abrir frames individuais de `frames/` em resolução maior só quando precisar ler detalhes
   (texto pequeno, mensagens de erro, valores, campos de formulário).
6. Responder citando horários (ex.: "em 00:12:34 aparece o erro X") e então ajudar a resolver a tarefa.

Para vídeos muito longos, prefira delegar a leitura dos mosaicos por trechos a subagentes
(ex.: um por mosaico ou por bloco de 10 min) e pedir resumos com horários, para não lotar o contexto.

## Ajustes do script

- `--intervalo 2` — segundos entre frames amostrados. Menor = pega mudanças rápidas, mais trabalho.
- `--sensibilidade 0.0003` — quanto da tela precisa mudar para virar "tela nova".
  Muitas telas quase iguais (ex.: cursor se mexendo) → aumente (0.001). Perdendo mudanças pequenas → diminua.
- Webcam: detectada sozinha (`detectar_webcam`) e tirada da comparação de telas; os frames salvos continuam
  inteiros. Critério: blocos de 20x20 px que mudam em >30% dos pares "calmos" (resto da tela parado), região
  ligada de ≥6 blocos, total ≤25% da tela. Aparece no INDICE.md ("- Webcam: ..."). `--manter-webcam` desliga.
  Teste (60s, tela troca 1x, webcam animada no canto): 2 telas com a detecção, 30 sem.
- `--sem-transcricao`, `--modelo small|medium|large-v3`, `--idioma pt`.

## RESUMO.md automático (Claude Code em modo `-p`, conta do usuário, sem custo de API)

No fim, o script chama `claude -p` (em `~\.local\bin\claude.exe`) com `PEDIDO_RESUMO` e ele escreve
`analises/<nome>/RESUMO.md`: participantes, demandas com horário, combinados, info técnica, lacunas com
perguntas prontas, erros prováveis da transcrição. ~2 min para 20 min de vídeo. O .bat abre o RESUMO no Bloco de Notas.
Refazer só o resumo: `analisar_video.py "<video>" --so-resumo`. Pular: `--sem-resumo`.
Quando o usuário pedir para "ler a análise", comece pelo RESUMO.md (se existir) e confira na transcricao.md.

## Transcrição principal: AssemblyAI (nuvem, grátis com os US$ 50 de crédito inicial, sem cartão)

Se `chave_assemblyai.txt` (raiz) tiver uma chave, o script envia só o áudio (mp3 mono 48k, ~7 MB por 20 min)
para a AssemblyAI, com `speaker_labels`: a transcrição sai como "Pessoa A: …", "Pessoa B: …".
Ao ler, deduza pelo contexto/telas quem é cada pessoa (ex.: o usuário, o cliente) e diga isso ao usuário.
Se a API falhar (chave inválida, sem crédito, sem internet), cai sozinho para a transcrição local.
`--local` força a transcrição local. Nunca ler/mostrar a chave em conversa.

## Transcrição local (reserva; via transformers + PyTorch CUDA, na GPU)

(Notas abaixo são do notebook pessoal; em outro PC, conferir se `requirements-local.txt` foi instalado.)
Lenta neste notebook: a GPU MX550 fica limitada pelo Windows (SW Power Cap / SW Thermal, 300 de 2100 MHz),
então 20 min de vídeo levaram ~1h40. As janelas vão uma por vez (todas juntas lotavam os 2 GB e travavam)
e o texto é salvo aos poucos em `transcricao_parcial.md`.

O Windows tem Smart App Control ligado:
- `faster-whisper`/WhisperX (ctranslate2) → DLL bloqueada; o script tenta e cai para o motor 2.
- `transformers` + `torch==2.15.0+cu132` na GPU NVIDIA MX550 (2 GB, fp16) → funciona
  (instalado em 2026-10-29; o import do torch falhou uma vez logo após instalar e depois passou).

Proteções contra "alucinação" do Whisper (frases inventadas em silêncio), já no script:
janelas cortadas nas pausas, janelas sem som não vão ao modelo, trechos em silêncio ou que
"vazam" para o preenchimento de 30s são descartados, loops de repetição são colapsados.

Velocidade medida (modelo `small`, GPU): 3min07 de vídeo em 106s (~0,6x) → vídeo de 1h ≈ 35 min;
sempre rodar em background (CPU era ~1,6x).
Mais rápido com `--modelo base` (erra mais palavras).

## Complemento: plugin "watch" (github.com/bradautomates/claude-video) — instalado

Instalado em 2026-10-29 (escopo de usuário, v0.3.2), configurado `--engine local --backend none`
(nunca envia vídeo ao Google; fala vem das legendas nativas do site). Dependências via winget: ffmpeg, yt-dlp, Deno.

Quando usar cada um:
- **Gravações de tela locais do usuário → `analisar_video.py`** (transcrição na GPU, todas as telas que mudam).
- **Links (YouTube etc.) → skill watch**; para analisar a fundo, dá para rodar `analisar_video.py`
  no `video.mp4` que o watch baixa.

Comparação real (vídeo de 10min do YouTube, com webcam do apresentador no canto):
- watch: 27s, 19 telas, mas nenhuma entre 01:48 e 05:54 — perdeu 4 min de tela do tutorial.
- analisar_video.py: 37s, 321 telas (nenhuma descartada: a webcam muda todo frame) — medido antes da
  detecção de webcam existir.
Transcrição local do watch (WhisperX/ctranslate2) é bloqueada pelo Smart App Control aqui.
