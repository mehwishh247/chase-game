@echo off
echo [1/3] Checking for Python...
where python >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python not found. Please install Python 3.10+ and add it to PATH.
    pause
    exit /b
)

echo [2/3] Installing requirements...
REM Uncomment the next line if you're using a requirements.txt file
pip install -r requirements.txt

echo [3/3] Launching game...
REM Run the main script
python main.py

pause
