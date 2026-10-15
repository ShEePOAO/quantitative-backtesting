@echo off
setlocal
cd /d "%~dp0"
echo [Quant Studio] Installing dependencies...
python -m pip install -r requirements.txt
echo [Quant Studio] Starting server at http://127.0.0.1:8050
start "" /b cmd /c "timeout /t 6 /nobreak >nul & start http://127.0.0.1:8050"
python server.py
