# Analysis — fitting the EMA-crossover bot

Dev window: 136 hourly bars, 2026-10-29T01:00Z to 2026-11-03T16:00Z, all 7 symbols
(FARTCOIN, JITOSOL, POPCAT, RAY, SOL, WETH, WIF), no gaps. Starting capital
$10,000 USDC. The offline replay (`sim.py`) re-implements the harness fill
formulas from `contracts/bars-protocol.ts` with integer arithmetic and predicted
the grader exactly; `grade-local` (process driver) confirmed the dev score to
the micro-USDC, and an L1 regrade reproduced it byte-for-byte across two
executions.

## Sweep

7,776 configs over 4 windows (full dev window + first half + second half +
last-72-bars proxy for the final window). 5,076 configs passed all slices plus
the trade-count guardrail (≥8 trades). The chosen config won on:

- worst-slice margin over buy-and-hold: **+$155.70**
- 72-bar trade count: **14** vs 10 for the runner-up

## Chosen parameters

| Parameter | Value |
| --- | --- |
| Fast EMA | 6 bars |
| Slow EMA | 13 bars |
| Trailing stop | 3% below peak (peak from actual fill price) |
| Hard stop | 6% below fill price |
| Take profit | 20% above fill price |
| Momentum lookback | 6 bars, floor 0 |
| Breakout entry | disabled (swept and rejected — it added trades that lost money) |
| Max positions | 7, ~14.3% of equity each |
| Stop entering after | batch seq 66 (last 6 bars of the 72-bar final window) |
| Max slippage | 100 bps |

## Bug caught during fitting

An incremental-EMA variant seeded the fast EMA late. After the fix, the
incremental EMA was verified identical to a full recompute on all slices.

## Dev result (grade-local, process driver)

- **This bot: net PnL −$128.989173 (−1.29%), max DD 2.13%, 30 trades
  (15 buys / 15 sells), fees $42.55, 0 rejected orders, guardrails met.**
  `result_sha256 1085339b508e7ddab34a9620aa9b687cc0ddc5e037593dbb795a3d6e7507bba4`
- Buy-and-hold (official): net −$869.338396 (−8.69%), max DD 10.92%, 7 trades,
  fees $19.14 — and it fails the ≥8-trades guardrail itself. Beaten by +$740.35.
- EMA-cross house baseline (official): net −$173.035531, 28 trades, DD 2.51%.
  Beaten by +$44.05.

Note: `result_sha256` cannot equal the server's — local Node v24.22.1 vs server
v26.13.1; the score is unaffected per the kit docs.

## House baselines (dev window, grade-local)

Graded by the finisher after the phase-1 timeout; see `validation.md` for the
full table. Buy-and-hold and EMA-cross were graded in phase 1; the remaining
five (adx-momentum, hold-cash, macd-cci, momentum, rsi-bollinger) were graded
by the finisher.
