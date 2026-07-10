@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if not errorlevel 1 (
  python repair_settings.py
  goto :done
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 repair_settings.py
  goto :done
)

echo Python was not found. Install Python 3 and select Add Python to PATH.
pause
exit /b 1

:done
echo.
pause
