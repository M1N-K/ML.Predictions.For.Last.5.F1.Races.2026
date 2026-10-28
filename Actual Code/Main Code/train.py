#!/usr/bin/env python3
"""Train, backtest and save the F1 race prediction models.

Stages (feature sets): "pre" (before the weekend), "fp" (after practice), "post" (after
qualifying / sprint). Two older sets, "pre_v1" and "post_v1" (the first version of the model), are
back-tested too so the value of the additions can be measured.

Models (LightGBM) per stage:
    ranker   LambdaRank model that orders the whole field (the headline prediction)
    win      binary classifier, probabilities normalised per race to sum to 1
    podium   binary classifier, probabilities normalised per race to sum to 3
    dnf      retirement probability (used by the championship simulation)

Evaluation is walk-forward by season: to predict season Y the models only ever see seasons < Y.
Hyper-parameters are chosen on 2022 (trained on <= 2021), before any test season is touched.
The randomness of finishing orders (Plackett-Luce temperature) is fitted on the back-test.
"""
import json
import warnings
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression

import features as F
import simcore

warnings.filterwarnings("ignore")
MODEL_DIR, REPORT_DIR = Path("models"), Path("reports")
VALID_YEAR = 2022
TEST_YEARS = list(range(2018, 2027))        # walk-forward: season Y is predicted from seasons < Y
CLEAN_FROM = 2023                           # seasons after the tuning season: not touched by any choice
GRID = [(leaves, n) for leaves in (7, 15, 31) for n in (150, 300, 600)]
GRID_CLF = [(leaves, n) for leaves in (4, 8, 16) for n in (100, 200, 400)]   # classifiers: smaller models
BASE = dict(learning_rate=0.03, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
            reg_lambda=5.0, min_child_samples=30, random_state=0, verbose=-1, n_jobs=4)
POINTS = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}
PRODUCTION = list(F.FEATURE_SETS)            # pre, fp, post
CAL_BINS = [0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 0.70, 1.0001]


# ------------------------------------------------------------------------------ model fitting
# Recency weighting: a training race counts 0.5 ** (age / halflife), age in years before the newest
# training race. None = every race counts the same. Chosen by recency_test.py (2018-2022, checked on
# 2023 onward); see reports/recency_summary.md.
HALFLIFE = {"ranker": None, "clf": None, "dnf": None}


def recency_weights(train, halflife):
    """Per-row weights (None if halflife is None). Whole races share one weight."""
    if not halflife:
        return None
    age = (train["date"].max() - train["date"]).dt.days.to_numpy() / 365.25
    return 0.5 ** (age / halflife)


def fit_ranker(train, feats, leaves, n, halflife=None):
    train = train.sort_values("race_id", kind="stable")
    groups = train.groupby("race_id", sort=False).size().to_numpy()
    # Relevance = championship points for the finishing position (25,18,15,...,1, then 0), so the
    # ranker concentrates on the places that matter. Chosen over a plain linear-rank label using
    # seasons 2019-2022 only (all before the test seasons).
    y = train["final_rank"].map(POINTS).fillna(0).astype(int)
    m = lgb.LGBMRanker(objective="lambdarank", label_gain=list(range(26)),
                       num_leaves=leaves, n_estimators=n, **BASE)
    m.fit(train[feats], y, group=groups, sample_weight=recency_weights(train, halflife))
    return m


def fit_clf(train, feats, target, leaves, n, halflife=None):
    m = lgb.LGBMClassifier(objective="binary", num_leaves=leaves, n_estimators=n, **BASE)
    m.fit(train[feats], (train["final_rank"] <= target).astype(int),
          sample_weight=recency_weights(train, halflife))
    return m


def fit_dnf(train, feats, halflife=None):
    """Retirement model: a noisy target, so deliberately small and heavily regularised."""
    t = train[train["dnf"].notna()]
    params = {**BASE, "min_child_samples": 60}
    m = lgb.LGBMClassifier(objective="binary", num_leaves=5, n_estimators=150, **params)
    m.fit(t[feats], t["dnf"].astype(int), sample_weight=recency_weights(t, halflife))
    return m


