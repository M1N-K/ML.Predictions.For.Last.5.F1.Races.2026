#!/usr/bin/env python3
"""Draw reports/calibration.png from reports/calibration.csv (written by train.py).

One panel per thing the model predicts. A perfectly calibrated model lies on the dotted diagonal:
when it says "30%", that happens 30% of the time. Bins with fewer than 20 cases are left out.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
STAGES = [("pre", "Before the weekend", "#2a78d6", "o"),
          ("fp", "After practice", "#eb6834", "s"),
          ("post", "After qualifying", "#1baf7a", "^")]
PANELS = [("win", "Win chance"), ("podium", "Podium chance"), ("dnf", "Retirement chance")]
MIN_CASES = 20


def main():
    cal = pd.read_csv("reports/calibration.csv")
    fig, axes = plt.subplots(1, 3, figsize=(13, 5.2), facecolor=SURFACE)
    for ax, (target, title) in zip(axes, PANELS):
        d = cal[(cal.target == target) & (cal.n >= MIN_CASES)]
        top = max(d.mean_p.max(), d.observed.max()) * 1.08
        ax.set_facecolor(SURFACE)
        ax.plot([0, top], [0, top], color=INK2, lw=1, ls=":", zorder=1)
        for stage, label, color, marker in STAGES:
            s = d[d.stage == stage].sort_values("mean_p")
            ax.plot(s.mean_p, s.observed, color=color, lw=2, marker=marker, ms=7, mec=SURFACE, mew=1.5,
                    zorder=3, label=label)
            if len(s) and target == "win":                      # direct label at the line end
                ax.annotate(label.split()[-1] if stage != "pre" else "weekend", (s.mean_p.iloc[-1], s.observed.iloc[-1]),
                            xytext=(6, -3 if stage == "post" else 5), textcoords="offset points",
                            fontsize=8.5, color=INK2)
        ax.set_xlim(0, top)
        ax.set_ylim(0, top)
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(title, loc="left", fontsize=12, color=INK, fontweight="bold", pad=10)
        ax.set_xlabel("What the model said", fontsize=10, color=INK2)
        ax.set_ylabel("How often it happened" if target == "win" else "", fontsize=10, color=INK2)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax.grid(color=GRID, lw=0.8)
        ax.tick_params(colors=INK2, labelsize=9, length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=3, frameon=False, fontsize=10,
               labelcolor=INK2, bbox_to_anchor=(0.99, 0.945))
    fig.suptitle("Do the model's percentages match reality?  (88 races, 2023-2026, never seen in training)",
                 x=0.012, y=0.985, ha="left", fontsize=13, color=INK, fontweight="bold")
    fig.text(0.012, 0.915, "On the dotted line = perfectly calibrated. Bins with fewer than 20 cases are hidden.",
             fontsize=9.5, color=INK2)
    fig.tight_layout(rect=(0, 0.02, 1, 0.88))
    out = Path("reports/calibration.png")
    fig.savefig(out, dpi=160, facecolor=SURFACE, bbox_inches="tight", pad_inches=0.25)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
