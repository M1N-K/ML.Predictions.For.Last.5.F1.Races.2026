#!/usr/bin/env python3
"""Replay past seasons to check (and fit) how much the simulated races should depend on each other.

For every season 2018-2025 and three cut points (30%, 50%, 70% of the season) the script does what
the real tool does mid-season: it hides the results of the races after the cut, predicts all of them
from what was known at the cut (models trained on earlier seasons only), simulates the rest of the
season, and compares the simulated points with what really happened.

    python season_backtest.py            (about 10 minutes the first time; stale predictions are cached)

Writes reports/dependence_*.csv, reports/dependence.json (the fitted settings that
simulate_season.py uses) and reports/dependence_summary.md.

What is measured
  * residual persistence: are the model's misses for a team (and a team's retirements) correlated from
    one race to the next?
  * season coverage: do the middle 80% / 50% of the simulated remaining-points totals contain the real
    total 80% / 50% of the time? CRPS (lower is better) scores the whole simulated distribution.
  * title odds: the probability the simulation gave to the driver who really finished top.
Settings are chosen on the 2018-2022 seasons and judged on 2023-2025, which they never saw.
"""
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

import engine as E
import features as F
import simcore as S
import train as T

REPORT = Path("reports")
CACHE = REPORT / "dependence_stale_predictions.pkl"
YEARS = list(range(2018, 2026))
CUTS = (0.3, 0.5, 0.7)
FIT_YEARS = range(2018, 2023)
RUNS = 1500


def stale_predictions():
    """Predictions for every race after each cut, made with only what was known at the cut."""
    if CACHE.exists():
        return pd.read_pickle(CACHE)
    res, races, weekend = pd.read_csv("data/results.csv"), pd.read_csv("data/races.csv"), pd.read_csv("data/weekend.csv")
    metrics = json.load(open(REPORT / "metrics.json"))
    leaves, n = metrics["best_params"]["pre"]
    feats = F.FEATURE_SETS["pre"]
    full = F.build_features(res, weekend, races)
    data = full[full.completed]
    out = []
    for year in YEARS:
        train = data[data.year < year]
        ranker, dnf = T.fit_ranker(train, feats, leaves, n), T.fit_dnf(train, feats)
        season = races[races.year == year].sort_values("round")
        for frac in CUTS:
            cut = int(round(len(season) * frac))
            future = set(season[season["round"] > cut]["race_id"])
            keep_res = res[(res.year <= year) & ~res.race_id.isin(future)]
            races_m = races[races.year <= year].copy()
            races_m.loc[races_m.race_id.isin(future), "has_results"] = False
            weekend_m = weekend[weekend.race_id.isin(set(keep_res.race_id))]
            frame = keep_res
            targets = sorted(future)
            for t in targets:
                frame = E.with_upcoming_lineup(frame, races_m, t)
            df = F.build_features(frame, weekend_m, races_m)
            for t in targets:
                rows = df[df.race_id == t].copy()
                rows["score"] = ranker.predict(rows[feats])
                rows["p_dnf"] = dnf.predict_proba(rows[feats])[:, 1]
                rows["cut"], rows["cut_frac"] = cut, frac
                out.append(rows[["race_id", "year", "round", "cut", "cut_frac", "driver_id", "team", "score", "p_dnf"]])
            print(f"  stale predictions {year} cut {cut}/{len(season)}", flush=True)
    stale = pd.concat(out, ignore_index=True)
    stale.to_pickle(CACHE)
    return stale


def actual_table():
    res, races, weekend = pd.read_csv("data/results.csv"), pd.read_csv("data/races.csv"), pd.read_csv("data/weekend.csv")
    full = F.build_features(res, weekend, races)
    d = full[full.completed].copy()
    d["pts"] = np.where(d["pos_num"].between(1, 10) & ~d["is_dsq"], d["pos_num"].map(T.POINTS), 0.0)
    d["pts"] = d["pts"].fillna(0.0)
    return d[["race_id", "year", "round", "driver_id", "team", "pts", "pos_num", "final_rank", "finish_pct",
              "dnf", "n_starters"]]


