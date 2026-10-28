# Dashboard (`dashboard.html`)

**A one-file web page that shows the F1 predictor's numbers as charts and tables.**

Download `dashboard.html` and double-click it, and it opens in your browser. You don't need Python, a
server or an internet connection, because everything the page needs is inside the file.

> Unofficial hobby project. Not affiliated with Formula 1 or the FIA. Not betting advice.

## What's on it

The page has four tabs.

### Next race
- The predicted finishing order for the next Grand Prix.
- Each driver's chance of **winning**, finishing on the **podium**, and **retiring**, with bars so the
  favourites stand out.
- A drop-down to see any other race left in the season.
- A line saying how much the prediction knew: before the weekend, after practice, or after qualifying.

### Championship
- **Title chances** for the drivers and the teams, from 20,000 simulated runs of the rest of the season,
  starting from the real standings.
- Each one's expected final points, with a range covering the middle 80% of the simulated outcomes.
- **When the title could be decided**: the chance it is settled after each remaining race.

### Track record
- How the model did when tested on **191 past races (2018 to 2026)**. For each season it was trained only
  on earlier seasons.
- A comparison with simple baselines, "the starting grid order" and "recent driver form", so you can see
  whether the model adds anything.
- A scorecard of predictions saved **before** each race and checked after it. It fills in as the season goes on.

### Calibration
- Three charts (win, podium, retirement) that answer one question: when the model says "30%", does it
  happen about 30% of the time?
- A point on the dotted diagonal means the chance was right.

## How to open it

1. Download `dashboard.html`. On GitHub, open the file and click the download button.
2. Double-click it. It opens in Chrome, Edge, Firefox or Safari.
3. If it shows as text instead, right-click it, choose **Open with**, and pick your browser.

If GitHub Pages is switched on for this repository, you can also view it online at
`https://<your-username>.github.io/<repo-name>/dashboard.html`.

## Good to know

- **It is a snapshot.** It shows the numbers from the last time the predictor was run, and it does not
  update itself. The date at the top of the page says when the data was made.
- **It is made automatically.** Every run of `run_all.py` saves a fresh copy as
  `Predictions/dashboard.html` (the script that does it is `make_single_page.py`).
- **For the live version**, use `index.html`, which reads the latest tables in `site_data/`.
- **The predictions can't know about the unexpected**, such as crashes, safety cars, weather, penalties or
  upgrades, beyond what recent results already show.

## Credits

- Race data: [f1db](https://github.com/f1db/f1db), used under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Charts drawn with [d3](https://d3js.org) 7.9.0 (ISC licence), included inside the file.
