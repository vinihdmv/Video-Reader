# Video-Reader — análise de gravações de tela e reuniões

Transforma vídeos `.mp4` (reuniões, gravações de tela de 1h ou mais) em material que o Claude consegue ler:

- **`transcricao.md`**: tudo o que foi falado, com horário e separado por pessoa ("Pessoa A", "Pessoa B"). A transcrição é feita pela AssemblyAI.
- **`RESUMO.md`**: escrito pelo Claude Code. Traz participantes, demandas com horário, combinados, lacunas com perguntas prontas e erros prováveis da transcrição.
- **`mosaicos/` e `frames/`**: as telas que mudaram ao longo do vídeo, com horário. Se houver webcam no canto, ela não conta como "tela nova".

Funciona no **Windows**.

## Instalar com o Claude (recomendado)

1. Tenha o **Claude** instalado e com login feito: o app Claude para desktop (aba *Code*) ou o Claude Code no terminal.
2. Abra uma conversa nova no Claude Code e cole esta mensagem:

   > Clone https://github.com/vinihdmv/Video-Reader.git para a pasta `claude-trabalho` dentro de Documentos. Depois leia o README.md e siga a seção "Passo a passo para o Claude", me orientando em cada parte que depende de mim.

3. O Claude faz o resto. Ele vai parar e pedir a sua ajuda em três momentos:
   - para **aprovar a instalação** dos programas que faltarem (Git, Python, Claude Code);
   - para você **criar a sua conta grátis na AssemblyAI** e colar a sua chave num arquivo;
   - para responder algumas perguntas sobre o seu trabalho, que ajudam o resumo a acertar nomes e siglas.

## Uso no dia a dia

1. Coloque os `.mp4` na pasta `videos/`.
2. Rode o **`ANALISAR VIDEOS.bat`**:
   - no VS Code, com **Ctrl+Shift+B**. Abra no VS Code a pasta `Video-Reader` em *File → Open Folder*, e não a pasta de cima, senão o atalho não acha a tarefa;
   - ou com duplo clique pelo Explorador de Arquivos do Windows. No VS Code, o duplo clique só abre o arquivo para editar.

   O progresso aparece numa **janela própria do Windows**. No fim ela mostra quantas **horas grátis** restam na AssemblyAI e fica aberta até você apertar uma tecla.
3. Para cada vídeo novo, ele:
   - extrai as telas;
   - transcreve o áudio (~1 min);
   - escreve o `RESUMO.md` (~2–5 min), que abre sozinho no Bloco de Notas.
4. Apagou um vídeo de `videos/`? Na próxima execução, a análise dele vai para a **Lixeira**.
5. Para ir além do resumo, abra o Claude nesta pasta e diga: *"lê a análise do vídeo NOME"*.

## Detalhes

- **Custo.** A AssemblyAI dá US$ 50 grátis, sem cartão, o que equivale a ~215 h de áudio. Quando o crédito acaba, ela para de transcrever e não cobra nada. O resumo usa a sua própria conta do Claude.
- **Privacidade.** Só o **áudio** vai para a AssemblyAI. Vídeos, telas, análises, a sua chave e o seu `CLAUDE.local.md` ficam no seu PC e são ignorados pelo git.
- **Transcrição local (opcional, reserva).** Pode ser usada se a AssemblyAI falhar, mas é bem lenta. Para instalar:
  ```
  .venv\Scripts\python.exe -m pip install -r requirements-local.txt
  ```
- **Opções do script.** Estão em `CLAUDE.md` e em `.venv\Scripts\python.exe ferramentas\analisar_video.py --help`.

## Instalar sem o Claude

1. `git clone https://github.com/vinihdmv/Video-Reader.git`
2. Dê duplo clique no `INSTALAR.bat` pelo Explorador de Arquivos. Ele instala o Python se faltar, cria o `.venv`, instala as dependências, abre o `chave_assemblyai.txt` para você colar a chave e confere o Claude Code.
3. Copie `CLAUDE.local.exemplo.md` para `CLAUDE.local.md` e preencha com o seu contexto.

---

## Passo a passo para o Claude

