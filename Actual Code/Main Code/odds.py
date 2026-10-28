#!/usr/bin/env python3
"""How does the model's win chance compare with the bookmakers'?

You type bookmaker odds for a race into odds.csv; this turns them into chances and sets them next
to the model's. For a race that has not been run it shows where model and market disagree. For a
race that has been run it scores both (how much chance each gave the real winner).

    python odds.py template 2026-19      write a blank odds sheet with this race's drivers
    python odds.py                       compare everything in odds.csv -> Predictions/odds_report.txt
    python odds.py --tail 0.01           same, assuming unlisted drivers have a 1% chance each

odds.csv columns:  race_id, stage, source, date, driver_id, odds
    stage   pre / fp / post: which model to compare with. Use the one that matches WHEN the odds were
            taken: before practice = pre, after practice = fp, after qualifying = post.
    source  any label for where the odds came from (one block of rows per source and stage).
    odds    American with a sign (+120, -150), fractional (5/2) or decimal (3.4). A plain number
            is decimal. Always write the + for American odds.

Things to know before reading the numbers:
  * Bookmaker prices add up to more than 100% (their margin). Each source is scaled down in
    proportion so it adds up to 100%. That is the simplest fix; it is not exact (long shots are
    usually priced shorter than their real chance).
  * Where several sources price a driver, their chances are averaged. A driver no source prices
    gets the same small chance each (--tail, default 0.4%, about 250/1). That is an assumption;
    the report prints how much it moves the favourite.
  * An optional "note" column is ignored; use it to record where a price came from.
  * A handful of races cannot show which forecaster is better. The scoring is there to be
    accumulated over time, and the report says so.
  * The model's chance comes from tracker/predictions.csv (saved before the race) or, for older
    races, reports/backtest_predictions.csv (model fitted on earlier seasons only).
"""
import argparse
import math
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ODDS_FILE = Path("odds.csv")
TRACKER = Path("tracker/predictions.csv")
BACKTEST = Path("reports/backtest_predictions.csv")
OUT_TXT = Path("Predictions/odds_report.txt")
OUT_CSV = Path("reports/odds_comparison.csv")
DEFAULT_TAIL = 0.004
STAGES = ("pre", "fp", "post")
HEADER = ["race_id", "stage", "source", "date", "driver_id", "odds"]


# ---------------------------------------------------------------- odds -> chances

def to_decimal(text):
    """'+120' / '-150' (American), '5/2' (fractional), '3.4' (decimal) -> decimal odds (> 1)."""
    s = str(text).strip().replace(",", ".")
    if not s or s.lower() == "nan":
        raise ValueError("empty odds")
    if s[0] in "+-" and re.fullmatch(r"[+-]\d+(\.\d+)?", s):
        a = float(s)
        if abs(a) < 100:
            raise ValueError(f"American odds must be at least 100 away from zero: {text}")
        return 1 + a / 100 if a > 0 else 1 + 100 / -a
    if "/" in s:
        top, bottom = s.split("/", 1)
        top, bottom = float(top), float(bottom)
        if bottom <= 0 or top <= 0:
            raise ValueError(f"bad fractional odds: {text}")
        return 1 + top / bottom
    d = float(s)
    if d <= 1:
        raise ValueError(f"decimal odds must be above 1: {text}")
    return d


def market_chances(listed, field, tail=DEFAULT_TAIL):
    """listed: {driver: decimal odds} for one source, or a list of such dicts; field: every driver.

    -> (chance per driver in `field`, adding to 1, info). A driver priced by one or more sources gets
    the average of 1/odds over the sources that price him; a driver nobody prices gets `tail`; then
    everything is scaled to add up to 1."""
    sources = [listed] if isinstance(listed, dict) else list(listed)
    raw, priced = {}, set()
    for d in field:
        vals = [1 / s[d] for s in sources if d in s]
        if vals:
            raw[d] = float(np.mean(vals))
            priced.add(d)
        else:
            raw[d] = tail
    total = sum(raw.values())
    probs = {d: v / total for d, v in raw.items()}
    n_tail = len(field) - len(priced)
    info = {"listed_sum": sum(raw[d] for d in priced), "n_listed": len(priced),
            "n_tail": n_tail, "tail_sum": tail * n_tail,
            "not_in_field": sorted({d for s in sources for d in s} - set(field))}
    return probs, info


