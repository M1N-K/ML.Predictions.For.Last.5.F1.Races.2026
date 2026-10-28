# F1 race predictor: detailed notes

This is the long version: how the model works, every test and its numbers, and the limits. The short
introduction for new readers is in [README.md](README.md).

Machine-learning model that predicts the finishing order of a Formula 1 race, each driver's
probability of winning, making the podium and retiring, and the championship odds for the rest of
the season.

Data: [f1db](https://github.com/f1db/f1db) (CC BY 4.0), every race from 2014 (the hybrid era)
through the latest completed round: results, qualifying, free practice, pit stops, sprints and
championship standings. Model: LightGBM.

## Quick start

```bash
pip install -r requirements.txt
python fetch_data.py           # download the data (~1 min the first time)
python train.py                # tune, backtest, calibrate, save models (20-30 minutes)
python run_all.py              # predict the rest of the season + simulate the championship
```

Or just double-click `Run_Predictions` (see `START HERE.txt`).

| command | what it does |
|---|---|
| `python run_all.py --out Predictions` | Everything: score the tracker, predict the remaining races, simulate the championship, write the web-page data (`site_data/`). |
| `python run_all.py --refresh` | Download the latest data and refit first. Use after practice, qualifying or a race. |
| `python predict.py` | The next race only. Uses the most informed stage available. |
| `python predict.py --race 2026-18` | Replay a past race using only the races before it. |
| `python predict.py --mode pre\|fp\|post` | Force how much information is used. |
| `python predict_season.py` | Every remaining race in one text file. |
| `python simulate_season.py --runs 50000` | Championship odds (default 20,000 simulated seasons). |
| `python overrides.py list` / `check` | Names you can use in `overrides.csv` / what each line there would do. |
| `python tracker.py score` / `status` | Score saved predictions against real results / list what is saved. |
| `python test_no_leakage.py` | Check that no stage uses information from the future. |
| `python test_overrides.py` | Tests for the manual-changes file. |
| `python lineup.py` | Show the entry list used for each remaining race and where it came from. |
| `python test_lineup.py` | Tests for the automatic entry list. |
| `python recency_test.py` | Re-run the "should recent seasons count more?" test (about 10 minutes). |
| `python dnf_shift_test.py` | Re-run the retirement-rate shift test (a few minutes). |
| `python ablation.py` | Re-run the "do the extra features help?" test over 2018-2026 (about 10 minutes). |
| `python season_backtest.py` | Re-run the replay of past seasons that fits the simulation's shared shocks (about 10 minutes). |
| `python make_charts.py` | Redraw `reports/calibration.png`. |

## How it works

**Three stages, because information arrives as the weekend goes on.**

- **pre** (before the weekend): driver and team form, team qualifying pace, circuit history,
  championship position, how each driver compares with the field, team pit-stop history,
  whether it is a sprint weekend.
- **fp** (after practice): everything above plus this weekend's practice pace (best and average
  gap to the fastest car, laps run, comparison with the team-mate and with recent form).
- **post** (after qualifying): everything above plus the grid, qualifying gap to pole, grid
  penalties / pit-lane starts, team-mate gap and, on sprint weekends, the sprint result and
  sprint-qualifying gap.

**Three LightGBM models per stage.**

- A *LambdaRank* model orders the whole field. Its training label is championship points for the
  finishing position (25, 18, 15, ... 1, then 0).
- Classifiers give P(win) and P(podium), normalised within each race so they sum to 1 and 3, and
  P(retirement).

**Championship simulation.** Each remaining race is played 20,000 times: drivers retire with
their predicted probability, the rest are ordered by the model's score plus random luck whose
size was fitted on the back-test, and points (race and sprint) are added to the real current
standings. **The races depend on each other**: each team (and, less, each driver) gets a pace
shock that builds up and carries from race to race, so a team that is better or worse than the
model thinks stays so for several races. The size of the shocks was fitted by replaying past
seasons (see "Shared shocks" below).

**No leakage.** Every form feature uses only races strictly before the one being predicted, and
`test_no_leakage.py` blanks out what is not yet known at each stage and confirms the model inputs
do not change (passes for all three stages; the rating and circuit features that are switched off
were checked the same way while they were included). Renamed teams (e.g. Force India -> Racing Point -> Aston Martin) share one history.

## Results

Walk-forward back-test: for each season the models are trained only on earlier seasons. Settings
(tree sizes) were chosen on 2022, so 2022 and earlier are not a clean test of those choices; the
2023-2026 table is the one nothing was tuned on. Both are shown.

**2018 to 2026 round 18: 191 races**

