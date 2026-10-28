#!/usr/bin/env python3
"""Download Formula 1 race data from the open-source f1db project and build tidy CSVs.

Source: https://github.com/f1db/f1db (CC BY 4.0), read as raw files from GitHub.

Outputs (in ./data):
    raw/<year>/<NN-slug>/{race,race-results,qualifying-results}.yml   cached downloads
    races.csv     one row per race (including the upcoming one if f1db lists it)
    results.csv   one row per driver per race (race result + qualifying)

Re-running is cheap: cached files are reused, new rounds are discovered, and races without
results yet are re-checked so the data keeps up with the season.
"""
import argparse
import datetime as dt
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
import yaml

BASE = "https://raw.githubusercontent.com/f1db/f1db/main/src/data/seasons"
RAW = Path("data/raw")
INDEX = RAW / "races_index.json"

# Every f1db grandPrixId that has been on the calendar since 2014. Race folders are named
# "<round>-<grandPrixId>", so we find each round by trying these until one exists.
POOL = [
    "australia", "bahrain", "china", "spain", "monaco", "canada", "austria", "great-britain",
    "hungary", "belgium", "italy", "singapore", "japan", "united-states", "brazil", "abu-dhabi",
    "mexico", "mexico-city", "sao-paulo", "azerbaijan", "russia", "france", "germany",
    "netherlands", "saudi-arabia", "miami", "qatar", "las-vegas", "emilia-romagna", "portugal",
    "turkey", "styria", "70th-anniversary", "eifel", "sakhir", "tuscany", "europe", "malaysia",
    "madrid", "barcelona", "barcelona-catalunya", "south-africa", "korea", "india", "san-marino",
]

_local = threading.local()


def session():
    if not hasattr(_local, "s"):
        s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=3, pool_maxsize=32)
        s.mount("https://", adapter)
        _local.s = s
    return _local.s


