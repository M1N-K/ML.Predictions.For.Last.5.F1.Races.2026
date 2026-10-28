"""Feature engineering for F1 race prediction.

Every "history" feature for a driver / team at race t is computed from races strictly before t
(shift(1) before any rolling/expanding aggregate), so nothing from the race being predicted
leaks into its own features. Qualifying / grid information for the race itself is kept in a
separate group (POST_EXTRA) because it is only known after Saturday.

Three feature sets, one per moment at which you can make a prediction:
    "pre"  - before the weekend: form, team pace, circuit history, pit-stop history, standings
    "fp"   - after Friday/Saturday practice: "pre" plus this weekend's practice pace
    "post" - after qualifying (and any sprint): "fp" plus the grid, qualifying pace, sprint result

Two older sets ("pre_v1", "post_v1": the first version of the model, without practice, pit-stop
or sprint information) are kept only so the back-test can show what the additions are worth.

Practice, sprint and pit-stop inputs come from data/weekend.csv, sprint flags from data/races.csv.
Pit-stop information is used as history only (it is a result of the race it belongs to).
"""
from pathlib import Path

import numpy as np
import pandas as pd

# Teams that were renamed / rebranded keep one history.
TEAM_LINEAGE = {
    "force-india": "aston-martin", "racing-point": "aston-martin",
    "toro-rosso": "racing-bulls", "alphatauri": "racing-bulls", "rb": "racing-bulls",
    "alfa-romeo": "sauber", "kick-sauber": "sauber", "audi": "sauber",
    "lotus-f1": "alpine", "renault": "alpine",
    "marussia": "manor",
}
# First season of each technical era (new regulations reset how much old form tells you).
ERA_START_YEARS = [2014, 2017, 2022, 2026]

PRE_V1 = [
    # driver form (exponentially weighted over previous races; halflife in races)
    "d_finish_ewm3", "d_finish_ewm10", "d_pace_ewm5", "d_dnf_ewm10", "d_grid_ewm5", "d_gap_ewm5",
    "d_gain_ewm10", "d_pts_ewm5", "d_win_ewm10", "d_podium_ewm10", "d_races",
    "d_circ_finish_mean", "d_circ_visits",
    # team form
    "c_finish_ewm3", "c_finish_ewm10", "c_pace_ewm5", "c_dnf_ewm10", "c_grid_ewm5",
    "c_gap_ewm3", "c_gap_ewm10", "c_pts_ewm5", "c_circ_finish_mean",
    # championship context
    "d_season_pts_rel", "d_standing_pct", "c_season_pts_rel",
    # circuit / era / race context
    "circ_abs_change", "circ_pole_win", "era_race_idx", "round", "n_starters",
    # how the driver's form compares with the rest of this field
    "d_finish_ewm3_rk", "d_finish_ewm10_rk", "c_finish_ewm3_rk", "c_finish_ewm10_rk",
    "c_gap_ewm3_rk", "d_gap_ewm5_rk", "d_vs_tm_form",
]
POST_EXTRA = [
    "grid", "grid_pct", "quali_pos", "quali_gap_pct", "quali_gap_rk", "pit_lane",
    "grid_penalty", "grid_vs_tm", "gap_vs_tm",
]
PIT_HISTORY = ["c_stops_ewm5", "c_pit_time_ewm5", "circ_stops_mean"]   # strategy / pit-crew history
PRACTICE = [
    "fp_sessions", "fp_best_gap", "fp_mean_gap", "fp_laps_rel", "fp_best_rk", "fp_gap_vs_tm",
    "c_fp_gap", "c_fp_rk", "fp_vs_form",
]
SPRINT = ["sprint_pct", "sprint_dnf", "sprint_quali_gap"]               # sprint weekends only

