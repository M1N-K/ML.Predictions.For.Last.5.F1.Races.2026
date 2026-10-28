# Backtest (walk-forward by season)

Test races: 191 (2018: 21, 2019: 21, 2020: 17, 2021: 22, 2022: 22, 2023: 22, 2024: 24, 2025: 24, 2026: 18). For each season the models were trained only on earlier seasons.

Settings were chosen on 2022, so 2022 and the seasons before it are not a clean test of those choices. The 2023-2026 table (88 races) is the one nothing was tuned on; the longer table shows whether the picture holds on more history.

## Finishing-order quality, 2018-2026 (mean per race, 191 races)

| model | winner hit | podium overlap (of 3) | top-10 overlap | Spearman | MAE (places) |
|---|---|---|---|---|---|
| post (after qualifying) | 53.4% | 2.05 | 7.84 | 0.666 | 3.29 |
| post, first version | 55.0% | 2.02 | 7.80 | 0.664 | 3.32 |
| baseline: grid order | 54.5% | 2.07 | 7.64 | 0.628 | 3.46 |
| fp (after practice) | 46.6% | 1.77 | 7.58 | 0.626 | 3.62 |
| pre (before the weekend) | 43.5% | 1.76 | 7.46 | 0.603 | 3.75 |
| pre, first version | 47.1% | 1.78 | 7.45 | 0.605 | 3.73 |
| baseline: recent driver form | 44.0% | 1.63 | 7.39 | 0.584 | 3.85 |

## Finishing-order quality, 2023-2026 (never used for any choice, 88 races)

| model | winner hit | podium overlap (of 3) | top-10 overlap | Spearman | MAE (places) |
|---|---|---|---|---|---|
| post (after qualifying) | 62.5% | 2.02 | 8.02 | 0.695 | 3.12 |
| post, first version | 65.9% | 1.94 | 7.97 | 0.693 | 3.15 |
| baseline: grid order | 61.4% | 2.03 | 7.82 | 0.664 | 3.27 |
| fp (after practice) | 44.3% | 1.62 | 7.69 | 0.632 | 3.61 |
| pre (before the weekend) | 42.0% | 1.66 | 7.64 | 0.622 | 3.67 |
| pre, first version | 42.0% | 1.65 | 7.64 | 0.622 | 3.67 |
| baseline: recent driver form | 39.8% | 1.58 | 7.53 | 0.603 | 3.75 |

## Is the improvement real? (paired difference over the same races, 95% interval)

A difference only counts as clear if its interval excludes zero.