# ---------------------------------------------------------------------------- residual persistence
def persistence(stale, actual):
    """Lag-k correlation of the model's misses, per team, between consecutive races after a cut."""
    m = stale.merge(actual[["race_id", "driver_id", "finish_pct", "dnf"]], on=["race_id", "driver_id"], how="inner")
    m["pred_rank"] = m.groupby(["cut", "cut_frac", "race_id"])["score"].rank(ascending=False)
    n = m.groupby(["cut", "cut_frac", "race_id"])["driver_id"].transform("size")
    m["miss"] = m["finish_pct"] - (m["pred_rank"] - 1) / (n - 1)           # >0: finished behind the prediction
    m["dnf_miss"] = m["dnf"] - m["p_dnf"]
    g = m.groupby(["year", "cut_frac", "team", "race_id", "round"]).agg(
        miss=("miss", "mean"), dnf_miss=("dnf_miss", "mean"), n=("miss", "size")).reset_index()
    g = g.sort_values(["year", "cut_frac", "team", "round"])
    rows = []
    for lag in (1, 2, 3, 4):
        for col in ("miss", "dnf_miss"):
            x, y = [], []
            for _, s in g.groupby(["year", "cut_frac", "team"]):
                v = s[col].to_numpy()
                if len(v) > lag:
                    x.append(v[:-lag])
                    y.append(v[lag:])
            x, y = np.concatenate(x), np.concatenate(y)
            r = float(np.corrcoef(x, y)[0, 1])
            # bootstrap over (year, cut, team) series so the interval respects the clustering
            series = [s[col].to_numpy() for _, s in g.groupby(["year", "cut_frac", "team"]) if len(s) > lag]
            rng = np.random.default_rng(0)
            boots = []
            for _ in range(600):
                pick = rng.integers(0, len(series), len(series))
                xx = np.concatenate([series[i][:-lag] for i in pick])
                yy = np.concatenate([series[i][lag:] for i in pick])
                boots.append(np.corrcoef(xx, yy)[0, 1])
            rows.append({"lag_races": lag, "quantity": {"miss": "team finishing position", "dnf_miss": "team retirements"}[col],
                         "correlation": r, "lo": float(np.percentile(boots, 2.5)), "hi": float(np.percentile(boots, 97.5)),
                         "pairs": len(x)})
    # the two cars of a team in the same race
    mates = m.groupby(["race_id", "team"]).filter(lambda s: len(s) == 2)
    a = mates.groupby(["race_id", "team"])
    first = a.nth(0).set_index(["race_id", "team"])
    second = a.nth(1).set_index(["race_id", "team"]).reindex(first.index)
    rows.append({"lag_races": 0, "quantity": "team-mates, same race: finishing position",
                 "correlation": float(np.corrcoef(first["miss"], second["miss"])[0, 1]), "lo": np.nan, "hi": np.nan,
                 "pairs": len(first)})
    rows.append({"lag_races": 0, "quantity": "team-mates, same race: retirements",
                 "correlation": float(np.corrcoef(first["dnf_miss"], second["dnf_miss"])[0, 1]), "lo": np.nan, "hi": np.nan,
                 "pairs": len(first)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------- season simulation
def crps(samples, y):
    """CRPS of an empirical distribution (samples along axis 0) for each column's observation y."""
    s = np.sort(samples, axis=0)
    R = s.shape[0]
    term1 = np.abs(s - y[None, :]).mean(axis=0)
    ranks = np.arange(1, R + 1)[:, None]
    term2 = (s * (2 * ranks - R - 1)).sum(axis=0) / R ** 2
    return term1 - term2


def evaluate(stale, actual, dep, tau, seed=0):
    """-> one row per (year, cut, driver) with the simulated distribution's score."""
    rng = np.random.default_rng(seed)
    rows, title = [], []
    pts = actual.set_index(["race_id", "driver_id"])["pts"]
    started = set(zip(actual.race_id, actual.driver_id))
    for (year, frac), g in stale.groupby(["year", "cut_frac"]):
        race_ids = list(dict.fromkeys(g.sort_values("round")["race_id"]))
        drivers = sorted(g["driver_id"].unique())
        didx = {d: i for i, d in enumerate(drivers)}
        teams = sorted(g["team"].unique())
        tidx = {t: i for i, t in enumerate(teams)}
        team_vec = np.full(len(drivers), -1)
        for d, t in g.drop_duplicates("driver_id")[["driver_id", "team"]].itertuples(index=False):
            team_vec[didx[d]] = tidx[t]
        races = []
        for rid in race_ids:
            r = g[g.race_id == rid]
            races.append({"idx": np.array([didx[d] for d in r.driver_id]), "score": r["score"].to_numpy(),
                          "p_dnf": r["p_dnf"].to_numpy(), "sprint": False})
        sim = S.simulate_races(races, len(drivers), team_vec, len(teams), tau, rng, RUNS, dep)
        present = np.array([[(rid, d) in started for d in drivers] for rid in race_ids])     # (K, D)
        sim_tot = (sim * present[None]).sum(axis=1)                                          # (R, D)
        act_tot = np.array([sum(pts.get((rid, d), 0.0) for rid in race_ids) for d in drivers])
        cut = int(g["cut"].iloc[0])
        before = actual[(actual.year == year) & (actual["round"] <= cut)].groupby("driver_id")["pts"].sum()
        start = np.array([before.get(d, 0.0) for d in drivers])
        keep = (sim_tot.mean(axis=0) >= 3) | (act_tot >= 3)          # drivers who are in the points picture
        c = crps(sim_tot, act_tot)
        lo10, lo25, hi75, hi90 = np.percentile(sim_tot, [10, 25, 75, 90], axis=0)
        for j in np.where(keep)[0]:
            rows.append({"year": year, "cut_frac": frac, "driver": drivers[j], "crps": c[j],
                         "in80": float(lo10[j] <= act_tot[j] <= hi90[j]), "in50": float(lo25[j] <= act_tot[j] <= hi75[j]),
                         "sim_sd": float(sim_tot[:, j].std()), "err": float(act_tot[j] - sim_tot[:, j].mean())})
        final_sim = start[None, :] + sim_tot
        champ = int(np.argmax(start + act_tot))
        p_champ = (final_sim.argmax(axis=1) == champ).mean()
        p_all = np.bincount(final_sim.argmax(axis=1), minlength=len(drivers)) / RUNS
        onehot = np.zeros(len(drivers))
        onehot[champ] = 1
        title.append({"year": year, "cut_frac": frac, "champion": drivers[champ],
                      "p_champion": float(p_champ), "brier": float(((p_all - onehot) ** 2).sum()),
                      "logscore": float(-np.log(max(p_champ, 0.5 / RUNS)))})
    return pd.DataFrame(rows), pd.DataFrame(title)


def main():
    REPORT.mkdir(exist_ok=True)
    stale = stale_predictions()
    actual = actual_table()
    pers = persistence(stale, actual)
    pers.to_csv(REPORT / "dependence_persistence.csv", index=False)
    print(pers.round(3).to_string(index=False))

    bundle = json.load(open(REPORT / "metrics.json"))
    tau = bundle["pl_tau"]["pre"]
    grid = [{"sd_team": st, "sd_driver": sd, "rho": rho, "sd_rel": sr, "rho_rel": 0.5}
            for st, sd, rho, sr in itertools.product((0.0, 0.15, 0.3, 0.45, 0.6), (0.0, 0.15, 0.3),
                                                     (0.7, 1.0), (0.0, 0.3))
            if not ((st == 0 and sd == 0) and rho != 0.7)]
    results = []
    for k, dep in enumerate(grid):
        per, tt = evaluate(stale, actual, dep, tau)
        for part, sel in (("fit 2018-22", per.year.isin(FIT_YEARS)), ("held-out 2023-25", ~per.year.isin(FIT_YEARS))):
            p = per[sel]
            t = tt[tt.year.isin(FIT_YEARS) == (part == "fit 2018-22")]
            results.append({**dep, "part": part, "crps": p.crps.mean(), "coverage80": p.in80.mean(),
                            "coverage50": p.in50.mean(), "title_logscore": t.logscore.mean(),
                            "title_brier": t.brier.mean(), "n": len(p)})
        if k % 10 == 0:
            print(f"  grid {k + 1}/{len(grid)}", flush=True)
    res = pd.DataFrame(results)
    res.to_csv(REPORT / "dependence_grid.csv", index=False)
    fit = res[res.part == "fit 2018-22"].copy()
    # simplest setting among those within 0.5% of the best fit-years CRPS (guards against chasing noise)
    fit["size"] = fit.sd_team + fit.sd_driver + fit.sd_rel
    near = fit[fit.crps <= fit.crps.min() * 1.005].sort_values(["size", "crps"])
    best = near.iloc[0][["sd_team", "sd_driver", "rho", "sd_rel", "rho_rel"]].to_dict()
    json.dump({"dependence": {k: float(v) for k, v in best.items()}, "tau_pre": tau}, open(REPORT / "dependence.json", "w"), indent=1)
    write_summary(pers, res, best)


def write_summary(pers, res, best):
    indep = res[(res.sd_team == 0) & (res.sd_driver == 0) & (res.sd_rel == 0)]
    chosen = res[(res.sd_team == best["sd_team"]) & (res.sd_driver == best["sd_driver"]) & (res.rho == best["rho"])
                 & (res.sd_rel == best["sd_rel"])]
    L = ["# Do simulated races need to depend on each other?", "",
         "Replay of seasons 2018-2025 from three cut points each (30%, 50%, 70%): predictions made only from "
         "what was known at the cut, rest of season simulated, compared with what happened. "
         "Settings were picked on 2018-2022 and judged on 2023-2025.", "",
         "## Are the model's misses persistent?", "",
         "| quantity | races apart | correlation | 95% interval | pairs |", "|---|---|---|---|---|"]
    for r in pers.itertuples():
        ci = f"[{r.lo:+.2f}, {r.hi:+.2f}]" if pd.notna(r.lo) else "-"
        L.append(f"| {r.quantity} | {r.lag_races} | {r.correlation:+.2f} | {ci} | {r.pairs} |")
    L += ["", "## Season-total coverage and score", "",
          "Coverage = share of drivers whose real remaining points fell inside the simulated interval "
          "(80% interval should contain 80%, 50% interval 50%). CRPS: lower is better.", "",
          "| simulation | part | coverage 80% | coverage 50% | CRPS | title log score (lower better) | title Brier |",
          "|---|---|---|---|---|---|---|"]
    for name, df in (("independent races (before)", indep), ("with dependence (chosen)", chosen)):
        for r in df.sort_values("part").itertuples():
            L.append(f"| {name} | {r.part} | {r.coverage80:.0%} | {r.coverage50:.0%} | {r.crps:.2f} | "
                     f"{r.title_logscore:.3f} | {r.title_brier:.3f} |")
    L += ["", f"Chosen settings: team pace shock {best['sd_team']} per race, driver pace shock {best['sd_driver']}, "
          f"carry-over {best['rho']}, reliability shock {best['sd_rel']}.", ""]
    (REPORT / "dependence_summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