# ---------------------------------------------------------------- scoring

def score_race(p_model, p_market, winner, floor=1e-6):
    """Both inputs {driver: chance} over the same drivers. Lower log score and Brier are better."""
    out = {}
    for name, p in (("model", p_model), ("market", p_market)):
        pw = max(p.get(winner, 0.0), floor)
        out[f"{name}_p_winner"] = pw
        out[f"{name}_logscore"] = -math.log(pw)
        out[f"{name}_brier"] = sum((v - (1.0 if d == winner else 0.0)) ** 2 for d, v in p.items())
        out[f"{name}_top_pick_won"] = max(p, key=p.get) == winner
    return out


# ---------------------------------------------------------------- reading things

def slug(name):
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def resolve_driver(raw, known):
    """Match a typed name to a driver id in `known` (ids like carlos-sainz-jr). Raises if unsure."""
    s = slug(raw)
    if s in known:
        return s
    for cand in (re.sub(r"-jr$", "", s), s + "-jr"):
        if cand in known:
            return cand
    hits = [k for k in known if k.endswith("-" + s) or s.endswith("-" + k)]
    if len(hits) == 1:
        return hits[0]
    raise ValueError(f"don't know the driver '{raw}' (use ids like kimi-antonelli; "
                     f"'python odds.py template RACE' lists them)")


def load_odds(path, known):
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [c for c in HEADER if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(missing)}")
    df = df[df["odds"].str.strip() != ""].copy()
    df["stage"] = df["stage"].str.strip().str.lower().replace("", "pre")
    bad = sorted(set(df["stage"]) - set(STAGES))
    if bad:
        raise ValueError(f"stage must be pre, fp or post, not: {', '.join(bad)}")
    df["driver_id"] = [resolve_driver(d, known) for d in df["driver_id"]]
    df["decimal"] = [to_decimal(o) for o in df["odds"]]
    dup = df[df.duplicated(["race_id", "stage", "source", "driver_id"], keep=False)]
    if len(dup):
        raise ValueError("the same driver appears twice for one source: "
                         + ", ".join(sorted(set(dup["race_id"] + " " + dup["source"] + " " + dup["driver_id"]))))
    return df


def model_chances(race_id, stage, tracker=None, backtest=None):
    """-> ({driver: p_win}, where it came from) or (None, reason)."""
    if tracker is None and TRACKER.exists():
        tracker = pd.read_csv(TRACKER)
    if tracker is not None and len(tracker):
        t = tracker[(tracker.race_id == race_id) & (tracker.stage == stage)]
        if len(t):
            return dict(zip(t.driver_id, t.p_win)), f"saved before the race ({t.saved_at.iloc[0]})"
    if backtest is None and BACKTEST.exists():
        backtest = pd.read_csv(BACKTEST)
    col = f"p_win_{stage}"
    if backtest is not None and col in backtest.columns:
        b = backtest[backtest.race_id == race_id]
        if len(b):
            return dict(zip(b.driver_id, b[col])), "back-test (model fitted on earlier seasons only)"
    return None, (f"no saved {stage}-stage model prediction for {race_id}; "
                  f"run predict.py for that race before it is run")


def race_winner(results, race_id):
    r = results[results.race_id == race_id]
    pos = pd.to_numeric(r["position_raw"], errors="coerce")
    w = r[pos == 1]
    return w["driver_id"].iloc[0] if len(w) else None


# ---------------------------------------------------------------- the report

def pct(x):
    return f"{100 * x:5.1f}%"


