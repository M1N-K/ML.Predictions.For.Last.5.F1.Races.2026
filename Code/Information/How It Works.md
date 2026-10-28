# How the code works

A guided tour of the Python in this repository: what each file does, how data moves between them, and
where to change things. It is written for someone who wants to read, modify or extend the code. For
installing and running it, see `GET_STARTED.md`. For the test results and what did not help, see
`MODEL_NOTES.md`.

About 4,000 lines of Python in total, including tests. Every script is meant to be run **from the project
folder**, because paths such as `data/results.csv` are relative.

## The pipeline at a glance

```
  f1db on GitHub
        |   fetch_data.py
        v
  data/results.csv  races.csv  weekend.csv  entrants.csv  standings_*.csv
        |   features.build_features()      one row per driver per race
        v
  train.py  ---->  models/f1_models.joblib   +   reports/*  (back-test, calibration, ...)
        |
        v
  engine.py   line-up -> overrides -> features -> stage -> models -> table
        |
        +-- predict.py           one race (or a replay of a past one)
        +-- predict_season.py    every remaining race
        +-- simulate_season.py   championship odds (uses simcore.py)
        +-- tracker.py           save predictions before a race, score them after
        +-- odds.py              compare with bookmaker odds you type in
        +-- export_site_data.py  tables for the dashboard  ->  site_data/*.csv  ->  index.html

  run_all.py runs the steps above in order.
```

## Files, grouped by job

### Data

