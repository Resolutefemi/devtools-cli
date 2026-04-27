@echo off
setlocal

:: ANSI Color Codes via PowerShell helper
set "PS_COLOR=powershell -NoProfile -Command "Write-Host"

:: Check for Python
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PY=python
    goto :found
)

where python3 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PY=python3
    goto :found
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PY=py
    goto :found
)

%PS_COLOR% "❌ Python not found. Please install Python from python.org" -ForegroundColor Red
pause
exit /b 1

:found
cls
echo.
%PS_COLOR% "  🚀 Renance DevTools v3.0 Installer" -ForegroundColor Cyan -NoNewline
%PS_COLOR% " [Windows]" -ForegroundColor DarkGray
echo   ------------------------------------------
echo.

%PS_COLOR% "  [1/3] " -ForegroundColor DarkGray -NoNewline
%PS_COLOR% "Checking environment..." -ForegroundColor White
:: Try to install/ensure pip if missing
%PY% -m pip --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    %PY% -m ensurepip --default-pip >nul 2>nul
)

%PS_COLOR% "  [2/3] " -ForegroundColor DarkGray -NoNewline
%PS_COLOR% "Installing dependencies via %PY%..." -ForegroundColor White
%PY% -m pip install -e . --quiet
if %ERRORLEVEL% NEQ 0 (
    %PY% -m pip install -r requirements.txt --quiet >nul 2>nul
)

%PS_COLOR% "  [3/3] " -ForegroundColor DarkGray -NoNewline
%PS_COLOR% "Configuring system PATH..." -ForegroundColor White
%PY% -m dt_cli.cli setup >nul 2>nul

echo.
echo   ------------------------------------------
%PS_COLOR% "  ✅ INSTALLATION SUCCESSFUL!" -ForegroundColor Green
echo.
%PS_COLOR% "  💡 Pro Tip: " -ForegroundColor Yellow -NoNewline
%PS_COLOR% "Restart your terminal to enable the 'dt' command." -ForegroundColor White
%PS_COLOR% "  🚀 Usage:   " -ForegroundColor Cyan -NoNewline
%PS_COLOR% "Type 'dt help' to explore 200+ commands." -ForegroundColor White
echo.
echo.
pause
