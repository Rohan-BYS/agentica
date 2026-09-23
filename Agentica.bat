@echo off
:: Agentica AI Browser Launcher
set PLAYWRIGHT_BROWSERS_PATH=%~dp0bin
start "" /B python src\human\launcher.py
