@echo off
REM SquidSquad — delegates to start.ps1
cd /d "%~dp0"
pwsh -ExecutionPolicy Bypass -File start.ps1 %*
pause
