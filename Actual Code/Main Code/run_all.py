#!/usr/bin/env python3
"""One command for everything. This is what the double-click launchers run.

    python run_all.py --out Predictions            predict with the data you already have
    python run_all.py --refresh --out Predictions  download the latest results first, refit the
                                                    models, then predict (use after a race or
                                                    after qualifying/practice)

Steps: [refresh: download data, refit models] -> score the tracker -> predict the rest of the
season -> simulate the championship -> write the data files for the web page (site_data/).
Output goes into the folder given by --out. Manual changes (driver out, penalties, ...) are read
from overrides.csv by every step.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd


def run(*args, quiet=True):
    cmd = [sys.executable, *args] + (["--quiet"] if quiet else [])
    r = subprocess.run(cmd)
    if r.returncode:
        sys.exit(f"\nStep failed: {' '.join(args)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="download the latest results and refit first")
    ap.add_argument("--out", default="Predictions", help="folder for the text files")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.refresh:
        print("1/4 Downloading the latest results ...")
        run("fetch_data.py", quiet=False)
        print("\n2/4 Refitting the models on the new data ...")
        run("train.py", "--fast", quiet=False)
    else:
        print("(Using the data you already have. Use the Update launcher to fetch the latest results.)")

    print("\nChecking the prediction tracker ...")
    subprocess.run([sys.executable, "tracker.py", "score"])

    races = pd.read_csv("data/races.csv")
    if races["has_results"].all():
        print("\nThe season is complete: nothing left to predict.")
        return
    print("\nPredicting the remaining races ...")
    run("predict_season.py", "--out", str(out))
    if Path("odds.csv").exists():
        print("Comparing with the bookmaker odds in odds.csv ...")
        subprocess.run([sys.executable, "odds.py", "--out", str(out / "odds_report.txt")])   # a typo in odds.csv must not stop the run
    print("Simulating the championship ...")
    run("simulate_season.py", "--out", str(out))
    print("Writing the data files for the web page (site_data/) ...")
    run("export_site_data.py", quiet=False)

    print("\nDone. Files in", out.resolve(), ":")
    for f in sorted(out.glob("*.txt")):
        print("  ", f.name)


if __name__ == "__main__":
    main()
