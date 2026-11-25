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

All 7 graded by the finisher (buy-and-hold and ema-cross were also graded in
phase 1; the other five were graded by the finisher). L1 reproduced: true for
every baseline. `result_sha256` recorded per baseline in the grade-local JSONs
under `/tmp/gorun-*.json`.

| Baseline | Net PnL | Trades | Max DD | Fees |
| --- | --- | --- | --- | --- |
| macd-cci | −$20.22 | 17 | 2.46% | $28.56 |
| rsi-bollinger | −$56.49 | 8 | 5.16% | $19.95 |
| adx-momentum | −$114.42 | 11 | 1.38% | $19.81 |
| **This bot** | **−$128.99** | **30** | **2.13%** | **$42.55** |
| ema-cross | −$173.04 | 28 | 2.51% | — |
| momentum | −$268.23 | 19 | 5.66% | $54.59 |
| buy-and-hold | −$869.34 | 7 | 10.92% | $19.14 |
| hold-cash | $0.00 | 0 | 0.00% | $0.00 (non-compliant: 0 trades, fails the ≥8-trades guardrail) |

The best house baseline on the dev window is **macd-cci at −$20.22**; this bot
is 4th of 7 on dev. It beats buy-and-hold by +$740.35 (the stated bar), beats
ema-cross by +$44.05 and momentum by +$139.24, and meets both guardrails.
The prize is decided on the **final window** (3 whole UTC days after the
deadline), which is unseen — the dev ranking does not determine it. The sweep
(7,776 configs) found no EMA-crossover config better than −$93.21 on dev, and
that config fails the slice guardrails, so no re-fit within this strategy
family beats the dev best-house bar; the entry stands as fitted.
