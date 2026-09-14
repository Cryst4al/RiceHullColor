@echo off
setlocal
set "PROJECT_DIR=%~dp0"
if exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
  "%PROJECT_DIR%.venv\Scripts\python.exe" -m ricehullcolor.gui
) else (
  python -m ricehullcolor.gui
)
endlocal

