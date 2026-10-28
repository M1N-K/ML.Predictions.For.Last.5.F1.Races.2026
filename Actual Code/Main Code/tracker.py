#!/usr/bin/env python3
"""Prediction tracker: save each prediction BEFORE its race, then score it afterwards.

    python tracker.py score      score every saved prediction whose race now has a result
    python tracker.py status     what is saved, what has been scored

Predictions are saved automatically by predict.py and predict_season.py (never for a race that
already has a result, so the record can't be back-filled). Saving the same race and stage again
replaces the earlier copy, so the record holds the LAST prediction made at each stage.

Files:  tracker/predictions.csv   every saved prediction (one row per driver)
        tracker/scorecard.csv     scored races
        Predictions/scorecard.txt readable summary
"""
import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

import features as F
import train as T
from engine import pretty

TRACK_DIR = Path("tracker")
PRED_FILE = TRACK_DIR / "predictions.csv"


def save(race_id, stage, rows, trained_through):
    """rows: predict_rows() output for one race. Returns the path, or None if refused."""
    races = pd.read_csv("data/races.csv")
    done = bool(races.loc[races["race_id"] == race_id, "has_results"].iloc[0])
    if done:
        return None            # a race with a result is never saved: no after-the-fact predictions
    TRACK_DIR.mkdir(exist_ok=True)
    new = pd.DataFrame({
        "saved_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "race_id": race_id, "stage": stage, "trained_through": trained_through,
        "driver_id": rows["driver_id"], "team": rows["team"], "pred": rows["pred"],
        "p_win": rows["p_win"].round(4), "p_podium": rows["p_podium"].round(4),
        "p_dnf": rows["p_dnf"].round(4)})
    old = pd.read_csv(PRED_FILE) if PRED_FILE.exists() else pd.DataFrame()
    if len(old):
        old = old[~((old.race_id == race_id) & (old.stage == stage))]
    pd.concat([old, new], ignore_index=True).to_csv(PRED_FILE, index=False)
    return PRED_FILE


def score():
    if not PRED_FILE.exists():
        return None, "Nothing saved yet: run predict.py or predict_season.py before a race."
    pr = pd.read_csv(PRED_FILE)
    res, races = pd.read_csv("data/results.csv"), pd.read_csv("data/races.csv")
    feats = F.build_features(res, None, races)
    actual = feats[feats.completed]
    rows = []
    for (race_id, stage), p in pr.groupby(["race_id", "stage"]):
        a = actual[actual.race_id == race_id]
        if a.empty:
            continue
        g = p.merge(a[["driver_id", "final_rank", "grid"]], on="driver_id", how="inner")
        if len(g) < 10:
            continue
        m = T.order_metrics(g.rename(columns={"pred": "_o"}).assign(year=0), g["pred"], higher_is_better=False).iloc[0]
        g_order = T.order_metrics(g.assign(year=0), g["grid"], higher_is_better=False).iloc[0]
        winner = g.loc[g["final_rank"].idxmin()]
        pick = g.loc[g["pred"].idxmin()]
        podium = g[g.final_rank <= 3]
        rows.append({
            "race_id": race_id, "grand_prix": pretty(races.loc[races.race_id == race_id, "grand_prix"].iloc[0]),
            "stage": stage, "saved_at": p["saved_at"].iloc[0],
            "predicted_winner": pretty(pick.driver_id), "actual_winner": pretty(winner.driver_id),
            "winner_hit": int(m.winner_hit), "podium_right": round(m.podium_overlap * 3),
            "top10_right": round(m.top10_overlap * 10), "spearman": round(m.spearman, 3),
            "avg_position_error": round(m.mae_pos, 2),
            "p_win_given_to_actual_winner": round(float(winner.p_win), 3),
            "p_podium_given_to_podium_drivers": round(float(podium.p_podium.mean()), 3),
            "grid_order_spearman": round(g_order.spearman, 3),
            "grid_order_winner_hit": int(g_order.winner_hit)})
    if not rows:
        return None, "No saved prediction has a result yet. Run Update_And_Predict after the race."
    sc = pd.DataFrame(rows).sort_values(["race_id", "stage"])
    sc.to_csv(TRACK_DIR / "scorecard.csv", index=False)
    return sc, None


def summary_text(sc):
    lines = ["PREDICTION TRACKER: how the saved predictions did", "",
             "Each prediction was saved before its race. 'Grid order' is the reference: just using the "
             "starting order.", ""]
    for r in sc.itertuples():
        lines.append(f"{r.race_id} {r.grand_prix} ({r.stage}): predicted winner {r.predicted_winner} | "
                     f"actual {r.actual_winner} | {'HIT' if r.winner_hit else 'miss'} | "
                     f"{r.podium_right}/3 podium | rank correlation {r.spearman:.2f} "
                     f"(grid order {r.grid_order_spearman:.2f})")
    lines += ["", "Totals by stage:", ""]
    t = sc.groupby("stage").agg(races=("race_id", "count"), winners_right=("winner_hit", "sum"),
                                 podium_drivers_right=("podium_right", "mean"), spearman=("spearman", "mean"),
                                 grid_order_spearman=("grid_order_spearman", "mean"),
                                 avg_pos_error=("avg_position_error", "mean"))
    lines.append(t.round(2).to_string())
    lines += ["", "A handful of races is too few to judge the model; compare with the back-test "
              "(reports/backtest_summary.md) once you have 10 or more."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["score", "status"])
    args = ap.parse_args()
    if args.action == "status":
        if not PRED_FILE.exists():
            print("Nothing saved yet.")
            return
        pr = pd.read_csv(PRED_FILE)
        print(pr.groupby(["race_id", "stage"]).agg(saved_at=("saved_at", "first"),
                                                    drivers=("driver_id", "count")).to_string())
        return
    sc, msg = score()
    if sc is None:
        print(msg)
        return
    text = summary_text(sc)
    Path("Predictions").mkdir(exist_ok=True)
    Path("Predictions/scorecard.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
