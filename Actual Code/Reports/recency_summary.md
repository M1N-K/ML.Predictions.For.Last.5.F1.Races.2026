# Recency weighting: should recent seasons count more?

A training race counts half as much for every `half-life` years it is older than the newest one. Walk-forward back-test; half-life chosen on 2018-2022 and judged on 2023 onward. Averages over the before-the-weekend and after-qualifying stages.

## finishing order (Spearman, higher is better)

| half-life | 2018-22 | 2023 onward | 2023 onward, difference from none (95% interval) |
|---|---|---|---|
| none | 0.6139 | 0.6580 | +0.0000 [+0.0000, +0.0000] |
| 1.5y | 0.6120 | 0.6382 | -0.0198 [-0.0262, -0.0133] |
| 3y | 0.6123 | 0.6480 | -0.0100 [-0.0145, -0.0056] |
| 6y | 0.6126 | 0.6544 | -0.0036 [-0.0070, -0.0003] |

Rule outcome: **keep unweighted**.

## win and podium chances (log loss, lower is better)

| half-life | 2018-22 | 2023 onward | 2023 onward, difference from none (95% interval) |
|---|---|---|---|
| none | 0.1705 | 0.1735 | +0.0000 [+0.0000, +0.0000] |
| 1.5y | 0.1723 | 0.1773 | +0.0038 [+0.0012, +0.0067] |
| 3y | 0.1713 | 0.1740 | +0.0005 [-0.0009, +0.0019] |
| 6y | 0.1712 | 0.1735 | -0.0000 [-0.0010, +0.0009] |

Rule outcome: **keep unweighted**.

## retirement chance (log loss, lower is better)

| half-life | 2018-22 | 2023 onward | 2023 onward, difference from none (95% interval) |
|---|---|---|---|
| none | 0.4370 | 0.3829 | +0.0000 [+0.0000, +0.0000] |
| 1.5y | 0.4345 | 0.3889 | +0.0059 [+0.0028, +0.0092] |
| 3y | 0.4334 | 0.3850 | +0.0021 [-0.0001, +0.0043] |
| 6y | 0.4349 | 0.3834 | +0.0005 [-0.0009, +0.0019] |

Rule outcome: **keep unweighted**.

## Retirement calibration by season (mean predicted / observed)

| half-life | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | 2018-26 average |
|---|---|---|---|---|---|---|---|---|---|---|
| none | 0.234/0.195 | 0.225/0.138 | 0.160/0.163 | 0.163/0.124 | 0.191/0.167 | 0.172/0.138 | 0.141/0.105 | 0.127/0.107 | 0.157/0.195 | 0.174/0.148 |
| 1.5y | 0.215/0.195 | 0.203/0.138 | 0.159/0.163 | 0.145/0.124 | 0.162/0.167 | 0.156/0.138 | 0.134/0.105 | 0.115/0.107 | 0.142/0.195 | 0.159/0.148 |
| 3y | 0.224/0.195 | 0.214/0.138 | 0.158/0.163 | 0.155/0.124 | 0.173/0.167 | 0.161/0.138 | 0.134/0.105 | 0.120/0.107 | 0.148/0.195 | 0.165/0.148 |
| 6y | 0.227/0.195 | 0.214/0.138 | 0.158/0.163 | 0.156/0.124 | 0.180/0.167 | 0.166/0.138 | 0.138/0.105 | 0.123/0.107 | 0.156/0.195 | 0.169/0.148 |
