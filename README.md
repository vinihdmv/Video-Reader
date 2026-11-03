# Claude Trabalho — análise de gravações de tela e reuniões

Transforma vídeos `.mp4` (reuniões, gravações de tela de 1h ou mais) em material que o Claude consegue ler:

- **`transcricao.md`**: tudo o que foi falado, com horário e separado por pessoa ("Pessoa A", "Pessoa B"). A transcrição é feita pela AssemblyAI.
- **`RESUMO.md`**: escrito pelo Claude Code. Traz participantes, demandas com horário, combinados, lacunas com perguntas prontas e erros prováveis da transcrição.
- **`mosaicos/` e `frames/`**: as telas que mudaram ao longo do vídeo, com horário.

## Instalação num computador novo (uma vez)

1. **Baixar o projeto**:
   ```
   git clone https://github.com/<seu-usuario>/claude-trabalho.git
   ```
   Ou, no VS Code: *Clone Repository*.
2. **Rodar o `INSTALAR.bat`**, com duplo clique pelo Explorador de Arquivos do Windows. Ele:
   - instala o Python, se faltar;
   - cria o `.venv` e instala as dependências;
   - abre o `chave_assemblyai.txt` para você colar a chave;
   - confere se o Claude Code está instalado.
3. **Colar a chave da AssemblyAI** em `chave_assemblyai.txt`. Pode ser a mesma chave do outro PC: está em https://www.assemblyai.com/dashboard, no menu *API Keys*.
   Esse arquivo **não vai para o GitHub**, de propósito.
4. **Claude Code** instalado e com login feito. Se o instalador avisar que falta:
   ```
   irm https://claude.ai/install.ps1 | iex
   ```
   Rode isso no PowerShell e depois rode `claude` uma vez para entrar na conta.

## Uso no dia a dia

1. Coloque os `.mp4` na pasta `videos/`.
2. Rode o **`ANALISAR VIDEOS.bat`**: no VS Code, **Ctrl+Shift+B**; ou duplo clique pelo Explorador de Arquivos.
   No VS Code, o duplo clique só abre o arquivo para editar.
   Nos dois casos o progresso aparece numa **janela própria do Windows**, que fica aberta no fim mostrando o saldo da AssemblyAI até você apertar uma tecla.
   Para o Ctrl+Shift+B funcionar, abra no VS Code a pasta do projeto (*File → Open Folder*), e não a pasta de cima.
3. Para cada vídeo novo, ele:
   - extrai as telas;
   - transcreve o áudio (~1 min);
   - escreve o `RESUMO.md` (~2–5 min), que abre sozinho no fim.

   No fim, mostra também quantas **horas grátis** ainda restam na AssemblyAI.
4. Apagou um vídeo de `videos/`? Na próxima execução, a análise dele vai para a **Lixeira**.
5. Para ir além do resumo, abra o Claude nesta pasta e diga: *"lê a análise do vídeo NOME"*.

## Detalhes

- **Custo.** A AssemblyAI dá US$ 50 grátis, sem cartão, o que equivale a ~215 h de áudio; quando o crédito acaba, ela para de transcrever e não cobra nada. O resumo usa a sua própria conta do Claude.
- **Privacidade.** Só o **áudio** vai para a AssemblyAI. Vídeos, telas e análises ficam no PC e são ignorados pelo git.
- **Transcrição local (opcional, reserva).** Pode ser usada se a AssemblyAI falhar, mas é bem lenta. Para instalar:
  ```
  .venv\Scripts\python.exe -m pip install -r requirements-local.txt
  ```
- **Opções do script.** Estão em `CLAUDE.md` e em `.venv\Scripts\python.exe ferramentas\analisar_video.py --help`.
