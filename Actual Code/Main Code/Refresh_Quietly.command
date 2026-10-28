#!/bin/bash
# Same as Update_And_Predict.command but with no questions: meant to be started by macOS itself
# (see Schedule_Mac.command). Output goes to Predictions/refresh_log.txt.
cd "$(dirname "$0")"
mkdir -p Predictions
{
  echo "===== $(date) ====="
  python3 run_all.py --refresh --out Predictions
  echo "finished with code $?"
} >> Predictions/refresh_log.txt 2>&1