def http_get(url):
    """Return text, or None on 404. Raises on other failures."""
    r = session().get(url, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.text


def fetch_cached(year, folder, name, refresh=False, mark_missing=False):
    """Download one race file with an on-disk cache.

    mark_missing: for completed races, remember that a file does not exist (e.g. no sprint)
    so later runs don't ask for it again.
    """
    path = RAW / str(year) / folder / f"{name}.yml"
    none = path.with_name(path.name + ".none")
    if not refresh:
        if path.exists():
            return path.read_text()
        if none.exists():
            return None
    text = http_get(f"{BASE}/{year}/races/{folder}/{name}.yml")
    path.parent.mkdir(parents=True, exist_ok=True)
    if text is not None:
        path.write_text(text)
    elif mark_missing:
        none.write_text("")
    return text


def discover_year(year, known):
    """known: {round: slug} already indexed. Returns the extended mapping."""
    races = {int(k): v for k, v in known.items()}
    used = set(races.values())
    rnd = max(races, default=0) + 1
    while True:
        found = None
        for cand in POOL:
            if cand in used:
                continue
            folder = f"{rnd:02d}-{cand}"
            if fetch_cached(year, folder, "race") is not None:
                found = cand
                break
        if found is None:
            # Make sure this is the true end of the season and not an unknown slug.
            for cand in POOL:
                folder = f"{rnd + 1:02d}-{cand}"
                if cand not in used and fetch_cached(year, folder, "race") is not None:
                    print(f"WARNING {year}: round {rnd} has an unrecognised grand prix id")
                    break
            return races
        races[rnd] = found
        used.add(found)
        rnd += 1


def to_seconds(t):
    if not t or not isinstance(t, str):
        return None
    try:
        if ":" in t:
            m, s = t.split(":")
            return int(m) * 60 + float(s)
        return float(t)
    except ValueError:
        return None


EXTRA_FILES = ["free-practice-1-results", "free-practice-2-results", "free-practice-3-results",
               "sprint-qualifying-results", "sprint-race-results", "pit-stops"]


def load_yml(path):
    return yaml.safe_load(path.read_text()) if path.exists() else None


def weekend_rows(base):
    """Practice pace, sprint results and pit stops for one race weekend -> {driver_id: {...}}."""
    out = {}

    # --- practice: gap to the fastest car of each session, in % ----------------------------
    sessions = []
    for i in (1, 2, 3):
        rows = load_yml(base / f"free-practice-{i}-results.yml")
        if not rows:
            continue
        times = {r["driverId"]: to_seconds(r.get("time")) for r in rows}
        valid = [t for t in times.values() if t]
        if valid:
            best = min(valid)
            sessions.append({r["driverId"]: ((times[r["driverId"]] / best - 1) * 100
                                             if times[r["driverId"]] else None, r.get("laps") or 0)
                             for r in rows})
    for d in {d for s in sessions for d in s}:
        gaps = [s[d][0] for s in sessions if d in s and s[d][0] is not None]
        out.setdefault(d, {}).update(
            fp_best_gap=min(gaps) if gaps else None,
            fp_mean_gap=sum(gaps) / len(gaps) if gaps else None,
            fp_laps=sum(s[d][1] for s in sessions if d in s),
            fp_sessions=len(sessions))

    # --- sprint qualifying / shootout ---------------------------------------------------------
    sq = load_yml(base / "sprint-qualifying-results.yml")
    if sq:
        best_t = {}
        for r in sq:
            ts = [to_seconds(r.get(k)) for k in ("q1", "q2", "q3")]
            ts = [t for t in ts if t]
            best_t[r["driverId"]] = (min(ts) if ts else None, r["position"])
        pole = min((t for t, _ in best_t.values() if t), default=None)
        for d, (t, pos) in best_t.items():
            out.setdefault(d, {}).update(
                sprint_quali_pos=pos if isinstance(pos, int) else None,
                sprint_quali_gap=(t / pole - 1) * 100 if t and pole else None)

    # --- sprint race ------------------------------------------------------------------------
    sr = load_yml(base / "sprint-race-results.yml")
    if sr:
        for r in sr:
            out.setdefault(r["driverId"], {}).update(
                sprint_pos=r["position"], sprint_pts=r.get("points") or 0,
                sprint_grid=r.get("gridPosition"))

    # --- pit stops (history only: used for future races, never for the race itself) -----------
    ps = load_yml(base / "pit-stops.yml")
    if ps:
        per = {}
        for r in ps:
            per.setdefault(r["driverId"], []).append((to_seconds(r.get("time")), r.get("lap")))
        for d, stops in per.items():
            times = sorted(t for t, _ in stops if t and t < 120)   # ignore red-flag stops
            laps = [lap for _, lap in stops if lap]
            out.setdefault(d, {}).update(
                pit_n=len(stops),
                pit_med_time=times[len(times) // 2] if times else None,
                pit_first_lap=min(laps) if laps else None)
    return out


def fetch_standings(year):
    """Official championship tables for `year` (always refreshed)."""
    for kind, key in (("driver", "driverId"), ("constructor", "constructorId")):
        text = http_get(f"{BASE}/{year}/{kind}-standings.yml")
        if text:
            rows = yaml.safe_load(text)
            pd.DataFrame([{"position": r["position"], "id": r[key], "points": r["points"]}
                          for r in rows]).to_csv(f"data/standings_{kind}s_{year}.csv", index=False)


def build(index):
    race_rows, result_rows, weekend = [], [], []
    for year, rounds in sorted(index.items(), key=lambda kv: int(kv[0])):
        for rnd, slug in sorted(rounds.items(), key=lambda kv: int(kv[0])):
            folder = f"{int(rnd):02d}-{slug}"
            base = RAW / str(year) / folder
            race = yaml.safe_load((base / "race.yml").read_text())
            res_p, q_p = base / "race-results.yml", base / "qualifying-results.yml"
            results = yaml.safe_load(res_p.read_text()) if res_p.exists() else None
            quali = yaml.safe_load(q_p.read_text()) if q_p.exists() else None
            race_id = f"{year}-{int(rnd):02d}"
            race_rows.append({
                "race_id": race_id, "year": int(year), "round": int(rnd),
                "date": str(race["date"]), "grand_prix": slug, "circuit_id": race["circuitId"],
                "laps": race.get("laps"), "course_length": race.get("courseLength"),
                "has_results": bool(results), "has_quali": bool(quali),
                "is_sprint": race.get("sprintRaceDate") is not None,
                "circuit_type": race.get("circuitType"), "turns": race.get("turns"),
                "direction": race.get("direction"),
            })
            for driver, vals in weekend_rows(base).items():
                weekend.append({"race_id": race_id, "driver_id": driver, **vals})
            qmap = {}
            for q in quali or []:
                times = [to_seconds(q.get(k)) for k in ("q1", "q2", "q3")]
                times = [t for t in times if t]
                qmap[q["driverId"]] = {
                    "quali_pos": q["position"] if isinstance(q["position"], int) else None,
                    "quali_time": times[-1] if times else None,  # time from the last session reached
                }
            if results:
                entries = [(r["driverId"], r) for r in results]
            else:  # upcoming race: entry list comes from qualifying if it has happened
                entries = [(q["driverId"], q) for q in quali or []]
            for driver, r in entries:
                q = qmap.get(driver, {})
                pos = r.get("position") if results else None
                grid = r.get("gridPosition") if results else (q.get("quali_pos"))
                result_rows.append({
                    "race_id": race_id, "year": int(year), "round": int(rnd), "date": str(race["date"]),
                    "circuit_id": race["circuitId"], "grand_prix": slug,
                    "driver_id": driver, "constructor_id": r["constructorId"],
                    "driver_number": r.get("driverNumber"),
                    "grid_raw": grid, "quali_pos": q.get("quali_pos"), "quali_time": q.get("quali_time"),
                    "position_raw": pos, "laps_done": r.get("laps") if results else None,
                    "points": (r.get("points") or 0) if results else None,
                    "reason_retired": r.get("reasonRetired") if results else None,
                })
    pd.DataFrame(race_rows).to_csv("data/races.csv", index=False)
    pd.DataFrame(result_rows).to_csv("data/results.csv", index=False)
    pd.DataFrame(weekend).to_csv("data/weekend.csv", index=False)
    return len(race_rows), len(result_rows)


def parse_rounds(text):
    """'1-18' / '1-5, 7-10' / '3' / None  ->  sorted list of round numbers."""
    if text is None:
        return []
    out = []
    for part in str(text).replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def fetch_entrants(years):
    """Season entry lists from f1db (who is entered with which team, and for which rounds).
    f1db only fills in rounds that have been run, plus any it knows in advance, so this is a source of
    announced changes, not a guarantee. Written to data/entrants.csv; always re-downloaded (small)."""
    rows = []
    for year in years:
        text = http_get(f"{BASE}/{year}/entrants.yml")
        if text is None:
            continue
        for e in yaml.safe_load(text) or []:
            for d in e.get("drivers") or []:
                rows.append({"year": year, "driver_id": d["driverId"], "constructor_id": e["constructorId"],
                             "entrant_id": e["entrantId"], "test_driver": bool(d.get("testDriver")),
                             "rounds": " ".join(str(r) for r in parse_rounds(d.get("rounds")))})
    pd.DataFrame(rows, columns=["year", "driver_id", "constructor_id", "entrant_id", "test_driver", "rounds"]
                 ).to_csv("data/entrants.csv", index=False)
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--first-year", type=int, default=2014)
    ap.add_argument("--last-year", type=int, default=dt.date.today().year)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    index = json.loads(INDEX.read_text()) if INDEX.exists() else {}
    years = list(range(args.first_year, args.last_year + 1))

    def do_year(y):
        return y, discover_year(y, index.get(str(y), {}))

    with ThreadPoolExecutor(args.workers) as ex:
        for y, races in ex.map(do_year, years):
            index[str(y)] = {str(k): v for k, v in races.items()}
            print(f"{y}: {len(races)} races found")
    INDEX.write_text(json.dumps(index, indent=1, sort_keys=True))

    # Download results + qualifying (refreshing any race that had no results last time).
    jobs = []
    for y, rounds in index.items():
        for rnd, slug in rounds.items():
            folder = f"{int(rnd):02d}-{slug}"
            have = (RAW / y / folder / "race-results.yml").exists()
            for name in ("race-results", "qualifying-results"):
                jobs.append((int(y), folder, name, not have, False))
            for name in EXTRA_FILES:       # completed races: cache "doesn't exist" too
                jobs.append((int(y), folder, name, not have, have))
    with ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(lambda j: fetch_cached(j[0], j[1], j[2], refresh=j[3], mark_missing=j[4]), jobs))

    n_races, n_rows = build(index)
    fetch_standings(args.last_year)
    try:
        n_ent = fetch_entrants([args.last_year, args.last_year + 1])
        print(f"Wrote data/entrants.csv ({n_ent} entries)")
    except Exception as err:          # optional input: never stop the update for it
        print(f"Could not download the entrants list ({err}); line-ups will be copied from the last race.")
    print(f"Wrote data/races.csv ({n_races} races), data/results.csv ({n_rows} rows), "
          f"data/weekend.csv and the {args.last_year} standings")


if __name__ == "__main__":
    main()