> Esta seção é para o Claude Code de quem está instalando. Siga na ordem e fale com a pessoa em linguagem simples.
> Use PowerShell. Rode os comandos você mesmo. **Não rode o `INSTALAR.bat` nem o `ANALISAR VIDEOS.bat`**: os dois terminam com `pause` e travam o terminal.
> Antes de instalar qualquer programa, diga qual é e peça o "pode". Nunca peça a chave da AssemblyAI no chat e nunca mostre o conteúdo do `chave_assemblyai.txt`.

### 1. Pasta e clone

A pasta Documentos pode estar no OneDrive, então descubra o caminho real:

```powershell
$docs = [Environment]::GetFolderPath('MyDocuments')
$proj = "$docs\claude-trabalho\Video-Reader"
```

- Se `$proj\.git` já existe, atualize com `git -C $proj pull`. Se não existe, crie `$docs\claude-trabalho` e rode `git clone https://github.com/vinihdmv/Video-Reader.git $proj`. O repositório é público, então não pede login.
- Sem Git (`git --version` falha): com o "pode" da pessoa, rode `winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements`. O Windows pode pedir permissão de administrador, e a pessoa aprova. Na mesma sessão, use `& "C:\Program Files\Git\cmd\git.exe"`, porque o PATH só atualiza num terminal novo.
- Depois do clone, se a sua ferramenta permitir, mude a sessão para `$proj`. Em todo caso, use caminhos absolutos.

### 2. Python

- Procure nesta ordem: `py -3 --version`, `python --version` e `$env:LOCALAPPDATA\Programs\Python\Python313\python.exe`.
- **Cuidado:** o `python` em `...\WindowsApps\python.exe` é só um atalho da Microsoft Store. Ele responde "Python não foi encontrado" e **não conta** como Python instalado.
- Sem Python: com o "pode", rode `winget install -e --id Python.Python.3.13 --scope user --accept-package-agreements --accept-source-agreements --disable-interactivity`. Depois use o caminho completo `$env:LOCALAPPDATA\Programs\Python\Python313\python.exe`.

### 3. Ambiente e dependências

```powershell
& <python> -m venv "$proj\.venv"
& "$proj\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& "$proj\.venv\Scripts\python.exe" -m pip install -r "$proj\requirements.txt" --quiet
& "$proj\.venv\Scripts\python.exe" "$proj\ferramentas\analisar_video.py" --help
```

O `--help` precisa mostrar as opções do script. Se mostrar, a instalação está certa. O ffmpeg vem junto no pacote `imageio-ffmpeg`, então não precisa instalar à parte.

### 4. Claude Code no terminal (escreve o RESUMO.md)

- O script chama `claude -p`. Procure com `Get-Command claude` e com `Test-Path "$env:USERPROFILE\.local\bin\claude.exe"`. O app de desktop sozinho pode não deixar o `claude` disponível no terminal.
- Se faltar: com o "pode", rode `irm https://claude.ai/install.ps1 | iex`. Depois peça à pessoa para abrir um terminal, rodar `claude` uma vez e fazer login. Você não faz login por ela.
- Confira com `"Responda só OK" | & "$env:USERPROFILE\.local\bin\claude.exe" -p --max-turns 1`.

### 5. Chave da AssemblyAI (cada pessoa usa a sua)

1. Peça à pessoa para criar uma conta grátis em https://www.assemblyai.com, sem cartão, e copiar a chave em *Dashboard → API Keys*. A conta quem cria é ela, não você.
2. Copie `chave_assemblyai.exemplo.txt` para `chave_assemblyai.txt`, se ainda não existir, e abra no Bloco de Notas: `Start-Process notepad "$proj\chave_assemblyai.txt"`.
3. Peça para ela colar a chave na última linha, salvar e avisar.
4. Confira **sem mostrar** a chave: conte as linhas que não começam com `#` e não estão vazias. Deve haver 1, com cerca de 32 caracteres. Mostre só a contagem e o tamanho.

### 6. Contexto pessoal (`CLAUDE.local.md`)

