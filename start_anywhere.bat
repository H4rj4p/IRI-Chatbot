@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set PORT=7179
set HOST=0.0.0.0

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
  echo Creating local.settings.json...
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
echo ============================================================
echo  IRI AI - use from ANY device
echo ============================================================
echo  1. This window must stay open on the SQL Server PC.
echo  2. The app connects to SQL on this machine ^(127.0.0.1^).
echo  3. Open the LAN URL or Cloudflare URL from phone/laptop.
echo ============================================================
echo.

REM Start the Flask app in a new window
start "IRI AI Chatbot" cmd /k "cd /d \"%~dp0\" && set PORT=%PORT% && set HOST=%HOST% && %RUN_PYTHON% app.pyw"

timeout /t 3 /nobreak >nul

echo Checking SQL connection...
%RUN_PYTHON% diagnose_sql.py
echo.

REM Prefer cloudflared if installed for internet access from any device
where cloudflared >nul 2>nul
if not errorlevel 1 (
  echo Starting Cloudflare quick tunnel so any device can open the chat...
  echo Leave this window open. Look for the https://....trycloudflare.com URL.
  echo.
  cloudflared tunnel --url http://127.0.0.1:%PORT%
  goto :eof
)

echo cloudflared is not installed.
echo.
echo Same Wi-Fi devices: open http://THIS-PC-LAN-IP:%PORT%/api/Chat
echo Find THIS-PC-LAN-IP with: ipconfig
echo.
echo For internet access from any device, install Cloudflare tunnel:
echo   https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
echo Then re-run start_anywhere.bat
echo.
echo App window should already be running. Press any key to exit this helper.
pause