| model | winner correct | podium drivers right (of 3) | top-10 right (of 10) | rank correlation | avg position error |
|---|---|---|---|---|---|
| post (after qualifying) | 53.4% | 2.05 | 7.84 | 0.666 | 3.29 |
| baseline: grid order | 54.5% | 2.07 | 7.64 | 0.628 | 3.46 |
| fp (after practice) | 46.6% | 1.77 | 7.58 | 0.626 | 3.62 |
| pre (before the weekend) | 43.5% | 1.76 | 7.46 | 0.603 | 3.75 |
| baseline: recent driver form | 44.0% | 1.63 | 7.39 | 0.584 | 3.85 |

**2023 to 2026 round 18: 88 races (never used for any choice)**

| model | winner correct | podium drivers right (of 3) | top-10 right (of 10) | rank correlation | avg position error |
|---|---|---|---|---|---|
| post (after qualifying) | 62.5% | 2.02 | 8.02 | 0.695 | 3.12 |
| baseline: grid order | 61.4% | 2.03 | 7.82 | 0.664 | 3.27 |
| fp (after practice) | 44.3% | 1.62 | 7.69 | 0.632 | 3.61 |
| pre (before the weekend) | 42.0% | 1.66 | 7.64 | 0.622 | 3.67 |
| baseline: recent driver form | 39.8% | 1.58 | 7.53 | 0.603 | 3.75 |

**Is the improvement real?** `reports/backtest_summary.md` tests every comparison on the same
races with a 95% interval. Findings:

- After qualifying, the model orders the field better than "grid order" (rank correlation +0.038,
  position error -0.17 places, both clear over 2018-2026) but it does **not** pick the winner
  better: 53.4% against 54.5%, a difference well inside the noise. For "who wins", the pole sitter
  is about as good.
- Practice pace helps a little: after practice vs before the weekend is +0.023 rank correlation
  and -0.13 places over 2018-2026 (clear), but only +0.011 (not clear) on 2023-2026 alone.
- Before the weekend the model beats "recent driver form" on rank correlation (+0.019, clear) but
  not on winner calls.
- The pit-stop, practice and sprint information added after the first version makes no clear
  difference to the after-qualifying or before-the-weekend results (+0.002 and -0.003 rank
  correlation, intervals include zero). The practice stage is what carries the gain above.

**Two things tried and left out.** `ablation.py` compares the model with and without
(a) *driver-versus-car ratings* (an online estimate of how much of a result is the car and how
much the driver, with the car part fading when regulations change) and (b) *circuit kind* (street
or permanent, corners per kilometre, length, and how a driver/team does on circuits of the same
kind). Over 2018-2026, neither gives a clear gain at any stage and the combination is clearly worse
on win log loss after qualifying (+0.0017, interval +0.0002 to +0.0033), so they are computed
(`features.RATINGS`, `features.CIRCUIT`) but not used. See `reports/ablation_summary.md`.
The ratings are interesting on their own: for the latest race they put Verstappen's driver rating
far ahead of everyone else's and Mercedes' race-pace car rating at the top.

**Calibration** (do "30%" predictions happen about 30% of the time?): the average gap between
predicted and observed frequency is about 1 percentage point for wins and podiums at every stage
(`reports/calibration.png`). A recalibration step did not improve them, so none is applied.
Retirement chances run too high over 2018-2026 (17.3% predicted, 14.6% observed); that comes from
the early seasons, when models trained on 2014-2017 (more retirements) predicted for a more reliable
era. 2020-2025 are close to right.

## Tried and not adopted: recency weighting and a retirement-rate shift

Retirement chances run too high in the back-test and the pecking order resets with regulations, so
two fixes were tried (`recency_test.py`, `dnf_shift_test.py`, details in `reports/recency_summary.md`
and `reports/dnf_shift_summary.md`):

- **Count recent seasons more** (a training race counts half as much for every 1.5, 3 or 6 years it is
  older). It made things worse or no better everywhere: finishing order on 2023-2026 got clearly worse
  (rank correlation -0.020 at 1.5 years, -0.010 at 3, -0.004 at 6) and win/podium and retirement
  log loss did not improve. Models stay unweighted.
- **Shift the retirement chance to the recent retirement rate.** The gain was 0.0004 in log loss,
  well inside the noise, and the average predicted rate barely moved (17.4% -> 16.7% against 14.8%
  observed). The over-prediction is mostly year-to-year swings in how many cars retire (14% in 2019,
  20% in 2026), which these features cannot predict. Not adopted. (My first version of the rule would
  have adopted it on a better point estimate alone; I raised the bar to the "clear gain" standard used
  everywhere else.)

## Shared shocks in the championship simulation

`season_backtest.py` replays 2018-2025 from three cut points per season (30%, 50%, 70% of the
races): it hides the races after the cut, predicts them from what was known then, simulates the
rest of the season, and compares with what happened.

