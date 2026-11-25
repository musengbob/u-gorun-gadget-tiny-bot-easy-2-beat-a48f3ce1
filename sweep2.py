import sys
sys.path.insert(0, "/home/hatch/workspace/makefun/entries/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1")
from sim import SYMS, MIN_NOTIONAL

def make_strategy2(P):
    """Incremental-EMA version of the sweep strategy (identical decisions to sweep.make_strategy;
    state is per-instance, so create a fresh one per run)."""
    FAST, SLOW = P["fast"], P["slow"]
    TRAIL, STOP, TP = P["trail"], P["stop"], P["tp"]
    MOM_LB, MOM_MIN = P["mom_lb"], P["mom_min"]
    BO = P["breakout"]; MAXP = P["max_pos"]; NO_ENTRY = P["no_entry"]
    # per-symbol incremental EMA state
    st = {}
    def ema_step(e, close):
        if e["v"] is not None:
            e["v"] += (2 / (e["span"] + 1)) * (close - e["v"])
        else:
            e["warm"].append(close)
            if len(e["warm"]) == e["span"]:
                e["v"] = sum(e["warm"]) / e["span"]
        return e["v"]
    def strategy(ctx):
        seq = ctx["seq"]; hist = ctx["hist"]; closes = ctx["closes"]
        sig = {}
        for s in SYMS:
            h = hist[s]
            e = st.setdefault(s, {"fast": {"span": FAST, "warm": [], "v": None},
                                  "slow": {"span": SLOW, "warm": [], "v": None},
                                  "gap_prev": None, "down": False})
            c = h[-1]
            # step BOTH EMAs from bar 0 (seed = mean of first span closes), exactly
            # like the recompute version; gate only the signal on both being set
            f_now = ema_step(e["fast"], c)
            s_now = ema_step(e["slow"], c)
            if f_now is None or s_now is None:
                continue
            gap_now = f_now - s_now
            gap_prev = e["gap_prev"]
            e["gap_prev"] = gap_now
            if gap_prev is None:
                continue
            mom = (h[-1] - h[-1 - MOM_LB]) / h[-1 - MOM_LB] if len(h) > MOM_LB else 0.0
            cross_up = gap_now > 0 and gap_prev <= 0
            breakout = bool(BO) and h[-1] > max(h[-1 - BO:-1]) and gap_now > 0
            entry = (cross_up or breakout) and closes[s] > s_now and mom >= MOM_MIN
            down = gap_now < 0 and gap_prev >= 0
            if gap_now >= 0:
                e["down"] = False
            elif down:
                e["down"] = True
            sig[s] = {"gap": gap_now / s_now, "entry": entry, "down": e["down"]}
        orders = []
        for s, p in ctx["pos"].items():
            qty, cost, fill_seq, fill_price = p
            if seq <= fill_seq:
                continue
            c = closes[s]
            peak = max([fill_price] + hist[s][fill_seq + 1:])
            exit_now = False
            if sig.get(s, {}).get("down"): exit_now = True
            if c <= fill_price * (1 - STOP): exit_now = True
            if c >= fill_price * (1 + TP): exit_now = True
            if c <= peak * (1 - TRAIL): exit_now = True
            if exit_now:
                orders.append({"side": "sell", "symbol": s, "qty": qty, "max_slip": 100})
        stop_after = P.get("stop_after")
        if seq < ctx["last_seq"] - NO_ENTRY and (stop_after is None or seq < stop_after):
            room = MAXP - len(ctx["pos"])
            cands = [s for s in SYMS if s not in ctx["pos"] and sig.get(s, {}).get("entry")]
            cands.sort(key=lambda s: -sig[s]["gap"])
            for s in cands[:max(room, 0)]:
                stake = min(ctx["equity"] // MAXP, 2500 * ctx["equity"] // 10000)
                cash_left = ctx["cash"] - sum(o.get("notional", 0) for o in orders if o["side"] == "buy")
                stake = min(stake, cash_left)
                if stake >= MIN_NOTIONAL:
                    orders.append({"side": "buy", "symbol": s, "notional": stake, "max_slip": 100})
        return orders
    return strategy
