@echo off
cls
echo.

netstat -ano | find ":11434" >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] Ollama is already running.
) else (
    echo [INFO] Starting Ollama...
    start /B ollama serve
    timeout /t 8 /nobreak >nul
)

ollama list | findstr "qwen2.5-coder" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Pulling qwen2.5-coder:7b...
    ollama pull qwen2.5-coder:7b
    echo [OK] Model ready.
) else (
    echo [OK] qwen2.5-coder is ready.
)

echo.
echo [INFO] Starting server...
echo.

cls
python server.py

echo.
echo [INFO] Server has stopped.
pause