# ML.Predictions.For.Last.5.F1.Races.2026

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


# F1 Race Predictor

A machine-learning model that predicts the finishing order of a Formula 1 race, plus each driver's chance of winning and of making the podium. It runs in two stages: before qualifying (form only) and after qualifying (form plus the starting grid).

![Accuracy after qualifying](reports/charts/01_accuracy_post.png)

## Results

Tested on 88 real races (2023 to round 18 of 2026). Each season was predicted using only the seasons before it, and all settings were chosen on 2021-2022, never on a test season.

| | Winner correct | Podium drivers right (of 3) | Rank correlation |
|---|---|---|---|
| After qualifying | 61% | 1.98 | 0.70 |
| Baseline: finish in grid order | 61% | 2.03 | 0.66 |
| Before qualifying | 40% | 1.69 | 0.62 |
| Baseline: recent driver form | 40% | 1.58 | 0.60 |

**Honest take:** once the grid is known, it already explains most of the result, so the order predictions are only slightly better than "they finish where they start". The model's main strength is its **probabilities**: its win and podium percentages have 2-6% lower error than my first version, so "30% to win" is a more trustworthy number. See the charts in `reports/charts/` or open `reports/dashboard.html`.

## Quick start

```bash
pip install -r requirements.txt
python predict.py            # predict the next race
python predict_season.py     # forecast every remaining race of the season
python make_charts.py        # rebuild charts and reports/dashboard.html
```

To update with the latest results and retrain:

```bash
python fetch_data.py
python train.py             # about 2 minutes
```

Replay a past race using only the races before it: `python predict.py --race 2026-18`

## How it works

- **Data:** race results and qualifying times (Q1/Q2/Q3) for every race since 2014, from [f1db](https://github.com/f1db/f1db).
- **Features:** recent form for drivers and teams, qualifying pace, circuit history, championship position, and how a driver compares with their team-mate. Every feature uses only races *before* the one being predicted, so nothing leaks from the answer.
- **Models:** LightGBM ranking and regression models for the finishing order, plus small regularised classifiers (blended with logistic regression) for win and podium probabilities, with a light calibration step.
- **Testing:** walk-forward by season, compared against simple baselines and against the first version of this project, with a bootstrap to check what is real versus noise.

## Limitations

- 88 test races is a small sample, so a few percentage points either way is noise.
- Randomness (safety cars, first-lap crashes, weather, strategy) is not modelled.
- Before qualifying the model is much weaker, and forecasts for later races barely differ because it can't know what happens in between.
- New regulations (like 2026) make early-season predictions less reliable.
- Not betting advice.

## Files

| File | Purpose |
|---|---|
| `fetch_data.py` | Downloads and caches the data |
| `features.py` | Feature engineering |
| `modeling.py` | Models, calibration and metrics |
| `train.py` | Tuning, backtest and training |
| `predict.py`, `predict_season.py` | Predict one race or the rest of the season |
| `make_charts.py` | Charts and the one-page dashboard |
| `reports/` | Backtest results, charts, saved predictions |

## Credits

Race data from [f1db](https://github.com/f1db/f1db), licensed CC BY 4.0. This project is not affiliated with Formula 1 or the FIA.

Built by Marcel Nowak, 2026.
