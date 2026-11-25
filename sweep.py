import sys, itertools
sys.path.insert(0, "/home/hatch/workspace/makefun/entries/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1")
from sim import run, buy_and_hold, SYMS, CAPITAL, MIN_NOTIONAL

def ema_series(closes, span):
    # returns list of EMA values (None until seeded), seeded as mean of first span closes
    out = []
    v = None
    warm = []
    for c in closes:
        if v is not None:
            v += (2/(span+1))*(c - v)
        else:
            warm.append(c)
            if len(warm) == span:
                v = sum(warm)/span
        out.append(v)
    return out

def make_strategy(P):
    FAST, SLOW = P["fast"], P["slow"]
    TRAIL, STOP, TP = P["trail"], P["stop"], P["tp"]
    MOM_LB, MOM_MIN = P["mom_lb"], P["mom_min"]
    BO = P["breakout"]
    MAXP = P["max_pos"]
    NO_ENTRY = P["no_entry"]
    def strategy(ctx):
        seq = ctx["seq"]; hist = ctx["hist"]; closes = ctx["closes"]
        # per-symbol indicators from full history (pure function of bars)
        sig = {}
        for s in SYMS:
            h = hist[s]
            if len(h) < SLOW: continue
            ef = ema_series(h, FAST); es = ema_series(h, SLOW)
            f_now, s_now = ef[-1], es[-1]
            f_prev, s_prev = ef[-2], es[-2]
            if None in (f_now, s_now, f_prev, s_prev): continue
            gap_now = f_now - s_now; gap_prev = f_prev - s_prev
            mom = (h[-1] - h[-1-MOM_LB]) / h[-1-MOM_LB] if len(h) > MOM_LB else 0.0
            cross_up = gap_now > 0 and gap_prev <= 0
            breakout = False
            if BO:
                breakout = h[-1] > max(h[-1-BO:-1]) and gap_now > 0
            entry = (cross_up or breakout) and closes[s] > s_now and mom >= MOM_MIN
            sig[s] = {"gap": gap_now/s_now, "entry": entry, "down": gap_now < 0 and gap_prev >= 0, "f": f_now, "s": s_now}
        orders = []
        # exits first
        for s, p in ctx["pos"].items():
            qty, cost, fill_seq, fill_price = p
            if seq <= fill_seq:  # held < 1 full bar: never sell
                continue
            c = closes[s]
            # trailing peak: max fill price and closes since fill (approx: max of hist since fill_seq)
            peak = max([fill_price] + hist[s][fill_seq+1:])
            exit_now = False
            if sig.get(s, {}).get("down"): exit_now = True
            if c <= fill_price * (1 - STOP): exit_now = True
            if c >= fill_price * (1 + TP): exit_now = True
            if c <= peak * (1 - TRAIL): exit_now = True
            if exit_now:
                orders.append({"side":"sell","symbol":s,"qty":qty,"max_slip":100})
        # entries
        if seq < ctx["last_seq"] - NO_ENTRY:
            room = MAXP - len(ctx["pos"])
            cands = [s for s in SYMS if s not in ctx["pos"] and sig.get(s, {}).get("entry")]
            cands.sort(key=lambda s: -sig[s]["gap"])
            for s in cands[:max(room,0)]:
                slots = MAXP
                stake = min(ctx["equity"] // slots, 2500 * ctx["equity"] // 10000)
                cash_left = ctx["cash"] - sum(o.get("notional",0) for o in orders if o["side"]=="buy")
                stake = min(stake, cash_left)
                if stake >= MIN_NOTIONAL:
                    orders.append({"side":"buy","symbol":s,"notional":stake,"max_slip":100})
        return orders
    return strategy

if __name__ == "__main__":
    # diagnostics: cross-up counts
    for F,S in [(8,21),(6,18),(5,13),(8,26)]:
        cnt=0
        for s in SYMS:
            from sim import BARS
            closes=[int(r["c"]) for r in BARS[s]]
            ef=ema_series(closes,F); es=ema_series(closes,S)
            for i in range(1,len(closes)):
                if ef[i] is not None and es[i] is not None and ef[i-1] is not None and es[i-1] is not None:
                    if ef[i]-es[i]>0 and ef[i-1]-es[i-1]<=0: cnt+=1
        print(f"cross-ups F={F} S={S}: {cnt} total across 7 symbols")
    # baseline ema-cross replica (for sim sanity): FAST=8 SLOW=21 ROI 50% STOP 20%, no trail
    P = dict(fast=8, slow=21, trail=1e9, stop=0.20, tp=0.50, mom_lb=6, mom_min=-1e9, breakout=0, max_pos=7, no_entry=0)
    print("ema-cross-ish replica:", run(make_strategy(P)))
    print("buy-and-hold        :", run(buy_and_hold))
