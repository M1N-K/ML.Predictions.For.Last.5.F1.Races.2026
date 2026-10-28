# Ablation: do ratings and circuit kind help?

Walk-forward back-test; same settings for every variant. Differences are variant minus base, averaged over races, with a 95% interval from resampling whole races. **Clear** = the interval excludes zero.

## 2018-2026 (191 races)

| stage | variant | winner hit | podium overlap (of 3) | Spearman | MAE | win log loss | podium log loss |
|---|---|---|---|---|---|---|---|
| pre | base | 43.5% | 1.76 | 0.603 | 3.75 | 0.1216 | 0.2523 |
| pre | +ratings | 45.5% | 1.74 | 0.603 | 3.74 | 0.1212 | 0.2513 |
| pre | +circuit kind | 45.0% | 1.74 | 0.599 | 3.76 | 0.1212 | 0.2529 |
| pre | +both | 48.2% | 1.72 | 0.602 | 3.75 | 0.1210 | 0.2515 |
| post | base | 53.4% | 2.05 | 0.666 | 3.29 | 0.0986 | 0.2149 |
| post | +ratings | 53.9% | 2.03 | 0.663 | 3.31 | 0.0998 | 0.2165 |
| post | +circuit kind | 52.9% | 2.03 | 0.664 | 3.30 | 0.0994 | 0.2150 |
| post | +both | 52.4% | 2.03 | 0.663 | 3.31 | 0.1003 | 0.2149 |
| - | baseline: grid order | 54.5% | 2.07 | 0.628 | 3.46 | - | - |
| - | baseline: recent driver form | 44.0% | 1.63 | 0.584 | 3.85 | - | - |

Difference from base (variant - base):

| stage | variant | metric | difference | 95% interval | clear? | better? |
|---|---|---|---|---|---|---|
| pre | +ratings | spearman | +0.0001 | [-0.0043, +0.0045] | no | yes |
| pre | +ratings | mae_pos | -0.0041 | [-0.0338, +0.0267] | no | yes |
| pre | +ratings | win_logloss | -0.0005 | [-0.0022, +0.0012] | no | yes |
| pre | +ratings | podium_logloss | -0.0011 | [-0.0033, +0.0011] | no | yes |
| pre | +circuit kind | spearman | -0.0033 | [-0.0073, +0.0004] | no | no |
| pre | +circuit kind | mae_pos | +0.0118 | [-0.0125, +0.0383] | no | no |
| pre | +circuit kind | win_logloss | -0.0005 | [-0.0015, +0.0006] | no | yes |
| pre | +circuit kind | podium_logloss | +0.0005 | [-0.0016, +0.0034] | no | no |
| pre | +both | spearman | -0.0003 | [-0.0055, +0.0048] | no | no |
| pre | +both | mae_pos | +0.0013 | [-0.0322, +0.0363] | no | no |
| pre | +both | win_logloss | -0.0006 | [-0.0025, +0.0012] | no | yes |
| pre | +both | podium_logloss | -0.0008 | [-0.0031, +0.0014] | no | yes |
| post | +ratings | spearman | -0.0025 | [-0.0059, +0.0010] | no | no |
| post | +ratings | mae_pos | +0.0132 | [-0.0109, +0.0368] | no | no |
| post | +ratings | win_logloss | +0.0012 | [-0.0002, +0.0026] | no | no |
| post | +ratings | podium_logloss | +0.0017 | [-0.0007, +0.0058] | no | no |
| post | +circuit kind | spearman | -0.0021 | [-0.0053, +0.0012] | no | no |
| post | +circuit kind | mae_pos | +0.0116 | [-0.0135, +0.0364] | no | no |
| post | +circuit kind | win_logloss | +0.0008 | [-0.0001, +0.0018] | no | no |
| post | +circuit kind | podium_logloss | +0.0001 | [-0.0009, +0.0011] | no | no |
| post | +both | spearman | -0.0026 | [-0.0057, +0.0007] | no | no |
| post | +both | mae_pos | +0.0190 | [-0.0051, +0.0432] | no | no |
| post | +both | win_logloss | +0.0017 | [+0.0002, +0.0033] | yes | no |
| post | +both | podium_logloss | +0.0000 | [-0.0011, +0.0011] | no | no |

## 2023-2026 (88 races)

| stage | variant | winner hit | podium overlap (of 3) | Spearman | MAE | win log loss | podium log loss |
|---|---|---|---|---|---|---|---|
| pre | base | 42.0% | 1.66 | 0.622 | 3.67 | 0.1237 | 0.2674 |
| pre | +ratings | 44.3% | 1.66 | 0.620 | 3.67 | 0.1248 | 0.2655 |
| pre | +circuit kind | 44.3% | 1.61 | 0.615 | 3.69 | 0.1226 | 0.2659 |
| pre | +both | 46.6% | 1.61 | 0.622 | 3.65 | 0.1239 | 0.2651 |
| post | base | 62.5% | 2.02 | 0.695 | 3.12 | 0.0891 | 0.2137 |
| post | +ratings | 64.8% | 2.02 | 0.693 | 3.15 | 0.0907 | 0.2169 |
| post | +circuit kind | 61.4% | 2.02 | 0.695 | 3.12 | 0.0906 | 0.2132 |
| post | +both | 59.1% | 1.99 | 0.693 | 3.17 | 0.0908 | 0.2138 |
| - | baseline: grid order | 61.4% | 2.03 | 0.664 | 3.27 | - | - |
| - | baseline: recent driver form | 39.8% | 1.58 | 0.603 | 3.75 | - | - |

