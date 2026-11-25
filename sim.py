"""Exact offline replay of the bars-replay/v1 harness (from kit contracts/bars-protocol.ts
+ sim/bars/engine.ts) for the tiny-bot dev window, in integer arithmetic.
Quote scale 6, capital 10,000 USDC = 10_000_000_000 micro-units.
fee 10bps, slippage 5bps, latency 1 bar, max_weight 2500bps, max 10 positions, 16 orders/bar.
Fills at next bar open vs o_depth; flatten at end at last close vs c_depth.
"""
import gzip, json
from fractions import Fraction

KIT = "/home/hatch/workspace/makefun/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1-kit"
SYMS = ["FARTCOIN","JITOSOL","POPCAT","RAY","SOL","WETH","WIF"]
man = json.load(open(f"{KIT}/dataset/manifest.json"))
SCALES = {s["symbol"]: (s["price_scale"], s["qty_scale"]) for s in man["symbols"]}
BARS = {}
for sym in SYMS:
    rows = [json.loads(l) for l in gzip.open(f"{KIT}/dataset/bars/{sym}.ndjson.gz","rt")]
    BARS[sym] = rows
N = 136
CAPITAL = 10_000_000_000
FEE_BPS = 10
SLIP_BPS = 5
MAX_WEIGHT_BPS = 2500
MAX_POS = 10
MAX_ORDERS = 16
MIN_NOTIONAL = 1_000_000

def value(q, p, sym):
    ps, qs = SCALES[sym]
    return q * p * 10**6 // 10**(qs + ps)

def depth_D(depths):
    # harmonic: D = 1 / sum(1/Di) as Fraction
    s = sum(Fraction(1, int(d)) for d in depths)
    return Fraction(1, 1) / s

