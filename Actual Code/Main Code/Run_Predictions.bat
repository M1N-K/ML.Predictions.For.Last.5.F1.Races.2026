@echo off
REM Double-click: predict the rest of the season + simulate the championship.
REM Results (text files) go in the Predictions folder.
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Installing/checking libraries (first time can take a minute)...
%PY% -m pip install -q -r requirements.txt
%PY% run_all.py --out "%~dp0Predictions"
echo.
echo Opening the Predictions folder...
explorer "%~dp0Predictions"
pause
