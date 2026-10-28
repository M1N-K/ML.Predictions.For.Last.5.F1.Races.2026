#!/usr/bin/env python3
"""Write the data files that feed the web page (site_data/*.csv).

    python export_site_data.py

Run after the predictions and the championship simulation (run_all.py does this). Files:
    race_predictions.csv   every remaining race: predicted order, win / podium / retirement chances
    title_drivers.csv, title_constructors.csv, title_timeline.csv, title_summary.csv   championship odds
    model_accuracy.csv     back-test results for each model and baseline
    calibration.csv        predicted vs observed frequencies
    scorecard.csv          how saved predictions did (header only until a predicted race has been run)
    meta.csv               when the models were trained, when this export was made, size of the test
"""
import datetime as dt
from pathlib import Path

import pandas as pd

import engine as E
from predict_season import predict_remaining

OUT = Path("site_data")


def main():
    OUT.mkdir(exist_ok=True)
    res, races, weekend = E.load_data()
    remaining = races[~races["has_results"]]
    if remaining.empty:
        print("The season is complete: nothing to export.")
        return
    results, bundle = predict_remaining(res, races, weekend)

    rows = []
    for meta, stage, r in results:
        for x in r.itertuples():
            rows.append({
                "row_id": f"{meta['race_id']}|{x.driver_id}", "race_id": meta["race_id"],
                "grand_prix": E.pretty(meta["grand_prix"]), "round": int(meta["round"]), "date": meta["date"],
                "stage": stage, "stage_label": E.STAGE_LABEL[stage], "is_sprint": int(bool(meta["is_sprint"])),
                "pred": int(x.pred), "driver": E.pretty(x.driver_id), "team": E.pretty(x.team),
                "grid": int(x.grid) if stage == "post" and pd.notna(x.grid) else "",
                "p_win": round(float(x.p_win), 4), "p_podium": round(float(x.p_podium), 4),
                "p_dnf": round(float(x.p_dnf), 4)})
    pd.DataFrame(rows).to_csv(OUT / "race_predictions.csv", index=False)

    for f in ("title_drivers", "title_constructors", "title_timeline", "title_summary"):
        src = Path("reports/site") / f"{f}.csv"
        if not src.exists():
            raise SystemExit(f"{src} is missing: run simulate_season.py first.")
        (OUT / f"{f}.csv").write_text(src.read_text())

    br = pd.read_csv("reports/backtest_races.csv")
    acc = br.groupby("model").agg(races=("race_id", "nunique"), winner_hit_pct=("winner_hit", "mean"),
                                  podium_right=("podium_overlap", "mean"), top10_right=("top10_overlap", "mean"),
                                  spearman=("spearman", "mean"), avg_position_error=("mae_pos", "mean")).reset_index()
    acc["winner_hit_pct"] = (acc["winner_hit_pct"] * 100).round(1)
    acc["podium_right"] = (acc["podium_right"] * 3).round(2)
    acc["top10_right"] = (acc["top10_right"] * 10).round(2)
    acc["spearman"] = acc["spearman"].round(3)
    acc["avg_position_error"] = acc["avg_position_error"].round(2)
    acc["kind"] = ["baseline" if m.startswith("baseline") else ("earlier version" if "first version" in m or m.endswith("_v1") else "model")
                   for m in acc["model"]]
    acc.to_csv(OUT / "model_accuracy.csv", index=False)

    cal = pd.read_csv("reports/calibration.csv")
    cal[["mean_p", "observed", "lo", "hi"]] = cal[["mean_p", "observed", "lo", "hi"]].round(4)
    cal.to_csv(OUT / "calibration.csv", index=False)

    sc = Path("tracker/scorecard.csv")
    cols = ["race_id", "grand_prix", "stage", "predicted_winner", "actual_winner", "winner_hit", "podium_right",
            "spearman", "grid_order_spearman", "avg_position_error"]
    if sc.exists() and len(pd.read_csv(sc)):
        s = pd.read_csv(sc)
        s["row_id"] = s["race_id"] + "|" + s["stage"]
        s[["row_id"] + cols].to_csv(OUT / "scorecard.csv", index=False)
    else:
        pd.DataFrame(columns=["row_id"] + cols).to_csv(OUT / "scorecard.csv", index=False)

    first_model = br[br.model == br.model.iloc[0]]
    n_test = int(first_model.race_id.nunique())
    clean_from = 2023                      # seasons after the tuning season (see train.py CLEAN_FROM)
    n_clean = int(first_model[first_model.year >= clean_from].race_id.nunique())
    nxt = results[0][0]
    pd.DataFrame([{"trained_through": bundle["trained_through"],
                   "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                   "next_race": E.pretty(nxt["grand_prix"]), "next_date": nxt["date"],
                   "test_races": n_test, "first_test_year": int(first_model.year.min()),
                   "clean_races": n_clean, "clean_from": clean_from}]).to_csv(OUT / "meta.csv", index=False)
    print("Wrote", ", ".join(sorted(p.name for p in OUT.glob("*.csv"))))


if __name__ == "__main__":
    main()