| window | A | B | metric | A - B | 95% interval | clear? |
|---|---|---|---|---|---|---|
| 2018-2026 | post (after qualifying) | post, first version | spearman | +0.002 | [-0.004, +0.008] | no |
| 2018-2026 | post (after qualifying) | post, first version | winner_hit | -0.016 | [-0.068, +0.031] | no |
| 2018-2026 | post (after qualifying) | post, first version | mae_pos | -0.031 | [-0.071, +0.007] | no |
| 2018-2026 | post (after qualifying) | baseline: grid order | spearman | +0.038 | [+0.022, +0.054] | yes |
| 2018-2026 | post (after qualifying) | baseline: grid order | winner_hit | -0.010 | [-0.079, +0.058] | no |
| 2018-2026 | post (after qualifying) | baseline: grid order | mae_pos | -0.171 | [-0.271, -0.072] | yes |
| 2018-2026 | fp (after practice) | pre (before the weekend) | spearman | +0.023 | [+0.011, +0.034] | yes |
| 2018-2026 | fp (after practice) | pre (before the weekend) | winner_hit | +0.031 | [-0.037, +0.094] | no |
| 2018-2026 | fp (after practice) | pre (before the weekend) | mae_pos | -0.129 | [-0.200, -0.058] | yes |
| 2018-2026 | fp (after practice) | pre, first version | spearman | +0.020 | [+0.008, +0.032] | yes |
| 2018-2026 | fp (after practice) | pre, first version | winner_hit | -0.005 | [-0.058, +0.047] | no |
| 2018-2026 | fp (after practice) | pre, first version | mae_pos | -0.116 | [-0.189, -0.043] | yes |
| 2018-2026 | pre (before the weekend) | pre, first version | spearman | -0.003 | [-0.007, +0.002] | no |
| 2018-2026 | pre (before the weekend) | pre, first version | winner_hit | -0.037 | [-0.089, +0.016] | no |
| 2018-2026 | pre (before the weekend) | pre, first version | mae_pos | +0.013 | [-0.018, +0.044] | no |
| 2018-2026 | pre (before the weekend) | baseline: recent driver form | spearman | +0.019 | [+0.007, +0.032] | yes |
| 2018-2026 | pre (before the weekend) | baseline: recent driver form | winner_hit | -0.005 | [-0.084, +0.079] | no |
| 2018-2026 | pre (before the weekend) | baseline: recent driver form | mae_pos | -0.101 | [-0.176, -0.029] | yes |
| 2023-2026 | post (after qualifying) | post, first version | spearman | +0.002 | [-0.005, +0.010] | no |
| 2023-2026 | post (after qualifying) | post, first version | winner_hit | -0.034 | [-0.102, +0.034] | no |
| 2023-2026 | post (after qualifying) | post, first version | mae_pos | -0.023 | [-0.083, +0.035] | no |
| 2023-2026 | post (after qualifying) | baseline: grid order | spearman | +0.030 | [+0.010, +0.051] | yes |
| 2023-2026 | post (after qualifying) | baseline: grid order | winner_hit | +0.011 | [-0.080, +0.102] | no |
| 2023-2026 | post (after qualifying) | baseline: grid order | mae_pos | -0.146 | [-0.285, -0.005] | yes |
| 2023-2026 | fp (after practice) | pre (before the weekend) | spearman | +0.011 | [-0.004, +0.025] | no |
| 2023-2026 | fp (after practice) | pre (before the weekend) | winner_hit | +0.023 | [-0.057, +0.102] | no |
| 2023-2026 | fp (after practice) | pre (before the weekend) | mae_pos | -0.053 | [-0.143, +0.036] | no |
| 2023-2026 | fp (after practice) | pre, first version | spearman | +0.011 | [-0.004, +0.025] | no |
| 2023-2026 | fp (after practice) | pre, first version | winner_hit | +0.023 | [-0.045, +0.091] | no |
| 2023-2026 | fp (after practice) | pre, first version | mae_pos | -0.053 | [-0.143, +0.042] | no |
| 2023-2026 | pre (before the weekend) | pre, first version | spearman | -0.000 | [-0.006, +0.006] | no |
| 2023-2026 | pre (before the weekend) | pre, first version | winner_hit | +0.000 | [-0.068, +0.068] | no |
| 2023-2026 | pre (before the weekend) | pre, first version | mae_pos | -0.000 | [-0.040, +0.041] | no |
| 2023-2026 | pre (before the weekend) | baseline: recent driver form | spearman | +0.018 | [+0.001, +0.035] | yes |
| 2023-2026 | pre (before the weekend) | baseline: recent driver form | winner_hit | +0.023 | [-0.102, +0.148] | no |
| 2023-2026 | pre (before the weekend) | baseline: recent driver form | mae_pos | -0.082 | [-0.181, +0.022] | no |

## By season

