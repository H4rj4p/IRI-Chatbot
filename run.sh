#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== IRI Chatbot ==="

if ! command -v dotnet >/dev/null 2>&1; then
  echo "ERROR: .NET SDK not found. Install .NET 8 from https://dotnet.microsoft.com/download"
  exit 1
fi

if [ ! -f local.settings.json ]; then
  echo "ERROR: local.settings.json is missing."
  echo "Run: cp local.settings.example.json local.settings.json"
  echo "Then edit it with your MySQL IP, password, and OpenAI key."
  exit 1
fi

echo "Building..."
dotnet build IriChatbotFunction.csproj

echo ""
echo "Starting app..."
echo "Open in browser: http://localhost:7179/api/Chat"
echo "Press Ctrl+C to stop."
echo ""

if [ -x ".tools/func/func" ]; then
  echo "Using local Azure Functions tools (.tools/func/func)"
  .tools/func/func start --port 7179
elif command -v func >/dev/null 2>&1; then
  echo "Using global func"
  func start --port 7179
else
  echo "func not found — starting without it"
  export ASPNETCORE_URLS="http://localhost:7179"
  dotnet exec bin/Debug/net8.0/IriChatbotFunction.dll
fi
