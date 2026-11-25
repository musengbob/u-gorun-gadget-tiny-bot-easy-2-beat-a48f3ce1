# HANDOFF — brief-41, tiny SOL bot (u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)

## Status

Phase 1 was interrupted by the 16:44 WIB heartbeat cron timeout. The finisher
completed the build: README.md, LICENSE, package.json, `.makefun/owner.json`,
`analysis.md`, `validation.md` and this file were written; the GitHub repo was
created (public, main, About + topics verified live); all 17 files were pushed
(HEAD `b6f5c3c7940478880a10ca762d7d94af30c470be`, every blob SHA-1 verified
against the local files); the 5 remaining house baselines were graded with
grade-local (process driver); the entry was bundled, kit-checked and submitted
by the chat-owned finisher (see `submission.txt`).

## Competition

- `u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1` — "Tiny Bot, Easy $2: Beat
  Buy-and-Hold on Solana", FREE, $2.00 pot (1st $1.00 / 2nd $0.60 / 3rd $0.40),
  harness bars-replay/v1, hourly SOL bars, places by net PnL, beat
  buy-and-hold is the bar.
- Opened 2026-11-25T09:30:00Z; entries close 2026-11-27T00:00:00Z (07:00 WIB
  Nov 27); result due 2026-12-22T00:00:00Z. No blind rounds — dev phase,
  then the final window (3 whole UTC days after the deadline).
- Guardrails: at least 8 trades and max drawdown ≤ 25%; entries that miss them
  rank below every entry that meets them.

## Strategy

Long-only EMA(6)/EMA(13) crossover, entry requires close above slow EMA and
6-bar return ≥ 0; exits: 3% trailing stop (peak from actual fill price), 6%
hard stop, 20% take-profit, held cross-down signal; never sells while held < 1
full bar; max 7 positions at ~14.3% equity each; no new entries from batch seq
66; 100 bps max slippage. Deterministic, no clock/random/network.

## Dev backtest (grade-local, process driver, confirmed to the micro-USDC)

Dev window: 136 hourly bars, 2026-10-29T01:00Z → 2026-11-03T16:00Z.

- **This bot: net PnL −$128.989173 (−1.29%), max DD 2.13%, 30 trades
  (15 buys / 15 sells), fees $42.55, 0 rejected orders, guardrails met.**
- Buy-and-hold (official): net −$869.338396 (−8.69%), max DD 10.92%, 7 trades
  — beaten by +$740.35.
- EMA-cross (official): net −$173.035531, 28 trades, DD 2.51% — beaten by
  +$44.05.
- The 5 remaining house baselines (adx-momentum, hold-cash, macd-cci,
  momentum, rsi-bollinger) were graded by the finisher; see `validation.md`.

## Sessions

- Builder: `0e3fc61d-6bce-460e-9c85-ff31579d683a` (1 usage row: 193,819 in /
  1,628 out)
- Phase-1 coordinator: `644d26f6-4701-4942-96bd-e416eee653c1` (EXCLUDED from
  the bundle — contributed no entry code)
- Finisher: this session (0 rows at bundle time)

## Repo

https://github.com/musengbob/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1