| model | year | winner hit | podium overlap (of 3) | Spearman | MAE |
|---|---|---|---|---|---|
| post (after qualifying) | 2018 | 52.4% | 1.95 | 0.618 | 3.63 |
| post (after qualifying) | 2019 | 28.6% | 2.29 | 0.664 | 3.36 |
| post (after qualifying) | 2020 | 58.8% | 2.00 | 0.615 | 3.59 |
| post (after qualifying) | 2021 | 45.5% | 2.09 | 0.682 | 3.15 |
| post (after qualifying) | 2022 | 45.5% | 2.00 | 0.620 | 3.49 |
| post (after qualifying) | 2023 | 86.4% | 1.95 | 0.661 | 3.27 |
| post (after qualifying) | 2024 | 45.8% | 1.92 | 0.741 | 2.87 |
| post (after qualifying) | 2025 | 54.2% | 2.25 | 0.679 | 3.15 |
| post (after qualifying) | 2026 | 66.7% | 1.94 | 0.694 | 3.25 |
| post, first version | 2018 | 38.1% | 2.05 | 0.609 | 3.70 |
| post, first version | 2019 | 42.9% | 2.29 | 0.660 | 3.40 |
| post, first version | 2020 | 52.9% | 2.00 | 0.605 | 3.69 |
| post, first version | 2021 | 45.5% | 2.09 | 0.689 | 3.16 |
| post, first version | 2022 | 50.0% | 2.00 | 0.624 | 3.48 |
| post, first version | 2023 | 86.4% | 1.82 | 0.676 | 3.23 |
| post, first version | 2024 | 54.2% | 1.92 | 0.739 | 2.86 |
| post, first version | 2025 | 62.5% | 2.12 | 0.662 | 3.27 |
| post, first version | 2026 | 61.1% | 1.89 | 0.691 | 3.27 |
| baseline: grid order | 2018 | 47.6% | 2.10 | 0.574 | 3.87 |
| baseline: grid order | 2019 | 38.1% | 2.29 | 0.627 | 3.48 |
| baseline: grid order | 2020 | 58.8% | 2.06 | 0.608 | 3.70 |
| baseline: grid order | 2021 | 54.5% | 2.14 | 0.654 | 3.17 |
| baseline: grid order | 2022 | 45.5% | 1.91 | 0.525 | 3.95 |
| baseline: grid order | 2023 | 63.6% | 1.95 | 0.595 | 3.69 |
| baseline: grid order | 2024 | 45.8% | 2.00 | 0.732 | 2.86 |
| baseline: grid order | 2025 | 66.7% | 2.25 | 0.647 | 3.34 |
| baseline: grid order | 2026 | 72.2% | 1.89 | 0.682 | 3.22 |
| fp (after practice) | 2018 | 57.1% | 1.76 | 0.606 | 3.82 |
| fp (after practice) | 2019 | 38.1% | 2.00 | 0.639 | 3.60 |
| fp (after practice) | 2020 | 52.9% | 2.06 | 0.606 | 3.71 |
| fp (after practice) | 2021 | 36.4% | 2.14 | 0.644 | 3.35 |
| fp (after practice) | 2022 | 59.1% | 1.59 | 0.601 | 3.65 |
| fp (after practice) | 2023 | 81.8% | 1.55 | 0.603 | 3.74 |
| fp (after practice) | 2024 | 29.2% | 1.54 | 0.666 | 3.47 |
| fp (after practice) | 2025 | 33.3% | 1.79 | 0.596 | 3.75 |
| fp (after practice) | 2026 | 33.3% | 1.61 | 0.672 | 3.48 |
| pre (before the weekend) | 2018 | 47.6% | 1.76 | 0.575 | 3.93 |
| pre (before the weekend) | 2019 | 28.6% | 1.95 | 0.609 | 3.73 |
| pre (before the weekend) | 2020 | 29.4% | 1.88 | 0.540 | 4.13 |
| pre (before the weekend) | 2021 | 45.5% | 2.09 | 0.618 | 3.56 |
| pre (before the weekend) | 2022 | 68.2% | 1.55 | 0.581 | 3.80 |
| pre (before the weekend) | 2023 | 68.2% | 1.59 | 0.620 | 3.63 |
| pre (before the weekend) | 2024 | 37.5% | 1.62 | 0.668 | 3.46 |
| pre (before the weekend) | 2025 | 37.5% | 1.88 | 0.559 | 3.94 |
| pre (before the weekend) | 2026 | 22.2% | 1.50 | 0.646 | 3.62 |
| pre, first version | 2018 | 47.6% | 1.86 | 0.572 | 3.93 |
| pre, first version | 2019 | 47.6% | 1.90 | 0.603 | 3.78 |
| pre, first version | 2020 | 64.7% | 2.06 | 0.554 | 4.02 |
| pre, first version | 2021 | 31.8% | 2.09 | 0.637 | 3.49 |
| pre, first version | 2022 | 68.2% | 1.59 | 0.583 | 3.79 |
| pre, first version | 2023 | 81.8% | 1.59 | 0.616 | 3.66 |
| pre, first version | 2024 | 33.3% | 1.62 | 0.669 | 3.42 |
| pre, first version | 2025 | 29.2% | 1.96 | 0.566 | 3.94 |
| pre, first version | 2026 | 22.2% | 1.33 | 0.639 | 3.65 |
| baseline: recent driver form | 2018 | 52.4% | 1.81 | 0.529 | 4.20 |
| baseline: recent driver form | 2019 | 47.6% | 1.81 | 0.597 | 3.85 |
| baseline: recent driver form | 2020 | 64.7% | 1.65 | 0.542 | 4.06 |
| baseline: recent driver form | 2021 | 27.3% | 1.50 | 0.612 | 3.67 |
| baseline: recent driver form | 2022 | 50.0% | 1.64 | 0.549 | 3.93 |
| baseline: recent driver form | 2023 | 86.4% | 1.64 | 0.600 | 3.70 |
| baseline: recent driver form | 2024 | 25.0% | 1.54 | 0.668 | 3.38 |
| baseline: recent driver form | 2025 | 29.2% | 1.83 | 0.520 | 4.19 |
| baseline: recent driver form | 2026 | 16.7% | 1.22 | 0.633 | 3.71 |

