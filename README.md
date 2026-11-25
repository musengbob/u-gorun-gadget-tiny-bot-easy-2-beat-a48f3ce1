# Tiny Bot — EMA-Crossover SOL Bot

[![make.fun](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![rank](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/musengbob/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/rank.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![reward](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/musengbob/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/reward.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)

A tiny paper-trading bot for [make.fun's "Tiny Bot, Easy $2: Beat Buy-and-Hold on Solana" bounty](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1) — harness `bars-replay/v1`, hourly bars for FARTCOIN, JITOSOL, POPCAT, RAY, SOL, WETH and WIF, $10,000 USDC starting capital. Places go by net PnL on the final 3-day window; a placement reward needs a better score than the best house baseline.

## Strategy

Long-only EMA-crossover momentum with hard risk controls, one program, no network, no clock, no randomness — a pure function of the bars.

- **Indicators**, per symbol over its own closes: EMA(6) and EMA(13), each seeded as the mean of its first span of closes, then moving `2 / (span + 1)` of the way to each new close. They step on every bar the symbol appears in, from bar 0.
- **Entry**, on a bar's close (filled at the next open): EMA(6) crosses above EMA(13); the close must also sit above EMA(13) and the symbol's 6-bar return must not be negative. At most 7 positions, sized at `min(equity / 7, 25% of equity, cash left)` — about 14.3% of equity each, so the 25% weight cap never binds. Candidates ranked by the EMA gap `(fast - slow) / slow`, strongest first.
- **Exit**, the whole position: EMA(6) crosses below EMA(13) (the signal is held while fast stays below slow, so a refused sell is re-sent), or the close falls 6% below the actual fill price, or rises 20% above it, or falls 3% below the trailing peak (the peak starts at the actual fill price, never at the fill-bar close). A position is never sold while held under one full bar.
- **Sells are sent before buys**; each order caps slippage at 100 bps past the close it was decided on, so a sell into a liquidity gap is refused (and re-sent) rather than filled for almost nothing.
- **No new entries from batch seq 66**: the final window is 3 whole UTC days (72 hourly bars), so this keeps the bot out of the last 6 bars, where a fresh position could not play out before the flatten.

Fitted on the kit's dev window (136 hourly bars, 2026-10-29T01:00Z to 2026-11-03T16:00Z, all 7 symbols, no gaps) with an exact offline replay of the harness fill formulas; see `analysis.md` for the sweep and `validation.md` for the walk-forward splits. The entrypoint runs under Node 22 as `node main.ts`.

`vendor/makefun-bars.ts` is a byte-identical copy of the kit's `sdk/makefun-bars.ts`.

## Dev backtest (grade-local, process driver, confirmed to the micro-USDC)

Dev window: 136 hourly bars, 2026-10-29T01:00Z → 2026-11-03T16:00Z.

| Bot | Net PnL | Max DD | Trades |
| --- | --- | --- | --- |
| macd-cci (house baseline) | −$20.22 | 2.46% | 17 |
| rsi-bollinger (house baseline) | −$56.49 | 5.16% | 8 |
| adx-momentum (house baseline) | −$114.42 | 1.38% | 11 |
| **This bot** | **−$128.99 (−1.29%)** | 2.13% | 30 (15 buys / 15 sells) |
| EMA-cross (house baseline) | −$173.04 | 2.51% | 28 |
| momentum (house baseline) | −$268.23 | 5.66% | 19 |
| Buy-and-hold (official) | −$869.34 (−8.69%) | 10.92% | 7 |
| hold-cash (house baseline) | $0.00 | 0.00% | 0 (non-compliant: fails the ≥8-trades guardrail) |

This bot beats buy-and-hold by **+$740.35** (the stated bar) and EMA-cross by **+$44.05**. Fees $42.55, 0 rejected orders, guardrails met (≥8 trades, max DD ≤ 25%). The best house baseline on the dev window is macd-cci at −$20.22; the prize is decided on the final window (3 whole UTC days after the deadline), which is unseen — the dev ranking does not determine it. See `validation.md` for the full baseline table.

Walk-forward (offline replay, same strategy): first half (bars 0–68) −$88.25 (20 trades) vs B&H −$660.25; second half (68–136) −$85.84 (8 trades) vs B&H −$247.19; last-72-bars proxy for the final window −$156.07 (14 trades) vs B&H −$311.77. All slices beat B&H; max DD ≤ 3.8% everywhere.

Sweep: 7,776 configs over 4 windows; 5,076 passed all slices + trade counts. The chosen config won on worst-slice margin over B&H (+$155.70) and 72-bar trade count (14 vs 10 for the runner-up).

## Run it

```sh
# Grade locally (process driver runs the bot on this machine, unisolated)
node <kit>/cli/makefun.mjs grade-local --kit <kit> --bot . --driver process
```

## Files

- `main.ts` — the bot (entrypoint, Node 22)
- `vendor/makefun-bars.ts` — byte-identical copy of the kit's bars-protocol SDK shim
- `sim.py`, `sweep.py`, `sweep2.py`, `grid.py`, `grid2.py`, `grid3.py` — offline replay + sweep harness used for fitting
- `grid_top30.json`, `grid2_top40.json`, `grid3_ok50.json` — sweep results
- `analysis.md` — sweep and fitting notes
- `validation.md` — walk-forward validation

## License

MIT — see [LICENSE](LICENSE).
