@echo off
REM SquidSquad - SUPERVISED harness launcher (#12825).
REM
REM Runs the harness in an auto-relaunch loop so the harness itself can be
REM restarted without an operator at the terminal. This is the SUPERVISOR layer
REM ABOVE the harness: the harness owns agent lifecycle; this wrapper owns
REM harness lifecycle (mechanism, not a parallel control path).
REM
REM Exit-code contract (mirrors the agent self-restart exit-42 convention):
REM   42    -> RESTART: relaunch immediately. POST /restart makes the harness
REM           exit with this code.
REM   0     -> clean STOP (POST /shutdown) or operator Ctrl+C -> do NOT relaunch.
REM   other -> CRASH: relaunch, but a crash-loop guard gives up after
REM           CRASH_THRESHOLD consecutive crashes so a broken harness never
REM           respawns forever.
REM
REM Use this (not start-harness.bat, the one-shot) to run the harness for any
REM install that needs self-healing harness restart.
REM
REM Usage: restart-harness.bat [harness args...]
setlocal enabledelayedexpansion
cd /d "%~dp0"

if "%SQUIDSQUAD_HARNESS_RESTART_CODE%"=="" (set RESTART_CODE=42) else (set RESTART_CODE=%SQUIDSQUAD_HARNESS_RESTART_CODE%)
if "%SQUIDSQUAD_HARNESS_CRASH_THRESHOLD%"=="" (set CRASH_THRESHOLD=3) else (set CRASH_THRESHOLD=%SQUIDSQUAD_HARNESS_CRASH_THRESHOLD%)
if "%SQUIDSQUAD_HARNESS_CMD%"=="" (set "HARNESS_CMD=python references\scripts\harness.py") else (set "HARNESS_CMD=%SQUIDSQUAD_HARNESS_CMD%")
if "%SQUIDSQUAD_HARNESS_CRASH_WINDOW%"=="" (set CRASH_WINDOW=60) else (set CRASH_WINDOW=%SQUIDSQUAD_HARNESS_CRASH_WINDOW%)

set CRASH_COUNT=0

:loop
set START=
for /f %%t in ('python -c "import time;print(int(time.time()))" 2^>nul') do set START=%%t
%HARNESS_CMD% %*
set CODE=!ERRORLEVEL!
set END=
for /f %%t in ('python -c "import time;print(int(time.time()))" 2^>nul') do set END=%%t

if !CODE!==0 (
    echo [restart-harness] harness exited cleanly ^(0^) - not relaunching.
    goto :end
)
if !CODE!==!RESTART_CODE! (
    echo [restart-harness] restart requested ^(exit !CODE!^) - relaunching...
    set CRASH_COUNT=0
    goto :loop
)
REM Abnormal exit -> crash-loop guard. Mirror restart-harness.sh: a run that
REM lasted at least CRASH_WINDOW seconds was healthy (not a boot loop), so it
REM forgives prior crashes; the crash that ended it then starts a fresh streak
REM at 1. Wall-clock comes from a python epoch call (python is already required
REM to run the harness). If that call fails, START/END are empty -> ELAPSED
REM evaluates to 0 -> we gracefully fall back to pure CONSECUTIVE counting.
set /a ELAPSED=END-START
if !ELAPSED! GEQ !CRASH_WINDOW! set CRASH_COUNT=0
set /a CRASH_COUNT+=1
echo [restart-harness] harness exited abnormally ^(code !CODE!^) - crash !CRASH_COUNT!/!CRASH_THRESHOLD!.
if !CRASH_COUNT! GEQ !CRASH_THRESHOLD! (
    echo [restart-harness] crash-loop detected - giving up. See output above and .squidsquad\harness-errors.log. 1>&2
    endlocal
    exit /b 1
)
timeout /t 1 /nobreak >nul 2>&1
goto :loop

:end
endlocal
exit /b 0
