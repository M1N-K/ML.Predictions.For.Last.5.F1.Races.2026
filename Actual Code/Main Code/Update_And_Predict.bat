@echo off
REM Double-click AFTER a race, practice or qualifying: downloads the latest results, refits the
REM models, scores the saved predictions against what happened, then predicts again.
REM Needs an internet connection.
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Installing/checking libraries...
%PY% -m pip install -q -r requirements.txt
%PY% run_all.py --refresh --out "%~dp0Predictions"
echo.
echo Opening the Predictions folder...
explorer "%~dp0Predictions"
pause
