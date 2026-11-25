import sys, itertools, json
sys.path.insert(0, "/home/hatch/workspace/makefun/entries/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1")
from sim import run, buy_and_hold
from sweep import make_strategy

BH_full = run(buy_and_hold); BH_h1 = run(buy_and_hold,(0,68)); BH_h2 = run(buy_and_hold,(68,136)); BH_72 = run(buy_and_hold,(64,136))
print("B&H full %.2f | h1 %.2f | h2 %.2f | last72 %.2f" % (BH_full["net_usdc"], BH_h1["net_usdc"], BH_h2["net_usdc"], BH_72["net_usdc"]))

results = []
grid = list(itertools.product(
    [5,6,8], [13,18,21],
    [0.03,0.05,0.07,1e9], [0.04,0.06,0.10], [0.12,0.20,1e9],
    [6,12], [-1e9, 0.0],
    [0,12,24], [4,7], [6],
))
print("grid size:", len(grid))
for (F,S,TR,ST,TP,ML,MM,BO,MP,NE) in grid:
    P = dict(fast=F, slow=S, trail=TR, stop=ST, tp=TP, mom_lb=ML, mom_min=MM, breakout=BO, max_pos=MP, no_entry=NE)
    st = make_strategy(P)
    r_full = run(st)
    r_72 = run(st, (64,136))
    r_h1 = run(st, (0,68))
    r_h2 = run(st, (68,136))
    # score: must beat B&H everywhere, trades>=10 on last72 (final-window proxy), DD<=25% everywhere
    ok = (r_full["net_usdc"] > BH_full["net_usdc"] and r_h1["net_usdc"] > BH_h1["net_usdc"]
          and r_h2["net_usdc"] > BH_h2["net_usdc"] and r_72["net_usdc"] > BH_72["net_usdc"]
          and r_72["trades"] >= 10 and r_full["trades"] >= 8
          and max(r_full["max_dd_pct"], r_72["max_dd_pct"], r_h1["max_dd_pct"], r_h2["max_dd_pct"]) <= 25)
    # ranking score: worst margin over B&H across slices (robustness), tiebreak full net
    margins = [r_full["net_usdc"]-BH_full["net_usdc"], r_h1["net_usdc"]-BH_h1["net_usdc"],
               r_h2["net_usdc"]-BH_h2["net_usdc"], r_72["net_usdc"]-BH_72["net_usdc"]]
    results.append({"worst_margin": min(margins), "full": r_full, "h1": r_h1, "h2": r_h2, "w72": r_72, "P": P, "ok": ok})
results.sort(key=lambda x: (-x["worst_margin"], -x["full"]["net_usdc"]))
print("\nTOP 12 by worst-slice margin over B&H (all slices must beat B&H, last72 trades>=10):")
for r in results[:12]:
    print(f"worstMargin {r['worst_margin']:8.2f} full {r['full']['net_usdc']:8.2f} (tr{r['full']['trades']:2d} dd{r['full']['max_dd_pct']:4.1f}%) "
          f"h1 {r['h1']['net_usdc']:8.2f} (tr{r['h1']['trades']:2d}) h2 {r['h2']['net_usdc']:8.2f} (tr{r['h2']['trades']:2d}) "
          f"last72 {r['w72']['net_usdc']:8.2f} (tr{r['w72']['trades']:2d} dd{r['w72']['max_dd_pct']:4.1f}%) ok={r['ok']} P={r['P']}")
n_ok = sum(1 for r in results if r["ok"])
print(f"\n{n_ok}/{len(results)} configs pass all slices + trade counts")
json.dump(results[:40], open("/home/hatch/workspace/makefun/entries/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/grid2_top40.json","w"), indent=1, default=str)
