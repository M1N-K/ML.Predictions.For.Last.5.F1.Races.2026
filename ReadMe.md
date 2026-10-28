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

For every driver in a race, it gives a predicted finishing position and the chance of winning, reaching the
podium or retiring. For the rest of the season it gives each driver's and team's chance of winning the
championship. It's a machine-learning model (LightGBM) trained on every race since 2014. The results come out
as plain text files, plus a web page with charts.

> Unofficial hobby project. Not affiliated with Formula 1 or the FIA. Not betting advice.

---

## 🚀 Quick start

1. Install [Python](https://www.python.org/downloads). On Windows, tick **Add Python to PATH**.
2. Download the project from [Google Drive](https://drive.google.com/drive/folders/1AT_yU_6ySvWNcQNuzkBZ2hiR9vJrsoMC?usp=drive_link)
   or with the green **Code** button above, then unzip it.
3. Double-click **`Run_Predictions`** (`.bat` on Windows, `.command` on Mac).
4. Open the **`Predictions`** folder.

After each practice, qualifying or race, double-click **`Update_And_Predict`** to get new predictions.

**Just want to look?** Download `dashboard.html` and double-click it. It opens in your browser with no setup.

---

## 📊 What you get

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

| File | What's in it |
|---|---|
| `rest_of_season_2026.txt` | Predicted order, win and podium chances for every remaining race |
| `championship_2026.txt` | Title chances for drivers and teams, and when the title could be decided |
| `scorecard.txt` | How earlier predictions did against the real results |
| `dashboard.html` | All of it as an interactive page: next race, championship, track record, calibration |

---

## 🤔 Why this exists

Predicting sport is easy to do badly. A model can look brilliant because it quietly saw information from the
future, because only its best number was reported, or because nobody compared it with something simple. This
project is set up to avoid all three:

- **Predictions are saved before the race and scored after it.** A race that already has a result is never
  saved, so the record can't be back-filled.
- **Every model is compared with plain baselines** ("the starting grid order", "recent driver form") on the
  same races, with a 95% interval on each difference.
- **A test checks for leaks.** `test_no_leakage.py` blanks out everything that isn't known yet at each point
  of the weekend and confirms the model's inputs don't change.
- **Ideas that didn't help are left out,** and listed below with their numbers.

The aim is a model whose numbers can be checked, not just admired.

---

## 🧠 How it thinks

- **Three stages.** One set of models for before the weekend, one for after practice, one for after qualifying.
  Each sees more than the last, and none sees anything it couldn't have known.
- **Two kinds of model.** A ranking model orders the whole field. Separate classifiers give the chances of
  winning, a podium and retiring, scaled within each race so they add up properly.
- **Championship odds by simulation.** The rest of the season is played 20,000 times from the real standings.
  Teams carry a pace "shock" from race to race, so a team that's faster than expected stays faster for a while,
  as in real life.
- **Data:** [f1db](https://github.com/f1db/f1db): results, qualifying, practice, pit stops, sprints and
  standings for every race since 2014.

---

## 🎯 How well does it work?

Walk-forward back-test: each season is predicted by a model trained only on earlier seasons. Settings were
chosen on 2022, so the 2023–26 columns are the ones nothing was tuned on.

| Model | Winner right, 2018–26 (191 races) | Order match*, 2018–26 | Winner right, 2023–26 (88 races) | Order match*, 2023–26 |
|---|---|---|---|---|
| **After qualifying** | 53.4% | 0.666 | 62.5% | 0.695 |
| Baseline: starting grid | 54.5% | 0.628 | 61.4% | 0.664 |
| **After practice** | 46.6% | 0.626 | 44.3% | 0.632 |
| **Before the weekend** | 43.5% | 0.603 | 42.0% | 0.622 |
| Baseline: recent form | 44.0% | 0.584 | 39.8% | 0.603 |

\*Spearman rank correlation between predicted and real finishing order (1 is perfect).

![Do the model's percentages match reality?](reports/calibration.png)

*Do the model's percentages match reality? 88 races (2023 to 2026) never used to choose any setting. Close to
the dotted diagonal is good. Win and podium chances are close; the highest retirement chances are too high.*

**What this does and doesn't show:**

- After qualifying it **orders the field better** than the starting grid, and that gap is clear in the
  statistics. It does **not pick the winner better** than "the pole sitter wins": 53.4% against 54.5% is
  inside the noise.
- Before the weekend it beats "recent form" on order, but not on winner calls.
- Win and podium chances are close to honest: a "30%" happens roughly 30% of the time. Retirement chances
  run too high: 17.3% predicted against 14.6% observed.
- Even 191 races is a small sample for winner calls. A few percentage points either way is noise.

---

## 🚫 What didn't help

An idea is only kept if it gives a clear gain, meaning a 95% interval that excludes zero.

| Idea | Result |
|---|---|
| Driver-versus-car ratings, circuit-type features | No clear gain; together they made win chances worse after qualifying. Switched off. |
| Counting recent seasons more | Finishing order got clearly worse on 2023–26. Not used. |
| Shifting retirement chances to the recent rate | Gain inside the noise. Not used. |
| Shared team shocks in the championship simulation | **Kept, partly.** The 80% ranges now contain 82–85% of real outcomes (53–65% before), but the title odds didn't clearly improve. |
| Comparing with bookmaker odds | No free source of past F1 odds, so only two races could be compared. A tool to keep adding to, not a result. |

---

## ⚠️ What it isn't

- **Not a winner-picker that beats the pole sitter.** After qualifying, the grid does most of the work.
- **Weaker before the weekend,** where it swings with how dominant the leading car is.
- **Blind to chaos.** Safety cars, first-lap incidents, strategy and weather aren't predicted.
- **Short on data for the newest rules.** The 2026 regulations reset the pecking order, and only 18 races of
  this era exist so far.
- **Not tested on a real Windows or Mac machine** for the daily automatic-update scripts.

---

## Data and credit

Race data comes from [f1db](https://github.com/f1db/f1db) and is used under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The files in `data/` are derived from it.
