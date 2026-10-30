@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
if not exist ".venv\Scripts\python.exe" (echo Run FIRST_RUN.bat first. & pause & exit /b 1)
".venv\Scripts\python.exe" -m backend.manage admin
pause
