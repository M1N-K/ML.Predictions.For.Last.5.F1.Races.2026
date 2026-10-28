#!/bin/bash
# Double-click AFTER a race, practice or qualifying: downloads the latest results, refits the
# models, scores the saved predictions against what happened, then predicts again.
# Needs an internet connection.
cd "$(dirname "$0")"
echo "Installing/checking libraries..."
python3 -m pip install -q -r requirements.txt
python3 run_all.py --refresh --out Predictions
echo
echo "Opening the Predictions folder..."
open Predictions 2>/dev/null || xdg-open Predictions 2>/dev/null
read -p "Press Enter to close"
