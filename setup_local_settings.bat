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
echo Updated local.settings.json with SQL Server and OpenAI settings:
echo   Server:   172.18.0.4,1433
echo   Database: Prohance
echo   User:     VMWinSQLS
echo   Password: configured
echo.
echo If 172.18.0.4 is unreachable from your PC, on the SQL Server machine
echo run ipconfig and put the Ethernet/Wi-Fi IPv4 into SqlServer instead.
echo.
echo Then run: python app.pyw
echo Test:     http://localhost:7179/api/TestSqlConnection
echo Chat:     http://localhost:7179/api/Chat
echo.
pause
