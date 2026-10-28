<div align="center">

# 🏁 F1 Race Predictor: The Master Guide

**Everything in one place: setting it up, running it, keeping it updated every race, sharing it, and
how the code works.**

![Windows](https://img.shields.io/badge/Windows-supported-0078D6?logo=windows&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-supported-000000?logo=apple&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Model](https://img.shields.io/badge/Model-LightGBM-2E7D32)
![Data](https://img.shields.io/badge/Data-every%20race%20since%202014-E10600)

</div>

---

## 📑 Contents

1. [What it does](#1-what-it-does)
2. [Setting it up](#2-setting-it-up)
3. [Running it](#3-running-it)
4. [Reading the results](#4-reading-the-results)
5. [The race-weekend routine](#5-the-race-weekend-routine)
6. [Telling it what it doesn't know (`overrides.csv`)](#6-telling-it-what-it-doesnt-know-overridescsv)
7. [The dashboard](#7-the-dashboard)
8. [Comparing with bookmaker odds](#8-comparing-with-bookmaker-odds)
9. [Updating automatically every day](#9-updating-automatically-every-day)
10. [Keeping GitHub and Google Drive up to date](#10-keeping-github-and-google-drive-up-to-date)
11. [Retraining, and starting a new season](#11-retraining-and-starting-a-new-season)
12. [How good is it?](#12-how-good-is-it)
13. [How it works](#13-how-it-works)
14. [What's in the folder](#14-whats-in-the-folder)
15. [Every command](#15-every-command)
16. [Troubleshooting](#16-troubleshooting)
17. [FAQ](#17-faq)

---

## 1. What it does

For every race left in the season, the predictor gives:

- a **predicted finishing order**;
- each driver's chance of **winning**, finishing on the **podium**, and **retiring**;
- the chance of each driver and team **winning the championship**, and when the title could be decided.

It also **keeps score of itself**. Every prediction is saved before the race and checked after it, so you
can see whether it's any good.

Everything comes out as plain text files you can open in Notepad or TextEdit, plus an optional web page
with charts.

> Unofficial hobby project. Not affiliated with Formula 1 or the FIA. **Not betting advice.**

---

## 2. Setting it up

You'll need about **10 minutes**, an internet connection, and about **25 MB** of space. You don't need any
coding knowledge or accounts.

### Step 1 · Install Python

1. Go to **[python.org/downloads](https://www.python.org/downloads)** and click **Download**.
2. Install it.

> ⚠️ **Windows:** on the **first** installer screen, tick **"Add Python to PATH"**. This is the step people
> miss most.

### Step 2 · Download the project

Get the whole folder from **either**:

- **Google Drive:** [open the folder](https://drive.google.com/drive/folders/1AT_yU_6ySvWNcQNuzkBZ2hiR9vJrsoMC?usp=drive_link),
  click the folder name at the top, then **Download**; or
- **GitHub:** on the repository page, click the green **Code** button, then **Download ZIP**.

Then unzip it. On Windows, right-click it and choose **Extract All**. On a Mac, double-click it.

> Always download the **whole folder**. The program needs the `data` and `models` folders that sit next to it.

### Step 3 · Check it

Open the **F1-Predictor** folder. You should see `START HERE.txt`, `run_all.py`, and the folders `data`,
`models` and `site_data`.

---

## 3. Running it

There are **two buttons**. Each comes as a `.bat` file for Windows and a `.command` file for Mac.

| Button | What it does | Internet? | Use it when |
|---|---|---|---|
| **`Run_Predictions`** | Predicts with the data you already have | Only the first time | You just want to see the predictions |
| **`Update_And_Predict`** | Downloads the latest results, retrains, then predicts | Yes | Something has happened on track |

**To run one,** double-click it. A window opens, does the work, then opens the **`Predictions`** folder.

- **First run:** it installs the extra Python pieces it needs, which takes a minute or two.
- **Mac, first time:** if macOS won't open the file, right-click it, choose **Open**, then **Open** again.

> 💡 Running `Run_Predictions` twice gives **the same numbers**, because nothing new has gone in. To get
> **new** predictions, use `Update_And_Predict`.

### From the terminal instead

```bash
python -m pip install -r requirements.txt            # first time only
python run_all.py --out Predictions                  # same as Run_Predictions
python run_all.py --refresh --out Predictions        # same as Update_And_Predict
```

On a Mac, type `python3` instead of `python`. Always run commands **from inside the F1-Predictor folder**.

### What happens during a run

```
[Update only]  1. download the latest results      (fetch_data.py)
               2. refit the models on them          (train.py --fast, about 10 seconds)
               3. score saved predictions            (tracker.py)
               4. predict every remaining race       (predict_season.py)
               5. compare with bookmaker odds        (odds.py, only if you've added odds)
               6. simulate the championship 20,000x  (simulate_season.py)
               7. write the dashboard's tables       (export_site_data.py)
               8. save dashboard.html                (make_single_page.py)
```

---

## 4. Reading the results

Everything is in the **`Predictions`** folder:

| File | What's in it |
|---|---|
| 📄 `rest_of_season_2026.txt` | Predicted order, win and podium chances for **every remaining race** |
| 🏆 `championship_2026.txt` | Title chances for drivers and teams, expected points, and when it could be decided |
| 📈 `scorecard.txt` | How earlier predictions did against the real results (appears once a predicted race has been run) |
| 💰 `odds_report.txt` | The model next to bookmaker odds (only if you've added odds) |
| 🌐 `dashboard.html` | All of the above as a web page: double-click to open |

### A race prediction

```
R19 Mexico   2026-11-01  Kimi Antonelli 32% | Max Verstappen 32% | Lewis Hamilton 8%   [pre]

 Pred            Driver      Team P(win) P(podium)
    1    Kimi Antonelli  Mercedes  32.2%       62%
    2    Max Verstappen  Red Bull  31.8%       56%
    3      Lando Norris   Mclaren   7.5%       33%
    4    Lewis Hamilton   Ferrari   8.4%       34%
```

| Column | Meaning |
|---|---|
| **Pred** | Predicted finishing position |
| **P(win)** | Chance of winning the race |
| **P(podium)** | Chance of finishing in the top three |
| **Grid** | Starting position (only shown after qualifying) |
| **[pre] / [fp] / [post]** | How much it knew: before the weekend / after practice / after qualifying |

> 💡 The order and the win chances come from two different models, so they can disagree slightly. Here
> Norris is predicted 3rd but Hamilton has a higher win chance.

### The championship file

| Column | Meaning |
|---|---|
| **Title %** | Share of the 20,000 simulated seasons that driver or team won |
| **Top 3 %** | Share in which they finished in the top three |
| **Now** | Real points today |
| **Expected pts** | Average final points across the simulations |
| **Range (10-90%)** | The middle 80% of simulated final totals |

The bottom of the file shows the chance the title is **settled by the end of each race**.

### The scorecard

For each race it predicted, the scorecard shows the predicted and actual winner, **HIT** or **miss**, how many
of the podium it got right, and how well the whole order matched. It sets that against simply using the
starting grid order. A handful of races is too few to judge the model: give it 10 or more.

---

## 5. The race-weekend routine

This is how to keep it current through a race weekend. Each update makes the next prediction sharper.

| When | Do this | What it learns | Picks the winner |
|---|---|---|---|
| **Before the weekend** (Mon–Thu) | `Update_And_Predict` | Nothing new; it **saves a "before" prediction** | ~4 in 10 |
| **After practice** (Fri/Sat) | `Update_And_Predict` | Who looked fast in practice | ~4.5 in 10 |
| **After qualifying** (Sat) | Check penalties, then `Update_And_Predict` | The starting grid | ~5.5 in 10 |
| **After the race** (Sun/Mon) | `Update_And_Predict` | The result and the new standings | Scores the weekend |

### Your weekend checklist

- [ ] **Before the weekend:** run an update so a "before" prediction is saved for the scorecard.
- [ ] **After practice:** update.
- [ ] **After qualifying:** if anyone has a **grid penalty**, add it to `overrides.csv` ([section 6](#6-telling-it-what-it-doesnt-know-overridescsv)), then update.
- [ ] **After the race:** update, then open `scorecard.txt` to see how it did.
- [ ] **If you share it:** push to GitHub or re-upload to Drive ([section 10](#10-keeping-github-and-google-drive-up-to-date)).

### Good to know

- **The data takes time to appear.** Results come from [f1db](https://github.com/f1db/f1db), an open F1 database,
  which isn't instant. If an update shows nothing new, try again a few hours later.
- **Each stage is saved separately.** The scorecard keeps the *last* prediction made at each stage (before,
  after practice, after qualifying), so updating twice at the same stage just replaces the earlier one.
- **A race that has happened is never saved.** You can't add a prediction after the fact, which keeps the
  record honest.
- **Sprint weekends** are handled automatically. The sprint result is used after qualifying, and sprint points
  count in the championship simulation.
- **Races further ahead are less certain.** They only know results up to the latest race. They sharpen as each
  race passes.

---

## 6. Telling it what it doesn't know (`overrides.csv`)

The predictor works out **who is racing** by itself, from the season's official entry list and, after
practice, from who actually turned up. To check what it's using, run `python lineup.py`.

If you know something it doesn't, such as an injury, a stand-in or a grid penalty, add a line to
**`overrides.csv`** (open it in Notepad or Excel).

### The columns

| Column | What to put |
|---|---|
| `race` | A race id like `2026-19`, or `next` (the next race), or `all` (every remaining race) |
| `driver` | A surname (`Hamilton`) or full id (`lewis-hamilton`) |
| `action` | `out`, `replace`, `add`, `team` or `penalty` |
| `value` | Depends on the action (see below) |
| `team` | Only for `add` |
| `note` | Anything you like |

### The actions

| Action | Meaning | Example line |
|---|---|---|
| `out` | The driver doesn't race | `next,Stroll,out,,,injured` |
| `replace` | Someone else takes the seat | `next,Stroll,replace,Drugovich,,stand-in` |
| `add` | An extra car | `next,,add,New Driver,cadillac,` |
| `team` | The driver races for another team | `all,Perez,team,cadillac,,` |
| `penalty` | Places lost on the grid, or `pitlane` | `next,Hamilton,penalty,10,,gearbox` |

**Then:** save the file and run an update.

- `python overrides.py list` shows the names you can use.
- `python overrides.py check` shows what each line will do, before you run anything.
- Lines starting with `#` are ignored. That's how the examples at the top are switched off.
- **Grid penalties only work after qualifying,** because the model doesn't use the grid before then.
- Only races that haven't happened yet can be changed.
- **Remove old lines when they no longer apply**, especially ones set to `all`.

---

## 7. The dashboard

The same numbers as a web page with four tabs: **Next race**, **Championship**, **Track record** and
**Calibration**.

| Version | How to open it | Updates? |
|---|---|---|
| **`Predictions/dashboard.html`** | Double-click it. No setup needed. | Remade every run (a snapshot) |
| **`index.html`** (live) | Run `python -m http.server` in the folder, then open `http://localhost:8000/` | Reads the latest `site_data/` |
| **GitHub Pages** | `https://<your-username>.github.io/<repo-name>/` | After you push new `site_data/` files |

- Double-clicking `index.html` **won't work**: browsers block a page opened from a file from reading the data
  files next to it. Use `dashboard.html` for double-clicking.
- To **share** it, send `dashboard.html` itself (zipped is safest), not a `file:///` link, which only works on
  your computer.
- GitHub shows `.html` files as code. To see them as pages, switch on **GitHub Pages** (Settings, then Pages,
  then deploy from branch `main`, folder `/ (root)`). The repository must be **public** on a free account.

---

## 8. Comparing with bookmaker odds

This is optional. It checks the model against the betting market.

1. Make a blank sheet for a race: `python odds.py template 2026-20`
2. Fill in **`odds.csv`**, one row per driver:

   | Column | What to put |
   |---|---|
   | `race_id` | e.g. `2026-20` |
   | `stage` | When you took the odds: `pre` (before practice), `fp` (after practice), `post` (after qualifying) |
   | `source` | Where they came from, any label |
   | `date` | When you took them |
   | `driver_id` | e.g. `max-verstappen` |
   | `odds` | `+120` / `-150` (American: **always** write the `+`), `5/2` (fractional) or `3.4` (decimal) |
   | `note` | Optional |

3. Run the predictions. `Predictions/odds_report.txt` shows the model's chances next to the market's, and
   after the race it scores both.

Things to know:

- **Take the odds before the race.** Odds taken afterwards prove nothing.
- Bookmakers' prices add up to more than 100% (their margin). This is removed in proportion.
- Drivers you leave out get a small chance each (0.4% by default, change it with `--tail`).
- **A few races can't show who is better.** It takes dozens of races to separate two good forecasters.

---

## 9. Updating automatically every day

Double-click once, and your computer updates by itself **every day at 9am**:

| Windows | Mac |
|---|---|
| `Schedule_Windows.bat` | `Schedule_Mac.command` |

- The computer has to be **on** at 9am. A Mac that is asleep runs it when it wakes.
- To see what happened, open `Predictions/refresh_log.txt`.
- To change the time, edit `09:00` in the file and run it again.

> ⚠️ These haven't been tested on a real Windows PC or Mac yet. If one shows an error, update by hand instead.

**To stop it:**

- **Windows** (Command Prompt): `schtasks /Delete /TN "F1 Predictor refresh" /F`
- **Mac** (Terminal): `launchctl unload ~/Library/LaunchAgents/com.f1predictor.refresh.plist`

---

## 10. Keeping GitHub and Google Drive up to date

Updating on your computer doesn't change what other people see online. After each race (or each session),
publish the new files.

### GitHub, with GitHub Desktop

1. Run **`Update_And_Predict`** in your repository folder.
2. Open **GitHub Desktop**. It lists the changed files.
3. Type a summary such as `Update after Mexico GP` at the bottom left.
4. Click **Commit to main**, then **Push origin**.

What normally changes after an update:

| Folder | Why |
|---|---|
| `data/` | New results |
| `models/` | Models refitted on them |
| `site_data/` | New tables, so **GitHub Pages updates itself** about a minute after the push |
| `tracker/` | New saved predictions and scores |
| `reports/` | New prediction tables |

`Predictions/` is **not** uploaded, because it's on the ignore list (`.gitignore`). If you also want
`dashboard.html` on GitHub, copy it from `Predictions/` into the main folder before you commit.

### Google Drive

The Drive copy doesn't sync by itself. After an update:

- **Just the dashboard:** upload the new `Predictions/dashboard.html` and choose **Replace** (keep both
  versions off, so the link stays the same).
- **The whole project:** delete the old folder and upload the new one. Check it's still shared as
  **Anyone with the link**.

### ⚠️ Don't update by re-downloading

Your **saved predictions and scorecard** live in your own `tracker/` folder. If you replace your folder with a
fresh download, you lose them. Update with `Update_And_Predict` instead, and **back up `tracker/`**, because
it's the only copy of your record.

---

## 11. Retraining, and starting a new season

### Quick refit vs full retrain

| | Quick refit | Full retrain |
|---|---|---|
| How | Happens automatically in every `Update_And_Predict` | `python train.py` |
| Time | About 10 seconds | 20 to 30 minutes |
| What it does | Refits the models on the latest results, reusing the tuned settings | Re-tunes the settings, re-runs the full back-test and accuracy reports, then refits |
| When | Every update | After the season, after changing the code, or if the models fail to load |

### A new season

- **New races are found automatically.** `fetch_data.py` discovers rounds as f1db publishes them, and the
  output files are named after the year (for example `rest_of_season_2027.txt`).
- **The line-up comes from the season's entry list,** so new drivers and team moves are picked up once f1db
  lists them. Check with `python lineup.py`, and use `overrides.csv` for anything missing.
- **A big rule change** (like 2026's) resets the pecking order. Add the new year to `ERA_START_YEARS` in
  `features.py`, then run a full `python train.py`.
- **The first races of a new era are the hardest** to predict: there's little data on the new cars.
- **Clear out `overrides.csv`** from last season.

> The new-season steps haven't been tried yet, because the project was built mid-2026. Check the first
> predictions of a new season carefully.

---

## 12. How good is it?

Tested on **191 past races (2018 to 2026)**. Each season was predicted by models trained only on earlier
seasons. Settings were chosen on 2022, so the **88 races from 2023 on** were never used to choose anything.

| Prediction | Winner right (2018–26) | Order match* (2018–26) | Winner right (2023–26) | Order match* (2023–26) |
|---|---|---|---|---|
| **After qualifying** | 53.4% | 0.666 | 62.5% | 0.695 |
| Baseline: starting grid | 54.5% | 0.628 | 61.4% | 0.664 |
| **After practice** | 46.6% | 0.626 | 44.3% | 0.632 |
| **Before the weekend** | 43.5% | 0.603 | 42.0% | 0.622 |
| Baseline: recent form | 44.0% | 0.584 | 39.8% | 0.603 |

\*Rank correlation between predicted and real finishing order (1 = perfect).

**In plain words:**

- After qualifying it **orders the whole field better than the grid does**, but it **doesn't pick the winner
  better than "the pole sitter wins"**.
- Before the weekend it beats "recent form" on order, but not on winner calls.
- Win and podium chances are **honest**: a "30%" happens about 30% of the time.
- **Retirement chances run too high**: 17.3% predicted against 14.6% observed.
- It **can't know** about crashes, safety cars, weather, strategy or upgrades beyond what results show.

Full details: `reports/backtest_summary.md` and `MODEL_NOTES.md`.

---

## 13. How it works

```
  f1db (open F1 database)
        |  fetch_data.py: download every race since 2014
        v
  data/  results, races, practice, pit stops, sprints, entry lists, standings
        |  features.py: turn history into inputs (form, team pace, circuit history...)
        v
  train.py: LightGBM models  ->  models/f1_models.joblib
        |
        v
  engine.py: who's racing -> your overrides -> inputs -> best stage -> predictions
        |
        +-- predict_season.py    every remaining race
        +-- simulate_season.py   championship odds
        +-- tracker.py           save before, score after
        +-- odds.py              vs bookmakers
        +-- export_site_data.py  -> site_data/ -> dashboard
```

**The models.** For each stage (before the weekend, after practice, after qualifying) there are four:

| Model | Job |
|---|---|
| **Ranker** | Orders the whole field (trained to care most about the points-scoring places) |
| **Win** | Chance of winning (scaled so each race adds up to 100%) |
| **Podium** | Chance of a top-three finish (scaled to add up to 3 per race) |
| **Retirement** | Chance of not finishing |

**No peeking at the future.** Every input uses only races *before* the one being predicted.
`test_no_leakage.py` checks this automatically.

**The championship.** Each remaining race is played 20,000 times. Drivers retire at their predicted rate, and
the rest are ordered by the model plus random luck (sized from past seasons). A team that's faster or slower
than expected stays that way for several races, as in real life. Points are added to the real standings.

**Ideas that were tested and didn't help:** driver-versus-car ratings, circuit-type features, weighting recent
seasons more, and shifting the retirement rate. They're listed with numbers in `MODEL_NOTES.md`.

For a file-by-file tour of the code, see **`CODE_GUIDE.md`** ("How It Works").

---

## 14. What's in the folder

```
F1-Predictor/
├── START HERE.txt              short instructions
├── Run_Predictions.*           ▶ predict with the data you have
├── Update_And_Predict.*        ▶ download new results, then predict
├── Schedule_Windows.bat        ⏰ daily automatic updates (Windows)
├── Schedule_Mac.command        ⏰ daily automatic updates (Mac)
├── Refresh_Quietly.*           used by the schedulers (no need to touch)
├── overrides.csv               ✏️ your changes: driver out, penalties...
├── odds.csv                    💰 bookmaker odds you type in
├── index.html, assets/         🌐 the live dashboard (needs a server or GitHub Pages)
│
├── run_all.py                  runs everything in order
├── fetch_data.py               downloads the data
├── features.py                 builds the model inputs
├── train.py                    trains and tests the models
├── engine.py                   shared prediction logic
├── predict.py                  one race
├── predict_season.py           every remaining race
├── simulate_season.py          championship simulation (with simcore.py)
├── lineup.py                   works out who's racing
├── overrides.py                applies overrides.csv
├── tracker.py                  saves and scores predictions
├── odds.py                     bookmaker comparison
├── export_site_data.py         dashboard tables
├── make_single_page.py         makes dashboard.html
├── make_charts.py              draws the calibration chart
├── ablation.py, recency_test.py, dnf_shift_test.py, season_backtest.py   experiments
├── test_*.py                   automatic checks
│
├── data/                       race data (raw downloads in data/raw are not uploaded)
├── models/                     trained models
├── site_data/                  tables for the dashboard
├── tracker/                    📒 your saved predictions: back this up
├── reports/                    accuracy tests, charts, experiment results
└── Predictions/                📂 your results (made when you run it)
```

---

## 15. Every command

Run these from inside the F1-Predictor folder. On a Mac, use `python3`.

### Everyday

| Command | What it does |
|---|---|
| `python run_all.py --out Predictions` | Everything, with the data you have |
| `python run_all.py --refresh --out Predictions` | Download the latest results first, then everything |

### One piece at a time

| Command | What it does |
|---|---|
| `python predict.py` | The next race only, at the most informed stage |
| `python predict.py --mode pre` | Force a stage (`pre`, `fp` or `post`) |
| `python predict.py --race 2026-18` | Replay a past race using only the races before it |
| `python predict_season.py` | Every remaining race in one file |
| `python simulate_season.py --runs 50000` | Championship odds with more simulations |
| `python fetch_data.py` | Just download the latest data |
| `python train.py --fast` | Quick refit on the latest data |
| `python train.py` | Full retrain with the back-test (20 to 30 minutes) |
| `python make_single_page.py` | Remake `Predictions/dashboard.html` |
| `python export_site_data.py` | Remake the dashboard tables in `site_data/` |
| `python -m http.server` | Serve the live dashboard at `http://localhost:8000/` |

### Checking things

| Command | What it does |
|---|---|
| `python tracker.py status` | What predictions are saved |
| `python tracker.py score` | Score saved predictions against results |
| `python lineup.py` | Who it thinks is racing in each remaining race, and why |
| `python overrides.py list` | Driver and team names you can use in `overrides.csv` |
| `python overrides.py check` | What each line in `overrides.csv` will do |
| `python odds.py` | Compare with the odds in `odds.csv` |
| `python odds.py template 2026-20` | Blank odds sheet for a race |

### Tests

| Command | Checks |
|---|---|
| `python test_no_leakage.py` | No information from the future gets in |
| `python test_overrides.py` | `overrides.csv` handling |
| `python test_lineup.py` | Automatic line-ups |
| `python test_odds.py` | Odds conversion and scoring |

### Experiments (slow, only if you're changing the model)

| Command | Question |
|---|---|
| `python ablation.py` | Do extra feature groups help? |
| `python recency_test.py` | Should recent seasons count more? |
| `python dnf_shift_test.py` | Can the retirement rate be corrected? |
| `python season_backtest.py` | How much should simulated races depend on each other? |

---

## 16. Troubleshooting

<details>
<summary><b>"python is not recognized" (Windows)</b></summary>

Python isn't installed, or **Add Python to PATH** wasn't ticked. Run the installer again, choose **Modify**,
and add it to PATH. You can also try `py` instead of `python`.
</details>

<details>
<summary><b>The window flashes and closes straight away</b></summary>

Usually the Python problem above. To see the real error, open a terminal in the folder and run
`python run_all.py --out Predictions`.
</details>

<details>
<summary><b>The Mac file won't open, or nothing happens</b></summary>

Right-click it, choose **Open**, then **Open**. If that fails, run `chmod +x *.command` in Terminal inside
the folder, or use the terminal commands.
</details>

<details>
<summary><b>Errors while installing (pip)</b></summary>

Run `python -m pip install --upgrade pip`, then try again.
</details>

<details>
<summary><b>"Could not load the models" or a version warning</b></summary>

Your libraries are a different version from the ones that built the models (lightgbm 4.7.0, scikit-learn
1.9.1, pandas 3.0.5). Run `python train.py` once. It takes 20 to 30 minutes.
</details>

<details>
<summary><b>An update shows nothing new</b></summary>

The data source hasn't published the session yet. Try again in a few hours. It also needs an internet
connection.
</details>

<details>
<summary><b>The prediction still says "before the weekend" after practice</b></summary>

It needs practice times for at least 10 drivers. If the data isn't out yet, it falls back to the
before-the-weekend prediction. Update again later.
</details>

<details>
<summary><b>A driver is missing or wrong</b></summary>

Run `python lineup.py` to see where the line-up came from, then fix it in `overrides.csv`.
</details>

<details>
<summary><b>"overrides.csv line X: unknown driver"</b></summary>

Check the spelling with `python overrides.py list`. A surname is usually enough. If two drivers share a
surname, use the full id.
</details>

<details>
<summary><b>The dashboard says "The data files could not be loaded"</b></summary>

You double-clicked `index.html`. Open `Predictions/dashboard.html` instead, or serve the folder with
`python -m http.server`.
</details>

<details>
<summary><b>dashboard.html shows code, not a page</b></summary>

It's open in a text editor or a preview. Right-click it, choose **Open with**, and pick your browser.
</details>

<details>
<summary><b>GitHub Pages shows 404</b></summary>

Wait a few minutes after switching it on. Check that `index.html` is in the main folder, and that Pages is
set to branch `main`, folder `/ (root)`.
</details>

<details>
<summary><b>The odds report shows an error</b></summary>

Usually a typo in `odds.csv`, often a missing `+` on American odds or a comma inside a note. The rest of the
run still finishes.
</details>

---

## 17. FAQ

**Why are the numbers the same every time I run it?**
`Run_Predictions` uses the data you already have. Use `Update_And_Predict` to get new results.

**Why is a driver predicted 3rd but with a higher win chance than 2nd?**
The order and the chances come from separate models. They usually agree, but not always.

**Why are races later in the season less certain?**
They can only use results up to today. Every race that passes sharpens them.

**Does it know about the weather, upgrades or penalties?**
Not by itself. It only learns from results. You can add penalties and driver changes in `overrides.csv`.

**Can I use it for betting?**
It isn't betting advice. Even after qualifying, it doesn't pick the winner better than "the pole sitter wins".

**How do I reset the scorecard?**
Delete `tracker/predictions.csv` and `tracker/scorecard.csv`. This loses your record, so back them up first.

**Can other people see my predictions?**
Only if you share them: send `dashboard.html`, switch on GitHub Pages, or share the Drive folder.

**Where does the data come from?**
[f1db](https://github.com/f1db/f1db), an open-source F1 database, used under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

---

<div align="center">
<sub>Unofficial hobby project, not affiliated with Formula 1 or the FIA. Not betting advice.<br>
Race data from <a href="https://github.com/f1db/f1db">f1db</a> under
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.</sub>
</div>
