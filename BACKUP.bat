@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -m backend.manage backup
pause