def race_normalise(p, race_ids, total):
    s = pd.Series(p, index=race_ids.index)
    out = s / s.groupby(race_ids).transform("sum") * total
    return out.clip(1e-4, 1 - 1e-4)


# ------------------------------------------------------------------------------------ metrics
def order_metrics(test, score, higher_is_better=True):
    """Per-race ranking quality of `score` (a Series aligned with test)."""
    rows = []
    for rid, g in test.assign(_s=score).groupby("race_id"):
        s = g["_s"].fillna(g["_s"].median() if g["_s"].notna().any() else 0).to_numpy()
        order = np.argsort(-s if higher_is_better else s, kind="stable")
        pred = np.empty(len(g), int)
        pred[order] = np.arange(1, len(g) + 1)
        act = g["final_rank"].to_numpy()
        rows.append({
            "race_id": rid, "year": int(g["year"].iloc[0]),
            "winner_hit": float(act[pred == 1][0] == 1),
            "podium_overlap": len(set(np.where(pred <= 3)[0]) & set(np.where(act <= 3)[0])) / 3,
            "top10_overlap": len(set(np.where(pred <= 10)[0]) & set(np.where(act <= 10)[0])) / 10,
            "spearman": spearmanr(pred, act)[0],
            "mae_pos": float(np.abs(pred - act).mean()),
        })
    return pd.DataFrame(rows)


def prob_metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), float(np.mean((p - y) ** 2))


def slot_baseline(train, test, target):
    """Empirical P(rank <= target | grid slot) from the training years, normalised per race."""
    freq = (train.assign(hit=(train.final_rank <= target)).groupby(train["grid"].clip(upper=22))["hit"].mean())
    p = test["grid"].clip(upper=22).map(freq).fillna(freq.mean())
    return race_normalise(p.to_numpy(), test["race_id"], target)


def reliability(y, p, bins=CAL_BINS):
    d = pd.DataFrame({"y": np.asarray(y, float), "p": np.asarray(p, float)})
    d["bin"] = pd.cut(d["p"], bins, right=False)
    t = d.groupby("bin", observed=True).agg(n=("y", "size"), mean_p=("p", "mean"), observed=("y", "mean"))
    t["lo"] = [iv.left for iv in t.index]
    t["hi"] = [min(iv.right, 1.0) for iv in t.index]
    return t.reset_index(drop=True)


def ece(t):
    return float((t["n"] * (t["observed"] - t["mean_p"]).abs()).sum() / t["n"].sum())


