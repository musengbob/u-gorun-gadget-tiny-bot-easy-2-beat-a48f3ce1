import sys, itertools, json
sys.path.insert(0, "/home/hatch/workspace/makefun/entries/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1")
from sim import run, buy_and_hold
from sweep import make_strategy

BH = run(buy_and_hold)
print("B&H:", BH)

results = []
grid = list(itertools.product(
    [5,6,8],        # fast
    [13,18,21],     # slow
    [0.03,0.05,0.07,1e9],  # trail
    [0.04,0.06,0.10],      # stop
    [0.10,0.20,1e9],       # tp
    [6,12],         # mom_lb
    [0.0],          # mom_min
    [0,12],         # breakout
    [4],            # max_pos
    [6],            # no_entry
))
print("grid size:", len(grid))
for i,(F,S,TR,ST,TP,ML,MM,BO,MP,NE) in enumerate(grid):
    P = dict(fast=F, slow=S, trail=TR, stop=ST, tp=TP, mom_lb=ML, mom_min=MM, breakout=BO, max_pos=MP, no_entry=NE)
    r = run(make_strategy(P))
    ok = r["trades"] >= 8 and r["max_dd_pct"] <= 25
    results.append((r["net_usdc"], r, P, ok))
results.sort(key=lambda x: -x[0])
print("\nTOP 15 (net PnL, must beat B&H -869.34, trades>=8, DD<=25%):")
for net, r, P, ok in results[:15]:
    print(f"net {net:9.2f} ret {r['return_pct']:6.2f}% dd {r['max_dd_pct']:5.2f}% tr {r['trades']:3d} fees {r['fees_usdc']:6.2f} ok={ok} P={P}")
print("\nWORST 3:")
for net, r, P, ok in results[-3:]:
    print(f"net {net:9.2f} tr {r['trades']} dd {r['max_dd_pct']:.2f} P={P}")
n_beat = sum(1 for net,_,_,ok in results if net > BH["net_usdc"] and ok)
print(f"\n{ n_beat}/{len(results)} configs beat B&H with guardrails met")
json.dump([{"net":n,"r":r,"P":P,"ok":ok} for n,r,P,ok in results[:30]], open("/home/hatch/workspace/makefun/entries/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/grid_top30.json","w"), indent=1, default=str)