# Driver-versus-car ratings: an online estimate of how much of a result is the car and how much the
# driver (item "separate driver skill from car pace"). Race pace and qualifying are rated separately.
RATINGS = ["rr_car", "rr_drv", "rq_car", "rq_drv", "rr_tot_rk", "rq_tot_rk"]
# What kind of circuit it is (street / permanent, corners per km, length), and how this driver and
# this team have done on circuits of the same kind (not only on the same circuit).
CIRCUIT = ["circ_street", "circ_turns_km", "circ_length", "d_class_adv", "c_class_adv"]

PRE_BASE = PRE_V1 + PIT_HISTORY + ["is_sprint"]
# RATINGS and CIRCUIT are computed for every row but are NOT inputs of the production models: the
# 2018-2026 back-test (ablation.py, reports/ablation_summary.md) found no clear gain from either,
# and a small loss at the "post" stage, so the simpler model stays. Add them here to switch them on.
PRE = PRE_BASE
FP = PRE + PRACTICE
POST = FP + POST_EXTRA + SPRINT
FEATURE_SETS = {"pre": PRE, "fp": FP, "post": POST}
BASELINE_SETS = {"pre_v1": PRE_V1, "post_v1": PRE_V1 + POST_EXTRA}      # first version, for comparison
ALL_SETS = {**FEATURE_SETS, **BASELINE_SETS}
WEEKEND_COLS = ["fp_best_gap", "fp_mean_gap", "fp_laps", "fp_sessions", "pit_n", "pit_med_time",
                "pit_first_lap", "sprint_pos", "sprint_pts", "sprint_grid", "sprint_quali_pos",
                "sprint_quali_gap"]


def _ewm_prior(df, by, col, halflife):
    return df.groupby(by)[col].transform(
        lambda s: s.shift(1).ewm(halflife=halflife, min_periods=1).mean())


def _teammate_mean(df, col):
    """Mean of `col` over the other car(s) of the same team in the same race."""
    g = df.groupby(["race_id", "team"])[col]
    total = g.transform("sum")
    cnt = g.transform("count")
    other_cnt = cnt - df[col].notna().astype(int)
    out = (total - df[col].fillna(0)) / other_cnt.replace(0, np.nan)
    return out


# Fitted on races before 2023 only (see tune_ratings()); nothing from the test seasons is used.
RATING_PARAMS = {"race": {"kc": 0.20, "kd": 0.10, "shrink": 0.8},      # run `python features.py tune`
                 "quali": {"kc": 0.30, "kd": 0.10, "shrink": 0.6}}
RESET_YEARS = [y for y in ERA_START_YEARS if y > ERA_START_YEARS[0]]    # new rules: car ratings fade
CLASS_PRIOR = 4.0          # a driver/team needs a few races on a kind of circuit before it counts fully
TURN_DENSITY_SPLIT = 3.2   # corners per km: below = flowing, above = technical


