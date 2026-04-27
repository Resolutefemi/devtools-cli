@echo off
setlocal

:: 1. Try Ariyo's specific Store Python first (since 'python' is MSYS2 and broken)
set ARIYO_PY="C:\Users\ariyo\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe"
if exist %ARIYO_PY% (
    set PY=%ARIYO_PY%
    goto :run
)

:: 2. Fallback to standard names for future/other users
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PY=python
    goto :run
)

where python3 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PY=python3
    goto :run
)

echo ❌ Python not found.
exit /b 1

:run
%PY% -m dt_cli.cli %*
