#!/usr/bin/env python3
"""Tests for odds.py with small made-up data, plus a check of the real odds.csv.

    python test_odds.py
"""
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import odds as O

FAILED = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))
    if not cond:
        FAILED.append(name)


def raises(fn, *a):
    try:
        fn(*a)
    except ValueError:
        return True
    return False


def close(a, b, tol=1e-9):
    return abs(a - b) < tol


def main():
    # 1. odds formats
    check("American +120 -> 2.2", close(O.to_decimal("+120"), 2.2))
    check("American -200 -> 1.5", close(O.to_decimal("-200"), 1.5))
    check("fractional 5/2 -> 3.5", close(O.to_decimal("5/2"), 3.5))
    check("fractional 1/1 -> 2.0", close(O.to_decimal("1/1"), 2.0))
    check("decimal 3.4 -> 3.4", close(O.to_decimal("3.4"), 3.4))
    check("decimal with comma 3,4 -> 3.4", close(O.to_decimal("3,4"), 3.4))
    check("rejects +50, 1.0, text and blank",
          all(raises(O.to_decimal, x) for x in ["+50", "-50", "1.0", "0.8", "abc", "", "5/0"]))

    # 2. turning prices into chances
    p, info = O.market_chances({"a": 2.0, "b": 4.0}, ["a", "b", "c"], tail=0.1)
    check("one source: chances add up to 1", close(sum(p.values()), 1.0))
    check("one source: scaled in proportion (a = 0.5/0.85)", close(p["a"], 0.5 / 0.85), p)
    check("unlisted driver gets the tail before scaling", close(p["c"], 0.1 / 0.85))
    check("info counts", info["n_listed"] == 2 and info["n_tail"] == 1 and close(info["listed_sum"], 0.75))
    p2, _ = O.market_chances([{"a": 2.0}, {"a": 4.0, "b": 4.0}], ["a", "b"], tail=0.01)
    check("two sources: average of 1/odds where priced (a = .375 / .625)", close(p2["a"], 0.375 / 0.625), p2)
    check("driver priced by only one source keeps that price", close(p2["b"], 0.25 / 0.625))
    _, info3 = O.market_chances({"a": 2.0, "zz": 9.0}, ["a", "b"], tail=0.1)
    check("prices for drivers not in the race are reported and ignored", info3["not_in_field"] == ["zz"])

    # 3. scoring
    s = O.score_race({"a": 0.6, "b": 0.4}, {"a": 0.8, "b": 0.2}, "a")
    check("log score = -ln(chance of the winner)", close(s["market_logscore"], -math.log(0.8)) and close(s["model_logscore"], -math.log(0.6)))
    check("Brier over all drivers", close(s["market_brier"], 0.04 + 0.04) and close(s["model_brier"], 0.16 + 0.16))
    check("favourite hit flags", s["model_top_pick_won"] and s["market_top_pick_won"])
    s2 = O.score_race({"a": 0.6, "b": 0.4}, {"a": 0.8, "b": 0.2}, "b")
    check("winner given no chance is floored, not infinite", math.isfinite(O.score_race({"a": 1.0, "b": 0.0}, {"a": 1.0, "b": 0.0}, "b")["model_logscore"]))
    check("favourite miss flags", not s2["model_top_pick_won"] and not s2["market_top_pick_won"])

    # 4. driver names
    known = {"carlos-sainz-jr", "kimi-antonelli", "nico-hulkenberg", "max-verstappen"}
    check("exact id", O.resolve_driver("kimi-antonelli", known) == "kimi-antonelli")
    check("name with capitals and spaces", O.resolve_driver("Kimi Antonelli", known) == "kimi-antonelli")
    check("Jr is handled either way", O.resolve_driver("Carlos Sainz", known) == "carlos-sainz-jr")
    check("surname only", O.resolve_driver("Verstappen", known) == "max-verstappen")
    check("accents", O.resolve_driver("Hülkenberg", known) == "nico-hulkenberg")
    check("unknown name is an error, not a guess", raises(O.resolve_driver, "Nobody Here", known))

    # 5. reading odds.csv
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "o.csv"
        f.write_text("race_id,stage,source,date,driver_id,odds\n"
                     "T-01,,s1,2030-01-01,Kimi Antonelli,+120\n"
                     "T-01,pre,s1,2030-01-01,max-verstappen,-150\n"
                     "T-01,pre,s1,2030-01-01,nico-hulkenberg,\n")
        df = O.load_odds(f, known)
        check("sign survives and decimal conversion is right", sorted(df.decimal.round(3)) == [1.667, 2.2], df.decimal.tolist())
        check("blank odds rows are skipped, blank stage means pre", len(df) == 2 and set(df.stage) == {"pre"})
        f.write_text("race_id,stage,source,date,driver_id,odds\nT-01,pre,s1,,max-verstappen,2.0\nT-01,pre,s1,,max-verstappen,3.0\n")
        check("same driver twice for one source is an error", raises(O.load_odds, f, known))
        f.write_text("race_id,stage,source,date,driver_id,odds\nT-01,later,s1,,max-verstappen,2.0\n")
        check("unknown stage is an error", raises(O.load_odds, f, known))
        f.write_text("race_id,stage,source,date,driver_id\nT-01,pre,s1,,max-verstappen\n")
        check("missing column is an error", raises(O.load_odds, f, known))

    # 6. the report on made-up races
    drivers = ["a", "b", "c", "d"]
    tracker = pd.DataFrame({"race_id": "T-01", "stage": "pre", "saved_at": "2030-01-01 00:00 UTC", "driver_id": drivers,
                            "p_win": [0.5, 0.3, 0.15, 0.05]})
    results = pd.DataFrame({"race_id": ["T-01"] * 4 + ["T-02"] * 4 + ["T-03"] * 4, "driver_id": drivers * 3,
                            "position_raw": ["2", "1", "3", "4"] + [""] * 8})
    rows = []
    for rid in ("T-01", "T-02", "T-03"):
        for d, o in zip(drivers, ["+100", "+200", "+500", "+1000"]):
            rows.append({"race_id": rid, "stage": "pre", "source": "s1", "date": "2030-01-01", "driver_id": d, "odds": o,
                         "decimal": O.to_decimal(o)})
    odds = pd.DataFrame(rows)
    # T-02 gets a model row too (not run yet); T-03 has no saved model prediction at all
    tracker = pd.concat([tracker, tracker.assign(race_id="T-02")], ignore_index=True)
    backtest = pd.DataFrame(columns=["race_id", "driver_id", "p_win_pre"])
    text, table = O.build_report(odds, results, tail=0.004, tracker=tracker, backtest=backtest)
    check("one race scored (the one with a result and a model)", len(table) == 1 and table.race_id.iloc[0] == "T-01", table)
    exp = (1 / 3.0) / (1 / 2.0 + 1 / 3.0 + 1 / 6.0 + 1 / 11.0)
    check("market chance of the winner b matches by hand", close(table.market_p_winner.iloc[0], exp), (table.market_p_winner.iloc[0], exp))
    check("model chance of the winner comes from the saved prediction", close(table.model_p_winner.iloc[0], 0.3))
    check("race not run yet is shown but not scored", "Race not run yet" in text)
    check("race with no saved model prediction says so", "Not compared" in text and "T-03" in text)
    check("tells the reader what one race can show", "says nothing about which is better" in text)

    # 7. the real odds.csv and data
    try:
        res = pd.read_csv("data/results.csv", dtype={"position_raw": str})
        real = O.load_odds("odds.csv", set(res.driver_id))
        txt, tab = O.build_report(real, res)
        check("real odds.csv: every driver name resolves and the report builds", len(txt) > 500)
        for (rid, st), g in real.groupby(["race_id", "stage"]):
            field = sorted(set(res[res.race_id == rid].driver_id)) or sorted(real[real.race_id == rid].driver_id)
            if rid == "2026-19":
                field = sorted(pd.read_csv("tracker/predictions.csv").query("race_id == @rid").driver_id.unique())
            pr, _ = O.market_chances([dict(zip(x.driver_id, x.decimal)) for _, x in g.groupby("source")], field)
            check(f"real {rid}: market chances add up to 1", close(sum(pr.values()), 1.0), sum(pr.values()))
        if "2026-18" in set(tab.race_id):
            r = tab[tab.race_id == "2026-18"].iloc[0]
            check("US GP 2026: winner is Antonelli and he is scored", r.winner == "kimi-antonelli")
    except FileNotFoundError as err:
        print("SKIP real-data check:", err)

    print("\nAll odds tests passed." if not FAILED else f"\n{len(FAILED)} FAILED: {FAILED}")
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
