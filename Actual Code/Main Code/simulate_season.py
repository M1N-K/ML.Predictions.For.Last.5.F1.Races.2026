#!/usr/bin/env python3
"""Championship simulation: play the rest of the season thousands of times.

    python simulate_season.py                    writes reports/championship_<year>.txt
    python simulate_season.py --refresh          download the latest results first
    python simulate_season.py --runs 50000       more simulations (default 20000)
    python simulate_season.py --out my.txt       choose the file (or a folder)
    python simulate_season.py --quiet            don't print in the terminal

How it works, for every remaining race and every simulated season:
  1. each driver retires with the probability given by the retirement model;
  2. the cars still running are put in order by the ranking model's score plus random luck
     (a Plackett-Luce / Gumbel draw whose spread was fitted on the back-test);
  3. championship points are awarded (25-18-15-12-10-8-6-4-2-1) on top of the real current
     standings, plus 8-7-...-1 for a sprint if the weekend has one.
Counting who wins the title in each run gives the odds.

Races depend on each other: every team (and, less, every driver) gets a pace shock that is carried
from one simulated race to the next, so a team that is better or worse than the model thinks is so
for several races, not one. How big the shocks are was fitted by replaying past seasons
(season_backtest.py); with independent races the simulated 80% ranges held the real season total
for only 53-65% of drivers, with the shocks 82-85%. Retirements are NOT given shared shocks: the
replay found no sign that a team's retirements follow one another.

Simplifications: no fastest-lap point (not awarded now) and the line-up stays as in the latest race
unless overrides.csv says otherwise. Only classified finishers score.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import engine as E
import features as F
import simcore
from simcore import RACE_POINTS, SPRINT_POINTS, award
from predict_season import predict_remaining

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--runs", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.refresh:
        subprocess.run([sys.executable, "fetch_data.py"], check=True)
    res, races, weekend = E.load_data()
    if races["has_results"].all():
        sys.exit("No races left in the season.")
    results, bundle = predict_remaining(res, races, weekend)
    year = int(results[0][0]["year"])
    rng = np.random.default_rng(args.seed)
    R = args.runs

    # ---- where the championship stands now (official f1db tables) ---------------------------
    st_d = pd.read_csv(f"data/standings_drivers_{year}.csv").set_index("id")["points"].astype(float)
    st_c = pd.read_csv(f"data/standings_constructors_{year}.csv")
    st_c["id"] = st_c["id"].map(F.TEAM_LINEAGE).fillna(st_c["id"])
    st_c = st_c.groupby("id")["points"].sum().astype(float)
    drivers = list(dict.fromkeys(list(st_d.index) + [d for _, _, r in results for d in r["driver_id"]]))
    didx = {d: i for i, d in enumerate(drivers)}
    start = np.array([st_d.get(d, 0.0) for d in drivers])
    team_of = {}
    for _, _, rows in results:
        team_of.update(dict(zip(rows["driver_id"], rows["team"])))
    teams = list(dict.fromkeys(list(st_c.index) + list(team_of.values())))
    tidx = {t: i for i, t in enumerate(teams)}
    t_start = np.array([st_c.get(t, 0.0) for t in teams])
    team_vec = np.array([tidx[team_of[d]] if d in team_of else -1 for d in drivers])

    # ---- simulate ---------------------------------------------------------------------------
    dep = simcore.load_dependence()
    race_specs = []
    win_check = []
    for r, (meta, stage, rows) in enumerate(results):
        tau = bundle["pl_tau"][stage]
        idx = np.array([didx[d] for d in rows["driver_id"]])
        sc, pdnf = rows["score"].to_numpy(), rows["p_dnf"].to_numpy()
        race_specs.append({"idx": idx, "score": sc, "p_dnf": pdnf, "sprint": bool(meta["is_sprint"]),
                           "tau": tau, "fresh": stage != "pre"})
        # sanity: simulated win frequency vs the win classifier (a single race, so no shocks)
        sim_win = (award(sc, pdnf, tau, rng, 4000, np.array([1.0])) > 0).mean(axis=0)
        win_check.append((meta["race_id"], float(np.abs(sim_win - rows["p_win"].to_numpy()).max()),
                          float(np.corrcoef(sim_win, rows["p_win"].to_numpy())[0, 1])))
    per_race = simcore.simulate_races(race_specs, len(drivers), team_vec, len(teams), None, rng, R, dep)
    final = start[None, :] + per_race.sum(axis=1)                  # (R, drivers)
    tfinal = np.zeros((R, len(teams)))
    for j in range(len(drivers)):
        if team_vec[j] >= 0:
            tfinal[:, team_vec[j]] += per_race[:, :, j].sum(axis=1)
    tfinal += t_start[None, :]

    n_left = len(results)
    max_per = sum(25.0 + (8.0 if m["is_sprint"] else 0.0) for m, _, _ in results)       # best driver
    max_team = sum(43.0 + (15.0 if m["is_sprint"] else 0.0) for m, _, _ in results)     # 25 + 18 (+ 8 + 7)

    def pct_text(p, alive):
        """Never print a flat 0% / 100% while the title is still mathematically open."""
        if p >= 0.9995:
            return ">99.9" if alive_rivals_exist else "100"
        if p < 0.0005:
            return "<0.1" if alive else "0"
        return f"{p * 100:.1f}"

    def table(final, start_pts, names, label, max_pts, keep):
        rank = (-final).argsort(axis=1).argsort(axis=1)            # 0 = champion
        champ = (rank == 0).mean(axis=0)
        top3 = (rank < 3).mean(axis=0)
        q10, _, q90 = np.percentile(final, [10, 50, 90], axis=0)
        alive = start_pts + max_pts >= start_pts.max()             # could still catch the leader
        t = pd.DataFrame({label: [E.pretty(n) for n in names], "Now": start_pts.astype(int),
                          "_champ": champ, "Top 3 %": (top3 * 100).round(0).astype(int),
                          "Expected pts": final.mean(axis=0).round(0).astype(int),
                          "Range (10-90%)": [f"{int(a)}-{int(b)}" for a, b in zip(q10, q90)],
                          "_top3": top3, "_p10": q10, "_p90": q90,
                          "_exp": final.mean(axis=0), "_now": start_pts})
        t["Title %"] = [pct_text(p, a) for p, a in zip(champ, alive)]
        t = t.sort_values(["_champ", "Expected pts"], ascending=False)
        t = t[(t["_champ"] > 0) | (t["Expected pts"] >= t["Expected pts"].nlargest(keep).iloc[-1])]
        return t[[label, "Title %", "Top 3 %", "Now", "Expected pts", "Range (10-90%)"]], t.copy()

    alive_rivals_exist = bool(((start + max_per) >= start.max()).sum() > 1)
    dtab, dnum = table(final, start, drivers, "Driver", max_per, 10)
    alive_rivals_exist = bool(((t_start + max_team) >= t_start.max()).sum() > 1)
    ctab, cnum = table(tfinal, t_start, teams, "Constructor", max_team, 6)

    # ---- mathematics: who is still alive, and when could it be decided ----------------------
    order_now = np.argsort(-start)
    leader = order_now[0]
    alive = [E.pretty(drivers[i]) for i in order_now if start[i] + max_per >= start[leader] and i != leader]
    cum = start[None, None, :] + per_race.cumsum(axis=1)             # (R, races, drivers)
    left_after = np.array([sum(25.0 + (8.0 if results[k][0]["is_sprint"] else 0.0) for k in range(r + 1, n_left))
                           for r in range(n_left)])
    srt = np.sort(cum, axis=2)
    decided = (srt[:, :, -1] - srt[:, :, -2]) > left_after[None, :]  # leader unreachable after race r
    decided_by = decided.mean(axis=0)

    # ---- text report ------------------------------------------------------------------------
    lead_gap = start[order_now[0]] - start[order_now[1]]
    lines = [f"{year} F1 CHAMPIONSHIP SIMULATION", "",
             f"{R:,} simulated runs of the remaining {n_left} races, starting from the real standings. "
             f"Models trained through {bundle['trained_through']}.", "",
             f"Right now: {E.pretty(drivers[order_now[0]])} leads on {int(start[order_now[0]])} points, "
             f"{int(lead_gap)} ahead of {E.pretty(drivers[order_now[1]])}. "
             f"Most points still available: {int(max_per)}.",
             "Still mathematically alive for the drivers' title: "
             + (", ".join(alive) if alive else "nobody else (it is decided).") , "",
             "DRIVERS' CHAMPIONSHIP", dtab.to_string(index=False), "",
             "CONSTRUCTORS' CHAMPIONSHIP", ctab.to_string(index=False), "",
             "WHEN COULD THE DRIVERS' TITLE BE DECIDED? (chance it is settled by the end of each race)"]
    for (meta, stage, _), p in zip(results, decided_by):
        lines.append(f"  {E.pretty(meta['grand_prix']):<14} {meta['date']}   "
                     f"{'>99.9%' if p >= 0.9995 else format(p, '.0%')}")
    lines += ["", "How to read it: 'Title %' is the share of simulated seasons that driver/team won; "
              "'Range' covers the middle 80% of simulated final points totals. Odds are only as good as "
              "the model, which cannot know about crashes, reliability problems, penalties, weather or "
              "upgrades beyond what recent results already show. Not betting advice."]
    text = "\n".join(lines) + "\n"

    path = Path(args.out) if args.out else Path(f"reports/championship_{year}.txt")
    if path.is_dir():
        path = path / f"championship_{year}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    Path("reports").mkdir(exist_ok=True)
    site = Path("reports/site")
    site.mkdir(parents=True, exist_ok=True)
    pid = {E.pretty(d): d for d in drivers}
    pd.DataFrame({
        "driver": dnum["Driver"].to_numpy(),
        "team": [E.pretty(team_of.get(pid[n], "")) for n in dnum["Driver"]],
        "now": dnum["_now"].round(0).astype(int).to_numpy(),
        "title_pct": (dnum["_champ"] * 100).round(4).to_numpy(),
        "top3_pct": (dnum["_top3"] * 100).round(1).to_numpy(),
        "expected_pts": dnum["_exp"].round(0).astype(int).to_numpy(),
        "p10": dnum["_p10"].round(0).astype(int).to_numpy(), "p90": dnum["_p90"].round(0).astype(int).to_numpy(),
    }).to_csv(site / "title_drivers.csv", index=False)
    pd.DataFrame({
        "team": cnum["Constructor"].to_numpy(),
        "now": cnum["_now"].round(0).astype(int).to_numpy(),
        "title_pct": (cnum["_champ"] * 100).round(4).to_numpy(),
        "top3_pct": (cnum["_top3"] * 100).round(1).to_numpy(),
        "expected_pts": cnum["_exp"].round(0).astype(int).to_numpy(),
        "p10": cnum["_p10"].round(0).astype(int).to_numpy(), "p90": cnum["_p90"].round(0).astype(int).to_numpy(),
    }).to_csv(site / "title_constructors.csv", index=False)
    pd.DataFrame({"race_id": [m["race_id"] for m, _, _ in results],
                  "grand_prix": [E.pretty(m["grand_prix"]) for m, _, _ in results],
                  "date": [m["date"] for m, _, _ in results],
                  "pct_settled": (decided_by * 100).round(1)}).to_csv(site / "title_timeline.csv", index=False)
    champ_d = dnum.set_index("Driver")["_champ"]
    pd.DataFrame([{
        "leader": E.pretty(drivers[order_now[0]]), "leader_pts": int(start[order_now[0]]),
        "second": E.pretty(drivers[order_now[1]]), "second_pts": int(start[order_now[1]]),
        "gap": int(lead_gap), "max_available": int(max_per), "races_left": n_left,
        "leader_title_pct": round(float(champ_d.get(E.pretty(drivers[order_now[0]]), 0)) * 100, 2),
        "runs": R, "alive": ", ".join(alive)}]).to_csv(site / "title_summary.csv", index=False)
    dtab.to_csv(f"reports/championship_{year}_drivers.csv", index=False)
    ctab.to_csv(f"reports/championship_{year}_constructors.csv", index=False)
    print(f"Saved {path}" if args.quiet else text + f"\nSaved {path}")
    if not args.quiet:
        print("\nSanity check, simulated win chance vs win classifier (max abs diff, correlation):")
        for rid, mx, cr in win_check:
            print(f"  {rid}: {mx:.3f}, {cr:.3f}")


if __name__ == "__main__":
    main()