def build_report(odds, results, tail=DEFAULT_TAIL, tracker=None, backtest=None):
    """-> (text, table of scored races). Pure enough to test with small made-up frames."""
    lines = ["MODEL vs BOOKMAKER ODDS (win chance)", "=" * 40,
             f"Unlisted drivers assumed {100 * tail:.1f}% each. Each source is scaled to add up to 100%.", ""]
    scored = []
    for (race_id, stage), g in odds.groupby(["race_id", "stage"], sort=True):
        model, origin = model_chances(race_id, stage, tracker, backtest)
        lines += [f"{race_id}  [{stage} stage]", "-" * 40]
        if model is None:
            lines += [f"  Not compared: {origin}.", ""]
            continue
        field = sorted(model)
        winner = race_winner(results, race_id)
        per_source = {}
        for src, gs in g.groupby("source", sort=True):
            listed = dict(zip(gs.driver_id, gs.decimal))
            probs, info = market_chances(listed, field, tail)
            per_source[src] = (listed, probs, info, gs["date"].iloc[0])
        all_listed = [v[0] for v in per_source.values()]
        market, minfo = market_chances(all_listed, field, tail)

        lines.append(f"  Model: {origin}.")
        for src, (listed, probs, info, date) in per_source.items():
            note = (f"{info['n_listed']} drivers priced, prices add up to {pct(info['listed_sum']).strip()}")
            lines.append(f"  Source '{src}'{' (' + date + ')' if date else ''}: {note}.")
            if info["not_in_field"]:
                lines.append("    Ignored (not in this race's line-up): " + ", ".join(info["not_in_field"]))
        if minfo["n_tail"]:
            lines.append(f"  {minfo['n_tail']} drivers priced by no source are assumed {pct(tail).strip()} each "
                         f"({pct(minfo['tail_sum']).strip()} in total before scaling).")
        if len(per_source) > 1:
            lines.append("  'market' = average over the sources that price a driver, scaled to 100%; "
                         "a dash means that source did not price him.")
        lines.append("")
        head = f"  {'driver':<18}{'model':>8}{'market':>9}{'diff':>8}"
        if len(per_source) > 1:
            head += "   " + "  ".join(f"{s[:12]:>12}" for s in per_source)
        lines.append(head)
        for d in sorted(field, key=lambda x: -max(model[x], market[x]))[:10]:
            row = f"  {d.replace('-', ' ').title():<18}{pct(model[d]):>8}{pct(market[d]):>9}{100 * (model[d] - market[d]):>+7.1f}"
            if len(per_source) > 1:
                row += "   " + "  ".join(f"{pct(v[1][d]) if d in v[0] else '-':>12}" for v in per_source.values())
            if d == winner:
                row += "   <- won"
            lines.append(row)
        lines.append("  (top 10 by chance; 'diff' is model minus market in percentage points)")

        # how much does the tail assumption matter?
        if minfo["n_tail"]:
            lo = market_chances(all_listed, field, tail / 4)[0]
            hi = market_chances(all_listed, field, tail * 2.5)[0]
            fav = max(market, key=market.get)
            lines.append(f"  Tail check: with those drivers at {100 * tail / 4:.2f}% to {100 * tail * 2.5:.2f}% each, "
                         f"{fav.replace('-', ' ').title()} is {pct(hi[fav]).strip()} to {pct(lo[fav]).strip()}, "
                         f"against {pct(market[fav]).strip()} as assumed.")

        if winner is None:
            lines += ["  Race not run yet: nothing to score.", ""]
            continue
        s = score_race(model, market, winner)
        scored.append({"race_id": race_id, "stage": stage, "winner": winner, "n_sources": len(per_source), **s})
        lines += [f"  Winner: {winner.replace('-', ' ').title()}. Chance given: model {pct(s['model_p_winner']).strip()}, "
                  f"market {pct(s['market_p_winner']).strip()}.", ""]

    table = pd.DataFrame(scored)
    lines += ["SCORING (races already run)", "=" * 40]
    if table.empty:
        lines.append("No race with odds has a result yet.")
    else:
        lines.append(f"{'race':<9}{'stage':<6}{'winner':<18}{'model':>8}{'market':>9}   (chance given to the winner)")
        for r in table.itertuples():
            lines.append(f"{r.race_id:<9}{r.stage:<6}{r.winner.replace('-', ' ').title():<18}"
                         f"{pct(r.model_p_winner):>8}{pct(r.market_p_winner):>9}")
        n = len(table)
        lines += ["", f"Races scored: {n}",
                  f"  mean log score (lower is better): model {table.model_logscore.mean():.3f}, market {table.market_logscore.mean():.3f}",
                  f"  mean Brier score (lower is better): model {table.model_brier.mean():.3f}, market {table.market_brier.mean():.3f}",
                  f"  favourite won: model {int(table.model_top_pick_won.sum())} of {n}, market {int(table.market_top_pick_won.sum())} of {n}", ""]
        lines.append(f"With {n} race{'s' if n != 1 else ''} this says nothing about which is better. One surprise winner moves "
                     "these averages a lot. How many races it takes depends on the gap: in the 191-race back-test a big "
                     "gap (the after-qualifying model against grid order, about 0.3 per race on the log score) needed "
                     "roughly 70 races to show, while a gap of 0.01 would need over 1,000. Keep adding races, with odds "
                     "taken BEFORE each race, and read this again much later.")
    return "\n".join(lines) + "\n", table


