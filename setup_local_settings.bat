@echo off
setlocal
cd /d "%~dp0"

if not exist "local.settings.example.json" (
  echo local.settings.example.json is missing.
  pause
  exit /b 1
)

copy /Y "local.settings.example.json" "local.settings.json" >nul
echo.
echo Updated local.settings.json with the saved OpenAI key and SQL Server settings.
echo.
echo NEXT: open local.settings.json and replace YOUR_PASSWORD with your SQL password
echo in BOTH SqlPassword and SqlConnectionString.
echo.
echo Then run: python app.pyw
echo.
pause
