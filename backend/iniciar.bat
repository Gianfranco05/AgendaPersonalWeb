@echo off
title Vida Personal
cd /d "%~dp0"
echo.
echo ========================================
echo    Vida Personal - Arrancando...
echo ========================================
echo.
echo Abriendo navegador en http://127.0.0.1:8000
echo Presiona Ctrl+C para detener
echo.
start http://127.0.0.1:8000
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause
