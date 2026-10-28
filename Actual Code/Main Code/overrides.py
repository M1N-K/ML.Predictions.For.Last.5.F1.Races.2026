#!/usr/bin/env python3
"""Manual changes to the entry list and the starting grid of upcoming races.

Edit overrides.csv (any text editor or Excel), save it, and run the predictions again. Every
prediction script reads it, so the predictions, the championship simulation and the page data all
pick the changes up.

    python overrides.py list     the drivers and teams in the latest line-up (the names you can use)
    python overrides.py check    read overrides.csv and show what each line would do

Actions (one per line):
    out      the driver does not race                        driver=Stroll
    replace  another driver takes the seat                   driver=Stroll  value=Drugovich
    add      an extra car                                    value=New Driver  team=cadillac
    team     the driver races for a different team           driver=Perez  value=cadillac
    penalty  places lost on the grid (or "pitlane")          driver=Hamilton  value=10

Driver changes (out / replace / add / team) work at every stage. A grid penalty needs a grid, so it
only has an effect after qualifying: before that the model does not use the grid. Only races that
have no result yet can be changed.
"""
import csv
import difflib
import io
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PATH = Path("overrides.csv")
COLUMNS = ["race", "driver", "action", "value", "team", "note"]
ACTIONS = {"out", "replace", "add", "team", "penalty"}
ROSTER = ["out", "replace", "add", "team"]          # applied before penalties


def pretty(slug):
    return str(slug).replace("-", " ").title()


