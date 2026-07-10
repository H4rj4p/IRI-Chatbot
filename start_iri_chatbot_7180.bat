@echo off
setlocal
cd /d "%~dp0"
set PORT=7180

where py >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3 from https://www.python.org/downloads/windows/
  echo During installation, select "Add Python to PATH".
  pause
  exit /b 1
)

if not exist "local.settings.json" (
  echo local.settings.json is missing.
  echo Copy local.settings.example.json to local.settings.json and enter your SQL Server details.
  pause
  exit /b 1
)

py -3 -c "import flask, pyodbc, requests" >nul 2>nul
if errorlevel 1 (
  echo Installing required Python packages...
  py -3 -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Could not install the required Python packages.
    pause
    exit /b 1
  )
)

echo Starting IRI AI at http://localhost:%PORT%/api/Chat
py -3 app.pyw
pause
