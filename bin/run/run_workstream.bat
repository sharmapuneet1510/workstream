@echo off
setlocal
cd /d "%~dp0"

REM Use venv if present
if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

set "PYTHONPATH=src"
"%PYTHON%" src\desktop_main.py
endlocal