| | share of drivers whose real remaining points fell inside the simulated 80% range | 50% range | CRPS (lower is better) |
|---|---|---|---|
| independent races, 2018-22 | 65% | 39% | 12.25 |
| independent races, 2023-25 | 53% | 30% | 19.18 |
| with shared shocks, 2018-22 | 85% | 59% | 11.47 |
| with shared shocks, 2023-25 | 82% | 50% | 16.39 |

- The model's misses for a team are strongly correlated from one race to the next (about 0.35-0.40
  at 1 to 4 races apart), team-mates' misses are correlated within a race (0.48), but a team's
  retirements are not correlated from race to race (0.03, interval -0.01 to +0.07). So the
  simulation gets shared **pace** shocks and no shared reliability shock.
- The settings were picked on 2018-2022 (the simplest setting within 0.5% of the best score) and
  checked on 2023-2025, which they never saw: ranges improve there too.
- **Title odds are not clearly better**: the log score of the real champion's simulated chance is
  worse in 2018-22 (0.25 -> 0.33) and unchanged in 2023-25 (0.67 -> 0.67), the Brier score worse
  then better (0.148 -> 0.181, 0.380 -> 0.344), over only 15 and 9 seasons-and-cut-points. The
  shocks mainly fix the ranges, not the odds. Details: `reports/dependence_summary.md`.

## Who is on the grid? `lineup.py`

Before qualifying there is no entry list, so the tool used to copy the previous race's. That is
wrong more often than you would think: in 2014-2026, 107 of 269 races started a different set of
drivers than the race before (mostly at the start of a season). Now:

1. The season's **entrant list** from f1db (`data/entrants.csv`, downloaded by `fetch_data.py`) says
   who drives for which team in which rounds. It covers mid-season swaps and, at the start of a
   season, the whole new line-up. f1db only knows rounds that have been run plus anything it has
   announced, so for an ordinary next race it agrees with the last race and changes nothing (it
   does today: Mexico has the same 22 drivers).
2. Once all three **practice sessions** have been run, a driver of the line-up who took part in none
   of them is taken out. Checked on 2014-2026: 77 drivers flagged this way, 76 really did not
   race. The reverse is not used: reserve drivers practise too, so someone who practised but is
   not in the line-up is not added (add them in `overrides.csv` if they are racing).
3. After qualifying the line-up is the real one, as before.

`overrides.csv` is applied on top. The notes appear in the prediction files. `python lineup.py`
shows the result for every remaining race.

## Manual changes: `overrides.csv`

Edit `overrides.csv` (instructions at the top) for a driver who is out, a replacement, an extra
car, a team change or a grid penalty, then run the predictions again. Every script reads it, so the
race predictions, championship simulation and web-page data all pick it up. Driver changes work at
every stage. A grid penalty can only have an effect after qualifying, because before that there is
no grid and the model does not use one. `python overrides.py check` shows what each line does;
`python test_overrides.py` runs the tests.

## Model against bookmaker odds: `odds.py`

Bookmaker odds are the hardest benchmark for a model like this, because they already include
everything the market knows (weather forecasts, team news, who looked fast in practice). `odds.py`
reads `odds.csv` (one row per driver and source: race, stage, source, date, driver, odds), turns the
prices into win chances, and sets them next to the model's. For a race not yet run it shows where
they disagree; for a race already run it scores both on the chance they gave the winner.

How the prices become chances: each price is 1/decimal odds; where several sources price a driver
the chances are averaged; a driver nobody prices gets 0.4% (`--tail`); then everything is scaled
to add up to 100%. Scaling removes the bookmakers' margin in the simplest way (in proportion), which
is not exact. The `stage` column says which model to compare with: odds taken before practice go
with `pre`, after practice `fp`, after qualifying `post`.

`python odds.py template 2026-20` writes a blank sheet with that race's drivers. Odds must be taken
**before** the race, like the tracker's predictions.

What is in `odds.csv` so far (28 October 2026), and what it shows:

- **No historical odds were available**, so there is no long back-test against the market. I found
  no free source of past F1 race odds that I could read. Only two races have odds: the United States
  GP (odds from 19 October, one site, 22 drivers) and the Mexico GP (four sources, 27 October).
  The prices were read from web pages by an automated page reader, so check them if the numbers matter.
- **United States GP, one race:** the winner Antonelli was given 19.2% by the model and 25.5% by
  the market. One race says nothing about which is better. (The model figure there is the back-test
  version, fitted on earlier seasons, not a prediction saved before the race.)
- **Mexico GP, not yet run:** model and market agree closely on the two favourites (model: Antonelli
  32.2%, Verstappen 31.8%; market about 29.7% and 33.6%). The biggest gap is Norris, 7.5% against
  about 5.0%.
