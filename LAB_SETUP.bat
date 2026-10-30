@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -m venv .venv
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install -r requirements-labs.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m labs.lab_1_2.seed
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m labs.lab_1_2.verify_db
pause
