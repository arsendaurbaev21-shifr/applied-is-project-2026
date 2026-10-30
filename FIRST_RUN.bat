@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
where py >nul 2>nul
if errorlevel 1 (echo Install Python from python.org with the Python launcher. & pause & exit /b 1)
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if errorlevel 1 (pause & exit /b 1)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (pause & exit /b 1)
".venv\Scripts\python.exe" -m backend.install
pause
