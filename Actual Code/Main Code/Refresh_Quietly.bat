@echo off
REM Same as Update_And_Predict.bat but with no windows and no questions: it is meant to be started
REM by the Windows Task Scheduler (see Schedule_Windows.bat). Everything it prints goes to
REM Predictions\refresh_log.txt so you can look at it afterwards.
cd /d "%~dp0"
if not exist Predictions mkdir Predictions
set PY=python
where python >nul 2>nul || set PY=py
echo ===== %date% %time% ===== >> "Predictions\refresh_log.txt"
%PY% run_all.py --refresh --out "%~dp0Predictions" >> "Predictions\refresh_log.txt" 2>&1
echo finished with code %errorlevel% >> "Predictions\refresh_log.txt"
