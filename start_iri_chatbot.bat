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
  if exist "local.settings.example.json" (
    echo Creating local.settings.json from local.settings.example.json...
    copy /Y "local.settings.example.json" "local.settings.json" >nul
  ) else (
    echo local.settings.json is missing.
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
echo IMPORTANT: This chatbot must run on a PC that can reach SQL Server.
echo 172.18.0.4 is usually Docker/internal and often fails from another machine.
echo On the SQL Server PC, run ipconfig and put the Ethernet/Wi-Fi IPv4 into
echo local.settings.json as SqlServer, e.g. 192.168.1.50,1433
echo.
echo Starting IRI AI at http://localhost:%PORT%/api/Chat
echo SQL test: http://localhost:%PORT%/api/TestSqlConnection
echo.
start "" "http://localhost:%PORT%/api/Chat"
set PORT=%PORT%
set HOST=%HOST%
%RUN_PYTHON% app.pyw
pause
