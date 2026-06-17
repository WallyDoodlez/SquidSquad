@echo off
REM SquidSquad — BARE harness launcher (#12525).
REM
REM Brings up ONLY the harness in a visible, persistent window. Unlike
REM start.bat / start.ps1 (the FULL setup launchers), this does NOT sync clones
REM and does NOT install dependencies — it assumes the environment is already
REM set up. Run start.ps1 once for that; use this for the greenfield install
REM smoke test and for debugging a harness you want to watch.
REM
REM Double-click it, or run from a terminal: start-harness.bat [harness args...]
REM The window stays open (pause) so harness output and any startup error remain
REM visible after it exits.
cd /d "%~dp0"
python references\scripts\harness.py %*
pause
