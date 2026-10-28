#!/usr/bin/env python3
"""Predict every remaining race of the season and save one text file.

    python predict_season.py                  writes reports/rest_of_season_<year>.txt
    python predict_season.py --refresh        download the latest results first
    python predict_season.py --out my.txt     choose the file (or a folder)
    python predict_season.py --quiet          don't print in the terminal

Each race uses the most informed stage its data supports (after qualifying, after practice, or
before the weekend). Races further ahead only know results up to the latest completed race, so they
are less certain; re-run with --refresh after each race. The NEXT race's prediction is also saved to
the tracker so it can be scored once the race has happened.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

import engine as E
import tracker


def predict_remaining(res, races, weekend):
    """-> list of (race meta, stage, predicted rows) for every race without a result."""
    remaining = races[~races["has_results"]].sort_values("date")
    df = E.build_frame(res, races, weekend, list(remaining["race_id"]))
    bundle = E.load_bundle()
    out = []
    for _, meta in remaining.iterrows():
        rows = df[df["race_id"] == meta["race_id"]]
        stage = E.stage_for(rows)
        out.append((meta, stage, E.predict_rows(rows, stage, E.bundle_models(bundle, stage))))
    return out, bundle


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.refresh:
        subprocess.run([sys.executable, "fetch_data.py"], check=True)
    res, races, weekend = E.load_data()
    if races["has_results"].all():
        sys.exit("No races left in the season.")
    results, bundle = predict_remaining(res, races, weekend)

    lines, summary, frames = [], [], []
    for i, (meta, stage, rows) in enumerate(results):
        fav = rows.sort_values("p_win", ascending=False).head(3)
        summary.append(f"R{meta['round']:<2} {E.pretty(meta['grand_prix']):<14} {meta['date']}  "
                       + " | ".join(f"{E.pretty(r.driver_id)} {r.p_win:.0%}" for r in fav.itertuples())
                       + f"   [{stage}]")
        table = E.display_table(rows, with_grid=(stage == "post"))
        lines += [f"\n=== Round {meta['round']}: {E.pretty(meta['grand_prix'])} GP, {meta['date']} "
                  f"({E.STAGE_LABEL[stage]}){'  SPRINT WEEKEND' if meta['is_sprint'] else ''} ===",
                  table.to_string(index=False)]
        frames.append(table.assign(race=meta["race_id"], gp=E.pretty(meta["grand_prix"]), stage=stage))
        if i == 0:
            tracker.save(meta["race_id"], stage, rows, bundle["trained_through"])

    year = int(results[0][0]["year"])
    header = [f"{year} F1 season: predictions for the remaining {len(results)} races",
              f"Models trained on all races through {bundle['trained_through']}. "
              "Top 3 by win probability per race ([pre] = before the weekend, [fp] = after practice, "
              "[post] = after qualifying):", ""] + summary
    if E.LINEUP_NOTES:
        header += ["", "Line-up changes found automatically (entrant list / practice attendance):"] \
            + ["  " + n for n in E.LINEUP_NOTES]
    if E.NOTES:
        header += ["", "Manual changes applied from overrides.csv:"] + ["  " + n for n in E.NOTES]
    footer = ["", "Notes: entry list = the latest race's line-up, adjusted by the season's entrant list and practice "
              "attendance where they say something different (add your own changes to overrides.csv). "
              "Later races are less certain "
              "(the model can't know what happens in the races before them). Not betting advice."]
    text = "\n".join(header + lines + footer) + "\n"

    path = Path(args.out) if args.out else Path(f"reports/rest_of_season_{year}.txt")
    if path.is_dir():
        path = path / f"rest_of_season_{year}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    Path("reports").mkdir(exist_ok=True)
    pd.concat(frames).to_csv(Path("reports") / f"rest_of_season_{year}.csv", index=False)
    print(f"Saved {path}" if args.quiet else text + f"\nSaved {path}")


if __name__ == "__main__":
    main()
