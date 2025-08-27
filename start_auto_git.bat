@echo off
echo Starting Git Auto-commit System...
cd /d "%~dp0"

REM Try different Python installations
if exist "C:\python38_32bit\python.exe" (
    echo Using Python 3.8 32-bit
    "C:\python38_32bit\python.exe" -m pip install watchdog --quiet
    "C:\python38_32bit\python.exe" auto_git.py
) else if exist "C:\Python38\python.exe" (
    echo Using Python 3.8
    "C:\Python38\python.exe" -m pip install watchdog --quiet  
    "C:\Python38\python.exe" auto_git.py
) else (
    echo Using system Python
    python -m pip install watchdog --quiet
    python auto_git.py
)

pause