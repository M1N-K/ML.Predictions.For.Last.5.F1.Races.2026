#!/usr/bin/env python3
"""Should recent seasons count more when the models learn?

Regulations and the pecking order keep changing, and the retirement model in particular learns from
early seasons that were less reliable than today's. This tries "half-lives" for the weight of a
training race (a race `halflife` years older than the newest one counts half as much) in the same
walk-forward back-test as everything else (season Y is predicted from seasons before Y).

    python recency_test.py            (about 10-15 minutes; writes reports/recency_*.csv / .md)

Decision rule, fixed before looking at the results:
  * for each part of the model (finishing order, win/podium chances, retirement chance) take the
    half-life that scores best on 2018-2022;
  * adopt it only if it also beats "no weighting" on 2023 onward, which was not used to choose it.
Otherwise the part stays unweighted.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import features as F
import train as T

REPORT = Path("reports")
HALFLIVES = [None, 1.5, 3.0, 6.0]
FIT_END = 2022
FIRST_TEST_YEAR = 2018
STAGES = ("pre", "post")


def label(h):
    return "none" if h is None else f"{h:g}y"


def per_race_ll(frame, p, y):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    y = np.asarray(y, float)
    ll = -(y * np.log(p) + (1 - y) * np.log(1 - p))
    return pd.Series(ll, index=frame.index).groupby(frame["race_id"]).mean()


def main():
    params = json.load(open(REPORT / "metrics.json"))
    best = {k: tuple(v) for k, v in params["best_params"].items()}
    best_clf = {k: tuple(v) for k, v in params["best_params_clf"].items()}
    df = F.load_features()
    data = df[df["completed"]].copy()
    rows, dnf_rows = [], []
    for year in [y for y in sorted(data.year.unique()) if y >= FIRST_TEST_YEAR]:
        train, test = data[data.year < year], data[data.year == year]
        for stage in STAGES:
            feats = F.FEATURE_SETS[stage]
            leaves, n = best[stage]
            cl, cn = best_clf[stage]
            for h in HALFLIVES:
                score = pd.Series(T.fit_ranker(train, feats, leaves, n, h).predict(test[feats]), index=test.index)
                m = T.order_metrics(test, score, True)
                for tgt, lab in ((1, "win"), (3, "podium")):
                    p = T.race_normalise(T.fit_clf(train, feats, tgt, cl, cn, h).predict_proba(test[feats])[:, 1],
                                         test["race_id"], tgt)
                    m[f"{lab}_logloss"] = m["race_id"].map(per_race_ll(test, p, test["final_rank"] <= tgt))
                pd_ = T.fit_dnf(train, feats, h).predict_proba(test[feats])[:, 1]
                m["dnf_logloss"] = m["race_id"].map(per_race_ll(test, pd_, test["dnf"]))
                m["stage"], m["halflife"] = stage, label(h)
                rows.append(m)
                dnf_rows.append({"year": year, "stage": stage, "halflife": label(h),
                                 "mean_predicted": float(pd_.mean()), "mean_observed": float(test["dnf"].mean())})
        print(f"  {year} done", flush=True)
    res = pd.concat(rows, ignore_index=True)
    res.to_csv(REPORT / "recency_races.csv", index=False)
    pd.DataFrame(dnf_rows).to_csv(REPORT / "recency_dnf_calibration.csv", index=False)
    summarise(res, pd.DataFrame(dnf_rows))


def summarise(res, dnf):
    parts = {"finishing order (Spearman, higher is better)": ("spearman", +1, ["spearman"]),
             "win and podium chances (log loss, lower is better)": ("logloss", -1, ["win_logloss", "podium_logloss"]),
             "retirement chance (log loss, lower is better)": ("dnf_logloss", -1, ["dnf_logloss"])}
    L = ["# Recency weighting: should recent seasons count more?", "",
         "A training race counts half as much for every `half-life` years it is older than the newest one. "
         f"Walk-forward back-test; half-life chosen on {FIRST_TEST_YEAR}-{FIT_END} and judged on {FIT_END + 1} onward. "
         "Averages over the before-the-weekend and after-qualifying stages.", ""]
    decisions = {}
    for name, (key, sign, cols) in parts.items():
        L += [f"## {name}", "", "| half-life | 2018-22 | 2023 onward | 2023 onward, difference from none (95% interval) |",
              "|---|---|---|---|"]
        # one number per race: mean over the stages' columns
        res = res.copy()
        res["_v"] = res[cols].mean(axis=1)
        piv = res.pivot_table(index=["stage", "race_id", "year"], columns="halflife", values="_v").reset_index()
        fit = piv[piv.year <= FIT_END]
        held = piv[piv.year > FIT_END]
        scores = {}
        for h in [label(x) for x in HALFLIVES]:
            f_, g_ = fit[h].mean(), held[h].mean()
            d, lo, hi = T.paired_bootstrap(held[h].to_numpy(), held["none"].to_numpy())
            scores[h] = (f_, g_)
            L.append(f"| {h} | {f_:.4f} | {g_:.4f} | {d:+.4f} [{lo:+.4f}, {hi:+.4f}] |")
        better = (lambda a, b: a > b) if sign > 0 else (lambda a, b: a < b)
        cand = [h for h in scores if h != "none" and better(scores[h][0], scores["none"][0])]
        pick = None
        if cand:
            pick = max(cand, key=lambda h: sign * scores[h][0])
            if not better(scores[pick][1], scores["none"][1]):
                pick = None
        decisions[name] = pick
        L += ["", f"Rule outcome: **{'adopt ' + pick if pick else 'keep unweighted'}**.", ""]
    L += ["## Retirement calibration by season (mean predicted / observed)", "",
          "| half-life | " + " | ".join(str(y) for y in sorted(dnf.year.unique())) + " | 2018-26 average |",
          "|---|" + "---|" * (len(dnf.year.unique()) + 1)]
    d = dnf[dnf.stage == "post"]
    for h in [label(x) for x in HALFLIVES]:
        sub = d[d.halflife == h].sort_values("year")
        L.append(f"| {h} | " + " | ".join(f"{p:.3f}/{o:.3f}" for p, o in zip(sub.mean_predicted, sub.mean_observed))
                 + f" | {sub.mean_predicted.mean():.3f}/{sub.mean_observed.mean():.3f} |")
    (REPORT / "recency_summary.md").write_text("\n".join(L) + "\n")
    json.dump(decisions, open(REPORT / "recency_decision.json", "w"), indent=1)
    print("\n".join(L))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        r = pd.read_csv(REPORT / "recency_races.csv")
        summarise(r, pd.read_csv(REPORT / "recency_dnf_calibration.csv"))
    else:
        main()
