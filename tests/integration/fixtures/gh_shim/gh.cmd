@ECHO off
REM Windows entry point for the gh PATH-shim (#9398 Phase A test infra).
REM See gh_main.py for the contract. Invokes the Python implementation,
REM forwarding all arguments via %*. Multi-line args from tracker.py
REM are not used so the %* mangling that bit run_comprehension_test
REM (#9574) is not a concern here.
python "%~dp0gh_main.py" %*
