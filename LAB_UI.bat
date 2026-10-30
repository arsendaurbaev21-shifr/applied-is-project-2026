@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m streamlit run labs/lab_1_2/frontend.py --server.address 127.0.0.1 --server.port 8501
pause
