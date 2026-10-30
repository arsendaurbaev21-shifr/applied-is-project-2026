@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
".venv\Scripts\python.exe" -m backend.migrate
pause
