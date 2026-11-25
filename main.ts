// Tiny trend bot for make.fun's "Tiny Bot, Easy $2: Beat Buy-and-Hold on Solana"
// (competition u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1, harness bars-replay/v1).
//
// Strategy: long-only EMA-crossover momentum with hard risk controls, one program,
// no network, no clock, no randomness — a pure function of the bars.
//
//   - Indicators, per symbol over its own closes: EMA(FAST) and EMA(SLOW), each seeded
//     as the mean of its first span of closes, then moving 2 / (span + 1) of the way to
//     each new close. They step on every bar the symbol appears in, from bar 0.
//   - Entry, on a bar's close (filled at the next open): EMA(6) crosses above
//     EMA(13); the close must also sit above EMA(13) and the symbol's 6-bar
//     return must not be negative. (A breakout entry was swept and rejected:
//     it added trades that lost money.) At most 7 positions, sized at
//     min(equity / 7, 25% of equity, cash left) — about 14.3% of equity each,
//     so the 25% weight cap never binds; candidates ranked by the EMA gap
//     (fast - slow) / slow, strongest first.
//   - Exit, the whole position: EMA(FAST) crosses below EMA(SLOW) (the signal is held
//     while fast stays below slow, so a refused sell is re-sent), or the close falls
//     STOP below the actual fill price, or rises TP above it, or falls TRAIL below the
//     trailing peak (the peak starts at the actual fill price, never at the fill-bar
//     close). A position is never sold while held under one full bar: a sell is only
//     decided on a batch after the batch that reported its buy fill.
//   - Sells are sent before buys; each order caps slippage at 100 bps past the close
//     it was decided on, so a sell into a liquidity gap is refused (and re-sent)
//     rather than filled for almost nothing.
//   - No new entries once the replay has run STOP_ENTER_AFTER_SEQ bars: the final
//     window is 3 whole UTC days (72 hourly bars), so this keeps the bot out of the
//     last 6 bars, where a fresh position could not play out before the flatten.
//
// Fitted on the kit's dev window (136 hourly bars, 2026-10-29T01:00Z to
// 2026-11-03T16:00Z, all 7 symbols, no gaps) with an exact offline replay of the
// harness fill formulas; see analysis.md for the sweep and validation.md for the
// walk-forward splits. The entrypoint runs under Node 22 as `node main.ts`.
//
// vendor/makefun-bars.ts is a byte-identical copy of the kit's sdk/makefun-bars.ts.

import { BPS, runBars, type BarsState, type BuyInput, type SellInput } from './vendor/makefun-bars.ts';

// ---- fitted parameters (see analysis.md) ----
const FAST_BARS = 6;
const SLOW_BARS = 13;
const TRAIL = 0.03; // trailing stop: 3% below the peak since the fill
const STOP = 0.06; // hard stop: 6% below the fill price
const TAKE_PROFIT = 0.2; // take profit: 20% above the fill price
const MOM_LB = 6; // momentum lookback, bars
const MOM_MIN = 0; // momentum floor: the 6-bar return must not be negative
const BREAKOUT_BARS = 0; // 0 disables the breakout entry
const MAX_POS = 7;
const STOP_ENTER_AFTER_SEQ = 66; // no new entries from this batch seq on
const MAX_SLIPPAGE_BPS = 100;

interface Ema {
  span: number;
  warm: number[];
  value: number | null;
}

interface Series {
  fast: Ema;
  slow: Ema;
  /** fast - slow after the symbol's bar before this one, once both are set. */
  gapPrev: number | null;
  /** The cross-down sell signal, held while fast stays below slow. */
  down: boolean;
  /** Closes seen, in batch order. */
  closes: number[];
}

interface FillInfo {
  /** Batch seq that reported the buy fill. */
  fillSeq: number;
  /** Actual fill price (integer at the symbol's price_scale). */
  fillPrice: number;
}

const series = new Map<string, Series>();
const fills = new Map<string, FillInfo>();

function step(e: Ema, close: number): number | null {
  if (e.value !== null) {
    e.value += (2 / (e.span + 1)) * (close - e.value);
    return e.value;
  }
  e.warm.push(close);
  if (e.warm.length === e.span) e.value = e.warm.reduce((a, x) => a + x, 0) / e.span;
  return e.value;
}

function getSeries(symbol: string): Series {
  let s = series.get(symbol);
  if (s === undefined) {
    s = {
      fast: { span: FAST_BARS, warm: [], value: null },
      slow: { span: SLOW_BARS, warm: [], value: null },
      gapPrev: null,
      down: false,
      closes: [],
    };
    series.set(symbol, s);
  }
  return s;
}

