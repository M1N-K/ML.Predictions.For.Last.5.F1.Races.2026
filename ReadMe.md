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

A machine-learning model that predicts Formula 1 races: the finishing order, each driver's chance of
winning, reaching the podium or retiring, and the odds of the championship for the rest of the season.

It makes a prediction at three points of a race weekend, because information arrives as the weekend
goes on: **before the weekend**, **after practice** and **after qualifying**. Every prediction is saved
before the race and scored afterwards, so the model's real record builds up in public rather than
being judged only on past data.

> Unofficial hobby project. Not affiliated with Formula 1 or the FIA. Not betting advice.

![Do the model's percentages match reality?](reports/calibration.png)

*Do the model's percentages match reality? 88 races (2023 to 2026) that were never used to choose
any setting. Close to the dotted diagonal is good. Win and podium chances are close; the highest
retirement chances are too high.*

## What it does

- Predicts the finishing order, with P(win), P(podium) and P(retirement) for every driver
- Predicts every remaining race of the season, and simulates the championship 20,000 times from the
  real standings (drivers' and constructors' title odds, and when the title could be decided)
- Works out who is on the grid by itself (season entry list, practice attendance), with a small
  file for changes you know about (driver out, replacement, grid penalty)
- Saves each prediction before the race and scores it afterwards (`tracker.py`)
- Compares its win chances with bookmaker odds you type in (`odds.py`)
- Writes everything as plain text files you can open in Notepad

## How accurate is it?

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
- Even 191 races is a small sample for winner calls; a few percentage points either way is noise.
  Every comparison is tested on the same races with a 95% interval (`reports/backtest_summary.md`).

## Example output

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

## Quick start

```bash
git clone https://github.com/<your-username>/f1-race-predictor.git
cd f1-race-predictor
pip install -r requirements.txt
python run_all.py --out Predictions
```

That uses the data and trained models in the repository and takes under a minute. The prediction
files appear in `Predictions/`. Developed and tested on Python 3.13.

To get the latest results first (after a race, or after practice or qualifying), then refit:

```bash
python run_all.py --refresh --out Predictions
```

Retraining from scratch (`python fetch_data.py`, then `python train.py`) takes 20 to 30 minutes.
On Windows or Mac you can also double-click `Run_Predictions` (see `START HERE.txt`).

## How it works

- **Data:** [f1db](https://github.com/f1db/f1db), every race from 2014 (the hybrid era): results,
  qualifying, practice, pit stops, sprints and standings.
- **Models:** LightGBM. A ranking model orders the whole field; classifiers give P(win),
  P(podium) and P(retirement). One set per stage (before the weekend, after practice, after
  qualifying), each seeing more information than the last.
- **No peeking at the future:** every form feature uses only races before the one being predicted.
  `test_no_leakage.py` blanks out what isn't known yet at each stage and checks that the model's
  inputs don't change.
- **Championship simulation:** each remaining race is played 20,000 times, with drivers retiring at
  their predicted rate and random luck whose size was fitted on past seasons. Teams share a pace
  "shock" that carries from race to race, which fixed ranges that were too narrow when each race was
  treated as independent.

## What I tried that did not help

Most of the later work was testing ideas fairly and leaving out the ones that failed. An idea is only
kept if it gives a clear gain, meaning a 95% interval that excludes zero. For the retirement shift I
tightened that rule after seeing that my first version of it would have accepted a gain inside the noise.

| idea | result |
|---|---|
| Driver-versus-car ratings, and circuit-type features | No clear gain at any stage; together they were clearly worse on win chances after qualifying. Built and tested, switched off. |
| Count recent seasons more when training | Finishing order got clearly worse on 2023 to 2026. Not used. |
| Shift the retirement chance to the recent retirement rate | Gain was inside the noise. The over-prediction mostly comes from retirements varying from year to year (14% in 2019, 20% in 2026). Not used. |
| Shared team shocks in the championship simulation | **Kept, partly.** The simulated 80% ranges now contain 82 to 85% of real outcomes against 53 to 65% before, but the title odds themselves did not clearly improve. |
| Comparing with bookmaker odds | No free source of past F1 odds was found, so only two races could be compared. It is a tool to keep adding to, not a result. |

Details and numbers for all of these are in [MODEL_NOTES.md](MODEL_NOTES.md).

## Limitations

- After qualifying, the grid does most of the work.
- Before the weekend the model is weaker and swings with how dominant the leading car is.
- Safety cars, first-lap incidents, strategy and weather are not predicted.
- New regulations (2026) reset the pecking order, and only 18 races of this era exist so far.
- The daily-update scripts (`Schedule_Windows.bat`, `Schedule_Mac.command`) have not been tested on
  a real Windows or Mac machine.

## Repository guide

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
test_*.py              tests (no leakage, overrides, line-up, odds)
reports/               back-test, experiments, calibration chart
data/  models/  tracker/  site_data/   data, trained models, saved predictions, tables for a web page
MODEL_NOTES.md         the long version: every test and its numbers
```

Run the tests with `python test_no_leakage.py`, `python test_overrides.py`, `python test_lineup.py`
and `python test_odds.py`.

## Data and credit

Race data comes from [f1db](https://github.com/f1db/f1db) and is used under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The files in `data/` are derived from it.

<!-- Add a LICENSE file for the code (MIT is a common choice) and mention it here. -->
