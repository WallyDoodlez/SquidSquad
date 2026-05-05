@echo off
REM SquidSquad — one command to boot everything.
REM Usage: start.bat (or double-click)

cd /d "%~dp0"
python references/scripts/squidsquad_cli.py start
pause
