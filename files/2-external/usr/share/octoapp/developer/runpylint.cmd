@echo off
REM This is just for local dev help, the github workflow does the real checkin linting.
pylint ..\octoapp\
pylint ..\octoprint_octoapp\
pylint ..\moonraker_octoapp\