## Probability quality (lower is better)

| target | model | log loss | Brier |
|---|---|---|---|
| dnf | baseline: average rate | 0.4200 | 0.1259 |
| dnf | fp | 0.4127 | 0.1245 |
| dnf | post | 0.4108 | 0.1240 |
| dnf | pre | 0.4146 | 0.1252 |
| podium | baseline: grid slot frequency | 0.2377 | 0.0681 |
| podium | baseline: uniform | 0.4219 | 0.1272 |
| podium | fp | 0.2443 | 0.0775 |
| podium | post | 0.2142 | 0.0656 |
| podium | post_v1 | 0.2141 | 0.0656 |
| podium | pre | 0.2517 | 0.0798 |
| podium | pre_v1 | 0.2518 | 0.0797 |
| win | baseline: grid slot frequency | 0.1160 | 0.0320 |
| win | baseline: uniform | 0.1981 | 0.0474 |
| win | fp | 0.1184 | 0.0346 |
| win | post | 0.0984 | 0.0291 |
| win | post_v1 | 0.0987 | 0.0292 |
| win | pre | 0.1216 | 0.0348 |
| win | pre_v1 | 0.1213 | 0.0347 |

## Calibration (do predicted chances match how often things happen?)

ECE = average gap between predicted and observed frequency (0 is perfect).

| target | stage | ECE | mean predicted | mean observed |
|---|---|---|---|---|
| win | pre | 0.009 | 0.050 | 0.050 |
| win | fp | 0.008 | 0.050 | 0.050 |
| win | post | 0.006 | 0.050 | 0.050 |
| podium | pre | 0.009 | 0.150 | 0.150 |
| podium | fp | 0.009 | 0.150 | 0.150 |
| podium | post | 0.012 | 0.150 | 0.150 |
| dnf | pre | 0.027 | 0.173 | 0.146 |
| dnf | fp | 0.027 | 0.173 | 0.146 |
| dnf | post | 0.028 | 0.174 | 0.146 |

Would a simple recalibration (fit on 2018-2023, tested on 2024-26) help? Log loss:

| target | stage | as is | recalibrated |
|---|---|---|---|
| win | pre | 0.1406 | 0.1417 |
| win | fp | 0.1358 | 0.1374 |
| win | post | 0.0989 | 0.0976 |
| podium | pre | 0.2570 | 0.2579 |
| podium | fp | 0.2498 | 0.2505 |
| podium | post | 0.2059 | 0.2071 |

## Simulation check (how random the championship simulation makes each race)

The simulation's randomness setting was fitted on the back-test so that simulated points and win chances match what really happened.

| stage | setting | points error (MSE) | win log loss, simulation | win log loss, classifier | top pick wins: simulated | top pick wins: actual |
|---|---|---|---|---|---|---|
| pre | 0.80 | 25.03 | 0.1257 | 0.1216 | 39.4% | 43.5% |
| fp | 0.70 | 23.11 | 0.1184 | 0.1184 | 40.4% | 46.6% |
| post | 0.50 | 19.73 | 0.1030 | 0.0984 | 51.1% | 53.4% |
