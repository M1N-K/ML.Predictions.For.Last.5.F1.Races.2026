#!/usr/bin/env python3
"""Predict an F1 race.

    python predict.py                    next race on the calendar
    python predict.py --refresh          download the latest results first, then predict
    python predict.py --race 2026-18     replay a past race, using only races before it
    python predict.py --mode pre|fp|post force how much information to use
    python predict.py --out file.txt     where to save the text file (a file name or a folder)
    python predict.py --quiet            don't print the table in the terminal

The most informed stage is chosen automatically: "post" once there is a grid (after qualifying),
"fp" once practice has been run, otherwise "pre". The entry list before qualifying is assumed to be
the line-up of the most recent race. Predictions for upcoming races are saved to the tracker.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

import engine as E
import train as T
import tracker


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--race", help="race id such as 2026-18; default is the next race")
    ap.add_argument("--mode", choices=["pre", "fp", "post"])
    ap.add_argument("--refresh", action="store_true", help="re-download data before predicting")
    ap.add_argument("--out", help="where to save the text file (a file name or a folder); "
                                  "default: reports/prediction_<race>_<stage>.txt")
    ap.add_argument("--quiet", action="store_true", help="don't print the table in the terminal")
    args = ap.parse_args()

    if args.refresh:
        subprocess.run([sys.executable, "fetch_data.py"], check=True)
    res, races, weekend = E.load_data()
    if args.race:
        target = args.race
        if target not in set(races["race_id"]):
            sys.exit(f"Unknown race id {target}. Examples: {', '.join(races['race_id'].tail(3))}")
    else:
        target = races[~races["has_results"]].sort_values("date")["race_id"].iloc[0]
    meta = races[races["race_id"] == target].iloc[0]

    df = E.build_frame(res, races, weekend, [target])
    rows = df[df["race_id"] == target]
    completed = bool(rows["completed"].all())
    stage = args.mode or E.stage_for(rows)
    if stage == "post" and not rows["grid"].notna().all():
        sys.exit("Qualifying hasn't happened yet for this race, so there is no grid: use --mode fp or pre.")
    if stage == "fp" and rows["fp_best_gap"].notna().sum() < 10:
        sys.exit("No practice results for this race yet: use --mode pre.")

    bundle = E.load_bundle() if E.MODEL_PATH.exists() else None
    if completed:   # honest replay: retrain on strictly earlier races
        train = df[df["completed"] & (df["race_id"] < target)]
        models = E.train_models(train, stage, bundle)
        basis = f"models retrained on the {train.race_id.nunique()} races before this one"
        trained_through = None
    else:
        models = E.bundle_models(bundle, stage)
        trained_through = bundle["trained_through"]
        basis = f"models trained on all races through {trained_through}"
    rows = E.predict_rows(rows, stage, models)

    out = E.display_table(rows, with_grid=(stage == "post"), with_actual=completed)
    buf = [f"\n{meta['year']} round {meta['round']}: {E.pretty(meta['grand_prix'])} GP, {meta['date']}"
           + ("  (sprint weekend)" if meta.get("is_sprint") else ""),
           f"Prediction {E.STAGE_LABEL[stage]}; {basis}.\n", out.to_string(index=False)]
    if E.LINEUP_NOTES and not completed:
        buf.append("Line-up changes found automatically (entrant list / practice attendance):")
        buf += ["  " + n for n in E.LINEUP_NOTES]
    if E.NOTES and not completed:
        buf.append("Manual changes applied from overrides.csv:")
        buf += ["  " + n for n in E.NOTES]
    top = rows.sort_values("p_win", ascending=False).iloc[0]
    buf.append(f"\nMost likely winner by win probability: {E.pretty(top['driver_id'])} ({top['p_win']:.0%})")
    if stage != "post" and not completed:
        buf.append("Entry list: the latest race's line-up, adjusted by the season's entrant list and practice attendance where they say something different. "
                   + ("Re-run after qualifying for a sharper call." if stage == "fp"
                      else "Re-run after practice and again after qualifying for sharper calls."))
    if completed:
        m = T.order_metrics(rows, rows["score"]).iloc[0]
        buf.append(f"Replay check: winner {'correct' if m.winner_hit else 'wrong'}, "
                   f"{m.podium_overlap * 3:.0f}/3 podium drivers, Spearman {m.spearman:.2f}, "
                   f"mean position error {m.mae_pos:.1f}")
    else:
        saved = tracker.save(target, stage, rows, trained_through)
        if saved:
            buf.append(f"Saved to the prediction tracker ({stage} stage), to be scored after the race.")

    Path("reports").mkdir(exist_ok=True)
    csv_path = Path(f"reports/prediction_{target}_{stage}.csv")
    out.to_csv(csv_path, index=False)
    txt_path = Path(args.out) if args.out else Path(f"reports/prediction_{target}_{stage}.txt")
    if txt_path.is_dir():
        txt_path = txt_path / f"prediction_{target}_{stage}.txt"
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    txt_path.write_text("\n".join(buf) + "\n", encoding="utf-8")
    if args.quiet:
        print(f"Saved {txt_path}")
    else:
        print("\n".join(buf))
        print(f"\nSaved {txt_path} (and {csv_path})")


if __name__ == "__main__":
    main()
