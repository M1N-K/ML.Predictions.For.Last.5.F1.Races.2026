<div align="center">

# 🛠️ Set Up the F1 Predictor

**Run the predictions on your own computer and read the results as plain text files.**
*No web page needed: everything opens in Notepad or TextEdit.*

![Time](https://img.shields.io/badge/Setup-about%2010%20minutes-2E7D32)
![Windows](https://img.shields.io/badge/Windows-supported-0078D6?logo=windows&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-supported-000000?logo=apple&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)

</div>

---

## ✅ Before you start

You need three things:

- [ ] A Windows PC or a Mac
- [ ] An internet connection (for the first run and for updates)
- [ ] About 25 MB of free space

You **don't** need a GitHub or Google account, or any coding knowledge.

---

## Step 1 · Install Python

Python is the free program the predictor runs on.

1. Go to **[python.org/downloads](https://www.python.org/downloads)** and click the big yellow **Download** button.
2. Open the file you downloaded and install it.

> ⚠️ **Windows users:** on the **first** installer screen, tick **"Add Python to PATH"** before clicking
> Install. This is the step people miss most. If you miss it, the predictor can't find Python.

---

## Step 2 · Download the project

1. Open the **[Google Drive folder](https://drive.google.com/drive/folders/1AT_yU_6ySvWNcQNuzkBZ2hiR9vJrsoMC?usp=drive_link)**.
2. Click the folder name at the top, then **Download**. You get a `.zip` file.
3. Unzip it:
   - **Windows:** right-click it and choose **Extract All**.
   - **Mac:** double-click it.
4. Open the new **F1-Predictor** folder. You should see `START HERE.txt`, `run_all.py`, and folders called
   `data` and `models`.

> Download the **whole folder**. The program needs `data` and `models`, which sit next to it.

---

## Step 3 · Run your first prediction

| Windows | Mac |
|---|---|
| Double-click **`Run_Predictions.bat`** | Double-click **`Run_Predictions.command`** |
| | *First time only:* if macOS won't open it, right-click it, choose **Open**, then **Open** again |

A black window opens and does the work:

1. **The first time,** it installs the extra pieces it needs. This takes a minute or two.
2. It predicts every race left in the season.
3. It simulates the championship 20,000 times.
4. It opens the **`Predictions`** folder for you.

On later runs the install step is skipped, and the whole thing takes under a minute.

---

## Step 4 · Read your predictions

Everything is in the **`Predictions`** folder. Open any `.txt` file in Notepad or TextEdit.

| File | What's in it |
|---|---|
| 📄 `rest_of_season_2026.txt` | Predicted finishing order, win and podium chances for **every remaining race** |
| 🏆 `championship_2026.txt` | Title chances for drivers and teams, and when the title could be decided |
| 📈 `scorecard.txt` | How earlier predictions did against the real results (appears after a predicted race has been run) |
| 💰 `odds_report.txt` | The model's chances next to bookmaker odds, if you've typed some into `odds.csv` |

### What a prediction looks like

```
R19 Mexico   2026-11-01  Kimi Antonelli 32% | Max Verstappen 32% | Lewis Hamilton 8%   [before the weekend]

 Pred            Driver      Team P(win) P(podium)
    1    Kimi Antonelli  Mercedes  32.2%       62%
    2    Max Verstappen  Red Bull  31.8%       56%
    3      Lando Norris   Mclaren   7.5%       33%
    4    Lewis Hamilton   Ferrari   8.4%       34%
    5     Oscar Piastri   Mclaren   2.7%       16%
```

| Column | Meaning |
|---|---|
| **Pred** | Predicted finishing position |
| **P(win)** | Chance of winning the race |
| **P(podium)** | Chance of finishing in the top three |
| **[before the weekend]** | How much the model knew: before the weekend, after practice, or after qualifying |

> 💡 The order and the win chances come from two different models. A driver can be predicted 3rd but have a
> slightly higher win chance than the driver predicted 4th, like Norris and Hamilton above.

---

## Step 5 · Keep it up to date

The predictions get sharper as the weekend goes on:

```
before the weekend  →  after practice  →  after qualifying
   ~4 in 10              ~4.5 in 10          ~5.5 in 10       (how often it picks the winner)
```

After **practice**, **qualifying** or the **race**, double-click:

| Windows | Mac |
|---|---|
| **`Update_And_Predict.bat`** | **`Update_And_Predict.command`** |

It downloads the latest results, retrains the models, scores the earlier predictions, and predicts again.

---

## ✏️ Optional: add your own information

The predictor works out the line-up by itself. If you know something it doesn't, such as a driver being
injured, a stand-in or a grid penalty, tell it in **`overrides.csv`**:

1. Open `overrides.csv` in Notepad or Excel.
2. Follow the examples at the top of the file. Each change is one line, for example a 10-place grid penalty
   for Hamilton.
3. Save it, then run the predictions again.

> Grid penalties only have an effect after qualifying, because the model doesn't use the grid before then.

---

## 🖥️ Prefer the terminal?

Open a terminal in the F1-Predictor folder and run:

```bash
python -m pip install -r requirements.txt            # first time only
python run_all.py --out Predictions                  # predict
python run_all.py --refresh --out Predictions        # update with the latest results, then predict
```

On a Mac, type `python3` instead of `python`.

---

## ❓ Something went wrong?

<details>
<summary><b>"python is not recognized" (Windows)</b></summary>

Python isn't installed, or **Add Python to PATH** wasn't ticked. Run the Python installer again, choose
**Modify**, and make sure it's added to PATH. You can also try typing `py` instead of `python`.
</details>

<details>
<summary><b>The black window flashes and closes straight away</b></summary>

Usually the same Python problem as above. To see the error, open a terminal in the folder and run
`python run_all.py --out Predictions`. The message will say what's wrong.
</details>

<details>
<summary><b>The Mac file won't open, or nothing happens</b></summary>

Right-click it, choose **Open**, then **Open**. If that doesn't work, open Terminal in the folder and run
`chmod +x *.command`, then try again. You can also use the terminal commands above.
</details>

<details>
<summary><b>Errors while installing (pip)</b></summary>

Update the installer, then run the launcher again:
`python -m pip install --upgrade pip`
</details>

<details>
<summary><b>"Could not load the models" or a version warning</b></summary>

Your Python libraries are a different version from the ones that built the models. Retrain them once on
your computer with `python train.py`. It takes 20 to 30 minutes.
</details>

<details>
<summary><b>The predictions look out of date</b></summary>

They only change when you run something. Use **Update_And_Predict** after each session.
</details>

---

## ⚠️ Keep in mind

- It's a **statistical guide, not a guarantee**. It can't know about crashes, safety cars, weather or strategy.
- After qualifying it orders the field better than the starting grid, but it **doesn't pick the winner
  better than "the pole sitter wins"**.
- **Not betting advice.**

<div align="center">
<sub>Unofficial hobby project, not affiliated with Formula 1 or the FIA.<br>
Race data from <a href="https://github.com/f1db/f1db">f1db</a> under
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.</sub>
</div>
