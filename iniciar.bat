@echo off
title Servidor Ezetec - Sistema de OS
cls
echo ===================================================
echo           INICIANDO SISTEMA DA EZETEC              
echo ===================================================
echo.

:: Garante que o prompt está na mesma pasta deste arquivo .bat
cd /d "%~dp0"

:: Verifica e instala o Flask caso não esteja presente (silenciosamente)
echo [1/3] Verificando dependencias do sistema...
python -m pip install flask --quiet

:: Dá um comando para abrir o navegador padrão no endereço do sistema
echo [2/3] Abrindo o painel de controle no navegador...
start http://127.0.0.1:5000

:: Inicia o servidor Python
echo [3/3] Servidor Flask online! Nao feche esta janela.
echo ===================================================
echo.
python app.py

pause