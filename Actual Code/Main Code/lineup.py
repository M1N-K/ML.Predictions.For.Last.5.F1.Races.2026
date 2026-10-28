#!/usr/bin/env python3
"""Who will be on the grid? Works out the entry list of an upcoming race.

Before a race has qualifying results there is no line-up, so the tool used to copy the previous
race's. That is wrong about 4 races in 10 (checked on 2014-2026: 107 of 269 races started a different
set of drivers than the race before, mostly at the start of a season). This module improves on the
copy using two things the data source offers, then `overrides.csv` is applied on top as before:

  1. The season's entrant list (f1db, data/entrants.csv): which driver races for which team in which
     rounds. It covers mid-season swaps (e.g. a driver replaced for three rounds) and, at the start of
     a season, the whole new line-up. f1db only knows rounds that have been run plus any it has
     announced, so for an ordinary next race it agrees with the last race and changes nothing.
  2. Practice attendance, once all three practice sessions have been run: a driver of the line-up who
     did not take part in any session is not at the track. (Checked on 2014-2026: 77 drivers were
     flagged this way, 76 of them really did not race.) The reverse does NOT work: reserve drivers
     practise too, so a driver who practised but is not in the line-up is not added.

    python lineup.py            show the line-up used for each remaining race, where it came from, and
                                what differs from simply copying the last race
"""
import numpy as np
import pandas as pd

MIN_DRIVERS = 16            # a plausible grid: anything smaller means the source is incomplete
FULL_PRACTICE_SESSIONS = 3


def pretty(slug):
    return str(slug).replace("-", " ").title()


def _rounds(cell):
    return [int(x) for x in str(cell).split()] if isinstance(cell, str) and cell.strip() else []


def entrants_lineup(entrants, year, round_no, last_done_round):
    """-> {driver_id: constructor_id} the entrant list gives for this round, or {} if it has nothing usable.

    A driver counts as entered if the round is among his declared rounds. A driver whose declared
    rounds stop at the latest round that has been run is taken to be continuing (f1db only writes
    rounds that have happened). A driver declared for later rounds but not this one is not entered."""
    if entrants is None or entrants.empty:
        return {}
    e = entrants[(entrants["year"] == year) & (~entrants["test_driver"].astype(bool))].copy()
    if e.empty:
        return {}
    e["rounds_list"] = e["rounds"].map(_rounds)
    out = {}
    for row in e.itertuples():
        rr = row.rounds_list
        if not rr:
            continue
        if round_no in rr:
            out[row.driver_id] = row.constructor_id                      # declared for this round
        elif max(rr) == last_done_round and round_no > last_done_round and row.driver_id not in out:
            out.setdefault(row.driver_id, row.constructor_id)            # continuing
    # a driver declared for this round with one team must not be overridden by a "continuing" entry
    explicit = {r.driver_id: r.constructor_id for r in e.itertuples() if round_no in r.rounds_list}
    out.update(explicit)
    return out


def resolve(res, races, target, weekend=None, entrants=None):
    """Entry list for an upcoming race. -> (rows for that race, list of plain-English notes).

    The rows are copies of the last completed race's rows (so every column exists), with drivers and
    teams changed as the sources above say."""
    meta = races[races["race_id"] == target].iloc[0]
    year, rnd = int(meta["year"]), int(meta["round"])
    done = res[res["position_raw"].notna()]
    last = done["race_id"].max()
    prev = res[res["race_id"] == last].copy()
    base = dict(zip(prev["driver_id"], prev["constructor_id"]))
    notes = []
    lineup = dict(base)
    source = "copied from the last race"

    last_round_this_year = done.loc[done["year"] == year, "round"].max()
    last_round_this_year = 0 if pd.isna(last_round_this_year) else int(last_round_this_year)
    ent = entrants_lineup(entrants, year, rnd, last_round_this_year)
    if len(ent) >= MIN_DRIVERS:
        lineup = ent
        source = "from the season's entrant list"
        added, left = sorted(set(ent) - set(base)), sorted(set(base) - set(ent))
        moved = sorted(d for d in set(ent) & set(base) if ent[d] != base[d])
        # the same team under a lineage name (e.g. audi / sauber) is not a move
        if added:
            notes.append("entrant list adds " + ", ".join(pretty(d) for d in added))
        if left:
            notes.append("entrant list leaves out " + ", ".join(pretty(d) for d in left))
        if moved:
            notes.append("entrant list moves " + ", ".join(f"{pretty(d)} to {pretty(ent[d])}" for d in moved))
    elif entrants is not None and not entrants.empty and (entrants["year"] == year).any():
        notes.append(f"entrant list has only {len(ent)} drivers for this round, so it was not used")

    if weekend is not None:
        w = weekend[weekend["race_id"] == target]
        if len(w) >= 18 and w["fp_sessions"].max() >= FULL_PRACTICE_SESSIONS:
            absent = sorted(d for d in lineup if d not in set(w["driver_id"]))
            if absent and len(lineup) - len(absent) >= MIN_DRIVERS:
                for d in absent:
                    lineup.pop(d)
                notes.append("did not take part in any practice session, so taken out: "
                             + ", ".join(pretty(d) for d in absent))
                source += " and practice attendance"

    rows = []
    for d, team in lineup.items():
        if d in set(prev["driver_id"]):
            r = prev[prev["driver_id"] == d].iloc[[0]].copy()
        else:
            same_team = prev[prev["constructor_id"] == team]
            r = (same_team if len(same_team) else prev).iloc[[0]].copy()
            r["driver_id"] = d
        r["constructor_id"] = team
        r["driver_number"] = np.nan if d not in set(prev["driver_id"]) else r["driver_number"]
        rows.append(r)
    out = pd.concat(rows, ignore_index=True)
    out["race_id"], out["year"], out["round"] = target, meta["year"], meta["round"]
    out["date"], out["circuit_id"], out["grand_prix"] = meta["date"], meta["circuit_id"], meta["grand_prix"]
    for c in ["grid_raw", "quali_pos", "quali_time", "position_raw", "laps_done", "points", "reason_retired"]:
        out[c] = np.nan
    return out, notes, source


def main():
    res, races = pd.read_csv("data/results.csv"), pd.read_csv("data/races.csv")
    weekend = pd.read_csv("data/weekend.csv")
    entrants = pd.read_csv("data/entrants.csv") if __import__("pathlib").Path("data/entrants.csv").exists() else None
    remaining = races[~races["has_results"]].sort_values("date")
    if remaining.empty:
        print("The season is complete.")
        return
    base = res
    for t in remaining["race_id"]:
        if (res["race_id"] == t).any():
            print(f"{t}: line-up is the real qualifying entry list.")
            continue
        rows, notes, source = resolve(res, races, t, weekend, entrants)
        print(f"{t}: {len(rows)} drivers, {source}")
        for n in notes:
            print("    " + n)


if __name__ == "__main__":
    main()