Difference from base (variant - base):

| stage | variant | metric | difference | 95% interval | clear? | better? |
|---|---|---|---|---|---|---|
| pre | +ratings | spearman | -0.0014 | [-0.0082, +0.0054] | no | no |
| pre | +ratings | mae_pos | +0.0011 | [-0.0418, +0.0448] | no | no |
| pre | +ratings | win_logloss | +0.0011 | [-0.0008, +0.0032] | no | no |
| pre | +ratings | podium_logloss | -0.0019 | [-0.0046, +0.0010] | no | yes |
| pre | +circuit kind | spearman | -0.0069 | [-0.0118, -0.0018] | yes | no |
| pre | +circuit kind | mae_pos | +0.0218 | [-0.0136, +0.0568] | no | no |
| pre | +circuit kind | win_logloss | -0.0011 | [-0.0028, +0.0007] | no | yes |
| pre | +circuit kind | podium_logloss | -0.0014 | [-0.0035, +0.0005] | no | yes |
| pre | +both | spearman | +0.0004 | [-0.0073, +0.0073] | no | yes |
| pre | +both | mae_pos | -0.0144 | [-0.0591, +0.0313] | no | yes |
| pre | +both | win_logloss | +0.0002 | [-0.0019, +0.0026] | no | no |
| pre | +both | podium_logloss | -0.0022 | [-0.0052, +0.0008] | no | yes |
| post | +ratings | spearman | -0.0017 | [-0.0075, +0.0039] | no | no |
| post | +ratings | mae_pos | +0.0268 | [-0.0122, +0.0648] | no | no |
| post | +ratings | win_logloss | +0.0016 | [-0.0001, +0.0033] | no | no |
| post | +ratings | podium_logloss | +0.0032 | [-0.0013, +0.0113] | no | no |
| post | +circuit kind | spearman | +0.0006 | [-0.0044, +0.0051] | no | yes |
| post | +circuit kind | mae_pos | -0.0053 | [-0.0390, +0.0298] | no | yes |
| post | +circuit kind | win_logloss | +0.0015 | [-0.0001, +0.0031] | no | no |
| post | +circuit kind | podium_logloss | -0.0006 | [-0.0019, +0.0007] | no | yes |
| post | +both | spearman | -0.0018 | [-0.0066, +0.0028] | no | no |
| post | +both | mae_pos | +0.0425 | [+0.0055, +0.0811] | yes | no |
| post | +both | win_logloss | +0.0016 | [-0.0001, +0.0035] | no | no |
| post | +both | podium_logloss | +0.0000 | [-0.0014, +0.0015] | no | no |

## By season (base vs +both)

| stage | variant | year | winner hit | Spearman |
|---|---|---|---|---|
| post | +both | 2018 | 52.4% | 0.612 |
| post | +both | 2019 | 33.3% | 0.655 |
| post | +both | 2020 | 64.7% | 0.620 |
| post | +both | 2021 | 40.9% | 0.685 |
| post | +both | 2022 | 45.5% | 0.612 |
| post | +both | 2023 | 86.4% | 0.659 |
| post | +both | 2024 | 50.0% | 0.739 |
| post | +both | 2025 | 45.8% | 0.673 |
| post | +both | 2026 | 55.6% | 0.698 |
| post | base | 2018 | 52.4% | 0.618 |
| post | base | 2019 | 28.6% | 0.664 |
| post | base | 2020 | 58.8% | 0.615 |
| post | base | 2021 | 45.5% | 0.682 |
| post | base | 2022 | 45.5% | 0.620 |
| post | base | 2023 | 86.4% | 0.661 |
| post | base | 2024 | 45.8% | 0.741 |
| post | base | 2025 | 54.2% | 0.679 |
| post | base | 2026 | 66.7% | 0.694 |
| pre | +both | 2018 | 47.6% | 0.568 |
| pre | +both | 2019 | 47.6% | 0.611 |
| pre | +both | 2020 | 29.4% | 0.546 |
| pre | +both | 2021 | 50.0% | 0.627 |
| pre | +both | 2022 | 68.2% | 0.569 |
| pre | +both | 2023 | 81.8% | 0.622 |
| pre | +both | 2024 | 37.5% | 0.675 |
| pre | +both | 2025 | 37.5% | 0.561 |
| pre | +both | 2026 | 27.8% | 0.632 |
| pre | base | 2018 | 47.6% | 0.575 |
| pre | base | 2019 | 28.6% | 0.609 |
| pre | base | 2020 | 29.4% | 0.540 |
| pre | base | 2021 | 45.5% | 0.618 |
| pre | base | 2022 | 68.2% | 0.581 |
| pre | base | 2023 | 68.2% | 0.620 |
| pre | base | 2024 | 37.5% | 0.668 |
| pre | base | 2025 | 37.5% | 0.559 |
| pre | base | 2026 | 22.2% | 0.646 |
