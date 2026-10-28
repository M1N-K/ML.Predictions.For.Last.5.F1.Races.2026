"""Core of the race simulation (shared by train.py, which fits its randomness, and
simulate_season.py, which uses it)."""
import numpy as np

RACE_POINTS = np.array([25, 18, 15, 12, 10, 8, 6, 4, 2, 1], float)
SPRINT_POINTS = np.array([8, 7, 6, 5, 4, 3, 2, 1], float)


GUMBEL_SD = float(np.pi / np.sqrt(6))          # standard deviation of the Gumbel noise (1.2825)


def award(scores, p_dnf, tau, rng, runs, table, shift=None, noise_scale=1.0):
    """Simulate one race `runs` times -> points per driver, shape (runs, drivers).

    Each driver retires with probability p_dnf (a scalar per driver, or an array (runs, drivers));
    the cars still running are ordered by score / tau + Gumbel noise (a Plackett-Luce draw). Lower
    tau = the model's order is followed more strictly; higher tau = more random.

    `shift` (runs, drivers) is an extra amount added to a driver's value in every run: the team and
    driver "form" shocks that make races depend on each other (see `simulate_races`).
    `noise_scale` shrinks the Gumbel noise to make room for that shared part."""
    m = len(scores)
    running = rng.random((runs, m)) >= p_dnf
    value = scores / tau + noise_scale * rng.gumbel(size=(runs, m))
    if shift is not None:
        value = value + shift
    value = np.where(running, value, -np.inf)
    order = np.argsort(-value, axis=1)
    rank = np.empty_like(order)
    np.put_along_axis(rank, order, np.arange(m)[None, :].repeat(runs, 0), axis=1)
    pts = np.zeros((runs, m))
    for k, v in enumerate(table):
        pts += np.where((rank == k) & running, v, 0.0)
    return pts


def fit_temperature(preds, stage, points_by_rank, taus=None, runs=1500, seed=0):
    """Choose tau for one stage from back-test predictions.

    Scores each candidate tau on (a) squared error of simulated expected points per driver-race
    against actual points and (b) log loss of the simulated win chance, and picks the one with the
    smallest sum of the two relative errors. Returns (tau, table of all candidates)."""
    taus = taus if taus is not None else np.round(np.arange(0.2, 1.65, 0.1), 2)
    rng = np.random.default_rng(seed)
    d = preds.assign(pts=np.where(preds["dnf"] == 0, preds["final_rank"].map(points_by_rank).fillna(0), 0.0))
    races = [g for _, g in d.groupby("race_id")]
    rows = []
    for tau in taus:
        se = wl = n = 0
        top_pred, top_act = [], []
        for g in races:
            sc, pdnf = g[f"score_{stage}"].to_numpy(), g[f"p_dnf_{stage}"].to_numpy()
            ep = award(sc, pdnf, tau, rng, runs, RACE_POINTS).mean(axis=0)
            win = np.clip((award(sc, pdnf, tau, rng, runs, np.array([1.0])) > 0).mean(axis=0), 1e-3, 1 - 1e-3)
            y = g["final_rank"].to_numpy() == 1
            se += ((ep - g["pts"].to_numpy()) ** 2).sum()
            wl += -(y * np.log(win) + (1 - y) * np.log(1 - win)).sum()
            n += len(g)
            i = sc.argmax()
            top_pred.append(win[i])
            top_act.append(float(y[i]))
        rows.append({"stage": stage, "tau": float(tau), "points_mse": se / n, "win_logloss": wl / n,
                     "top_pick_win_pred": float(np.mean(top_pred)), "top_pick_win_actual": float(np.mean(top_act))})
    t = pd_frame(rows)
    t["loss"] = t.points_mse / t.points_mse.min() + t.win_logloss / t.win_logloss.min() - 2
    return float(t.loc[t["loss"].idxmin(), "tau"]), t


