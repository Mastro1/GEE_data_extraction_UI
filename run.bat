@echo off
SETLOCAL EnableDelayedExpansion

SET VENV_DIR=.venv
SET REQS_FILE=requirements.txt

IF NOT EXIST "%VENV_DIR%" (
    echo Creating virtual environment in %VENV_DIR%...
    python -m venv %VENV_DIR%
    IF ERRORLEVEL 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
    
    echo Activating environment and installing dependencies...
    call %VENV_DIR%\Scripts\activate.bat
    python -m pip install --upgrade pip
    IF EXIST "%REQS_FILE%" (
        pip install -r %REQS_FILE%
    ) ELSE (
        echo Warning: requirements.txt not found. Skipping dependency installation.
    )
    
    IF ERRORLEVEL 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
) ELSE (
    call %VENV_DIR%\Scripts\activate.bat
)

echo Starting application...
python run.py %*
IF ERRORLEVEL 1 (
    echo.
    echo Application exited with an error.
    pause
)
