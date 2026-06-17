@echo off
setlocal
cd /d "%~dp0"

echo === IRI Chatbot ===

where dotnet >nul 2>&1
if errorlevel 1 (
  echo ERROR: .NET SDK not found. Install .NET 8 from https://dotnet.microsoft.com/download
  exit /b 1
)

if not exist local.settings.json (
  echo ERROR: local.settings.json is missing.
  echo Run: copy local.settings.example.json local.settings.json
  echo Then edit it with your MySQL password and OpenAI key.
  exit /b 1
)

echo Building...
dotnet build IriChatbotFunction.csproj
if errorlevel 1 exit /b 1

echo.
echo Starting app...
echo Open in browser: http://localhost:7179/api/Chat
echo Press Ctrl+C to stop.
echo.

where func >nul 2>&1
if not errorlevel 1 (
  echo Using global func
  func start --port 7179
  exit /b 0
)

echo func not found - starting without it
set ASPNETCORE_URLS=http://localhost:7179
dotnet exec bin\Debug\net8.0\IriChatbotFunction.dll
