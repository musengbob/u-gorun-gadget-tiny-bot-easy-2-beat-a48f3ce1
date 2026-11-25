import sys, itertools, json, time
sys.path.insert(0, "/home/hatch/workspace/makefun/entries/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1")
from sim import run, buy_and_hold
from sweep2 import make_strategy2

BH_full = run(buy_and_hold); BH_h1 = run(buy_and_hold,(0,68)); BH_h2 = run(buy_and_hold,(68,136)); BH_72 = run(buy_and_hold,(64,136))
t0=time.time()
ok_list = []
grid = list(itertools.product(
    [5,6,8], [13,18,21],
    [0.03,0.05,0.07,1e9], [0.04,0.06,0.10], [0.12,0.20,1e9],
    [6,12], [-1e9, 0.0],
    [0,12,24], [4,7], [6],
))
for (F,S,TR,ST,TP,ML,MM,BO,MP,NE) in grid:
    P = dict(fast=F, slow=S, trail=TR, stop=ST, tp=TP, mom_lb=ML, mom_min=MM, breakout=BO, max_pos=MP, no_entry=NE)
    r_full = run(make_strategy2(P))
    r_72 = run(make_strategy2(P), (64,136))
    r_h1 = run(make_strategy2(P), (0,68))
    r_h2 = run(make_strategy2(P), (68,136))
    ok = (r_full["net_usdc"] > BH_full["net_usdc"] and r_h1["net_usdc"] > BH_h1["net_usdc"]
          and r_h2["net_usdc"] > BH_h2["net_usdc"] and r_72["net_usdc"] > BH_72["net_usdc"]
          and r_72["trades"] >= 10 and r_full["trades"] >= 8
          and max(r_full["max_dd_pct"], r_72["max_dd_pct"], r_h1["max_dd_pct"], r_h2["max_dd_pct"]) <= 25)
    if not ok: continue
    margins = [r_full["net_usdc"]-BH_full["net_usdc"], r_h1["net_usdc"]-BH_h1["net_usdc"],
               r_h2["net_usdc"]-BH_h2["net_usdc"], r_72["net_usdc"]-BH_72["net_usdc"]]
    ok_list.append({"worst_margin": min(margins), "full": r_full, "h1": r_h1, "h2": r_h2, "w72": r_72, "P": P})
ok_list.sort(key=lambda x: (-x["worst_margin"], -x["full"]["net_usdc"]))
print(f"ok: {len(ok_list)}/{len(grid)} in {time.time()-t0:.0f}s")
print("\nTOP 15 ok=True by worst-slice margin over B&H:")
for r in ok_list[:15]:
    print(f"worstMargin {r['worst_margin']:8.2f} full {r['full']['net_usdc']:8.2f} (tr{r['full']['trades']:2d} dd{r['full']['max_dd_pct']:4.1f}%) "
          f"h1 {r['h1']['net_usdc']:8.2f} (tr{r['h1']['trades']:2d}) h2 {r['h2']['net_usdc']:8.2f} (tr{r['h2']['trades']:2d}) "
          f"last72 {r['w72']['net_usdc']:8.2f} (tr{r['w72']['trades']:2d} dd{r['w72']['max_dd_pct']:4.1f}%) P={r['P']}")
print("\nTOP 10 ok=True by full-window net PnL:")
for r in sorted(ok_list, key=lambda x: -x["full"]["net_usdc"])[:10]:
    print(f"full {r['full']['net_usdc']:8.2f} (tr{r['full']['trades']:2d} dd{r['full']['max_dd_pct']:4.1f}%) "
          f"h1 {r['h1']['net_usdc']:8.2f} (tr{r['h1']['trades']:2d}) h2 {r['h2']['net_usdc']:8.2f} (tr{r['h2']['trades']:2d}) "
          f"last72 {r['w72']['net_usdc']:8.2f} (tr{r['w72']['trades']:2d}) worstMargin {r['worst_margin']:8.2f} P={r['P']}")
json.dump(ok_list[:50], open("/home/hatch/workspace/makefun/entries/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/grid3_ok50.json","w"), indent=1, default=str)