def paired_bootstrap(a, b, reps=4000, seed=0):
    """Mean and 95% interval of (a - b) over races, resampling whole races."""
    d = np.asarray(a, float) - np.asarray(b, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), (reps, len(d)))
    means = d[idx].mean(axis=1)
    return float(d.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


# ------------------------------------------------------------------------------ the main flow
def train_final(data, best, best_clf, taus):
    """Fit and save the production models (all stages) on every completed race."""
    bundle = {"features": F.FEATURE_SETS, "best_params": {k: list(v) for k, v in best.items()},
              "best_params_clf": {k: list(v) for k, v in best_clf.items()},
              "pl_tau": taus, "trained_through": data.race_id.max(), "models": {}}
    for name in PRODUCTION:
        feats = F.FEATURE_SETS[name]
        leaves, n = best[name]
        cl, cn = best_clf[name]
        bundle["models"][f"ranker_{name}"] = fit_ranker(data, feats, leaves, n)
        bundle["models"][f"win_{name}"] = fit_clf(data, feats, 1, cl, cn)
        bundle["models"][f"podium_{name}"] = fit_clf(data, feats, 3, cl, cn)
        bundle["models"][f"dnf_{name}"] = fit_dnf(data, feats)
    joblib.dump(bundle, MODEL_DIR / "f1_models.joblib")
    return bundle


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fast", action="store_true",
                    help="only refit the final models on the latest data (about 10 seconds), reusing "
                         "the tuned settings; skips the back-test and reports")
    args = ap.parse_args()
    REPORT_DIR.mkdir(exist_ok=True)
    MODEL_DIR.mkdir(exist_ok=True)
    df = F.load_features()
    data = df[df["completed"]].copy()
    print(f"{len(data)} driver-race rows, {data.race_id.nunique()} races, "
          f"{data.year.min()}-{data.year.max()} (through {data.race_id.max()})")
    if args.fast:
        old = joblib.load(MODEL_DIR / "f1_models.joblib")
        bundle = train_final(data, {k: tuple(v) for k, v in old["best_params"].items()},
                             {k: tuple(v) for k, v in old["best_params_clf"].items()}, old["pl_tau"])
        print(f"Refitted the models through {bundle['trained_through']} (tuned settings reused).")
        return

    # ---- 1. hyper-parameter choice on the validation season ---------------------------------
    best, best_clf = {}, {}
    tr, va = data[data.year < VALID_YEAR], data[data.year == VALID_YEAR]
    print(f"\nTuning on {VALID_YEAR} (train < {VALID_YEAR}): rankers by Spearman per race, "
          "win/podium classifiers by log loss:")
    for name, feats in F.ALL_SETS.items():
        scores = {}
        for leaves, n in GRID:
            m = fit_ranker(tr, feats, leaves, n)
            scores[(leaves, n)] = order_metrics(va, pd.Series(m.predict(va[feats]), index=va.index))["spearman"].mean()
        best[name] = max(scores, key=scores.get)
        cscores = {}
        for leaves, n in GRID_CLF:
            ll = 0.0
            for tgt in (1, 3):
                p = race_normalise(fit_clf(tr, feats, tgt, leaves, n).predict_proba(va[feats])[:, 1],
                                   va["race_id"], tgt)
                ll += prob_metrics(va["final_rank"] <= tgt, p)[0]
            cscores[(leaves, n)] = ll
        best_clf[name] = min(cscores, key=cscores.get)
        print(f"  {name:8s} ranker {best[name][0]:>2d} leaves x {best[name][1]:>3d} trees "
              f"(Spearman {scores[best[name]]:.3f}) | classifiers {best_clf[name][0]:>2d} x {best_clf[name][1]:>3d}")

    # ---- 2. walk-forward backtest -----------------------------------------------------------
    race_rows, prob_rows, pred_frames = [], [], []
    for year in TEST_YEARS:
        train, test = data[data.year < year], data[data.year == year]
        if test.empty:
            continue
        out = test[["race_id", "year", "round", "driver_id", "team", "grid", "final_rank", "dnf"]].copy()
        for name, feats in F.ALL_SETS.items():
            leaves, n = best[name]
            cl, cn = best_clf[name]
            out[f"score_{name}"] = fit_ranker(train, feats, leaves, n).predict(test[feats])
            for label, tgt in (("win", 1), ("podium", 3)):
                clf = fit_clf(train, feats, tgt, cl, cn)
                out[f"p_{label}_{name}"] = race_normalise(clf.predict_proba(test[feats])[:, 1], test["race_id"], tgt)
            if name in PRODUCTION:
                out[f"p_dnf_{name}"] = fit_dnf(train, feats).predict_proba(test[feats])[:, 1]
        out["p_win_grid"] = slot_baseline(train, test, 1)
        out["p_podium_grid"] = slot_baseline(train, test, 3)
        out["dnf_base_rate"] = train["dnf"].mean()
        pred_frames.append(out)

        entries = {
            "post (after qualifying)": (out["score_post"], True),
            "post, first version": (out["score_post_v1"], True),
            "baseline: grid order": (test["grid"], False),
            "fp (after practice)": (out["score_fp"], True),
            "pre (before the weekend)": (out["score_pre"], True),
            "pre, first version": (out["score_pre_v1"], True),
            "baseline: recent driver form": (test["d_finish_ewm3"], False),
        }
        for label, (score, hib) in entries.items():
            m = order_metrics(test, score, hib)
            m["model"] = label
            race_rows.append(m)
        for label, tgt in (("win", 1), ("podium", 3)):
            y = (test["final_rank"] <= tgt)
            uniform = tgt / test.groupby("race_id")["driver_id"].transform("size")
            for model, p in [(f"{s}", out[f"p_{label}_{s}"]) for s in F.ALL_SETS] + [
                    ("baseline: grid slot frequency", out[f"p_{label}_grid"]),
                    ("baseline: uniform", uniform.clip(1e-4, 1 - 1e-4))]:
                ll, br = prob_metrics(y, p)
                prob_rows.append({"year": year, "target": label, "model": model, "logloss": ll, "brier": br,
                                  "n": len(y)})
        for s in PRODUCTION:
            ll, br = prob_metrics(test["dnf"], out[f"p_dnf_{s}"])
            prob_rows.append({"year": year, "target": "dnf", "model": s, "logloss": ll, "brier": br, "n": len(test)})
        ll, br = prob_metrics(test["dnf"], np.full(len(test), train["dnf"].mean()))
        prob_rows.append({"year": year, "target": "dnf", "model": "baseline: average rate", "logloss": ll,
                          "brier": br, "n": len(test)})

    races = pd.concat(race_rows, ignore_index=True)
    probs = pd.DataFrame(prob_rows)
    preds = pd.concat(pred_frames, ignore_index=True)
    races.to_csv(REPORT_DIR / "backtest_races.csv", index=False)
    preds.to_csv(REPORT_DIR / "backtest_predictions.csv", index=False)

    metric_cols = ["winner_hit", "podium_overlap", "top10_overlap", "spearman", "mae_pos"]
    model_order = list(entries)
    overall = races.groupby("model")[metric_cols].mean().reindex(model_order)
    clean = races[races.year >= CLEAN_FROM]
    overall_clean = clean.groupby("model")[metric_cols].mean().reindex(model_order)
    by_year = races.groupby(["model", "year"])[metric_cols].mean().reindex(model_order, level=0)
    n_races = races[races.model == model_order[0]].groupby("year").size()
    prob_overall = probs.assign(w=probs.n).groupby(["target", "model"]).apply(
        lambda g: pd.Series({"logloss": np.average(g.logloss, weights=g.w), "brier": np.average(g.brier, weights=g.w)}))

    # ---- 3. is each improvement real? paired bootstrap over races ---------------------------
    wide = {m: races[races.model == m].set_index("race_id") for m in model_order}
    pairs = [("post (after qualifying)", "post, first version"),
             ("post (after qualifying)", "baseline: grid order"),
             ("fp (after practice)", "pre (before the weekend)"),
             ("fp (after practice)", "pre, first version"),
             ("pre (before the weekend)", "pre, first version"),
             ("pre (before the weekend)", "baseline: recent driver form")]
    boot = []
    first_year = int(races.year.min())
    for window, y0 in ((f"{first_year}-{int(races.year.max())}", first_year), (f"{CLEAN_FROM}-{int(races.year.max())}", CLEAN_FROM)):
        keep = set(races.loc[races.year >= y0, "race_id"])
        for a, b in pairs:
            wa, wb = wide[a].loc[wide[a].index.isin(keep)], wide[b].loc[wide[b].index.isin(keep)]
            for metric in ("spearman", "winner_hit", "mae_pos"):
                mean, lo, hi = paired_bootstrap(wa[metric].loc[wb.index], wb[metric])
                boot.append({"window": window, "A": a, "B": b, "metric": metric, "diff": mean, "lo": lo,
                             "hi": hi, "clear": (lo > 0) or (hi < 0)})
    boot = pd.DataFrame(boot)
    boot.to_csv(REPORT_DIR / "backtest_significance.csv", index=False)

    # ---- 4. calibration: do "30%" events happen about 30% of the time? -----------------------
    cal_rows, ece_rows = [], []
    for target, col in (("win", "p_win"), ("podium", "p_podium"), ("dnf", "p_dnf")):
        for s in PRODUCTION:
            y = (preds["final_rank"] <= {"win": 1, "podium": 3}[target]) if target != "dnf" else preds["dnf"]
            t = reliability(y, preds[f"{col}_{s}"])
            t.insert(0, "stage", s)
            t.insert(0, "target", target)
            cal_rows.append(t)
            ece_rows.append({"target": target, "stage": s, "ECE": ece(t),
                             "mean_predicted": float(preds[f"{col}_{s}"].mean()),
                             "mean_observed": float(np.mean(y))})
    cal = pd.concat(cal_rows, ignore_index=True)
    cal.to_csv(REPORT_DIR / "calibration.csv", index=False)
    ece_df = pd.DataFrame(ece_rows)
    ece_df.to_csv(REPORT_DIR / "calibration_summary.csv", index=False)

    # Would a simple recalibration help? Fit on the 2018-2023 back-test, score on 2024-26 (out of sample).
    recal = []
    early, late = preds[preds.year <= 2023], preds[preds.year >= 2024]
    for target, col in (("win", "p_win"), ("podium", "p_podium")):
        for s in PRODUCTION:
            ytr = (early["final_rank"] <= {"win": 1, "podium": 3}[target]).astype(int)
            yte = (late["final_rank"] <= {"win": 1, "podium": 3}[target]).astype(int)
            logit = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4))).to_numpy().reshape(-1, 1)
            lr = LogisticRegression(C=100).fit(logit(early[f"{col}_{s}"]), ytr)
            raw = prob_metrics(yte, late[f"{col}_{s}"])[0]
            fixed = prob_metrics(yte, lr.predict_proba(logit(late[f"{col}_{s}"]))[:, 1])[0]
            recal.append({"target": target, "stage": s, "logloss_raw": raw, "logloss_recalibrated": fixed})
    recal = pd.DataFrame(recal)
    recal.to_csv(REPORT_DIR / "calibration_recalibration_test.csv", index=False)

    # ---- 5. randomness of finishing orders (for the championship simulation) -----------------
    taus, tau_tables = {}, []
    for s in PRODUCTION:
        taus[s], t = simcore.fit_temperature(preds, s, POINTS)
        tau_tables.append(t)
    pd.concat(tau_tables).to_csv(REPORT_DIR / "simulation_temperature_fit.csv", index=False)
    pl_check = pd.concat([t[t.tau == taus[t.stage.iloc[0]]] for t in tau_tables])
    pl_check["win_logloss_classifier"] = [prob_metrics(preds.final_rank == 1, preds[f"p_win_{s}"])[0]
                                          for s in pl_check.stage]
    pl_check.to_csv(REPORT_DIR / "simulation_check.csv", index=False)

    # ---- 6. report --------------------------------------------------------------------------
    n_clean = int(n_races[n_races.index >= CLEAN_FROM].sum())
    lines = ["# Backtest (walk-forward by season)", "",
             f"Test races: {int(n_races.sum())} ({', '.join(f'{y}: {c}' for y, c in n_races.items())}). "
             "For each season the models were trained only on earlier seasons.", "",
             f"Settings were chosen on {VALID_YEAR}, so {VALID_YEAR} and the seasons before it are not a clean test "
             f"of those choices. The {CLEAN_FROM}-{int(races.year.max())} table ({n_clean} races) is the one "
             "nothing was tuned on; the longer table shows whether the picture holds on more history.", ""]
    for title, table in ((f"## Finishing-order quality, {int(races.year.min())}-{int(races.year.max())} "
                          f"(mean per race, {int(n_races.sum())} races)", overall),
                         (f"## Finishing-order quality, {CLEAN_FROM}-{int(races.year.max())} "
                          f"(never used for any choice, {n_clean} races)", overall_clean)):
        lines += [title, "", "| model | winner hit | podium overlap (of 3) | top-10 overlap | Spearman | MAE (places) |",
                  "|---|---|---|---|---|---|"]
        for model, r in table.iterrows():
            lines.append(f"| {model} | {r.winner_hit:.1%} | {r.podium_overlap * 3:.2f} | "
                         f"{r.top10_overlap * 10:.2f} | {r.spearman:.3f} | {r.mae_pos:.2f} |")
        lines.append("")
    lines += ["## Is the improvement real? (paired difference over the same races, 95% interval)", "",
              "A difference only counts as clear if its interval excludes zero.", "",
              "| window | A | B | metric | A - B | 95% interval | clear? |", "|---|---|---|---|---|---|---|"]
    for r in boot.itertuples():
        lines.append(f"| {r.window} | {r.A} | {r.B} | {r.metric} | {r.diff:+.3f} | [{r.lo:+.3f}, {r.hi:+.3f}] | "
                     f"{'yes' if r.clear else 'no'} |")
    lines += ["", "## By season", "", "| model | year | winner hit | podium overlap (of 3) | Spearman | MAE |",
              "|---|---|---|---|---|---|"]
    for (model, year), r in by_year.iterrows():
        lines.append(f"| {model} | {year} | {r.winner_hit:.1%} | {r.podium_overlap * 3:.2f} | "
                     f"{r.spearman:.3f} | {r.mae_pos:.2f} |")
    lines += ["", "## Probability quality (lower is better)", "",
              "| target | model | log loss | Brier |", "|---|---|---|---|"]
    for (target, model), r in prob_overall.iterrows():
        lines.append(f"| {target} | {model} | {r.logloss:.4f} | {r.brier:.4f} |")
    lines += ["", "## Calibration (do predicted chances match how often things happen?)", "",
              "ECE = average gap between predicted and observed frequency (0 is perfect).", "",
              "| target | stage | ECE | mean predicted | mean observed |", "|---|---|---|---|---|"]
    for r in ece_df.itertuples():
        lines.append(f"| {r.target} | {r.stage} | {r.ECE:.3f} | {r.mean_predicted:.3f} | {r.mean_observed:.3f} |")
    lines += ["", "Would a simple recalibration (fit on 2018-2023, tested on 2024-26) help? Log loss:", "",
              "| target | stage | as is | recalibrated |", "|---|---|---|---|"]
    for r in recal.itertuples():
        lines.append(f"| {r.target} | {r.stage} | {r.logloss_raw:.4f} | {r.logloss_recalibrated:.4f} |")
    lines += ["", "## Simulation check (how random the championship simulation makes each race)", "",
              "The simulation's randomness setting was fitted on the back-test so that simulated points and "
              "win chances match what really happened.", "",
              "| stage | setting | points error (MSE) | win log loss, simulation | win log loss, classifier | "
              "top pick wins: simulated | top pick wins: actual |", "|---|---|---|---|---|---|---|"]
    for r in pl_check.itertuples():
        lines.append(f"| {r.stage} | {r.tau:.2f} | {r.points_mse:.2f} | {r.win_logloss:.4f} | "
                     f"{r.win_logloss_classifier:.4f} | {r.top_pick_win_pred:.1%} | {r.top_pick_win_actual:.1%} |")
    (REPORT_DIR / "backtest_summary.md").write_text("\n".join(lines) + "\n")

    print("\n" + "\n".join(lines[:30]))
    print("\nSignificance (A - B, 95% interval):")
    print(boot[boot.metric.isin(["spearman", "winner_hit"])].round(3).to_string(index=False))
    print("\nCalibration ECE:\n" + ece_df.round(3).to_string(index=False))
    print("\nRecalibration test (log loss):\n" + recal.round(4).to_string(index=False))
    print("\nSimulation check:\n" + pl_check.round(4).to_string(index=False))

    # ---- 7. final models on everything completed so far -------------------------------------
    bundle = train_final(data, best, best_clf, taus)

    imp = pd.DataFrame({name: pd.Series(bundle["models"][f"ranker_{name}"].booster_.feature_importance("gain"),
                                        index=F.FEATURE_SETS[name]) for name in PRODUCTION})
    imp = (imp / imp.sum()).sort_values("post", ascending=False)
    imp.round(4).to_csv(REPORT_DIR / "feature_importance.csv")
    print("\nTop features (share of total gain), final rankers:")
    print(imp.head(12).round(3).to_string())

    json.dump({"trained_through": bundle["trained_through"], "best_params": bundle["best_params"],
               "best_params_clf": bundle["best_params_clf"], "pl_tau": taus, "overall": overall.round(4).to_dict("index"),
               "overall_clean": overall_clean.round(4).to_dict("index"), "clean_from": CLEAN_FROM},
              open(REPORT_DIR / "metrics.json", "w"), indent=1)
    print(f"\nSaved models/f1_models.joblib and reports/ (trained through {bundle['trained_through']})")


if __name__ == "__main__":
    main()