def run(strategy, bars_slice=None, verbose=False):
    """strategy(ctx) -> list of orders decided at batch k.
    ctx: dict with seq, closes{sym:price}, positions{sym:(qty,cost,fill_seq,fill_price)}, cash, equity,
         fills_prev, history closes list per sym.
    Returns dict of metrics. bars_slice: (start,end) index range to replay (walk-forward)."""
    lo, hi = (0, N) if bars_slice is None else bars_slice
    idx = list(range(lo, hi))
    cash = CAPITAL
    pos = {}  # sym -> [qty, cost, fill_seq, fill_price]
    equity_pts = [CAPITAL]
    fills_all = []  # filled orders (bot's own)
    fees_total = 0
    # pending orders decided at batch k, to fill at open of bar k+1
    pending = []
    # per-symbol close history (for strategy); strategy keeps its own state via ctx['hist']
    hist = {s: [] for s in SYMS}
    closes = {}
    # track pool state per symbol for fill bar: y as Fraction, D as Fraction
    for k_i, bi in enumerate(idx):
        seq = k_i  # seq within this replay
        # 1) resolve pending orders at this bar's open
        new_pending_fills = []
        # group pending by symbol, in reply order, pool per symbol starts fresh from o_depth
        pools = {}
        for o in pending:
            sym = o["symbol"]
            bar = BARS[sym][bi]
            if sym not in pools:
                pools[sym] = {"D": depth_D(bar["o_depth"]), "y": depth_D(bar["o_depth"])}
            pool = pools[sym]
            D, y = pool["D"], pool["y"]
            latest_close = closes.get(sym)
            if latest_close is None:
                continue  # no_bar (cannot happen in dev: every symbol has bar 0)
            if o["side"] == "buy":
                spend = o["notional"] * (10000 - FEE_BPS) // 10000
                fee = o["notional"] - spend
                a = spend  # raw units == quote units (quote_scale 6)
                M = y * (y + a) / (D * D)
                price = int(Fraction(int(bar["o"]) * (10000 + SLIP_BPS) * M, 10000))
                # max_slippage check vs latest close
                if price * 10000 > latest_close * (10000 + o["max_slip"]):
                    continue
                ps, qs = SCALES[sym]
                qty = spend * 10**(qs + ps) // (price * 10**6)
                if qty == 0:
                    continue
                pool["y"] = y + a
                cash -= o["notional"]
                fees_total += fee
                if sym in pos:
                    pos[sym][0] += qty; pos[sym][1] += o["notional"]
                else:
                    pos[sym] = [qty, o["notional"], seq, price]
                fills_all.append(("buy", sym, qty, price, o["notional"], fee))
            else:
                qty = o["qty"]
                a = value(qty, int(bar["o"]), sym)
                M = (D*D + a*y) / (y*y)
                price = max(1, int(Fraction(int(bar["o"]) * (10000 - SLIP_BPS), 10000 * M)))
                if price * 10000 < latest_close * (10000 - o["max_slip"]):
                    continue
                gross = value(qty, price, sym)
                proceeds = gross * (10000 - FEE_BPS) // 10000
                fee = gross - proceeds
                pool["y"] = D*D*y / (D*D + a*y)
                cash += proceeds
                fees_total += fee
                p = pos[sym]
                p[1] = p[1] * (p[0]-qty) // p[0] if p[0] > 0 else 0
                p[0] -= qty
                if p[0] == 0:
                    del pos[sym]
                fills_all.append(("sell", sym, qty, price, proceeds, fee))
        pending = []
        # 2) update closes/history with this bar's close
        for sym in SYMS:
            bar = BARS[sym][bi]
            closes[sym] = int(bar["c"])
            hist[sym].append(int(bar["c"]))
        # equity point at this batch (after fills, at latest closes)
        eq = cash + sum(value(p[0], closes[s], s) for s, p in pos.items())
        equity_pts.append(eq)
        # 3) strategy decides (except last batch: orders would be after_end)
        if bi == hi - 1:
            break
        ctx = {"seq": seq, "closes": dict(closes), "hist": {s: list(h) for s, h in hist.items()},
               "pos": {s: tuple(v) for s, v in pos.items()}, "cash": cash, "equity": eq,
               "n_bars": len(idx), "last_seq": len(idx)-1}
        orders = strategy(ctx) or []
        # 4) decision-time checks in reply order
        accepted = []
        seen_ids = set()
        buy_spend = 0
        buy_by_sym = {}
        sell_by_sym = {}
        held_syms = set(pos.keys())
        bought_syms = set()
        for oi, o in enumerate(orders[:MAX_ORDERS]):
            sym = o["symbol"]
            cid = o.get("client_id", f"o{seq}-{oi}")
            if cid in seen_ids: continue
            seen_ids.add(cid)
            if sym not in SYMS: continue
            if o["side"] == "buy":
                notional = o["notional"]
                if notional == 0: continue
                if notional < MIN_NOTIONAL: continue
                if buy_spend + notional > cash: continue
                if sym not in held_syms and sym not in bought_syms and len(held_syms | bought_syms) >= MAX_POS: continue
                held_val = value(pos[sym][0], closes[sym], sym) if sym in pos else 0
                if (held_val + buy_by_sym.get(sym, 0) + notional) * 10000 > MAX_WEIGHT_BPS * eq: continue
                buy_spend += notional
                buy_by_sym[sym] = buy_by_sym.get(sym, 0) + notional
                bought_syms.add(sym)
                accepted.append({"side":"buy","symbol":sym,"notional":notional,"max_slip":o.get("max_slip",100)})
            else:
                if sym not in pos: continue
                qty = o["qty"]
                if qty == 0: continue
                if qty > pos[sym][0] - sell_by_sym.get(sym, 0): continue
                if value(qty, closes[sym], sym) < MIN_NOTIONAL and qty + sell_by_sym.get(sym,0) < pos[sym][0]: continue
                sell_by_sym[sym] = sell_by_sym.get(sym, 0) + qty
                accepted.append({"side":"sell","symbol":sym,"qty":qty,"max_slip":o.get("max_slip",100)})
        pending = accepted
    # flatten at end: sell each position at last close vs c_depth
    flat_fees = 0
    for sym in sorted(pos.keys()):
        bar = BARS[sym][hi-1]
        D = depth_D(bar["c_depth"]); y = D
        qty = pos[sym][0]
        a = value(qty, int(bar["c"]), sym)
        M = (D*D + a*y) / (y*y)
        price = max(1, int(Fraction(int(bar["c"]) * (10000 - SLIP_BPS), 10000 * M)))
        gross = value(qty, price, sym)
        proceeds = gross * (10000 - FEE_BPS) // 10000
        flat_fees += gross - proceeds
        cash += proceeds
    fees_total += flat_fees
    equity_pts.append(cash)
    net = cash - CAPITAL
    peak = CAPITAL; mdd = 0.0
    for e in equity_pts:
        if e > peak: peak = e
        dd = (peak - e) / peak if peak else 0
        if dd > mdd: mdd = dd
    n_trades = len(fills_all)
    return {"net_usdc": net/1e6, "return_pct": 100*net/CAPITAL, "max_dd_pct": 100*mdd,
            "trades": n_trades, "fees_usdc": fees_total/1e6, "final_cash_usdc": cash/1e6,
            "buys": sum(1 for f in fills_all if f[0]=="buy"), "sells": sum(1 for f in fills_all if f[0]=="sell")}

def buy_and_hold(ctx):
    if ctx["seq"] != 0: return []
    n = min(len(SYMS), MAX_POS, MAX_ORDERS)
    even = ctx["cash"] // n
    by_weight = MAX_WEIGHT_BPS * ctx["equity"] // 10000
    sl = min(even, by_weight)
    if sl < MIN_NOTIONAL: return []
    return [{"side":"buy","symbol":s,"notional":sl,"max_slip":10000} for s in SYMS[:n]]

if __name__ == "__main__":
    r = run(buy_and_hold)
    print("BUY-AND-HOLD full dev window (136 bars, 2026-10-29T01:00Z -> 2026-11-03T16:00Z):")
    print(" ", r)
    for name, sl in [("first half 0:68", (0,68)), ("second half 68:136", (68,136))]:
        print(name, run(buy_and_hold, sl))
