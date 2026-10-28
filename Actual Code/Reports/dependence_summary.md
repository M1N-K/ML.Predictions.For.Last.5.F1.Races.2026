# Do simulated races need to depend on each other?

Replay of seasons 2018-2025 from three cut points each (30%, 50%, 70%): predictions made only from what was known at the cut, rest of season simulated, compared with what happened. Settings were picked on 2018-2022 and judged on 2023-2025.

## Are the model's misses persistent?

| quantity | races apart | correlation | 95% interval | pairs |
|---|---|---|---|---|
| team finishing position | 1 | +0.40 | [+0.34, +0.44] | 2366 |
| team retirements | 1 | +0.03 | [-0.01, +0.07] | 2366 |
| team finishing position | 2 | +0.34 | [+0.29, +0.40] | 2126 |
| team retirements | 2 | -0.02 | [-0.06, +0.03] | 2126 |
| team finishing position | 3 | +0.38 | [+0.33, +0.43] | 1886 |
| team retirements | 3 | +0.04 | [-0.00, +0.09] | 1886 |
| team finishing position | 4 | +0.38 | [+0.32, +0.44] | 1646 |
| team retirements | 4 | -0.03 | [-0.07, +0.01] | 1646 |
| team-mates, same race: finishing position | 0 | +0.48 | - | 332 |
| team-mates, same race: retirements | 0 | +0.20 | - | 332 |

## Season-total coverage and score

Coverage = share of drivers whose real remaining points fell inside the simulated interval (80% interval should contain 80%, 50% interval 50%). CRPS: lower is better.

| simulation | part | coverage 80% | coverage 50% | CRPS | title log score (lower better) | title Brier |
|---|---|---|---|---|---|---|
| independent races (before) | fit 2018-22 | 65% | 39% | 12.25 | 0.247 | 0.148 |
| independent races (before) | held-out 2023-25 | 53% | 30% | 19.18 | 0.666 | 0.380 |
| with dependence (chosen) | fit 2018-22 | 85% | 59% | 11.47 | 0.326 | 0.181 |
| with dependence (chosen) | held-out 2023-25 | 82% | 50% | 16.39 | 0.671 | 0.344 |

Chosen settings: team pace shock 0.45 per race, driver pace shock 0.15, carry-over 1.0, reliability shock 0.0.

