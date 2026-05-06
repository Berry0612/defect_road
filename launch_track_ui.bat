@echo off
setlocal

cd /d "%~dp0"

uv run python track_ui.py

pause