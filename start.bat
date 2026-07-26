@echo off
REM Run with a console attached (shows tracebacks) — useful for debugging.
REM For normal use, double-click Nu-Doom-Launcher.vbs instead (no console window).
set PY=C:\msys64\mingw64\bin\python.exe
if not exist "%PY%" set PY=python
"%PY%" "%~dp0nu_doom_launcher.pyw"
pause
