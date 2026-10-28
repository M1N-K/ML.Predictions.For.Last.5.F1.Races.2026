@echo off
REM Double-click ONCE to make Windows refresh the predictions by itself every day at 09:00
REM (downloads new results, refits, predicts again, saves the text files in Predictions\).
REM The computer has to be on at that time. To change the time: edit 09:00 below and run this again.
REM To stop it: open a Command Prompt and run   schtasks /Delete /TN "F1 Predictor refresh" /F
REM
REM Not tested by the author on a real Windows machine: if it prints an error, copy it to Claude.
cd /d "%~dp0"
schtasks /Create /SC DAILY /ST 09:00 /TN "F1 Predictor refresh" /TR "\"%~dp0Refresh_Quietly.bat\"" /F
if errorlevel 1 (
  echo.
  echo Could not create the task. Try right-click, then Run as administrator.
) else (
  echo.
  echo Done. The predictions will refresh every day at 09:00.
  echo Look at Predictions\refresh_log.txt to see what happened each time.
)
pause
