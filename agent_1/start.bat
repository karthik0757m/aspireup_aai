@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run setup: creating a local Python environment...
  py -3 -m venv .venv
  if errorlevel 1 goto error
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
goto :eof
:error
echo Setup failed. Install Python 3.11 or newer with the Python launcher, then try again.
pause
