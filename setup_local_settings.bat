@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if not errorlevel 1 (
  set "RUN_PYTHON=python"
  goto :run
)
where py >nul 2>nul
if not errorlevel 1 (
  set "RUN_PYTHON=py -3"
  goto :run
)

echo Python was not found. Install Python 3 and Add to PATH.
pause
exit /b 1

:run
%RUN_PYTHON% repair_settings.py
if errorlevel 1 (
  echo Could not write local.settings.json
  pause
  exit /b 1
)

echo.
echo local.settings.json is ready with Prohance SQL + OpenAI settings.
echo Next: python diagnose_sql.py
echo Then:  python app.pyw
echo.
pause
