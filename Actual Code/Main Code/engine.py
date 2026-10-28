"""Shared prediction logic used by predict.py, predict_season.py, simulate_season.py, tracker.py.

A race can be predicted at three moments ("stages"):
    pre   before the weekend      - form, team pace, history
    fp    after practice          - plus this weekend's practice pace
    post  after qualifying        - plus the grid, qualifying pace and any sprint result
`stage_for` picks the most informed stage that the data supports.
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

import features as F
import lineup
import overrides as OV
import train as T

MODEL_PATH = Path("models/f1_models.joblib")
STAGE_LABEL = {"pre": "before the weekend (form only)",
               "fp": "after practice (form + practice pace)",
               "post": "after qualifying (grid + qualifying pace)"}


def pretty(slug):
    return str(slug).replace("-", " ").title()


def load_data():
    return (pd.read_csv("data/results.csv"), pd.read_csv("data/races.csv"),
            pd.read_csv("data/weekend.csv") if Path("data/weekend.csv").exists() else None)


LINEUP_NOTES = []   # plain-English notes about how the latest build_frame call chose the entry lists


def load_entrants():
    p = Path("data/entrants.csv")
    return pd.read_csv(p) if p.exists() else None


def with_upcoming_lineup(res, races, target, weekend=None, entrants=None):
    """If the target race has no entries yet, fill them in.

    With no `weekend` / `entrants` given, the most recent completed line-up is copied (what honest
    replays of past races need). With them, lineup.py improves on the copy: the season's entrant list
    and practice attendance (see lineup.py). Practice data, if any, is attached later by driver in
    features.build_features."""
    if (res["race_id"] == target).any():
        return res
    if weekend is not None or entrants is not None:
        rows, notes, _ = lineup.resolve(res, races, target, weekend, entrants)
        meta = races[races["race_id"] == target].iloc[0]
        label = f"{pretty(meta['grand_prix'])} GP"
        LINEUP_NOTES.extend(f"{label}: {n}" for n in notes)
        return pd.concat([res, rows], ignore_index=True)
    meta = races[races["race_id"] == target].iloc[0]
    last = res[res["position_raw"].notna()]["race_id"].max()
    lineup_rows = res[res["race_id"] == last].copy()
    lineup_rows["race_id"], lineup_rows["year"], lineup_rows["round"] = target, meta["year"], meta["round"]
    lineup_rows["date"], lineup_rows["circuit_id"], lineup_rows["grand_prix"] = meta["date"], meta["circuit_id"], meta["grand_prix"]
    for c in ["grid_raw", "quali_pos", "quali_time", "position_raw", "laps_done", "points", "reason_retired"]:
        lineup_rows[c] = np.nan
    return pd.concat([res, lineup_rows], ignore_index=True)


NOTES = []      # plain-English notes about overrides.csv changes from the latest build_frame call


def build_frame(res, races, weekend, targets=()):
    """Feature table for all races, with line-ups filled in for the upcoming `targets`
    and any changes from overrides.csv (driver changes, grid penalties) applied to them."""
    LINEUP_NOTES.clear()
    entrants = load_entrants()
    for t in targets:
        res = with_upcoming_lineup(res, races, t, weekend=weekend, entrants=entrants)
    res, notes = OV.apply(res, races, list(targets))
    NOTES[:] = notes
    return F.build_features(res, weekend, races)


def stage_for(rows):
    if rows["grid"].notna().all():
        return "post"
    if rows["fp_best_gap"].notna().sum() >= 10:
        return "fp"
    return "pre"


def load_bundle():
    return joblib.load(MODEL_PATH)


def train_models(train, stage, bundle=None):
    """Fit all four models for one stage on `train` (used for honest replays of past races),
    with the tuned settings stored in `bundle` (sensible defaults if there is none)."""
    feats = F.FEATURE_SETS[stage]
    leaves, n = bundle["best_params"][stage] if bundle else (15, 150)
    cl, cn = bundle["best_params_clf"][stage] if bundle else (8, 200)
    return {"ranker": T.fit_ranker(train, feats, leaves, n),
            "win": T.fit_clf(train, feats, 1, cl, cn),
            "podium": T.fit_clf(train, feats, 3, cl, cn),
            "dnf": T.fit_dnf(train, feats)}


def bundle_models(bundle, stage):
    return {k: bundle["models"][f"{k}_{stage}"] for k in ("ranker", "win", "podium", "dnf")}


def predict_rows(rows, stage, models):
    """Add score, P(win), P(podium), P(retire) and the predicted order to one race's rows."""
    feats = F.FEATURE_SETS[stage]
    rows = rows.copy()
    X = rows[feats]
    rows["score"] = models["ranker"].predict(X)
    rows["p_win"] = T.race_normalise(models["win"].predict_proba(X)[:, 1], rows["race_id"], 1)
    rows["p_podium"] = T.race_normalise(models["podium"].predict_proba(X)[:, 1], rows["race_id"], 3)
    rows["p_dnf"] = models["dnf"].predict_proba(X)[:, 1]
    rows = rows.sort_values("score", ascending=False).reset_index(drop=True)
    rows["pred"] = np.arange(1, len(rows) + 1)
    return rows


def display_table(rows, with_grid=False, with_actual=False):
    out = pd.DataFrame({
        "Pred": rows["pred"], "Driver": rows["driver_id"].map(pretty), "Team": rows["team"].map(pretty),
        "P(win)": (rows["p_win"] * 100).round(1).astype(str) + "%",
        "P(podium)": (rows["p_podium"] * 100).round(0).astype(int).astype(str) + "%",
    })
    if with_grid:
        out.insert(3, "Grid", rows["grid"].astype(int))
    if with_actual:
        out["Actual"] = rows["final_rank"].astype(int)
    return out
