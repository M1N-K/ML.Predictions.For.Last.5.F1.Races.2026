# Get started: download it and run it yourself

This page is only about getting the project onto your computer and running it. Allow about 10 minutes,
and about 25 MB of disk space.

## What you need

- **Python.** Download it from <https://www.python.org/downloads>. It was developed and tested on
  Python 3.13; a recent version should be fine.
  - **Windows:** on the first installer screen, tick **Add Python to PATH**. This is the step people miss.
  - **Mac:** the installer from python.org is fine.
- **An internet connection** for the first run (to install some libraries) and whenever you update.
- You do **not** need a GitHub account.

## Step 1: Download everything

Download the **whole repository**, not single files. The programs need the `data/` and `models/` folders
that sit next to them.

**Option A: a zip file (easiest)**

1. Open the repository page on GitHub.
2. Click the green **Code** button, then **Download ZIP**.
3. Unzip it. On Windows, right-click the file and choose **Extract All**. On a Mac, double-click it.
4. Open the new folder. You should see `run_all.py`, `README.md`, and folders called `data`, `models`
   and `site_data`.

**Option B: git (if you already use it)**

```bash
git clone https://github.com/<your-username>/f1-race-predictor.git
cd f1-race-predictor
```

Replace `<your-username>` with the GitHub name of whoever owns the repository.

## Step 2: Run it

### Windows

Double-click **`Run_Predictions.bat`**. The first time it installs the libraries it needs (a minute or two),
then makes the predictions and opens the `Predictions` folder.

### Mac

1. Double-click **`Run_Predictions.command`**.
2. The first time, macOS may refuse to open it. Right-click the file, choose **Open**, then **Open** again.

If double-clicking does nothing at all, use the terminal route below. Files that went through a Windows
computer or a zip can lose the "allowed to run" setting.

### Any computer, from the terminal

Open a terminal in the project folder, then run these two lines. On Windows use `python`. On a Mac use
`python3` in place of `python`.

```bash
python -m pip install -r requirements.txt
python run_all.py --out Predictions
```

On Windows, if `python` is not recognised, try `py` instead.

## Step 3: Read the results

Open the new **`Predictions`** folder. Everything is a plain text file you can open in Notepad or TextEdit.

| file | what is in it |
|---|---|
| `rest_of_season_2026.txt` | Predicted finishing order, win chance and podium chance for every remaining race |
| `championship_2026.txt` | Title chances for drivers and teams |
| `scorecard.txt` | How earlier predictions did against the real results. It appears once a predicted race has finished |
| `odds_report.txt` | The model's win chances next to any bookmaker odds you have typed into `odds.csv` |

In the race tables, **Pred** is the predicted finishing position, **P(win)** is the chance of winning and
**P(podium)** is the chance of finishing in the top three.

## Step 4: Update it after a session

The predictions get better as more of the weekend is known. After practice, after qualifying and after
the race, update it:

- **Windows:** double-click **`Update_And_Predict.bat`**
- **Mac:** double-click **`Update_And_Predict.command`**
- **Terminal:** `python run_all.py --refresh --out Predictions`

This downloads the latest data, refits the models and predicts again. It needs an internet connection and
takes longer than the first run.

If a driver is out, or has a grid penalty, open **`overrides.csv`** in Notepad or Excel, follow the notes at
the top, save it and run the update again.

## Step 5: See the dashboard (optional)

The repository includes a web page, `index.html`. Browsers will not let a page opened straight from a file
read the data files next to it, so serve the folder instead:

```bash
python -m http.server
```

Then open <http://localhost:8000/> in your browser. Stop it with `Ctrl+C`. Each update in Step 4
refreshes the data the page reads.

## If something goes wrong

**`python` is not recognised.** Python is not installed, or "Add Python to PATH" was not ticked. Run the
Python installer again and tick it. On Windows, `py` often works when `python` does not.

**`pip` errors during the install.** Update pip, then try again:
`python -m pip install --upgrade pip`

**The models fail to load, or you see a version warning.** The saved models were built with particular
library versions (lightgbm 4.7.0, scikit-learn 1.9.1, pandas 3.0.5). If yours are much older or newer,
retrain them on your own machine with `python train.py`. It takes 20 to 30 minutes and only needs doing once.

**The Mac file will not open.** Use the terminal route in Step 2. If you would rather fix the file itself,
run `chmod +x *.command` in the project folder.

**The dashboard shows "The data files could not be loaded".** You opened `index.html` by double-clicking
it. Use the `python -m http.server` route in Step 5.

**A prediction looks out of date.** Run the update in Step 4. The tables only change when you run something.

## Checking that it works

To run the built-in tests, which take a short while and print a pass for each check:

```bash
python test_no_leakage.py
python test_odds.py
```

---

This is an unofficial hobby project, not affiliated with Formula 1 or the FIA, and not betting advice. Race
data comes from [f1db](https://github.com/f1db/f1db) under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
