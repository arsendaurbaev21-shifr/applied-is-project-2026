@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
if not exist ".venv\Scripts\python.exe" (echo Run FIRST_RUN.bat first. & pause & exit /b 1)
if not exist ".env" (echo Run FIRST_RUN.bat first. & pause & exit /b 1)
echo QazCargo - http://127.0.0.1:5000
".venv\Scripts\python.exe" -m backend.app
pause