def load(path=PATH):
    """-> list of dicts (one per line of the file), or [] if there is no file or no entries."""
    path = Path(path)
    if not path.exists():
        return []
    lines = [ln for ln in path.read_text(encoding="utf-8-sig").splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return []
    header = [c.strip().lower() for c in next(csv.reader([lines[0]]))]
    if header[: len(COLUMNS)] != COLUMNS:
        raise SystemExit(f"{path}: the first non-comment line must be the header: {','.join(COLUMNS)}")
    out = []
    for n, row in enumerate(csv.reader(io.StringIO("\n".join(lines[1:]))), start=2):
        row = [c.strip() for c in row] + [""] * len(COLUMNS)
        e = dict(zip(COLUMNS, row[: len(COLUMNS)]))
        e["_line"] = n
        out.append(e)
    return out


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def resolve(name, known, kind, allow_new=False):
    """Match a typed name or surname to one of `known` ids. Returns (id, warning or None)."""
    key = _slug(name)
    if not key:
        raise ValueError(f"no {kind} given")
    if key in known:
        return key, None
    hits = [k for k in known if key == k.split("-")[-1] or key in k.split("-") or k.endswith("-" + key)]
    hits = list(dict.fromkeys(hits))
    if len(hits) == 1:
        return hits[0], None
    if len(hits) > 1:
        raise ValueError(f"'{name}' matches several {kind}s ({', '.join(hits)}): use the full id")
    if allow_new:
        return key, f"'{name}' has no race history, so the model will treat {pretty(key)} as a new driver"
    close = difflib.get_close_matches(key, known, n=3)
    raise ValueError(f"unknown {kind} '{name}'" + (f" (did you mean {', '.join(close)}?)" if close else ""))


def _renumber_grid(rows):
    """After drivers leave, close gaps so the numbered grid slots run 1..n in the same order."""
    g = pd.to_numeric(rows["grid_raw"], errors="coerce")
    if g.notna().sum() == 0:
        return rows
    order = g.sort_values(kind="stable").dropna().index
    rows.loc[order, "grid_raw"] = np.arange(1, len(order) + 1)
    return rows


def apply(res, races, targets, path=PATH):
    """Apply overrides.csv to the rows of the upcoming races in `targets` (line-ups must already
    be filled in). Returns (new results frame, list of plain-English notes)."""
    entries = load(path)
    notes = []
    if not entries:
        return res, notes
    res = res.copy()
    for c in ("driver_id", "constructor_id", "grid_raw", "driver_number"):
        res[c] = res[c].astype(object)
    history = set(res.loc[res["position_raw"].notna(), "driver_id"])
    all_teams = set(res["constructor_id"])
    remaining = [t for t in targets if res.loc[res["race_id"] == t, "position_raw"].isna().all()]
    first_remaining = races[~races["has_results"]].sort_values("date")["race_id"]
    nxt = first_remaining.iloc[0] if len(first_remaining) else None
    gp = races.set_index("race_id")["grand_prix"].to_dict()

    def label(t):
        return f"{pretty(gp.get(t, t))} GP"

    ordered = sorted(entries, key=lambda e: (0 if e["action"].lower() in ROSTER else 1, e["_line"]))
    for e in ordered:
        where = f"overrides.csv line {e['_line']}"
        action = e["action"].lower()
        try:
            if action not in ACTIONS:
                raise ValueError(f"unknown action '{e['action']}' (use {', '.join(sorted(ACTIONS))})")
            rid = e["race"].lower()
            race_ids = remaining if rid == "all" else [nxt] if rid == "next" else [e["race"]]
            for t in race_ids:
                if t not in remaining:
                    notes.append(f"{where}: skipped, race {t} is not an upcoming race that is being predicted")
                    continue
                m = res["race_id"] == t
                present = set(res.loc[m, "driver_id"])
                if action == "add":
                    new, warn = resolve(e["value"], history | present, "driver", allow_new=True)
                    team, _ = resolve(e["team"], all_teams, "team")
                    if warn:
                        notes.append(f"{where}: {warn}")
                    template = res[m & (res["constructor_id"] == team)]
                    template = template.iloc[[0]] if len(template) else res[m].iloc[[0]]
                    template = template.copy()
                    template["driver_id"], template["constructor_id"] = new, team
                    template["driver_number"] = np.nan
                    template["grid_raw"] = np.nan
                    res = pd.concat([res, template], ignore_index=True)
                    notes.append(f"{label(t)}: added {pretty(new)} to {pretty(team)}")
                    continue
                drv, _ = resolve(e["driver"], present, "driver")
                idx = res.index[m & (res["driver_id"] == drv)]
                if action == "out":
                    res = res.drop(idx)
                    notes.append(f"{label(t)}: {pretty(drv)} is not racing")
                elif action == "replace":
                    new, warn = resolve(e["value"], history | present, "driver", allow_new=True)
                    if warn:
                        notes.append(f"{where}: {warn}")
                    res.loc[idx, "driver_id"] = new
                    res.loc[idx, "driver_number"] = np.nan
                    notes.append(f"{label(t)}: {pretty(new)} replaces {pretty(drv)}")
                elif action == "team":
                    team, _ = resolve(e["value"], all_teams, "team")
                    res.loc[idx, "constructor_id"] = team
                    notes.append(f"{label(t)}: {pretty(drv)} drives for {pretty(team)}")
                elif action == "penalty":
                    rows = res.loc[m]
                    g = pd.to_numeric(rows["grid_raw"], errors="coerce")
                    if g.notna().sum() == 0:
                        notes.append(f"{label(t)}: penalty for {pretty(drv)} saved but not used yet "
                                     "(no grid until qualifying has happened)")
                        continue
                    res = _penalise(res, m, drv, e["value"])
                    notes.append(f"{label(t)}: {pretty(drv)} "
                                 + ("starts from the pit lane" if str(e["value"]).lower().startswith("pit")
                                    else f"drops {int(float(e['value']))} grid places"))
        except ValueError as err:
            notes.append(f"{where}: ignored, {err}")
    for t in remaining:
        m = res["race_id"] == t
        if m.any():
            res.loc[m] = _renumber_grid(res.loc[m].copy())
    return res.reset_index(drop=True), notes


def _penalise(res, mask, drv, value):
    rows = res.loc[mask].copy()
    g = pd.to_numeric(rows["grid_raw"], errors="coerce")
    ordered = list(g.sort_values(kind="stable").dropna().index)
    me = rows.index[rows["driver_id"] == drv][0]
    if me in ordered:
        ordered.remove(me)
    if str(value).lower().startswith("pit"):
        res.loc[me, "grid_raw"] = "PL"
        ordered_new = ordered
    else:
        places = int(float(value))
        old_pos = (g.loc[me] if pd.notna(g.loc[me]) else len(ordered) + 1)
        new_pos = int(min(old_pos + places, len(ordered) + 1))
        ordered_new = ordered[: new_pos - 1] + [me] + ordered[new_pos - 1:]
    for i, ix in enumerate(ordered_new, start=1):
        res.loc[ix, "grid_raw"] = i
    return res


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    res = pd.read_csv("data/results.csv")
    races = pd.read_csv("data/races.csv")
    if cmd == "list":
        last = res[res["position_raw"].notna()]["race_id"].max()
        t = res[res["race_id"] == last][["driver_id", "constructor_id"]].sort_values(["constructor_id", "driver_id"])
        print(f"Line-up of the latest race ({last}). You can use a surname or the id:\n")
        print(t.rename(columns={"driver_id": "driver id", "constructor_id": "team id"}).to_string(index=False))
        return
    import engine as E
    remaining = list(races[~races["has_results"]].sort_values("date")["race_id"])
    base = res
    weekend = pd.read_csv("data/weekend.csv")
    entrants = E.load_entrants()
    for t in remaining:
        base = E.with_upcoming_lineup(base, races, t, weekend=weekend, entrants=entrants)
    entries = load()
    if not entries:
        print("overrides.csv has no active lines: predictions use the automatic line-up (see lineup.py).")
        return
    _, notes = apply(base, races, remaining)
    print(f"{len(entries)} line(s) read from overrides.csv. What they do:\n")
    print("\n".join("  " + n for n in notes) if notes else "  (nothing changed)")


if __name__ == "__main__":
    main()
