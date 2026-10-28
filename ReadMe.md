```text
                                     d88b
                     _______________|8888|_______________
                    |_____________ ,~~~~~~. _____________|
  _________         |_____________: mmmmmm :_____________|         _________
 / _______ \   ,----|~~~~~~~~~~~,'\ _...._ /`.~~~~~~~~~~~|----,   / _______ \
| /       \ |  |    |       |____|,d~    ~b.|____|       |    |  | /       \ |
||         |-------------------\-d.-~~~~~~-.b-/-------------------|         ||
||         | |8888 ....... _,===~/......... \~===._         8888| |         ||
||         |=========_,===~~======._.=~~=._.======~~===._=========|         ||
||         | |888===~~ ...... //,, .`~~~~'. .,\\        ~~===888| |         ||
||        |===================,P'.::::::::.. `?,===================|        ||
||        |_________________,P'_::----------.._`?,_________________|        ||
`|        |-------------------~~~~~~~~~~~~~~~~~~-------------------|        |'
  \_______/                                                        \_______/
```

# F1 Race Predictor

**Predict a Formula 1 race, then check honestly how good the prediction was.**

For every driver in a race, this gives a predicted finishing position and the chance of winning,
reaching the podium or retiring. For the rest of a season it also gives the chance of each driver and
team winning the championship. It is a machine-learning model (LightGBM) trained on every race since
2014, and everything it produces is a plain text file you can open in Notepad.

> Unofficial hobby project. Not affiliated with Formula 1 or the FIA. Not betting advice.

