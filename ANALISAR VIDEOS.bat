@echo off
rem Duas formas de usar:
rem   1) Clique duplo: analisa todos os .mp4 da pasta "videos" que ainda nao foram analisados.
rem   2) Arraste um ou mais .mp4 (de qualquer pasta) e solte em cima deste arquivo.
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
title Analisador de videos

rem Analises de videos que voce apagou vao para a Lixeira
".venv\Scripts\python.exe" "ferramentas\analisar_video.py" --limpar

if "%~1"=="" goto pasta_videos

:arrastados
if "%~1"=="" goto fim
call :analisar "%~1"
shift
goto arrastados

:pasta_videos
set ACHOU=0
for %%V in ("videos\*.mp4") do (
    set ACHOU=1
    if exist "analises\%%~nV\INDICE.md" (
        echo Ja analisado, pulando: %%~nxV
    ) else (
        call :analisar "%%~fV"
    )
)
if "%ACHOU%"=="0" echo Nenhum .mp4 na pasta "videos". Coloque os videos la ou arraste-os sobre este arquivo.
goto fim

:analisar
echo.
echo ============================================================
echo  Analisando: %~nx1
echo ============================================================
".venv\Scripts\python.exe" "ferramentas\analisar_video.py" "%~1"
if errorlevel 1 (
    echo.
    echo  *** ERRO ao analisar %~nx1 - veja a mensagem acima. ***
    echo  Se o video ainda estava sendo copiado, espere a copia terminar e rode de novo.
)
if exist "analises\%~n1\RESUMO.md" start "" notepad "analises\%~n1\RESUMO.md"
exit /b

:fim
echo.
".venv\Scripts\python.exe" "ferramentas\analisar_video.py" --saldo
echo.
echo Concluido. Resultados na pasta "analises".
echo Cada video tem um RESUMO.md (demandas, combinados, duvidas) e a transcricao.md completa.
echo Para ir alem, abra o Claude nesta pasta e diga: "le a analise do video NOME".
pause