| file | job |
|---|---|
| `fetch_data.py` | Downloads race files from [f1db](https://github.com/f1db/f1db) and builds the CSVs in `data/`. |
| `data/results.csv` | One row per driver per race: grid, qualifying, finishing position, laps, points, retirement reason. |
| `data/races.csv` | One row per race: date, circuit, laps, length, corners, `has_results`, `is_sprint`. Includes the upcoming race. |
| `data/weekend.csv` | Practice pace, sprint results and pit stops for each driver and race. |
| `data/entrants.csv` | Which driver races for which team in which rounds of a season. |
| `data/standings_drivers_<year>.csv`, `standings_constructors_<year>.csv` | The official points tables for the current season. |
| `data/raw/` | Cached downloads (git-ignored, rebuilt by `fetch_data.py`). |

`fetch_data.py` is cheap to re-run. Cached files are reused, new rounds are discovered by trying each grand
prix id in a pool until a folder exists, and races without results yet are checked again each time. Files that
do not exist (for example, no sprint) are remembered with a `.none` marker so they are not requested again.
Options: `--first-year` (default 2014), `--last-year`, `--workers`.

### Features and models

| file | job |
|---|---|
| `features.py` | Builds every model input. Defines the three feature sets. |
| `train.py` | Tunes, back-tests, calibrates and saves the models. Also holds the fit functions and metrics. |
| `engine.py` | Shared prediction logic: line-up, overrides, stage choice, scoring a race. |
| `models/f1_models.joblib` | The saved models plus the settings they were trained with. |

### Using the models

| file | job |
|---|---|
| `predict.py` | One race. Writes a text table and saves to the tracker. |
| `predict_season.py` | Every remaining race in one text file. |
| `simulate_season.py`, `simcore.py` | Championship simulation. `simcore.py` is the race model; `simulate_season.py` is the season around it. |
| `tracker.py` | Saves predictions before a race and scores them afterwards. |
| `lineup.py` | Works out who is on the grid for a race that has no qualifying yet. |
| `overrides.py`, `overrides.csv` | Manual changes: driver out, replacement, extra car, team change, grid penalty. |
| `odds.py`, `odds.csv` | Model against bookmaker odds. |
| `export_site_data.py` | Writes the tables the dashboard reads. |
| `make_charts.py` | Draws `reports/calibration.png` from `reports/calibration.csv`. |
| `run_all.py` | One command that runs everything above. |

### Experiments (not needed to run the tool)

| file | question it answers | writes |
|---|---|---|
| `season_backtest.py` | How much should simulated races depend on each other? | `reports/dependence.json` and `dependence_*` |
| `ablation.py` | Do driver-versus-car ratings or circuit-type features help? | `reports/ablation_*` |
| `recency_test.py` | Should recent seasons count more in training? | `reports/recency_*` |
| `dnf_shift_test.py` | Can the retirement chance be fixed by shifting it to the recent rate? | `reports/dnf_shift_*` |

### Tests

`test_no_leakage.py`, `test_overrides.py`, `test_lineup.py`, `test_odds.py`. Each prints PASS or FAIL per
check and exits with code 1 if anything fails.

### Dashboard and launchers

`index.html` is a single static page. It fetches `site_data/*.csv` in the browser and draws everything with the
bundled copy of d3 in `assets/`. The `.bat` and `.command` files are thin wrappers around `run_all.py`.

## Conventions used everywhere

- **`race_id`** is `YYYY-NN`, the year and round number (for example `2026-18`). Plain string comparison
  therefore sorts races in order, and the code relies on that.
- **`driver_id`** and team ids are lower-case slugs from f1db, such as `max-verstappen` or `red-bull`.
  `pretty()` turns a slug into a display name.
- **Stage** means how much of the weekend is known: `pre` (before the weekend), `fp` (after practice) or
  `post` (after qualifying and any sprint).
- **Team lineage.** `features.TEAM_LINEAGE` maps renamed teams to one id (for example `alphatauri` and `rb` to
  `racing-bulls`, `kick-sauber` and `audi` to `sauber`), so a team keeps its history through rebrands. The
  column is called `team`. `constructor_id` is the raw f1db id.
- **Lower is better** for positions and for `finish_pct`, `pace_pct`, `quali_gap_pct` and similar columns.

## `features.py`: building the inputs

`build_features(res, weekend, races)` takes the results table and returns one row per driver per race, with
features and targets together. Rows for races that have not been run have no targets and `completed` false.

### The leak rule

Every history feature for race *t* is computed from races strictly before *t*. In practice every rolling
average is `shift(1)` first, then an exponentially weighted mean (`_ewm_prior`). Information about the race
itself is kept in separate groups, and each stage only receives the groups that are known by then.
`test_no_leakage.py` checks this by blanking out what is not yet known at each stage and confirming the
model inputs do not change.

### Targets

- `final_rank`: classified finishers in order, then retirements ordered by laps completed, then disqualified
  drivers last. Ties break on grid slot.
- `finish_pct = (final_rank - 1) / (n_starters - 1)`: finishing position scaled to 0 to 1.
- `pace_pct`: the same, but only for drivers who finished (so a crash does not look like slow pace).
- `dnf`: 1 for a retirement (`DNF`, `NC`, or a classified position with a retirement reason). Missing for
  races without a result. Drivers who never started (`DNS`, `DNP`) are dropped.
- `win`, `podium`, `points_share` are derived from `final_rank` and points.

### Feature groups and sets

| group | examples | known when |
|---|---|---|
| `PRE_V1` | driver and team form (`d_finish_ewm3`, `c_gap_ewm10`), circuit history, season points, rank within the field | before the weekend |
| `PIT_HISTORY` | `c_stops_ewm5`, `c_pit_time_ewm5`, `circ_stops_mean` | before the weekend (history only: pit stops are a result of the race they belong to) |
| `PRACTICE` | `fp_best_gap`, `fp_best_rk`, `c_fp_gap`, `fp_vs_form` | after practice |
| `POST_EXTRA` | `grid`, `quali_gap_pct`, `grid_penalty`, `pit_lane`, gaps to team-mate | after qualifying |
| `SPRINT` | `sprint_pct`, `sprint_dnf`, `sprint_quali_gap` | after a sprint weekend's sprint |

The names in the form features say how they are built: `d_` is driver, `c_` is team, `ewm3` is an exponentially
weighted mean with a half-life of 3 races, and `_rk` is the percentile rank within that race's field.

The production sets are built by stacking:

```
PRE  = PRE_V1 + PIT_HISTORY + is_sprint        41 features
FP   = PRE + PRACTICE                          50 features
POST = FP + POST_EXTRA + SPRINT                62 features
```

`pre_v1` (37 features) and `post_v1` (46) are the first version of the model, kept only so the back-test can
show what the additions are worth. They are never used to predict a real race.

### Computed but switched off

`rating_channel` (an online estimate of how much of a result is the car and how much the driver) and the
circuit-kind features (`circ_street`, `circ_turns_km`, `d_class_adv` and so on) are calculated for every row,
but they are **not** in the production sets. The ablation found no clear gain, and a small loss at the `post`
stage. To switch them on, add `RATINGS` or `CIRCUIT` to the lists near the top of `features.py`. The
rating speeds are fitted by `python features.py tune`, using races before 2023 only.

### Eras

`ERA_START_YEARS = [2014, 2017, 2022, 2026]` marks regulation changes. `era_race_idx` counts races since the
start of the current era, and the car ratings shrink at each new era (new cars, old drivers).

## `train.py`: tuning, back-test, saving

### The models

Four LightGBM models per stage, so 12 in the saved bundle.

| model | type | target | output |
|---|---|---|---|
| `ranker` | `LGBMRanker`, LambdaRank | relevance is championship points for the finishing place (25, 18, 15 ... 1, then 0) | a score per driver; sorting by it gives the predicted order |
| `win` | binary classifier | `final_rank <= 1` | P(win), scaled within each race to sum to 1 |
| `podium` | binary classifier | `final_rank <= 3` | P(podium), scaled within each race to sum to 3 |
| `dnf` | small, heavily regularised classifier (5 leaves, 150 trees) | retirement | P(retire) |

Shared settings are in `BASE` (learning rate 0.03, 80% row and column sampling, `reg_lambda` 5). Tree counts
and leaf counts are chosen per stage by a grid search on the 2022 season (trained on earlier seasons only):
rankers by mean Spearman correlation per race, classifiers by log loss.

### What `main()` does, in order

1. **Tune** on 2022, for all five feature sets.
2. **Walk-forward back-test** over 2018 to 2026. To predict season *Y*, the models see only seasons before *Y*.
   Compares each model with baselines (grid order, recent driver form, grid-slot frequency, a uniform guess).
3. **Paired bootstrap** (4,000 resamples of whole races) on the difference between pairs of models. A
   difference counts as "clear" only if its 95% interval excludes zero.
4. **Calibration**: bins predicted chances and compares them with what happened, plus a test of whether a
   simple recalibration would help (fitted on 2018 to 2023, scored on 2024 to 2026).
5. **Simulation randomness**: fits one temperature per stage for the championship simulation
   (`simcore.fit_temperature`).
6. **Report**: writes `reports/backtest_summary.md` and the supporting CSVs.
7. **Final models**: refits on every completed race and saves `models/f1_models.joblib`, `feature_importance.csv`
   and `metrics.json`.

`python train.py --fast` skips steps 1 to 6. It refits the final models on the latest data, reusing the saved
settings, in about ten seconds. This is what `run_all.py --refresh` calls. A full `python train.py` takes 20
to 30 minutes.

### Evaluation vocabulary

- `winner_hit`: did the top-ranked driver win?
- `podium_overlap`, `top10_overlap`: share of the real top 3 or top 10 that the prediction had in its own.
- `spearman`, `mae_pos`: rank correlation with the real order, and mean error in places.
- Log loss and Brier score for probabilities. ECE (expected calibration error) is the average gap between
  predicted and observed frequency across bins.
- `CLEAN_FROM = 2023`: seasons after the tuning season, never used to make any choice. Quote these numbers
  when you want an honest figure.

### The saved bundle

`models/f1_models.joblib` is a dictionary with `models` (keys like `ranker_post`, `win_fp`, `dnf_pre`),
`best_params` and `best_params_clf` (the chosen tree settings per stage), `pl_tau` (the simulation temperature
per stage), `features`, and `trained_through` (the last race the models saw). Because it is a pickle, it
depends on the library versions that built it. If loading fails, run `python train.py`.

## `engine.py`: from a race id to a table

`engine.py` is the glue that `predict.py`, `predict_season.py`, `simulate_season.py` and `export_site_data.py` share.

1. **`build_frame(res, races, weekend, targets)`** builds features for all races, with the upcoming `targets`
   filled in. For each target with no entries yet it calls `lineup.resolve`, then `overrides.apply`, then
   `features.build_features`. It also fills two module-level lists, `LINEUP_NOTES` and `NOTES`, with plain
   English descriptions of what changed. The scripts print these.
2. **`stage_for(rows)`** picks the most informed stage the data supports:
   `post` if every driver has a grid slot, `fp` if at least 10 drivers have a practice time, otherwise `pre`.
3. **`bundle_models` / `train_models`** get the four models for a stage: either the saved ones, or, for an
   honest replay of a past race, models trained on only the races before it (with the saved tuning settings).
4. **`predict_rows`** adds `score`, `p_win`, `p_podium`, `p_dnf` and the predicted order `pred`.
5. **`display_table`** formats the readable table.

## `lineup.py` and `overrides.py`: who is racing

Before qualifying there is no entry list, so one has to be worked out. The old approach copied the previous
race, which is wrong about 4 races in 10 (mostly at the start of a season). `lineup.resolve` improves on it
in three steps:

1. Start from the last completed race's line-up.
2. If `data/entrants.csv` gives at least 16 drivers for the round, use that instead. A driver whose declared
   rounds end at the latest round run so far is taken to be continuing, because f1db only writes rounds that
   have happened.
3. Once all three practice sessions have been run (at least 18 drivers in `weekend.csv`), a line-up driver who took
   part in no session is removed. The reverse is deliberately not done, because reserve drivers practise too.

`overrides.apply` then applies `overrides.csv` on top. Roster actions (`out`, `replace`, `add`, `team`) run before
grid penalties, and only races without a result can be changed. Driver names are matched loosely (a surname is
enough), and a wrong name gives a "did you mean" suggestion. A penalty needs a grid, so it has no effect before
qualifying, because the model does not use the grid until then.

## `predict.py` and `predict_season.py`

`predict.py` predicts one race: the next one by default, or `--race 2026-18` to replay a past one. For a past
race it retrains on the races before it, so the replay is honest, and prints a check against the real result.
For an upcoming race it uses the saved models and saves the prediction to the tracker.

`predict_season.py` does every remaining race in one pass. It builds the feature frame once with all the upcoming
line-ups, then predicts each race at the best stage its own data supports. Races further ahead only know
results up to the last completed race, which is why they are less certain. It saves **only the next race**
to the tracker. The function `predict_remaining` is reused by the simulation and the dashboard export.

## `tracker.py`: an honest record

`save()` writes one row per driver to `tracker/predictions.csv` with the time, stage and `trained_through`. It
**refuses** to save a race that already has a result, so the record cannot be back-filled. Saving the same
race and stage again replaces the earlier copy, so the record holds the last prediction made at each stage.

`score()` matches saved predictions with real results, computes the same metrics as the back-test, and also
scores the starting grid order as a reference. It writes `tracker/scorecard.csv` and `Predictions/scorecard.txt`.

## `simcore.py` and `simulate_season.py`: championship odds

### One race (`simcore.award`)

For every simulated run, each driver:

1. retires with probability `p_dnf`;
2. otherwise gets a value `score / tau + Gumbel noise`, and the running cars are ordered by that value (a
   Plackett-Luce draw);
3. is awarded points from the table (25, 18, 15, 12, 10, 8, 6, 4, 2, 1; or 8 to 1 for a sprint).

A small `tau` follows the model's order strictly, and a large one is closer to random. `fit_temperature`
chooses `tau` for each stage on the back-test by combining the error in simulated expected points with the
log loss of the simulated win chance.

### Races that depend on each other (`simulate_races`)

If every race were an independent draw, the simulation would be too sure of itself over a season, because
a team that is better or worse than the model thinks stays that way for many races. So each team and each driver
gets a **pace shock** that carries from race to race:

```
shock_k = rho * shock_(k-1) + Normal(0, sd)
```

The sizes (`sd_team`, `sd_driver`, `rho`) are fitted by `season_backtest.py` and stored in
`reports/dependence.json`. At present `rho` is 1.0, so a shock is a random walk. Retirements get **no**
shared shocks (`sd_rel` is 0), because the replay found no sign that a team's retirements follow one another.
A race predicted from its own weekend's grid or practice (flagged `fresh`) gets no shock, and the shocks start with
the first race after the fresh ones. If `dependence.json` is missing, races are independent and a note is printed.

### The season (`simulate_season.py`)

1. Load the real standings from `data/standings_*.csv`.
2. Call `predict_remaining` to get scores and retirement chances for every remaining race.
3. Simulate all remaining races for 20,000 runs (`--runs` changes this), adding the points to the real standings.
4. Count how often each driver and team finishes first or in the top 3, and take the 10th and 90th percentile of
   the final points.
5. Work out when the title could be settled: the share of runs in which the leader's lead after race *r*
   exceeds the points still available.

Constructors' points are the sum of that team's drivers' simulated points. Simplifications: no fastest-lap
point, and only classified finishers score. Intermediate tables go to `reports/site/`, and
`export_site_data.py` copies them into `site_data/`.

## `odds.py`

Reads `odds.csv`, converts each price to a chance, and compares it with the model's.

- Formats: American odds need the `+` sign (`+120`, `-150`), fractional is `a/b`, and a plain number is decimal.
- The bookmaker margin is removed by scaling each source in proportion so it adds up to 100%.
- Where several sources price a driver, the chances are averaged. A driver nobody prices gets a small
  tail chance (`--tail`, default 0.4%), and the report prints how much that assumption moves the favourite.
- The model's chance comes from `tracker/predictions.csv` for the matching stage, or from
  `reports/backtest_predictions.csv` for older races.
- For a finished race it scores both sides: log score of the real winner, Brier score and favourite-hit.
- `python odds.py template 2026-20` writes a blank sheet with that race's drivers.

## `export_site_data.py` and the dashboard

`export_site_data.py` writes nine tables to `site_data/`: `race_predictions`, the four `title_*` tables,
`model_accuracy`, `calibration`, `scorecard` and `meta`. `index.html` fetches them with `fetch` and `d3.csvParse`,
so it must be served over http. Opening it from a file does not work. To refresh the page, run
`run_all.py --refresh`, then commit and push `site_data/`.

## `run_all.py`: the order of steps

```
[--refresh]  fetch_data.py  ->  train.py --fast
tracker.py score
predict_season.py            (also saves the next race to the tracker)
odds.py                      (only if odds.csv exists; a typo there does not stop the run)
simulate_season.py
export_site_data.py
```

Each step is a separate Python process, so a failure names the step that broke.

## Common changes

**Add a feature.**
1. Compute it in `build_features`, using `shift(1)` before any rolling or expanding calculation if it describes
   the past.
2. Add its name to the right list in `features.py` (`PRE_BASE`, `PRACTICE`, `POST_EXTRA`, ...). Anything in
   `PRE_BASE` is available at every stage.
3. Run `python test_no_leakage.py`. If a feature uses this weekend's information, it must not be in a stage
   that cannot know it.
4. Run `python train.py` and read the paired bootstrap in `reports/backtest_summary.md` before keeping the
   feature. `ablation.py` shows how to compare variants with and without a group of features. The rule in this
   project is to keep an idea only when the 95% interval excludes zero.

**Change a model setting.** `BASE`, `GRID` and `GRID_CLF` are at the top of `train.py`. Re-run `python train.py`
afterwards, because the saved bundle and the simulation temperatures both depend on it.

**Change the points system.** Edit `RACE_POINTS` and `SPRINT_POINTS` in `simcore.py` and `POINTS` in `train.py`
(the ranker's target uses it). Retrain.

**Add new data.** `python fetch_data.py` finds new rounds and refreshes the standings by itself. At a regulation
change, add the new year to `ERA_START_YEARS` in `features.py`.

**Add a new script that uses the models.** Import `engine as E`, then:
`E.build_frame(...)`, `E.stage_for(...)`, `E.bundle_models(E.load_bundle(), stage)` and `E.predict_rows(...)`.

## Things to know before changing anything

- **Run from the project folder.** Paths are relative.
- **`engine.py` imports `train.py`** for the fitting functions, so importing the engine pulls in LightGBM.
- **`LINEUP_NOTES` and `NOTES` are module-level lists** that `build_frame` clears and refills on each call.
- **Upcoming races have no targets.** Anything computed from `final_rank` or `dnf` is missing for them by design.
- **The back-test only measures what it measures.** 191 races is a small sample for winner calls. Differences of a few
  percentage points are inside the noise, and `MODEL_NOTES.md` lists the experiments that did not help.
- **Git ignores** `data/raw/`, `Predictions/`, `__pycache__/` and `reports/dependence_stale_predictions.pkl`,
  all of which are rebuilt by the scripts.