O `CLAUDE.md` é igual para todos. O que é de cada pessoa fica em `CLAUDE.local.md`, que o git ignora. O Claude Code lê esse arquivo junto com o `CLAUDE.md`, inclusive quando escreve o RESUMO.md. É ele que permite identificar quem fala e corrigir nomes que a transcrição erra.

1. Copie `CLAUDE.local.exemplo.md` para `CLAUDE.local.md`.
2. Faça à pessoa as perguntas que estão no modelo: nome, empresa e área, sistemas com que trabalha, colegas e clientes que aparecem nas reuniões, siglas e nomes que costumam sair errados, e o app de reunião.
3. Preencha com as respostas dela. Se ela não quiser responder alguma, deixe em branco: o arquivo é opcional, e sem ele o resumo deduz tudo pela fala e pelas telas.

### 7. Teste de ponta a ponta

Monte um vídeo curto com voz em português. Use uma pasta curta, porque caminhos com mais de 260 caracteres quebram a voz do Windows:

```powershell
$t = "$env:TEMP\vr-teste"; New-Item -ItemType Directory -Force $t | Out-Null
Add-Type -AssemblyName System.Speech
$voz = New-Object System.Speech.Synthesis.SpeechSynthesizer
$pt = $voz.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'pt*' } | Select-Object -First 1
if ($pt) { $voz.SelectVoice($pt.VoiceInfo.Name) }
$voz.SetOutputToWaveFile("$t\fala.wav")
$voz.Speak("Olá, este é um vídeo de teste do analisador. A demanda é revisar o relatório até sexta-feira.")
$voz.Dispose()
$ff = & "$proj\.venv\Scripts\python.exe" -I -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"
& $ff -hide_banner -loglevel error -y -f lavfi -i "testsrc=size=1280x720:rate=10" -i "$t\fala.wav" -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "$t\teste_instalacao.mp4"
& "$proj\.venv\Scripts\python.exe" "$proj\ferramentas\analisar_video.py" "$t\teste_instalacao.mp4"
& "$proj\.venv\Scripts\python.exe" "$proj\ferramentas\analisar_video.py" --saldo
```

Rode o analisador a partir de `$proj` e espere até ~5 min. Depois confira:
- `analises\teste_instalacao\transcricao.md` tem a frase falada, como "Pessoa A". Se tiver, a chave funciona. Se a transcrição saiu local e lenta, a chave está errada.
- `analises\teste_instalacao\RESUMO.md` existe. Se existir, o Claude Code no terminal funciona.
- O `--saldo` mostra as horas grátis restantes.

Mostre à pessoa um trecho do RESUMO.md. Diga que ela pode apagar `analises\teste_instalacao` quando quiser. Se ela apagar o vídeo de teste, a próxima execução manda a análise para a Lixeira sozinha.

### 8. Orientar a pessoa

Explique a seção "Uso no dia a dia" com as palavras dela. Destaque:
- abrir no VS Code a pasta `Video-Reader`, e não a de cima;
- Ctrl+Shift+B abre uma janela própria;
- os vídeos vão em `videos/`;
- para perguntar sobre um vídeo, é só dizer "lê a análise do vídeo NOME".

### Problemas conhecidos

| Sintoma | Causa e solução |
|---|---|
| `python` responde "Python não foi encontrado" | É o atalho da Microsoft Store. Instale pelo winget (passo 2). |
| Ctrl+Shift+B diz "No build task to run found" | O VS Code está com a pasta de cima aberta. Abra a pasta `Video-Reader`. |
| O terminal trava no fim de um `.bat` | O `.bat` termina com `pause`. Rode o `analisar_video.py` direto (passo 7). |
| `cmd /c "ANALISAR VIDEOS.bat" algo` dá "'ANALISAR' não é reconhecido" | Com mais um argumento, o cmd tira as aspas. Não chame o `.bat` assim. |
| A voz do Windows diz "Não foi possível localizar uma parte do caminho" | Caminho longo demais. Use `$env:TEMP\vr-teste`. |
| A transcrição local falha com DLL bloqueada | É o Smart App Control do Windows. Use a AssemblyAI, porque a transcrição local é só reserva. |
| Se editar um `.bat` | Mantenha as quebras de linha CRLF. Com LF, o cmd não acha os rótulos. |
