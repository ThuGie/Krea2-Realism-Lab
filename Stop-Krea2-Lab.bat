@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0Start-Krea2-Lab.ps1" -Stop
if errorlevel 1 pause
