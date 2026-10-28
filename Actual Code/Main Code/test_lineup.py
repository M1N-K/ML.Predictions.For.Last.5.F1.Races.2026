#!/usr/bin/env python3
"""Tests for lineup.py (automatic entry lists). Uses small made-up data, plus a check on the real files.

    python test_lineup.py
"""
import sys

import numpy as np
import pandas as pd

import engine as E
import lineup as L

TEAMS = [f"team{i}" for i in range(11)]
DRIVERS = [f"d{i:02d}" for i in range(22)]


def make(year=2030, done_rounds=2, total=4):
    rows, race_rows = [], []
    for rnd in range(1, total + 1):
        rid = f"{year}-{rnd:02d}"
        has = rnd <= done_rounds
        race_rows.append({"race_id": rid, "year": year, "round": rnd, "date": f"{year}-0{rnd}-01",
                          "grand_prix": f"gp{rnd}", "circuit_id": f"c{rnd}", "has_results": has})
        if has:
            for i, d in enumerate(DRIVERS):
                rows.append({"race_id": rid, "year": year, "round": rnd, "date": f"{year}-0{rnd}-01",
                             "circuit_id": f"c{rnd}", "grand_prix": f"gp{rnd}", "driver_id": d,
                             "constructor_id": TEAMS[i // 2], "driver_number": i + 1, "grid_raw": i + 1,
                             "quali_pos": i + 1, "quali_time": 80 + i / 10, "position_raw": i + 1,
                             "laps_done": 50, "points": 0, "reason_retired": np.nan})
    return pd.DataFrame(rows), pd.DataFrame(race_rows)


def entrants(year=2030, rounds="1 2", drop=(), extra=()):
    rows = []
    for i, d in enumerate(DRIVERS):
        if d in drop:
            continue
        rows.append({"year": year, "driver_id": d, "constructor_id": TEAMS[i // 2], "entrant_id": f"e{i // 2}",
                     "test_driver": False, "rounds": rounds})
    rows += list(extra)
    return pd.DataFrame(rows)


def weekend_for(rid, skip=(), reserve=(), sessions=3.0):
    rows = [{"race_id": rid, "driver_id": d, "fp_sessions": sessions} for d in DRIVERS if d not in skip]
    rows += [{"race_id": rid, "driver_id": d, "fp_sessions": sessions} for d in reserve]
    return pd.DataFrame(rows)


FAILED = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILED.append(name)


def drivers_of(frame, rid):
    return set(frame[frame.race_id == rid].driver_id)


def main():
    res, races = make()
    t = "2030-03"

    # 1. no extra information: the old behaviour, a copy of the last race
    out = E.with_upcoming_lineup(res, races, t)
    check("copy of the last race when nothing else is given", drivers_of(out, t) == set(DRIVERS))

    # 2. entrant list that agrees changes nothing and says nothing
    rows, notes, src = L.resolve(res, races, t, None, entrants())
    check("agreeing entrant list: same drivers, no notes", set(rows.driver_id) == set(DRIVERS) and not notes, notes)

    # 3. a driver declared for the next round only (a stand-in), another one declared away
    ent = entrants(drop={"d03"}, extra=[
        {"year": 2030, "driver_id": "d03", "constructor_id": "team1", "entrant_id": "e1", "test_driver": False,
         "rounds": "1 2 4"},                                    # out for round 3, back for 4
        {"year": 2030, "driver_id": "newguy", "constructor_id": "team1", "entrant_id": "e1", "test_driver": False,
         "rounds": "3"}])
    rows, notes, src = L.resolve(res, races, t, None, ent)
    got = set(rows.driver_id)
    check("stand-in declared for this round is added", "newguy" in got, got)
    check("driver declared for later rounds but not this one is left out", "d03" not in got, got)
    check("notes say what changed", any("newguy" in n.title().lower() or "Newguy" in n for n in notes), notes)
    new_row = rows[rows.driver_id == "newguy"].iloc[0]
    check("stand-in gets the team from the entrant list", new_row.constructor_id == "team1")
    check("the next round (4) has the regular driver back",
          "d03" in set(L.resolve(res, races, "2030-04", None, ent)[0].driver_id))

    # 4. an entrant list with too few drivers is not trusted
    small = entrants()[:10]
    rows, notes, src = L.resolve(res, races, t, None, small)
    check("incomplete entrant list is ignored", set(rows.driver_id) == set(DRIVERS) and any("not used" in n for n in notes), notes)

    # 5. first race of a new season: the whole line-up comes from the new season's entrants
    res2, races2 = make(year=2030, done_rounds=4, total=4)
    races2 = pd.concat([races2, pd.DataFrame([{"race_id": "2031-01", "year": 2031, "round": 1, "date": "2031-03-01",
                                                "grand_prix": "gp1", "circuit_id": "c1", "has_results": False}])])
    new_ent = entrants(year=2031, rounds="1 2 3", drop={"d00"}, extra=[
        {"year": 2031, "driver_id": "rookie", "constructor_id": "team0", "entrant_id": "e0", "test_driver": False,
         "rounds": "1 2 3"}])
    rows, notes, src = L.resolve(res2, races2, "2031-01", None, new_ent)
    got = set(rows.driver_id)
    check("new season uses the new entrant list", "rookie" in got and "d00" not in got and len(got) == 22, got)

    # 6. practice attendance: absent from all three sessions -> out; reserves are NOT added
    w = weekend_for(t, skip={"d07"}, reserve={"reserve1"})
    rows, notes, src = L.resolve(res, races, t, w, None)
    got = set(rows.driver_id)
    check("driver who skipped every practice session is taken out", "d07" not in got and len(got) == 21, got)
    check("reserve driver who practised is not added", "reserve1" not in got)
    w2 = weekend_for(t, skip={"d07"}, sessions=2.0)
    rows, notes, src = L.resolve(res, races, t, w2, None)
    check("not applied until all three sessions have been run", "d07" in set(rows.driver_id))
    w3 = weekend_for(t, skip=set(DRIVERS[:8]))
    rows, notes, src = L.resolve(res, races, t, w3, None)
    check("never strips the grid below a plausible size", len(rows) == 22, len(rows))

    # 7. through the engine, with overrides still applied afterwards
    w_eng = weekend_for(t, skip={"d07"}, reserve={"newguy"})       # the stand-in practised, d07 did not
    out = E.with_upcoming_lineup(res, races, t, weekend=w_eng, entrants=ent)
    check("engine uses the cascade when given the extra sources",
          "newguy" in drivers_of(out, t) and "d07" not in drivers_of(out, t))
    check("engine records notes for the report", len(E.LINEUP_NOTES) >= 1)

    # 8. real files: the next race's line-up should equal the last race's (nothing announced right now)
    try:
        r_res, r_races = pd.read_csv("data/results.csv"), pd.read_csv("data/races.csv")
        r_w, r_e = pd.read_csv("data/weekend.csv"), E.load_entrants()
        nxt = r_races[~r_races["has_results"]].sort_values("date")["race_id"].iloc[0]
        last = r_res[r_res.position_raw.notna()].race_id.max()
        rows, notes, src = L.resolve(r_res, r_races, nxt, r_w, r_e)
        same = set(rows.driver_id) == set(r_res[r_res.race_id == last].driver_id)
        check(f"real data: {nxt} line-up matches the last race ({src})", same, notes)
    except Exception as err:      # the real files are optional for this test
        print("SKIP real-data check:", err)

    print("\nAll line-up tests passed." if not FAILED else f"\n{len(FAILED)} FAILED: {FAILED}")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