def cmd_template(race_id, stage, source):
    t = pd.read_csv(TRACKER) if TRACKER.exists() else pd.DataFrame()
    t = t[t.race_id == race_id] if len(t) else t
    if len(t):
        drivers = list(t.drop_duplicates("driver_id").sort_values("p_win", ascending=False).driver_id)
    else:
        b = pd.read_csv(BACKTEST)
        drivers = list(b[b.race_id == race_id].driver_id)
    if not drivers:
        sys.exit(f"No driver list for {race_id}: run predict.py for that race first.")
    out = Path("Predictions") / f"odds_template_{race_id}.csv"
    out.parent.mkdir(exist_ok=True)
    pd.DataFrame({"race_id": race_id, "stage": stage, "source": source, "date": "",
                  "driver_id": drivers, "odds": ""}).to_csv(out, index=False)
    print(f"Blank odds sheet written to {out}\nFill in the odds column (leave a row blank to skip a driver), "
          f"add a date, and paste the rows into odds.csv.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="compare", choices=["compare", "template"])
    ap.add_argument("race", nargs="?", help="race id for 'template', e.g. 2026-19")
    ap.add_argument("--stage", default="pre", choices=STAGES, help="template: stage column to pre-fill")
    ap.add_argument("--source", default="my_bookmaker", help="template: source label to pre-fill")
    ap.add_argument("--tail", type=float, default=DEFAULT_TAIL, help="chance given to each unlisted driver")
    ap.add_argument("--odds", default=str(ODDS_FILE))
    ap.add_argument("--out", default=str(OUT_TXT))
    args = ap.parse_args()
    if args.command == "template":
        if not args.race:
            sys.exit("Say which race, e.g.  python odds.py template 2026-19")
        return cmd_template(args.race, args.stage, args.source)
    if not Path(args.odds).exists():
        sys.exit(f"{args.odds} not found.")
    results = pd.read_csv("data/results.csv", dtype={"position_raw": str})
    known = set(results.driver_id)
    try:
        odds = load_odds(args.odds, known)
    except ValueError as err:
        sys.exit(f"Problem in {args.odds}: {err}")
    text, table = build_report(odds, results, args.tail)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    if len(table):
        OUT_CSV.parent.mkdir(exist_ok=True)
        table.to_csv(OUT_CSV, index=False)
    print(f"Odds comparison written to {out}")


if __name__ == "__main__":
    main()
