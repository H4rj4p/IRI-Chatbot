@echo off
setlocal
cd /d "%~dp0"
set PORT=7180
set HOST=127.0.0.1
set OPEN_BROWSER=1

where python >nul 2>nul
if not errorlevel 1 (
  set "RUN_PYTHON=python"
  goto :ready
)
where py >nul 2>nul
if not errorlevel 1 (
  set "RUN_PYTHON=py -3"
  goto :ready
)

echo Python was not found. Install Python 3 and select Add Python to PATH.
pause
exit /b 1

:ready
if not exist "local.settings.json" (
  echo local.settings.json is missing. Running repair_settings.py...
  %RUN_PYTHON% repair_settings.py
)

%RUN_PYTHON% -c "import flask, pyodbc, requests" >nul 2>nul
if errorlevel 1 (
  echo Installing required Python packages...
  %RUN_PYTHON% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Could not install packages.
    pause
    exit /b 1
  )
)

echo.
echo Starting IRI AI on http://localhost:%PORT%/api/Chat
echo The browser should open automatically. Leave this window open.
echo.
set PORT=%PORT%
set HOST=%HOST%
set OPEN_BROWSER=%OPEN_BROWSER%
%RUN_PYTHON% app.pyw
pause
