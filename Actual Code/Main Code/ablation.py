#!/usr/bin/env python3
"""Do the newer features (driver-vs-car ratings, circuit kind) actually help?

Walk-forward back-test over 2018-2026 (the models for season Y only ever see seasons < Y), the
same feature set with and without each addition, same LightGBM settings for every variant so the
only thing that changes is the inputs. Paired bootstrap over races says whether a difference is
bigger than noise.

    python ablation.py            (about 10-20 minutes; writes reports/ablation*.csv and .md)

Settings come from reports/metrics.json (chosen on 2022 with the base features). 2022 is also a test
season here, so 2022-2026 numbers are not independent of that choice; it affects every variant the
same way, so the comparison between variants is fair, but absolute numbers are a little optimistic.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import features as F
import train as T

REPORT = Path("reports")
FIRST_TEST_YEAR = 2018
ADDITIONS = {"base": [], "+ratings": F.RATINGS, "+circuit kind": F.CIRCUIT,
             "+both": F.RATINGS + F.CIRCUIT}
STAGES = {"pre": [], "post": F.PRACTICE + F.POST_EXTRA + F.SPRINT}


def variant_features(stage, name):
    return F.PRE_BASE + ADDITIONS[name] + (F.PRACTICE + F.POST_EXTRA + F.SPRINT if stage == "post" else [])


def per_race_logloss(frame, p, target):
    y = (frame["final_rank"] <= target).astype(float).to_numpy()
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    ll = -(y * np.log(p) + (1 - y) * np.log(1 - p))
    return pd.Series(ll, index=frame.index).groupby(frame["race_id"]).mean()


def main():
    params = json.load(open(REPORT / "metrics.json"))
    best = {k: tuple(v) for k, v in params["best_params"].items()}
    best_clf = {k: tuple(v) for k, v in params["best_params_clf"].items()}
    df = F.load_features()
    data = df[df["completed"]].copy()
    years = [y for y in sorted(data.year.unique()) if y >= FIRST_TEST_YEAR]
    rows = []
    for year in years:
        train, test = data[data.year < year], data[data.year == year]
        for stage in STAGES:
            leaves, n = best[stage]
            cl, cn = best_clf[stage]
            for name in ADDITIONS:
                feats = variant_features(stage, name)
                score = pd.Series(T.fit_ranker(train, feats, leaves, n).predict(test[feats]), index=test.index)
                m = T.order_metrics(test, score, True)
                for tgt, lab in ((1, "win"), (3, "podium")):
                    p = T.race_normalise(T.fit_clf(train, feats, tgt, cl, cn).predict_proba(test[feats])[:, 1],
                                         test["race_id"], tgt)
                    m[f"{lab}_logloss"] = m["race_id"].map(per_race_logloss(test, p, tgt))
                m["stage"], m["variant"] = stage, name
                rows.append(m)
        print(f"  {year} done", flush=True)
    for label, col in (("baseline: grid order", "grid"), ("baseline: recent driver form", "d_finish_ewm3")):
        for year in years:
            test = data[data.year == year]
            m = T.order_metrics(test, test[col], False)
            m["stage"], m["variant"] = "baseline", label
            rows.append(m)
    res = pd.concat(rows, ignore_index=True)
    res.to_csv(REPORT / "ablation_races.csv", index=False)
    summarise(res)


def summarise(res):
    metrics = ["winner_hit", "podium_overlap", "spearman", "mae_pos", "win_logloss", "podium_logloss"]
    lower_better = {"mae_pos", "win_logloss", "podium_logloss"}
    windows = {f"{FIRST_TEST_YEAR}-2026": (FIRST_TEST_YEAR, 2026), "2023-2026": (2023, 2026)}
    L = ["# Ablation: do ratings and circuit kind help?", "",
         "Walk-forward back-test; same settings for every variant. Differences are variant minus base, "
         "averaged over races, with a 95% interval from resampling whole races. "
         "**Clear** = the interval excludes zero.", ""]
    boot_rows = []
    for wname, (y0, y1) in windows.items():
        sub = res[(res.year >= y0) & (res.year <= y1)]
        nraces = sub[(sub.stage == "pre") & (sub.variant == "base")].race_id.nunique()
        L += [f"## {wname} ({nraces} races)", "",
              "| stage | variant | winner hit | podium overlap (of 3) | Spearman | MAE | win log loss | podium log loss |",
              "|---|---|---|---|---|---|---|---|"]
        for stage in ("pre", "post"):
            for v in ADDITIONS:
                g = sub[(sub.stage == stage) & (sub.variant == v)]
                L.append(f"| {stage} | {v} | {g.winner_hit.mean():.1%} | {g.podium_overlap.mean() * 3:.2f} | "
                         f"{g.spearman.mean():.3f} | {g.mae_pos.mean():.2f} | {g.win_logloss.mean():.4f} | "
                         f"{g.podium_logloss.mean():.4f} |")
        for v in ("baseline: grid order", "baseline: recent driver form"):
            g = sub[(sub.stage == "baseline") & (sub.variant == v)]
            L.append(f"| - | {v} | {g.winner_hit.mean():.1%} | {g.podium_overlap.mean() * 3:.2f} | "
                     f"{g.spearman.mean():.3f} | {g.mae_pos.mean():.2f} | - | - |")
        L += ["", "Difference from base (variant - base):", "",
              "| stage | variant | metric | difference | 95% interval | clear? | better? |", "|---|---|---|---|---|---|---|"]
        for stage in ("pre", "post"):
            base = sub[(sub.stage == stage) & (sub.variant == "base")].set_index("race_id")
            for v in list(ADDITIONS)[1:]:
                g = sub[(sub.stage == stage) & (sub.variant == v)].set_index("race_id")
                for met in metrics:
                    d, lo, hi = T.paired_bootstrap(g[met].loc[base.index], base[met])
                    clear = (lo > 0) or (hi < 0)
                    good = (d < 0) if met in lower_better else (d > 0)
                    boot_rows.append({"window": wname, "stage": stage, "variant": v, "metric": met,
                                      "diff": d, "lo": lo, "hi": hi, "clear": clear, "better": good})
                    if met in ("spearman", "win_logloss", "podium_logloss", "mae_pos"):
                        L.append(f"| {stage} | {v} | {met} | {d:+.4f} | [{lo:+.4f}, {hi:+.4f}] | "
                                 f"{'yes' if clear else 'no'} | {'yes' if good else 'no'} |")
        L.append("")
    by_year = (res[res.stage.isin(["pre", "post"]) & res.variant.isin(["base", "+both"])]
               .groupby(["stage", "variant", "year"])[["winner_hit", "spearman"]].mean().round(3))
    L += ["## By season (base vs +both)", "", "| stage | variant | year | winner hit | Spearman |", "|---|---|---|---|---|"]
    for (stage, v, y), r in by_year.iterrows():
        L.append(f"| {stage} | {v} | {y} | {r.winner_hit:.1%} | {r.spearman:.3f} |")
    pd.DataFrame(boot_rows).to_csv(REPORT / "ablation_significance.csv", index=False)
    (REPORT / "ablation_summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        summarise(pd.read_csv(REPORT / "ablation_races.csv"))
    else:
        main()
