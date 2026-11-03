@echo off
rem Prepara este computador para usar o ANALISAR VIDEOS.bat. Pode rodar mais de uma vez sem problema.
chcp 65001 >nul
cd /d "%~dp0"
title Instalador - Analisador de videos

echo.
echo [1/4] Procurando o Python...
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    python --version >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo       Python nao encontrado. Instalando o Python 3.13 pelo winget...
    winget install -e --id Python.Python.3.13 --scope user --accept-package-agreements --accept-source-agreements
    if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
)
if not defined PY (
    echo  *** Nao consegui instalar o Python. Instale em https://www.python.org/downloads/ e rode este arquivo de novo.
    goto fim
)
%PY% --version

echo.
echo [2/4] Criando o ambiente .venv e instalando as dependencias...
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  *** Falha ao instalar as dependencias. Veja a mensagem acima.
    goto fim
)
".venv\Scripts\python.exe" "ferramentas\analisar_video.py" --help >nul
if errorlevel 1 (
    echo  *** O script nao abriu. Veja a mensagem acima.
    goto fim
)
echo       OK

echo.
echo [3/4] Chave da AssemblyAI (transcricao rapida na nuvem)...
if not exist "chave_assemblyai.txt" copy "chave_assemblyai.exemplo.txt" "chave_assemblyai.txt" >nul
findstr /v /r /c:"^#" /c:"^$" "chave_assemblyai.txt" >nul
if errorlevel 1 (
    echo       FALTA a chave: abrindo chave_assemblyai.txt - cole a chave na ultima linha e salve.
    start "" notepad "chave_assemblyai.txt"
) else (
    echo       OK, chave encontrada.
)

echo.
echo [4/4] Claude Code (escreve o RESUMO.md de cada video)...
set "CLAUDE_OK="
where claude >nul 2>nul && set "CLAUDE_OK=1"
if exist "%USERPROFILE%\.local\bin\claude.exe" set "CLAUDE_OK=1"
if defined CLAUDE_OK (
    echo       OK, Claude Code encontrado.
) else (
    echo       Claude Code NAO encontrado. Sem ele os videos sao analisados, mas sem o RESUMO.md.
    echo       Instale abrindo o PowerShell e rodando:  irm https://claude.ai/install.ps1 ^| iex
    echo       e depois rode "claude" uma vez para fazer login.
)

echo.
echo Pronto! Coloque os .mp4 na pasta "videos" e rode o ANALISAR VIDEOS.bat
echo (no VS Code: Ctrl+Shift+B; ou duplo clique pelo Explorador de Arquivos).

:fim
echo.
pause
