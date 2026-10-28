<div align="center">

# 🏎️ F1 Race Predictor: Full Download

**Everything you need to predict Formula 1 races on your own computer, in one folder.**

[![Download from Google Drive](https://img.shields.io/badge/Download-Google%20Drive-4285F4?style=for-the-badge&logo=googledrive&logoColor=white)](https://drive.google.com/drive/folders/1AT_yU_6ySvWNcQNuzkBZ2hiR9vJrsoMC?usp=drive_link)

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Model](https://img.shields.io/badge/Model-LightGBM-2E7D32)
![Data](https://img.shields.io/badge/Data-every%20race%20since%202014-E10600)
![No account needed](https://img.shields.io/badge/Account-not%20needed-555)

</div>

---

## Two ways to use it

| I want to… | Download | Setup needed |
|---|---|---|
| **Just see the predictions** | `dashboard.html` only | None: double-click it |
| **Run the predictor myself** | The whole folder | Python, about 10 minutes |

---

## 👀 Just want to see the predictions?

The Drive folder includes **`dashboard.html`**, the whole set of results as one interactive web page.

1. In the [Google Drive folder](https://drive.google.com/drive/folders/1AT_yU_6ySvWNcQNuzkBZ2hiR9vJrsoMC?usp=drive_link),
   right-click `dashboard.html` and choose **Download**.
2. Double-click the downloaded file. It opens in your browser: Chrome, Edge, Firefox or Safari.

You don't need Python, a server or an internet connection. The data and the chart library are inside the file.

### What's on the page

| Tab | What it shows |
|---|---|
| **Next race** | Predicted finishing order, each driver's chance to win, reach the podium or retire, and a drop-down for every race left in the season |
| **Championship** | Title chances for drivers and teams from 20,000 simulated seasons, expected points with a likely range, and when the title could be decided |
| **Track record** | How the model did on 191 past races, compared with simple guesses like "the starting grid order", plus a scorecard of predictions saved before each race |
| **Calibration** | Charts that check whether the chances are honest: does a "30%" happen about 30% of the time? |

> **It's a snapshot.** The page shows the numbers from the day it was made, and the date is written at the
> top. It doesn't update itself. A newer copy appears in the Drive folder when the predictions are refreshed.

> **Opening it from Google Drive's preview won't work.** Drive shows the file's code instead of the page.
> Download it first, then double-click it.

---

## ⚡ Run it yourself

1. **[Open the Google Drive folder](https://drive.google.com/drive/folders/1AT_yU_6ySvWNcQNuzkBZ2hiR9vJrsoMC?usp=drive_link)**,
   click the folder name at the top, then **Download**. Drive gives you a `.zip`.
2. **Unzip it.** On Windows, right-click it and choose **Extract All**. On a Mac, double-click it.
3. **Install Python** from [python.org](https://www.python.org/downloads). On Windows, tick **Add Python to PATH**.
4. **Double-click the launcher:**

   | Windows | Mac |
   |---|---|
   | `Run_Predictions.bat` | `Run_Predictions.command` (first time: right-click it, choose **Open**, then **Open**) |

5. **Open the `Predictions` folder.** Your results are there as text files and as a fresh `dashboard.html`.

After each practice, qualifying or race, double-click **`Update_And_Predict`** to download the latest results
and predict again. The dashboard is rebuilt every time.

## 📦 What's inside

```
F1-Predictor/
├── dashboard.html            ← the results as a web page: double-click to open
├── START HERE.txt            ← read this first
├── Run_Predictions.*         ← double-click to predict
├── Update_And_Predict.*      ← double-click after each session to refresh
├── run_all.py, predict.py, train.py, ...   the code
├── data/                     every F1 race since 2014
├── models/                   trained models, ready to use
├── site_data/                tables behind the dashboard
├── reports/                  accuracy tests and charts
└── overrides.csv, odds.csv   your own changes and bookmaker odds
```

## 📊 What you'll get when you run it

| File (in `Predictions/`) | What it shows |
|---|---|
| `dashboard.html` | Everything below as one interactive page |
| `rest_of_season_2026.txt` | Predicted order, win and podium chances for every remaining race |
| `championship_2026.txt` | Title chances for drivers and teams, and when the title could be decided |
| `scorecard.txt` | How earlier predictions did against the real results |

## 🎯 How good is it?

Tested on **191 past races** (2018 to 2026), each season predicted using only earlier seasons:

| When the prediction is made | Picks the winner |
|---|---|
| Before the weekend | about 4 in 10 |
| After practice | about 4.5 in 10 |
| After qualifying | about 5.5 in 10 |

After qualifying it orders the whole field better than the starting grid does. It doesn't pick the winner
better than "the pole sitter wins". It's a guide, not a guarantee.

## ❓ Problems?

<details>
<summary><b>The Drive link says "Request access"</b></summary>

The folder isn't shared publicly yet. Let the owner know by opening an issue in this repository.
</details>

<details>
<summary><b>dashboard.html shows code instead of a page</b></summary>

You're seeing it in Google Drive's preview, or your computer opened it in a text editor. Download it, then
right-click it, choose **Open with**, and pick your browser.
</details>

<details>
<summary><b>"python is not recognized"</b></summary>

Python isn't installed, or **Add Python to PATH** wasn't ticked. Run the installer again and tick it.
</details>

<details>
<summary><b>The Mac launcher won't open</b></summary>

Right-click it, choose **Open**, then **Open** again. If nothing happens, open Terminal in the folder and run
`python3 run_all.py --out Predictions`.
</details>

<details>
<summary><b>Google Drive split the download into several zips</b></summary>

That happens with big folders. Download all the parts and unzip them into the **same** folder.
</details>

## 🔁 Drive or GitHub?

| | Google Drive | GitHub (this page) |
|---|---|---|
| Best for | Running it straight away, or just viewing the dashboard | Reading the code and following changes |
| You get | One zip with everything, or the single dashboard file | Files you can browse online |
| Account needed | No | No |

Both hold the same project. If they ever differ, go by the newer date.

---

<div align="center">
<sub>Unofficial hobby project, not affiliated with Formula 1 or the FIA. Not betting advice.<br>
Race data from <a href="https://github.com/f1db/f1db">f1db</a> under
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.</sub>
</div>
