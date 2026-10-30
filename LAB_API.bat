@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m uvicorn labs.lab_1_2.main:app --host 127.0.0.1 --port 8000
pause
