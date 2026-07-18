@echo off
setlocal enabledelayedexpansion

:: Renance DevTools Windows Installer

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

echo [ERROR] Python not found. Please install Python from python.org
pause
exit /b 1

:found
cls
echo.
echo   ==========================================
echo    Renance DevTools v3.1 Installer [Windows]
echo   ==========================================
echo.

echo   [1/4] Checking environment...
%PY% -m pip --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    %PY% -m ensurepip --default-pip >nul 2>nul
)

echo   [2/4] Installing dependencies via %PY%...
%PY% -m pip install -e . --quiet 2>nul
if %ERRORLEVEL% NEQ 0 (
    %PY% -m pip install -e .
)

echo   [3/4] Configuring system PATH...
%PY% -m dt_cli.cli setup >nul 2>nul

echo   [4/4] Applying PATH to current session...

:: Auto-apply PATH immediately in current CMD session
set "PATH=%USERPROFILE%\AppData\Roaming\Python\Scripts;%USERPROFILE%\AppData\Local\Programs\Python\Python*\Scripts;%LOCALAPPDATA%\Programs\Python\Python*\Scripts;%PATH%"
for /f "delims=" %%i in ('%PY% -c "import sys, os; print(os.path.join(sys.prefix, 'Scripts'))" 2^>nul') do set "PATH=%%i;%PATH%"
for /f "delims=" %%i in ('%PY% -c "import site; print(os.path.join(site.getuserbase(), 'Scripts'))" 2^>nul') do set "PATH=%%i;%PATH%"

echo.
echo   ==========================================
echo    ✅ INSTALLATION SUCCESSFUL!
echo   ==========================================
echo.
echo   💡 PATH has been set for this session.
echo   🚀 Usage:  Type 'dt help' to explore 235+ commands.
echo.

:: Verify
where dt >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo   ✅ 'dt' command is ready to use now!
) else (
    echo   💡 Close and reopen your terminal if 'dt' is not found.
)
echo.
pause