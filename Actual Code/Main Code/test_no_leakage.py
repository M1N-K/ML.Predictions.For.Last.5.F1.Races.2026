#!/usr/bin/env python3
"""Check that each feature set only uses information available at its stage.

For a chosen race we blank out what is NOT known at a given stage and rebuild all features. If
the model inputs for that race change, something from the future is leaking in.

    pre   stage: blank result, pit stops, practice, qualifying/grid, sprint  -> "pre"  must not change
    fp    stage: blank result, pit stops, qualifying/grid, sprint            -> "fp"   must not change
    post  stage: blank result and pit stops                                  -> "post" must not change

Run:  python test_no_leakage.py        (exit code 1 if any check fails)
"""
import sys

import numpy as np
import pandas as pd

import features as F

RESULT_COLS = ["position_raw", "laps_done", "points", "reason_retired"]
QUALI_COLS = ["quali_pos", "quali_time"]
PRACTICE_COLS = ["fp_best_gap", "fp_mean_gap", "fp_laps", "fp_sessions"]
SPRINT_COLS = ["sprint_pos", "sprint_pts", "sprint_grid", "sprint_quali_pos", "sprint_quali_gap"]
PIT_COLS = ["pit_n", "pit_med_time", "pit_first_lap"]
# circuit averages that, for a blanked race in the MIDDLE of history, use all visits by design
CIRCUIT_ALL_VISITS = ["circ_abs_change", "circ_pole_win", "circ_stops_mean"]


def rebuild(res, weekend, races, race_id, blank_res, blank_weekend, grid_unknown):
    """Blank the given columns for one race (wherever they live) and rebuild all features."""
    r, w = res.copy(), weekend.copy()
    to_blank = list(blank_res) + list(blank_weekend) + (["grid_raw"] if grid_unknown else [])
    for c in to_blank:
        frame = r if c in r.columns else w
        mask = frame["race_id"] == race_id
        if pd.api.types.is_numeric_dtype(frame[c]):
            frame[c] = frame[c].astype(float)          # keep numeric columns numeric
        else:
            frame[c] = frame[c].astype(object)
        frame.loc[mask, c] = np.nan
    return F.build_features(r, w, races)


def max_diff(a, b, cols, race_id):
    A = a[a.race_id == race_id].set_index("driver_id")[cols].sort_index().astype(float)
    B = b[b.race_id == race_id].set_index("driver_id")[cols].sort_index().astype(float)
    if list(A.index) != list(B.index):
        return None, ["driver lists differ"]
    d = A.fillna(-999).sub(B.fillna(-999)).abs()
    bad = d.max().loc[lambda s: s > 1e-9].index.tolist()
    return int((d > 1e-9).values.sum()), bad


def main():
    res, weekend, races = (pd.read_csv(f"data/{n}.csv") for n in ("results", "weekend", "races"))
    full = F.build_features(res, weekend, races)
    done = sorted(full[full.completed].race_id.unique())
    sprint_race = races[races.is_sprint & races.has_results].race_id.iloc[-1]
    targets = [done[-1], sprint_race, done[len(done) // 2]]
    stages = {
        "pre": (RESULT_COLS, QUALI_COLS + PRACTICE_COLS + SPRINT_COLS + PIT_COLS, True),
        "fp": (RESULT_COLS, QUALI_COLS + SPRINT_COLS + PIT_COLS, True),
        "post": (RESULT_COLS, PIT_COLS, False),
    }
    failed = False
    print(f"{'race':9s} {'stage':5s} {'features':8s} {'cells changed':14s} verdict")
    for race in targets:
        for stage, (bres, bweek, grid_unknown) in stages.items():
            # the grid is part of the qualifying information, but keep f1db's grid when testing "post"
            g = rebuild(res, weekend, races, race, bres, bweek, grid_unknown)
            cols = F.FEATURE_SETS[stage]
            if race != done[-1]:   # circuit averages of a blanked MID-history race use all visits by design
                cols = [c for c in cols if c not in CIRCUIT_ALL_VISITS]
            n, bad = max_diff(full, g, cols, race)
            ok = n == 0
            failed |= not ok
            print(f"{race:9s} {stage:5s} {len(cols):<8d} {str(n):14s} {'OK' if ok else 'LEAK in ' + ', '.join(bad)}")
    print("\nAll leakage checks passed." if not failed else "\nLEAKAGE FOUND.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
