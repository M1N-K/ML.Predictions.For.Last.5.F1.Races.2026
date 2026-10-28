#!/usr/bin/env python3
"""Can the retirement chance be fixed by matching the recent retirement rate?

Weighting recent seasons did not help (reports/recency_summary.md). A more direct fix: after fitting
the retirement model, shift all its probabilities up or down (on the logit scale) by one number so
that, over the last `k` seasons it was trained on, the average predicted chance equals the real
retirement rate of those seasons. Walk-forward, same as everything else; k chosen on 2018-2022 and
judged on 2023 onward (adopt only if it is also better there).

    python dnf_shift_test.py        (a few minutes)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq

import features as F
import train as T

REPORT = Path("reports")
WINDOWS = [None, 1, 2, 3, 5]          # None = no shift
FIT_END = 2022


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def shift_for(p_recent, observed_rate):
    """Logit shift d with mean(sigmoid(logit(p) + d)) == observed_rate."""
    z = logit(p_recent)
    f = lambda d: (1 / (1 + np.exp(-(z + d)))).mean() - observed_rate
    return brentq(f, -3, 3)


def apply(p, d):
    return 1 / (1 + np.exp(-(logit(p) + d)))


def per_race_ll(frame, p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    y = frame["dnf"].to_numpy(float)
    return pd.Series(-(y * np.log(p) + (1 - y) * np.log(1 - p)), index=frame.index).groupby(frame["race_id"]).mean()


def main():
    df = F.load_features()
    data = df[df["completed"] & df["dnf"].notna()].copy()
    rows, cal = [], []
    for year in [y for y in sorted(data.year.unique()) if y >= 2018]:
        train, test = data[data.year < year], data[data.year == year]
        for stage in ("pre", "post"):
            feats = F.FEATURE_SETS[stage]
            model = T.fit_dnf(train, feats)
            p_test = model.predict_proba(test[feats])[:, 1]
            p_train = model.predict_proba(train[feats])[:, 1]
            for k in WINDOWS:
                if k is None:
                    d = 0.0
                else:
                    recent = train.year >= year - k
                    d = shift_for(p_train[recent.to_numpy()], train.loc[recent, "dnf"].mean())
                p = apply(p_test, d)
                ll = per_race_ll(test, p).reset_index()
                ll.columns = ["race_id", "logloss"]
                ll["year"], ll["stage"], ll["window"] = year, stage, "none" if k is None else f"{k} seasons"
                rows.append(ll)
                cal.append({"year": year, "stage": stage, "window": "none" if k is None else f"{k} seasons",
                            "shift": d, "predicted": float(p.mean()), "observed": float(test["dnf"].mean())})
    res = pd.concat(rows, ignore_index=True)
    cal = pd.DataFrame(cal)
    res.to_csv(REPORT / "dnf_shift_races.csv", index=False)
    cal.to_csv(REPORT / "dnf_shift_calibration.csv", index=False)

    piv = res.pivot_table(index=["stage", "race_id", "year"], columns="window", values="logloss").reset_index()
    L = ["# Retirement chance: shift to the recent retirement rate", "",
         "After fitting, all retirement probabilities are shifted (logit scale) so their average over the "
         "last k training seasons matches the real rate there. Log loss per race (lower is better), averaged "
         "over the before-the-weekend and after-qualifying models.", "",
         "| window | 2018-22 | 2023 onward | 2023 onward, difference from none (95% interval) | predicted / observed, 2018-26 |",
         "|---|---|---|---|---|"]
    fit, held = piv[piv.year <= FIT_END], piv[piv.year > FIT_END]
    scores = {}
    for w in ["none"] + [f"{k} seasons" for k in WINDOWS[1:]]:
        f_, g_ = fit[w].mean(), held[w].mean()
        dd, lo, hi = T.paired_bootstrap(held[w].to_numpy(), held["none"].to_numpy())
        c = cal[(cal.window == w) & (cal.stage == "post")]
        scores[w] = (f_, g_)
        L.append(f"| {w} | {f_:.4f} | {g_:.4f} | {dd:+.4f} [{lo:+.4f}, {hi:+.4f}] | "
                 f"{c.predicted.mean():.3f} / {c.observed.mean():.3f} |")
    # Bar: best on 2018-22, AND a clear gain on 2023 onward (interval excludes zero). The first version
    # of this script only asked for a better point estimate on both; that passed for the 3-season window
    # with a gain of 0.0004 inside the noise, so the bar was raised to the one used everywhere else.
    cand = [w for w in scores if w != "none" and scores[w][0] < scores["none"][0]]
    pick = min(cand, key=lambda w: scores[w][0]) if cand else None
    if pick:
        dd, lo, hi = T.paired_bootstrap(held[pick].to_numpy(), held["none"].to_numpy())
        if not hi < 0:
            pick = None
    L += ["", f"Rule outcome: **{'adopt a shift to the last ' + pick if pick else 'keep as is'}** "
              "(needs the best 2018-22 score and a clear gain, interval below zero, on 2023 onward).", ""]
    L += ["## By season (post stage, predicted / observed)", "", "| window | " + " | ".join(str(y) for y in sorted(cal.year.unique())) + " |",
          "|---|" + "---|" * cal.year.nunique()]
    for w in ["none"] + [f"{k} seasons" for k in WINDOWS[1:]]:
        c = cal[(cal.window == w) & (cal.stage == "post")].sort_values("year")
        L.append(f"| {w} | " + " | ".join(f"{p:.3f}/{o:.3f}" for p, o in zip(c.predicted, c.observed)) + " |")
    (REPORT / "dnf_shift_summary.md").write_text("\n".join(L) + "\n")
    json.dump({"pick": pick}, open(REPORT / "dnf_shift_decision.json", "w"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