await runBars({
  onBatch(state: BarsState, batch) {
    // Record this batch's fills first: a buy's actual fill price and the batch
    // that reported it are what the exits are measured from.
    for (const f of batch.fills) {
      if (f.status !== 'filled') continue;
      if (f.side === 'buy') {
        fills.set(f.symbol, { fillSeq: state.seq, fillPrice: Number(f.price) });
      } else {
        fills.delete(f.symbol);
      }
    }

    const sig = new Map<string, { gap: number; entry: boolean; down: boolean }>();
    for (const bar of batch.bars) {
      const s = getSeries(bar.symbol);
      const close = Number(bar.c);
      s.closes.push(close);
      const fNow = step(s.fast, close);
      const sNow = step(s.slow, close);
      if (fNow === null || sNow === null) continue;
      const gapNow = fNow - sNow;
      const gapPrev = s.gapPrev;
      s.gapPrev = gapNow;
      if (gapPrev === null) continue;
      if (gapNow >= 0) s.down = false;
      else if (gapNow < 0 && gapPrev >= 0) s.down = true;
      const h = s.closes;
      const mom = h.length > MOM_LB ? (h[h.length - 1] - h[h.length - 1 - MOM_LB]) / h[h.length - 1 - MOM_LB] : 0;
      const crossUp = gapNow > 0 && gapPrev <= 0;
      const breakout =
        BREAKOUT_BARS > 0 &&
        h.length > BREAKOUT_BARS &&
        close > Math.max(...h.slice(h.length - 1 - BREAKOUT_BARS, h.length - 1)) &&
        gapNow > 0;
      const entry = (crossUp || breakout) && close > sNow && mom >= MOM_MIN;
      sig.set(bar.symbol, { gap: gapNow / sNow, entry, down: s.down });
    }

    if (state.warmingUp) return [];

    const sells: SellInput[] = [];
    for (const [symbol, held] of state.positions) {
      const info = fills.get(symbol);
      // No fill record yet (or held under one full bar): never sell.
      if (info === undefined || state.seq <= info.fillSeq) continue;
      const closeRaw = state.close(symbol);
      if (closeRaw === null) continue;
      const close = Number(closeRaw);
      const s = getSeries(symbol);
      // Trailing peak: the actual fill price, and the closes after the fill
      // batch (the fill batch's own close is not counted, matching the
      // offline replay the parameters were fitted with).
      let peak = info.fillPrice;
      for (let i = info.fillSeq + 1; i < s.closes.length; i++) {
        if (s.closes[i] > peak) peak = s.closes[i];
      }
      const exitNow =
        (sig.get(symbol)?.down ?? false) ||
        close <= info.fillPrice * (1 - STOP) ||
        close >= info.fillPrice * (1 + TAKE_PROFIT) ||
        close <= peak * (1 - TRAIL);
      if (exitNow) {
        sells.push({ side: 'sell', symbol, qty: held.qty, max_slippage_bps: MAX_SLIPPAGE_BPS });
      }
    }

    const orders: (SellInput | BuyInput)[] = sells.slice(0, state.hello.caps.max_orders_per_bar);
    if (state.seq < STOP_ENTER_AFTER_SEQ) {
      const room = MAX_POS - state.positions.size;
      const cands = state.hello.symbols
        .map((x) => x.symbol)
        .filter((symbol) => !state.positions.has(symbol) && (sig.get(symbol)?.entry ?? false));
      cands.sort((a, b) => (sig.get(b)?.gap ?? 0) - (sig.get(a)?.gap ?? 0));
      let cash = state.cash;
      for (const symbol of cands.slice(0, Math.max(room, 0))) {
        if (orders.length >= state.hello.caps.max_orders_per_bar) break;
        const bySlots = state.equity / BigInt(MAX_POS);
        const byWeight = (BigInt(state.hello.caps.max_weight_bps) * state.equity) / BPS;
        let stake = bySlots < byWeight ? bySlots : byWeight;
        if (cash < stake) stake = cash;
        if (stake === 0n || stake < BigInt(state.hello.fees.min_notional_quote_units)) break;
        orders.push({ side: 'buy', symbol, notional_quote_units: stake, max_slippage_bps: MAX_SLIPPAGE_BPS });
        cash -= stake;
      }
    }
    return orders;
  },
});