![Do the model's percentages match reality?](reports/calibration.png)

*Do the model's percentages match reality? 88 races (2023 to 2026) that were never used to choose
any setting. Close to the dotted diagonal is good. Win and podium chances are close; the highest
retirement chances are too high.*

## Why this exists

Predicting sport is easy to do badly. A model can look brilliant because it quietly saw information
from the future, or because only its best number was reported, or because nobody compared it with
something simple. This project is set up to avoid all three:

- **Predictions are saved before the race and scored after it.** A race that already has a result is
  never saved, so the record can't be back-filled.
- **Every model is compared with plain baselines** ("the starting grid order", "recent driver form"),
  on the same races, with a 95% interval on each difference.
- **A test checks for leaks.** `test_no_leakage.py` blanks out everything that isn't known yet at
  each point of the weekend and confirms the model's inputs don't change.
- **Ideas that did not help are left out**, and listed below with their numbers.

The aim is a model whose numbers can be checked, not just admired.

## Try it

```bash
git clone https://github.com/<your-username>/f1-race-predictor.git
cd f1-race-predictor
pip install -r requirements.txt
python run_all.py --out Predictions
```

That uses the data and trained models in the repository and takes under a minute (developed and
tested on Python 3.13). On Windows or Mac you can instead double-click `Run_Predictions`; see
`START HERE.txt`.

Text files appear in `Predictions/`:

| file | what is in it |
|---|---|
| `rest_of_season_2026.txt` | predicted order, win and podium chances for every remaining race |
| `championship_2026.txt` | title odds for drivers and teams, and when the title could be decided |
| `odds_report.txt` | the model's win chances next to bookmaker odds you have typed in |
| `scorecard.txt` | how earlier predictions did against the real results (after the first race) |

A taste of `rest_of_season_2026.txt`:

```
R19 Mexico   2026-11-01  Kimi Antonelli 32% | Max Verstappen 32% | Lewis Hamilton 8%   [before the weekend]

 Pred            Driver      Team P(win) P(podium)
    1    Kimi Antonelli  Mercedes  32.2%       62%
    2    Max Verstappen  Red Bull  31.8%       56%
    3      Lando Norris   Mclaren   7.5%       33%
    4    Lewis Hamilton   Ferrari   8.4%       34%
    5     Oscar Piastri   Mclaren   2.7%       16%
```

*Predicted on 28 October 2026 with models trained through round 18 (the United States GP).*

## Using it through a race weekend

The model gets better as the weekend gives it more to work with, so run it at each point:

1. **Before the weekend:** `python run_all.py --out Predictions`. Form only: no practice, no grid.
2. **After practice:** `python run_all.py --refresh --out Predictions`. This downloads the latest
   data, refits, and adds practice pace (once the data source has published the sessions).
3. **After qualifying:** the same command again. Now it knows the grid. If a driver has a grid
   penalty, add it to `overrides.csv` first (penalties only have an effect from this point).
4. **After the race:** the same command once more. It scores the saved predictions against the real
   result and updates the championship odds.

Changes you know about (a driver out, a stand-in, a penalty) go in `overrides.csv`. Everything
else, including who is on the grid, is worked out from the season's entry list and who turned up
to practice (`lineup.py`).

## How it thinks

- **Three stages.** One set of models for before the weekend, one for after practice, one for after
  qualifying. Each sees more than the last, and none sees anything it could not have known.
- **Two kinds of question, two kinds of model.** A ranking model orders the whole field (trained on
  championship points for each finishing position). Separate classifiers give P(win), P(podium) and
  P(retirement), scaled within each race so they add up properly.
- **Championship odds by simulation.** Each remaining race is played 20,000 times from the real
  standings. Drivers retire at their predicted rate, the rest are ordered by the model plus random
  luck sized from past seasons, and teams share a pace "shock" that carries from race to race. That
  last part fixed ranges that were far too narrow when every race was treated as independent.
- **Data:** [f1db](https://github.com/f1db/f1db), every race from 2014 (the hybrid era): results,
  qualifying, practice, pit stops, sprints and standings.

## How well does it work?

Walk-forward back-test: each season is predicted by a model trained only on earlier seasons.
Settings were chosen on 2022, so the 2023 to 2026 columns are the ones nothing was tuned on.

| model | winner right, 2018-26 (191 races) | order match*, 2018-26 | winner right, 2023-26 (88 races) | order match*, 2023-26 |
|---|---|---|---|---|
| **after qualifying** | 53.4% | 0.666 | 62.5% | 0.695 |
| baseline: starting grid order | 54.5% | 0.628 | 61.4% | 0.664 |
| **after practice** | 46.6% | 0.626 | 44.3% | 0.632 |
| **before the weekend** | 43.5% | 0.603 | 42.0% | 0.622 |
| baseline: recent driver form | 44.0% | 0.584 | 39.8% | 0.603 |

\*Spearman rank correlation between predicted and real finishing order (1 is perfect).

What this does and does not show:

- After qualifying the model **orders the field better** than the starting grid does, and over
  2018 to 2026 that gap is clear in the statistics. It does **not pick the winner better** than
  "the pole sitter wins": 53.4% against 54.5% is inside the noise.
- Before the weekend it beats "recent driver form" on order, but not on winner calls.
- Win and podium chances are close to calibrated: a "30%" happens roughly 30% of the time, with an
  average gap of about 1 percentage point. Retirement chances run too high: 17.3% predicted against
  14.6% observed over 2018 to 2026.
- Even 191 races is a small sample for winner calls; a few percentage points either way is noise.

All comparisons, with their intervals, are in `reports/backtest_summary.md`.

## What did not help

An idea is only kept if it gives a clear gain, meaning a 95% interval that excludes zero. For the
retirement shift that rule was tightened after the first version of it would have accepted a gain
inside the noise.

| idea | result |
|---|---|
| Driver-versus-car ratings, and circuit-type features | No clear gain at any stage; together they were clearly worse on win chances after qualifying. Built and tested, switched off. |
| Count recent seasons more when training | Finishing order got clearly worse on 2023 to 2026. Not used. |
| Shift the retirement chance to the recent retirement rate | Gain was inside the noise. The over-prediction mostly comes from retirements varying from year to year (14% in 2019, 20% in 2026). Not used. |
| Shared team shocks in the championship simulation | **Kept, partly.** The simulated 80% ranges now contain 82 to 85% of real outcomes against 53 to 65% before, but the title odds themselves did not clearly improve. |
| Comparing with bookmaker odds | No free source of past F1 odds was found, so only two races could be compared. It is a tool to keep adding to, not a result. |

Details and numbers for all of these are in [MODEL_NOTES.md](MODEL_NOTES.md).

## What it is not

- **Not a winner-picker that beats the pole sitter.** After qualifying, the grid does most of the work.
- **Weaker before the weekend**, where it swings with how dominant the leading car is.
- **Blind to chaos.** Safety cars, first-lap incidents, strategy and weather are not predicted.
- **Working with little data on the newest rules.** The 2026 regulations reset the pecking order, and
  only 18 races of this era exist so far.
- **Untested on a real Windows or Mac machine** for the daily-update scripts
  (`Schedule_Windows.bat`, `Schedule_Mac.command`).

## Command reference

| command | what it does |
|---|---|
| `python run_all.py --out Predictions` | Everything: score the tracker, predict the remaining races, simulate the championship |
| `python run_all.py --refresh --out Predictions` | The same, after downloading the latest data and refitting |
| `python predict.py` | The next race only, at the most informed stage available |
| `python predict.py --race 2026-18` | Replay a past race using only the races before it |
| `python predict_season.py` | Every remaining race in one file |
| `python simulate_season.py --runs 50000` | Championship odds with more simulated seasons |
| `python tracker.py score` | Score saved predictions against real results |
| `python odds.py` | Compare with the bookmaker odds in `odds.csv` (`python odds.py template 2026-20` makes a blank sheet) |
| `python overrides.py check` | Show what each line of `overrides.csv` does |
| `python lineup.py` | Show the entry list used for each remaining race, and where it came from |
| `python fetch_data.py`, `python train.py` | Download the data; retrain from scratch (20 to 30 minutes) |

Tests: `python test_no_leakage.py`, `python test_overrides.py`, `python test_lineup.py`,
`python test_odds.py`.

## What is in the repository

```
run_all.py             one command: tracker, predictions, championship, page data
fetch_data.py          download and cache f1db data -> data/
features.py            leakage-safe features for the three stages
train.py               tuning, back-test, calibration, final models, reports
predict.py             one race (or replay a past one); predict_season.py: all remaining races
simulate_season.py     championship simulation (simcore.py holds the race model)
lineup.py              who is on the grid; overrides.csv for manual changes
tracker.py             save predictions before a race, score them after
odds.py / odds.csv     model against bookmaker odds
ablation.py, recency_test.py, dnf_shift_test.py, season_backtest.py   the experiments above
test_*.py              the tests
reports/               back-test, experiments, calibration chart
data/  models/  tracker/  site_data/   data, trained models, saved predictions, tables for a web page
MODEL_NOTES.md         the long version: every test and its numbers
```

## Data and credit

Race data comes from [f1db](https://github.com/f1db/f1db) and is used under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The files in `data/` are derived from it.

<!-- Add a LICENSE file for the code (MIT is a common choice) and mention it here. -->