def pd_frame(rows):
    import pandas as pd
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------- races that depend on each other
# Without this, every simulated race is an independent draw: a team that happens to be fast in the
# first simulated race is no more likely than average to be fast in the next one. Reality is not like
# that. The model predicts a race several rounds ahead from form that is already out of date, and when
# it is wrong about a team (an upgrade that works, a car that loses its edge) it is wrong in the same
# direction for many races. That makes the independent version too sure of itself over a season: in a
# replay of 2018-2025 its "80% range" held the real season total for only 53-65% of drivers.
# `dep` describes the extra, shared randomness (fitted by season_backtest.py, none of it guessed):
#   sd_team, sd_driver   size of the team-wide / driver-wide pace shock added each race (same units as
#                        the Gumbel noise, whose own spread is 1.28)
#   rho                  how much of a shock carries into the next race (1 = a random walk)
#   sd_rel, rho_rel      spread and carry-over of a team's reliability shock (multiplies retirement chance)
# Shocks start at zero for the next race (its prediction is fresh) and build up with distance.
NO_DEPENDENCE = {"sd_team": 0.0, "sd_driver": 0.0, "rho": 0.0, "sd_rel": 0.0, "rho_rel": 0.0}


def shock_paths(rng, runs, steps, size, sd, rho):
    """Shock paths s_k = rho * s_(k-1) + N(0, sd), with s_0 = 0. Shape (runs, steps, size); the first
    race's shock is its own fresh innovation, later ones carry the earlier shocks forward."""
    out = np.zeros((runs, steps, size))
    if sd <= 0:
        return out
    prev = np.zeros((runs, size))
    for k in range(steps):
        prev = rho * prev + rng.normal(0, sd, (runs, size))
        out[:, k] = prev
    return out


def simulate_races(races, n_drivers, team_vec, n_teams, tau, rng, runs, dep=None):
    """Simulate a list of races one after another. -> points, shape (runs, races, drivers).

    races: list of dicts with `idx` (driver positions), `score`, `p_dnf`, `sprint` (bool).
    team_vec: team position for each driver (-1 = none)."""
    dep = {**NO_DEPENDENCE, **(dep or {})}
    K = len(races)
    # a race flagged `fresh` is predicted from this weekend's own information (grid / practice), so
    # it gets no shock and the shocks start with the first race after the fresh ones
    lead = 0
    while lead < K and races[lead].get("fresh"):
        lead += 1
    team_form = shock_paths(rng, runs, K - lead, n_teams, dep["sd_team"], dep["rho"])
    driver_form = shock_paths(rng, runs, K - lead, n_drivers, dep["sd_driver"], dep["rho"])
    team_rel = shock_paths(rng, runs, K - lead, n_teams, dep["sd_rel"], dep["rho_rel"])
    per_race = np.zeros((runs, K, n_drivers))
    for k, r in enumerate(races):
        idx = np.asarray(r["idx"])
        tv = team_vec[idx]
        has_team = tv >= 0
        j = k - lead
        shift = np.zeros((runs, len(idx)))
        if j >= 0:
            shift = driver_form[:, j, idx].copy()
            shift[:, has_team] += team_form[:, j, tv[has_team]]
        p = np.broadcast_to(np.asarray(r["p_dnf"], float), (runs, len(idx))).copy()
        if dep["sd_rel"] > 0 and j >= 0:
            rel = team_rel[:, j, tv[has_team]]
            mult = np.ones((runs, len(idx)))
            mult[:, has_team] = np.exp(rel - rel.var() / 2)           # keeps the average retirement rate
            p = np.clip(p * mult, 0.0, 0.9)
        sc = np.asarray(r["score"], float)
        t = r.get("tau", tau)
        pts = award(sc, p, t, rng, runs, RACE_POINTS, shift=shift)
        if r.get("sprint"):
            pts += award(sc, p * 0.6, t, rng, runs, SPRINT_POINTS, shift=shift)
        per_race[:, k, idx] = pts
    return per_race


def load_dependence(path="reports/dependence.json"):
    """The fitted shock settings (written by season_backtest.py); independent races if there is no file."""
    import json
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        print("Note: reports/dependence.json not found, so simulated races are independent.")
        return dict(NO_DEPENDENCE)
    return {**NO_DEPENDENCE, **json.load(open(p))["dependence"]}