def rating_channel(df, ycol, kc, kd, shrink):
    """Online car + driver rating from one performance measure (lower = faster).

    Races are processed in date order. Each driver's expected result is `car[team] + driver[id]`;
    after the race the miss is split: the team's average miss moves the car rating, the gap between
    a driver and his team-mate moves the driver rating. At the start of a new technical era every
    car rating is shrunk towards zero (the cars are new), driver ratings carry over.

    Returns (car_before, driver_before, squared_error): values BEFORE the race is taken into
    account, so a row never sees its own race. Rows of races without a result are not learned from.
    """
    n = len(df)
    car, drv = {}, {}
    car_b, drv_b, sq = np.zeros(n), np.zeros(n), np.full(n, np.nan)
    year = df["date"].dt.year.to_numpy()
    teams, drivers = df["team"].to_numpy(), df["driver_id"].to_numpy()
    y_all, done = df[ycol].to_numpy(float), df["completed"].to_numpy()
    last_year = None
    groups = df.groupby("race_id", sort=False).indices
    for rid in pd.unique(df["race_id"]):                    # chronological: df is sorted by date
        ix = groups[rid]
        yr = year[ix[0]]
        if last_year is not None and yr != last_year and yr in RESET_YEARS:
            for t in car:
                car[t] *= shrink
        last_year = yr
        cb = np.array([car.get(teams[i], 0.0) for i in ix])
        db = np.array([drv.get(drivers[i], 0.0) for i in ix])
        car_b[ix], drv_b[ix] = cb, db
        y = y_all[ix]
        obs = ~np.isnan(y) & done[ix]
        if obs.sum() < 4:
            continue
        e = (y - np.nanmean(y[obs])) - (cb + db)
        e = e - np.nanmean(e[obs])
        sq[ix[obs]] = e[obs] ** 2
        miss = pd.Series(np.where(obs, e, np.nan))
        by_team = miss.groupby(teams[ix])
        t_mean, t_cnt = by_team.transform("mean").to_numpy(), by_team.transform("count").to_numpy()
        seen = set()
        for k, i in enumerate(ix):
            if not obs[k]:
                continue
            solo = t_cnt[k] < 2                       # only one car with a clean result: less to go on
            if teams[i] not in seen:                  # the car moves once per race, not once per driver
                seen.add(teams[i])
                car[teams[i]] = car.get(teams[i], 0.0) + kc * (0.5 if solo else 1.0) * t_mean[k]
            dev = 0.5 * e[k] if solo else e[k] - t_mean[k]
            drv[drivers[i]] = drv.get(drivers[i], 0.0) + kd * dev
    return car_b, drv_b, sq


def tune_ratings(df, until_year=2023):
    """Pick the rating update speeds by one-step-ahead error on races before `until_year` only."""
    out = {}
    pre = (df["date"].dt.year < until_year).to_numpy()
    for name, ycol in (("race", "pace_pct"), ("quali", "quali_pct")):
        best = None
        for kc in (0.1, 0.15, 0.2, 0.3):
            for kd in (0.05, 0.1, 0.15, 0.2, 0.3):
                for sh in (0.6, 0.8, 0.9, 1.0):
                    _, _, sq = rating_channel(df, ycol, kc, kd, sh)
                    mse = float(np.nanmean(sq[pre]))
                    if best is None or mse < best[0]:
                        best = (mse, {"kc": kc, "kd": kd, "shrink": sh})
        out[name] = best[1] | {"mse": best[0]}
    return out


def class_advantage(frame, ent, cls, col, prior=CLASS_PRIOR):
    """How much better/worse (in `col` units) an entity does on this KIND of circuit than overall,
    from earlier races only, shrunk towards 0 when there are few earlier races of that kind."""
    one = lambda x: x.notna().astype(float).cumsum().shift(1, fill_value=0.0)
    tot = lambda x: x.fillna(0.0).cumsum().shift(1, fill_value=0.0)
    cs = frame.groupby([ent, cls])[col].transform(tot)
    cn = frame.groupby([ent, cls])[col].transform(one)
    os_ = frame.groupby(ent)[col].transform(tot)
    on_ = frame.groupby(ent)[col].transform(one)
    overall = os_ / on_.replace(0, np.nan)
    adv = (cs - cn * overall) / (cn + prior)
    return adv.where(cn > 0, 0.0).where(on_ > 0, np.nan)


def _optional_csv(path):
    return pd.read_csv(path) if Path(path).exists() else None


