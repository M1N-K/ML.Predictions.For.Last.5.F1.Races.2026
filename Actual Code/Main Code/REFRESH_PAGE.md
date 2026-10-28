# Refreshing the web page

This file is about the page hosted on claude.ai. The standalone copy (`index.html`, for GitHub Pages)
needs none of this: run step 1 below, then commit and push the changed `site_data/` files.

The page does not fetch anything by itself: it shows nine small data tables that were uploaded to it
(`site_data/*.csv`). Refreshing it is therefore two things: (1) rebuild those tables on a computer
that has this folder, (2) put the new tables into the page.

Step 1 can be automated on your own computer (`Schedule_Windows.bat` / `Schedule_Mac.command`).
Step 2 needs Claude: ask it (see `ROUTINE_PROMPT.txt` for words you can paste).

## 1. Rebuild the tables (any computer with the folder)

    python run_all.py --refresh --out Predictions

Downloads the newest results, refits the models, scores saved predictions, predicts the rest of the
season, simulates the championship and writes `site_data/`. Add a line to `overrides.csv` first if
a driver is out or has a grid penalty (see the comments at the top of that file).

## 2. Put them into the page (Claude does this)

For each file in `site_data/` (`race_predictions`, `title_drivers`, `title_constructors`,
`title_timeline`, `title_summary`, `model_accuracy`, `calibration`, `scorecard`, `meta`):

1. upload the CSV to the page's file store;
2. update the matching data source of the page with the new file's address, its name and the time;
3. read the page's own check result afterwards, and report any problem it names.

The page's layout (`index.html`) only needs republishing when the layout itself changes.

## What cannot be automated from here

* Claude cannot run on a timer in a free account, so step 2 happens when you ask for it.
* If a run fails, `Predictions/refresh_log.txt` has the reason (scheduled runs write there).
