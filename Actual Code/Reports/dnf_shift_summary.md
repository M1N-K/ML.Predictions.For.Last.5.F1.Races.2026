# Retirement chance: shift to the recent retirement rate

After fitting, all retirement probabilities are shifted (logit scale) so their average over the last k training seasons matches the real rate there. Log loss per race (lower is better), averaged over the before-the-weekend and after-qualifying models.

| window | 2018-22 | 2023 onward | 2023 onward, difference from none (95% interval) | predicted / observed, 2018-26 |
|---|---|---|---|---|
| none | 0.4370 | 0.3829 | +0.0000 [+0.0000, +0.0000] | 0.174 / 0.148 |
| 1 seasons | 0.4369 | 0.3819 | -0.0011 [-0.0028, +0.0006] | 0.162 / 0.148 |
| 2 seasons | 0.4365 | 0.3823 | -0.0007 [-0.0021, +0.0008] | 0.165 / 0.148 |
| 3 seasons | 0.4363 | 0.3825 | -0.0004 [-0.0016, +0.0007] | 0.167 / 0.148 |
| 5 seasons | 0.4371 | 0.3823 | -0.0007 [-0.0016, +0.0003] | 0.170 / 0.148 |

Rule outcome: **keep as is** (needs the best 2018-22 score and a clear gain, interval below zero, on 2023 onward).

## By season (post stage, predicted / observed)

| window | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| none | 0.234/0.195 | 0.225/0.138 | 0.160/0.163 | 0.163/0.124 | 0.191/0.167 | 0.172/0.138 | 0.141/0.105 | 0.127/0.107 | 0.157/0.195 |
| 1 seasons | 0.243/0.195 | 0.221/0.138 | 0.135/0.163 | 0.162/0.124 | 0.170/0.167 | 0.159/0.138 | 0.124/0.105 | 0.105/0.107 | 0.142/0.195 |
| 2 seasons | 0.232/0.195 | 0.231/0.138 | 0.150/0.163 | 0.147/0.124 | 0.187/0.167 | 0.156/0.138 | 0.131/0.105 | 0.111/0.107 | 0.141/0.195 |
| 3 seasons | 0.235/0.195 | 0.224/0.138 | 0.157/0.163 | 0.156/0.124 | 0.178/0.167 | 0.163/0.138 | 0.130/0.105 | 0.116/0.107 | 0.142/0.195 |
| 5 seasons | 0.235/0.195 | 0.226/0.138 | 0.161/0.163 | 0.163/0.124 | 0.188/0.167 | 0.163/0.138 | 0.130/0.105 | 0.120/0.107 | 0.146/0.195 |
