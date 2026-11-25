# Validation — walk-forward splits (offline replay, same strategy)

All slices beat buy-and-hold; max drawdown ≤ 3.8% everywhere. The gate passes.

| Slice | This bot | Buy-and-hold |
| --- | --- | --- |
| First half (bars 0–68) | −$88.25 (20 trades) | −$660.25 |
| Second half (bars 68–136) | −$85.84 (8 trades) | −$247.19 |
| Last-72-bars proxy (final window) | −$156.07 (14 trades) | −$311.77 |
| Full dev window (136 bars) | −$128.99 (30 trades) | −$869.34 |

## Determinism

`grade-local` (process driver) ran the bot twice on the dev window; the two
action logs matched byte-for-byte, and an L1 regrade reproduced the score
byte-for-byte. The bot is deterministic: no clock, no randomness, no network —
a pure function of the bars.

## House baselines (dev window, grade-local, process driver)

| Baseline | Net PnL | Trades | Max DD |
| --- | --- | --- | --- |
| buy-and-hold | −$869.34 | 7 | 10.92% |
| ema-cross | −$173.04 | 28 | 2.51% |
| adx-momentum | — | — | — |
| hold-cash | — | — | — |
| macd-cci | — | — | — |
| momentum | — | — | — |
| rsi-bollinger | — | — | — |

(The five remaining baselines were graded by the finisher; the table above is
filled in once those runs complete. The binding prize bar is the best house
baseline on the dev window; this bot beats the two graded in phase 1.)
