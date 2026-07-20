@echo off
cd /d "%~dp0"
py app.py
if errorlevel 1 (
    echo.
    echo InfoBuilder Studio closed with an error.
    pause
)
