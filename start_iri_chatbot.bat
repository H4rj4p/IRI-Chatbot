@echo off
setlocal
cd /d "%~dp0"
set PORT=7179
set HOST=127.0.0.1

where python >nul 2>nul
if not errorlevel 1 goto :have_python
where py >nul 2>nul
if not errorlevel 1 goto :have_py

echo Python was not found. Install Python 3 from https://www.python.org/downloads/windows/
echo During installation, select "Add Python to PATH".
pause
exit /b 1

:have_python
set "RUN_PYTHON=python"
goto :ready

:have_py
set "RUN_PYTHON=py -3"
goto :ready

:ready
if not exist "local.settings.json" (
  echo local.settings.json is missing. Running repair_settings.py...
  %RUN_PYTHON% repair_settings.py
  if not exist "local.settings.json" (
    echo Could not create local.settings.json.
    pause
    exit /b 1
  )
)

%RUN_PYTHON% -c "import flask, pyodbc, requests" >nul 2>nul
if errorlevel 1 (
  echo Installing required Python packages...
  %RUN_PYTHON% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Could not install the required Python packages.
    pause
    exit /b 1
  )
)

echo.
echo IMPORTANT: Run this on a PC that can reach SQL Server.
echo If SqlServer is 172.18.0.4 and login handshake fails, set SqlServer to
echo 127.0.0.1,1433 on the SQL Server PC, or the LAN IPv4 from ipconfig.
echo Optional check: python diagnose_sql.py
echo.
echo Starting IRI AI at http://localhost:%PORT%/api/Chat
echo SQL test: http://localhost:%PORT%/api/TestSqlConnection
echo.
start "" "http://localhost:%PORT%/api/Chat"
set PORT=%PORT%
set HOST=%HOST%
%RUN_PYTHON% app.pyw
pause