def build_features(res: pd.DataFrame, weekend=None, races=None) -> pd.DataFrame:
    """res: data/results.csv. Returns one row per driver per race with features and targets.

    weekend / races default to data/weekend.csv and data/races.csv when those exist.
    """
    weekend = _optional_csv("data/weekend.csv") if weekend is None else weekend
    races = _optional_csv("data/races.csv") if races is None else races
    df = res.copy()
    if weekend is not None:
        w = weekend.drop_duplicates(["race_id", "driver_id"])
        df = df.merge(w[["race_id", "driver_id"] + [c for c in WEEKEND_COLS if c in w.columns]],
                      on=["race_id", "driver_id"], how="left")
    for c in WEEKEND_COLS:
        if c not in df.columns:
            df[c] = np.nan
    if races is not None:
        df["is_sprint"] = df["race_id"].map(races.set_index("race_id")["is_sprint"].astype(float)).fillna(0.0)
    else:
        df["is_sprint"] = 0.0
    df["date"] = pd.to_datetime(df["date"])
    df["team"] = df["constructor_id"].map(TEAM_LINEAGE).fillna(df["constructor_id"])
    df["completed"] = df["position_raw"].notna()
    text = lambda col: df[col].astype(str).where(df[col].notna(), "")
    df = df[~text("position_raw").isin(["DNS", "DNP"])].copy()   # never started: not predictable
    df = df.sort_values(["date", "race_id", "driver_id"]).reset_index(drop=True)
    raw = df["position_raw"].astype(str).where(df["position_raw"].notna(), "")

    df["pos_num"] = pd.to_numeric(df["position_raw"], errors="coerce")
    df["is_dsq"] = raw.eq("DSQ")
    df["dnf"] = (raw.isin(["DNF", "NC"]) | (df["pos_num"].notna() & df["reason_retired"].notna()))
    df["dnf"] = df["dnf"].astype(float).where(df["completed"])
    df["n_starters"] = df.groupby("race_id")["driver_id"].transform("size")
    n = df["n_starters"]

    # ---- targets: final order, retirements ordered by laps completed ------------------------
    grid_num = pd.to_numeric(df["grid_raw"], errors="coerce")
    df["pit_lane"] = df["grid_raw"].astype(str).eq("PL").astype(int)
    grid_known = grid_num.groupby(df["race_id"]).transform(lambda s: s.notna().any())
    df["grid"] = grid_num.where(~(df["pit_lane"].eq(1)), np.nan)
    df["grid"] = df["grid"].fillna(n + 1).where(grid_known)  # pit-lane / missing starters go last

    grp = np.select([df["pos_num"].notna(), df["is_dsq"]], [0, 2], default=1)
    key = np.where(grp == 0, df["pos_num"], -df["laps_done"].fillna(0))
    order = (df.assign(_g=grp, _k=key).loc[df["completed"]]
               .sort_values(["race_id", "_g", "_k", "grid"]))
    df["final_rank"] = np.nan
    df.loc[order.index, "final_rank"] = order.groupby("race_id").cumcount() + 1
    df["finish_pct"] = (df["final_rank"] - 1) / (n - 1)
    df["pace_pct"] = df["finish_pct"].where((df["dnf"] == 0) & (~df["is_dsq"]))
    df["win"] = (df["final_rank"] == 1).astype(float).where(df["completed"])
    df["podium"] = (df["final_rank"] <= 3).astype(float).where(df["completed"])
    pts_total = df.groupby("race_id")["points"].transform("sum").replace(0, np.nan)
    df["points_share"] = df["points"] / pts_total

    # ---- this weekend's qualifying information ---------------------------------------------
    df["grid_pct"] = (df["grid"] - 1) / (n - 1)
    pole_time = df.groupby("race_id")["quali_time"].transform("min")
    df["quali_gap_pct"] = (df["quali_time"] / pole_time - 1) * 100
    df["grid_penalty"] = df["grid"] - df["quali_pos"]
    df["quali_gap_rk"] = df.groupby("race_id")["quali_gap_pct"].rank(pct=True)
    df["grid_vs_tm"] = df["grid_pct"] - _teammate_mean(df, "grid_pct")
    df["gap_vs_tm"] = df["quali_gap_pct"] - _teammate_mean(df, "quali_gap_pct")
    df["gain"] = df["grid_pct"] - df["finish_pct"]          # >0: finished ahead of grid slot

    # ---- this weekend's practice and sprint information (all known before the race) ----------
    lap_med = df.groupby("race_id")["fp_laps"].transform(lambda s: s[s > 0].median())
    df["fp_laps_rel"] = df["fp_laps"] / lap_med
    df["fp_best_rk"] = df.groupby("race_id")["fp_best_gap"].rank(pct=True)
    df["fp_gap_vs_tm"] = df["fp_best_gap"] - _teammate_mean(df, "fp_best_gap")
    df["c_fp_gap"] = df.groupby(["race_id", "team"])["fp_best_gap"].transform("mean")
    df["c_fp_rk"] = df.groupby("race_id")["c_fp_gap"].rank(pct=True)
    sp = pd.to_numeric(df["sprint_pos"], errors="coerce")
    df["sprint_pct"] = np.where(sp.notna(), (sp - 1) / (n - 1), np.where(df["sprint_pos"].notna(), 1.0, np.nan))
    df["sprint_dnf"] = np.where(df["sprint_pos"].isna(), np.nan, sp.isna().astype(float))
    # pit stops: a race result, so only ever used as history below. Finishers only for stop counts.
    df["pit_n_fin"] = df["pit_n"].where(df["dnf"] == 0)
    df["pit_time_c"] = df["pit_med_time"].clip(upper=45)

    # ---- driver history ---------------------------------------------------------------------
    by = "driver_id"
    df["d_finish_ewm3"] = _ewm_prior(df, by, "finish_pct", 3)
    df["d_finish_ewm10"] = _ewm_prior(df, by, "finish_pct", 10)
    df["d_pace_ewm5"] = _ewm_prior(df, by, "pace_pct", 5)
    df["d_dnf_ewm10"] = _ewm_prior(df, by, "dnf", 10)
    df["d_grid_ewm5"] = _ewm_prior(df, by, "grid_pct", 5)
    df["d_gap_ewm5"] = _ewm_prior(df, by, "quali_gap_pct", 5)
    df["d_gain_ewm10"] = _ewm_prior(df, by, "gain", 10)
    df["d_pts_ewm5"] = _ewm_prior(df, by, "points_share", 5)
    df["d_win_ewm10"] = _ewm_prior(df, by, "win", 10)
    df["d_podium_ewm10"] = _ewm_prior(df, by, "podium", 10)
    df["d_races"] = df.groupby(by).cumcount()
    cb = [by, "circuit_id"]
    df["d_circ_finish_mean"] = df.groupby(cb)["finish_pct"].transform(
        lambda s: s.shift(1).expanding().mean())
    df["d_circ_visits"] = df.groupby(cb).cumcount()

    # ---- driver-versus-car ratings (values before each race; see rating_channel) -------------
    df["quali_pct"] = (pd.to_numeric(df["quali_pos"], errors="coerce") - 1) / (n - 1)
    for tag, ycol, key in (("rr", "pace_pct", "race"), ("rq", "quali_pct", "quali")):
        p = RATING_PARAMS[key]
        c_b, d_b, _ = rating_channel(df, ycol, p["kc"], p["kd"], p["shrink"])
        df[f"{tag}_car"], df[f"{tag}_drv"] = c_b, d_b
        df[f"{tag}_tot_rk"] = (df[f"{tag}_car"] + df[f"{tag}_drv"]).groupby(df["race_id"]).rank(pct=True)

    # ---- kind of circuit: static character + how driver / team do on that kind -----------------
    attrs = ("circuit_type", "turns", "course_length")
    if races is not None and all(a in races.columns for a in attrs):
        rr = races.set_index("race_id")
        df["circ_street"] = df["race_id"].map(rr["circuit_type"].eq("STREET").astype(float))
        df["circ_length"] = df["race_id"].map(rr["course_length"].astype(float))
        df["circ_turns_km"] = df["race_id"].map((rr["turns"] / rr["course_length"]).astype(float))
    else:
        df["circ_street"] = df["circ_length"] = df["circ_turns_km"] = np.nan
    df["circ_class"] = (np.where(df["circ_street"].eq(1.0), "street", "track") + "-"
                        + np.where(df["circ_turns_km"] >= TURN_DENSITY_SPLIT, "technical", "flowing"))
    df["d_class_adv"] = class_advantage(df, "driver_id", "circ_class", "finish_pct")

    # ---- championship context ---------------------------------------------------------------
    df["year"] = df["date"].dt.year
    df["pts_prior"] = df.groupby(["year", by])["points"].transform(
        lambda s: s.fillna(0).cumsum().shift(1, fill_value=0))
    max_pts = df.groupby("race_id")["pts_prior"].transform("max")
    df["d_season_pts_rel"] = np.where(max_pts > 0, df["pts_prior"] / max_pts.replace(0, np.nan), 0.0)
    df["d_standing_pct"] = df.groupby("race_id")["pts_prior"].rank(ascending=False, pct=True)

    # ---- team history (both cars aggregated per race) ---------------------------------------
    tr = (df.groupby(["race_id", "team"], sort=False)
            .agg(date=("date", "first"), circuit_id=("circuit_id", "first"), year=("year", "first"),
                 finish_pct=("finish_pct", "mean"), pace_pct=("pace_pct", "mean"),
                 dnf=("dnf", "mean"), grid_pct=("grid_pct", "mean"),
                 gap=("quali_gap_pct", "mean"), pts_share=("points_share", "sum"),
                 pts=("points", "sum"), stops=("pit_n_fin", "mean"), pit_time=("pit_time_c", "median"))
            .reset_index().sort_values(["date", "race_id"]))
    for col, hl, name in [("finish_pct", 3, "c_finish_ewm3"), ("finish_pct", 10, "c_finish_ewm10"),
                          ("pace_pct", 5, "c_pace_ewm5"), ("dnf", 10, "c_dnf_ewm10"),
                          ("grid_pct", 5, "c_grid_ewm5"), ("gap", 3, "c_gap_ewm3"),
                          ("gap", 10, "c_gap_ewm10"), ("pts_share", 5, "c_pts_ewm5"),
                          ("stops", 5, "c_stops_ewm5"), ("pit_time", 5, "c_pit_time_ewm5")]:
        tr[name] = _ewm_prior(tr, "team", col, hl)
    tr["circ_class"] = tr["race_id"].map(df.groupby("race_id")["circ_class"].first())
    tr["c_class_adv"] = class_advantage(tr, "team", "circ_class", "finish_pct")
    tr["c_circ_finish_mean"] = tr.groupby(["team", "circuit_id"])["finish_pct"].transform(
        lambda s: s.shift(1).expanding().mean())
    tr["c_pts_prior"] = tr.groupby(["year", "team"])["pts"].transform(
        lambda s: s.fillna(0).cumsum().shift(1, fill_value=0))
    cmax = tr.groupby("race_id")["c_pts_prior"].transform("max")
    tr["c_season_pts_rel"] = np.where(cmax > 0, tr["c_pts_prior"] / cmax.replace(0, np.nan), 0.0)
    team_cols = [c for c in tr.columns if c.startswith("c_")]
    df = df.merge(tr[["race_id", "team"] + team_cols], on=["race_id", "team"], how="left")

    # ---- circuit-level character (from previous visits only) --------------------------------
    cl = df[df["completed"] & df["pos_num"].notna()].copy()
    cl["abs_change"] = (cl["grid"] - cl["final_rank"]).abs()
    cr = (cl.groupby("race_id").agg(circuit_id=("circuit_id", "first"), date=("date", "first"),
                                    circ_abs_change=("abs_change", "mean"),
                                    circ_stops=("pit_n", "mean")).reset_index())
    pole = cl[cl["grid"] == 1].groupby("race_id")["final_rank"].first().eq(1).astype(float)
    cr["pole_win"] = cr["race_id"].map(pole)
    cr = cr.sort_values(["date", "race_id"])
    raw_abs, raw_pole, raw_stops = (cr["circ_abs_change"].copy(), cr["pole_win"].copy(),
                                    cr["circ_stops"].copy())
    cr["circ_abs_change"] = raw_abs.groupby(cr["circuit_id"]).transform(
        lambda s: s.shift(1).expanding().mean())
    cr["circ_pole_win"] = raw_pole.groupby(cr["circuit_id"]).transform(
        lambda s: s.shift(1).expanding().mean())
    cr["circ_stops_mean"] = raw_stops.groupby(cr["circuit_id"]).transform(
        lambda s: s.shift(1).expanding().mean())
    df = df.merge(cr[["race_id", "circ_abs_change", "circ_pole_win", "circ_stops_mean"]],
                  on="race_id", how="left")
    # upcoming races have no row in `cr`: use the mean over ALL completed visits to that circuit
    all_visits = pd.DataFrame({"circ_abs_change": raw_abs.groupby(cr["circuit_id"]).mean(),
                               "circ_pole_win": raw_pole.groupby(cr["circuit_id"]).mean(),
                               "circ_stops_mean": raw_stops.groupby(cr["circuit_id"]).mean()})
    upcoming = ~df["completed"]
    for c in ["circ_abs_change", "circ_pole_win", "circ_stops_mean"]:
        df.loc[upcoming, c] = df.loc[upcoming, "circuit_id"].map(all_visits[c])

    # ---- era, ranks within the field, teammate form -----------------------------------------
    race_order = (df[["race_id", "date"]].drop_duplicates().sort_values(["date", "race_id"])
                    .reset_index(drop=True))
    race_order["seq"] = np.arange(len(race_order))
    race_order["year"] = race_order["date"].dt.year
    era_first_seq = {y: race_order.loc[race_order.year >= y, "seq"].min() for y in ERA_START_YEARS}
    def era_idx(row):
        start = max(y for y in ERA_START_YEARS if y <= row.year)
        return row.seq - era_first_seq[start]
    race_order["era_race_idx"] = race_order.apply(era_idx, axis=1)
    df = df.merge(race_order[["race_id", "era_race_idx"]], on="race_id", how="left")
    df["round"] = df["round"].astype(int)

    for c in ["d_finish_ewm3", "d_finish_ewm10", "c_finish_ewm3", "c_finish_ewm10",
              "c_gap_ewm3", "d_gap_ewm5"]:
        df[c + "_rk"] = df.groupby("race_id")[c].rank(pct=True)
    df["d_vs_tm_form"] = df["d_finish_ewm10"] - _teammate_mean(df, "d_finish_ewm10")
    df["fp_vs_form"] = df["fp_best_rk"] - df["d_gap_ewm5_rk"]     # practice better/worse than usual

    return df.sort_values(["date", "race_id", "driver_id"]).reset_index(drop=True)


def load_features(path="data/results.csv") -> pd.DataFrame:
    return build_features(pd.read_csv(path))


if __name__ == "__main__" and len(__import__("sys").argv) > 1 and __import__("sys").argv[1] == "tune":
    # python features.py tune  -> choose RATING_PARAMS using races before 2023 only
    _f = load_features()
    for k, v in tune_ratings(_f).items():
        print(k, v)
    raise SystemExit

if __name__ == "__main__":
    f = load_features()
    done = f[f.completed]
    print(f"{len(f)} rows, {f.race_id.nunique()} races ({done.race_id.nunique()} completed)")
    print("\nNaN share per feature (completed races):")
    cols = FEATURE_SETS["post"]
    print(done[cols].isna().mean().sort_values(ascending=False).head(14).round(3).to_string())
    print("\nfeatures per set:", {k: len(v) for k, v in ALL_SETS.items()})
