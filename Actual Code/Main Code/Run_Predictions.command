#!/bin/bash
# Double-click: predict the rest of the season + simulate the championship.
# Results (text files) go in the Predictions folder.
cd "$(dirname "$0")"
echo "Installing/checking libraries (first time can take a minute)..."
python3 -m pip install -q -r requirements.txt
python3 run_all.py --out Predictions
echo
echo "Opening the Predictions folder..."
open Predictions 2>/dev/null || xdg-open Predictions 2>/dev/null
read -p "Press Enter to close"
