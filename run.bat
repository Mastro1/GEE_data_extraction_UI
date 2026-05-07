@echo off
SETLOCAL EnableDelayedExpansion

SET VENV_DIR=.venv

IF NOT EXIST "%VENV_DIR%" (
    echo First run detected. Launching installer...
    python install.py --from-runbat
    IF ERRORLEVEL 1 (
        echo Installation failed.
        pause
        exit /b 1
    )
)

call %VENV_DIR%\Scripts\activate.bat

echo Starting application...
python run.py %*
IF ERRORLEVEL 1 (
    echo.
    echo Application exited with an error.
    pause
)
