@echo off
setlocal

:: Find Python (python, then python3)
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