- **How many races does it take?** It depends on the gap. In the 191-race back-test the
  after-qualifying model beat grid order by about 0.3 per race on the winner log score, and that took
  roughly 70 races to show. Two closer forecasters, a gap of 0.01, would need over 1,000. With five
  races left this season, the odds comparison can only be looked at, not used to judge the model.

`python test_odds.py` runs the tests. `run_all.py` runs the comparison whenever `odds.csv` exists.

## Web page and automatic updates

`export_site_data.py` (called by `run_all.py`) writes the tables behind the dashboard into
`site_data/`. There are two copies of the dashboard:

- **A standalone page in this folder, `index.html`**, which reads `site_data/*.csv` directly and can be
  hosted for free on GitHub Pages (Settings, Pages, deploy from branch `main`, folder `/ (root)`). It
  refreshes whenever the changed `site_data/` files are pushed, so no Claude step is needed. It is the
  hosted page's own markup and drawing code with a small data loader, its own colours and a local copy of
  d3 (`assets/d3.min.js`, ISC licence in `assets/d3-LICENSE.txt`). To view it on your own computer, run
  `python -m http.server` and open `http://localhost:8000/`; opening the file directly does not work.
  Checked in headless Chromium (desktop light and dark, phone width): all four tabs load, no console errors.
  Not checked on GitHub Pages itself.
- **A page hosted on claude.ai**, which is not part of this folder. See `REFRESH_PAGE.md` for how it is
  refreshed (it needs Claude for the upload step) and `ROUTINE_PROMPT.txt` for words to paste.

To keep the text files fresh without doing anything: `Schedule_Windows.bat` (Windows Task
Scheduler) or `Schedule_Mac.command` (macOS launchd) run `Refresh_Quietly` every day at 09:00 and
log to `Predictions/refresh_log.txt`. These two scripts have **not been tested on a real Windows or
Mac machine**.

## Honest limitations

- **The grid does most of the work.** After qualifying, the model orders the field better than "the
  order they started in" but does not pick winners better than the pole sitter.
- **Before the weekend it is weaker** and swings with how dominant the leading car is.
- **Even 191 test races is a small sample** for winner calls: a few percentage points either way is
  noise.
- **Randomness is not modelled beyond averages**: safety cars, first-lap incidents, strategy and
  weather are not predicted.
- **New regulations** (2026) reset the pecking order; only 18 races of this era so far.
- Predictions before qualifying use the most recent race's line-up, adjusted by the entrant list and
  practice attendance (see "Who is on the grid?"); an announced one-off substitute that f1db does not
  list yet needs `overrides.csv`.
- The championship simulation still ignores penalties and mid-season driver changes unless you add
  them to `overrides.csv`; retirements are independent between races; its title odds were not shown
  to be better than the independent version's (see above), only its ranges.
- Settings were chosen on 2022, so test seasons up to 2022 are slightly flattered; 2023 onward is
  clean.
- **The tracker starts empty.** It only counts predictions saved before a race, so its record
  builds up from the Mexico GP onwards.
- Not betting advice.

## Files

```
run_all.py             one command: tracker, predictions, championship, page data
fetch_data.py          download + cache f1db files -> data/*.csv
features.py            leakage-safe features, the pre / fp / post feature sets (+ rating and circuit-kind features, off)
train.py               tuning, back-test (2018-2026), calibration, final models, reports
engine.py              shared prediction logic
lineup.py              entry list of upcoming races (entrant list, practice attendance)
overrides.py / .csv    manual changes: drivers out/replaced/added, team changes, grid penalties
predict.py             predict one race or replay a past one
predict_season.py      predict all remaining races
simulate_season.py     championship simulation (uses simcore.py)
simcore.py             race simulation incl. the shared team/driver shocks
season_backtest.py     replay of past seasons that fits the shocks
ablation.py            do the extra features help? (2018-2026)
export_site_data.py    tables for the hosted page -> site_data/
tracker.py             save predictions, score them after the race
odds.py / odds.csv     model against bookmaker odds (win chance); you type the odds in
test_odds.py           tests for odds.py
test_no_leakage.py     checks the model never sees the future
test_overrides.py      tests for overrides.csv
test_lineup.py         tests for lineup.py
recency_test.py, dnf_shift_test.py   two ideas that were tested and not adopted
make_charts.py         calibration chart
Refresh_Quietly.*, Schedule_*.*   run the update by itself every day (untested)
REFRESH_PAGE.md, ROUTINE_PROMPT.txt   how to refresh the hosted page
models/                trained models (through the latest completed race)
reports/               back-test, ablation, season replay, calibration, championship
tracker/               saved predictions and scorecard
```
