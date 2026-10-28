#!/usr/bin/env python3
"""Tests for overrides.py on a copy of the data (never touches your real overrides.csv).

    python test_overrides.py        exit code 1 if anything fails
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import overrides as OV

res = pd.read_csv("data/results.csv")
races = pd.read_csv("data/races.csv")
last = res[res.position_raw.notna()].race_id.max()
HEADER = "race,driver,action,value,team,note\n"
fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


def upcoming_copy():
    """The latest completed race turned into an 'upcoming' one that has a grid but no result."""
    r = res.copy()
    r["grid_raw"] = r["grid_raw"].astype(object)
    m = r.race_id == last
    for c in ["position_raw", "laps_done", "points", "reason_retired"]:
        r.loc[m, c] = np.nan
    rc = races.copy()
    rc.loc[rc.race_id == last, "has_results"] = False
    return r, rc


def run(lines):
    r, rc = upcoming_copy()
    p = Path(tempfile.mkdtemp()) / "o.csv"
    p.write_text(HEADER + "\n".join(lines) + "\n")
    out, notes = OV.apply(r, rc, [last], path=p)
    return out[out.race_id == last].set_index("driver_id"), notes, r[r.race_id == last].set_index("driver_id")


grid = lambda d: pd.to_numeric(d.grid_raw, errors="coerce")
base = upcoming_copy()[0]
base = base[base.race_id == last].set_index("driver_id")
n_num = int(grid(base).notna().sum())        # drivers with a numbered slot (pit-lane starters have none)
victim = grid(base).sort_values().index[2]        # the driver starting 3rd
pos0 = int(grid(base)[victim])

after, notes, _ = run([f"{last},{victim},penalty,10,,test"])
g = grid(after)
check("penalty: numbered slots are still 1..n with no gaps or repeats", sorted(g.dropna().astype(int)) == list(range(1, n_num + 1)), notes)
check("penalty: driver drops exactly 10 places", int(g[victim]) == pos0 + 10, f"{pos0} -> {g[victim]}")
check("penalty: drivers between move up one", all(int(g[d]) == int(grid(base)[d]) - 1 for d in base.index
                                                   if pos0 < grid(base)[d] <= pos0 + 10))
check("penalty: drivers ahead are untouched", all(int(g[d]) == int(grid(base)[d]) for d in base.index if grid(base)[d] < pos0))

after, notes, _ = run([f"{last},{victim},penalty,pitlane,,test"])
check("pit lane start is marked PL and the rest close up", after.loc[victim, "grid_raw"] == "PL"
      and sorted(grid(after).dropna().astype(int)) == list(range(1, n_num)), notes)

after, notes, _ = run([f"{last},{victim},out,,,test"])
check("out: driver removed and the grid renumbered", victim not in after.index and len(after) == len(base) - 1
      and sorted(grid(after).dropna().astype(int)) == list(range(1, n_num)), notes)

after, notes, _ = run([f"{last},{victim},replace,Drugovich,,test"])
check("replace: new driver in the seat, old one gone", "drugovich" in " ".join(after.index) or any("Drugovich" in n or "drugovich" in n for n in notes) and victim not in after.index, notes)

after, notes, _ = run([f"{last},,add,Some Newcomer,cadillac,test"])
check("add: an extra car appears for the team", len(after) == len(base) + 1 and "some-newcomer" in after.index, notes)

after, notes, _ = run([f"{last},{victim},team,cadillac,,test"])
check("team: driver moves team", after.loc[victim, "constructor_id"] == "cadillac", notes)

after, notes, _ = run([f"{last},Nobody,out,,,test"])
check("unknown driver: ignored with a clear message, nothing else changes", len(after) == len(base) and any("unknown driver" in n for n in notes), notes)

after, notes, _ = run([f"2020-01,{victim},out,,,test"])
check("race that is not upcoming: skipped with a message", len(after) == len(base) and any("not an upcoming race" in n for n in notes), notes)

after, notes, _ = run([f"{last},{victim},banana,,,test"])
check("unknown action: ignored with a message", len(after) == len(base) and any("unknown action" in n for n in notes), notes)

p = Path(tempfile.mkdtemp()) / "none.csv"
check("no file: nothing changes", OV.apply(res, races, [last], path=p)[1] == [])
print()
print("All override tests passed." if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
