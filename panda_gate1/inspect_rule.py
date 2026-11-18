"""Is the pre-registered bootstrap biased? Sampling seeds with replacement shrinks the selection set."""
import numpy as np
from analyze_g import insert
from analyze_rule import scores, boot, SEL, TEST, NE
D = np.load("results/gate_rule.npz")["data"]
ok = insert(D, 0.005)
s, _, _ = scores(ok[..., SEL], ok[..., TEST])
pt = np.array([s["RULE"] - s["FIX8"], s["RULE"] - s["FIXS"], s["TABLE"] - s["RULE"]])
print("axes", ok.shape, "point", pt.round(4))
rng = np.random.default_rng(1)
H = ok.shape[5]
def draw(mode):
    h = rng.integers(H, size=H)
    a = ok[:, :, :, :, :, h]
    if mode == "orig":
        se = SEL[rng.integers(10, size=10)]; te = TEST[rng.integers(10, size=10)]
    elif mode == "sel_fixed":      # selection set kept whole, only test seeds and holes vary
        se = SEL; te = TEST[rng.integers(10, size=10)]
    elif mode == "holes_fixed":    # no hole resampling
        a = ok; se = SEL[rng.integers(10, size=10)]; te = TEST[rng.integers(10, size=10)]
    s, _, _ = scores(a[..., se], a[..., te])
    return s["RULE"] - s["FIX8"], s["RULE"] - s["FIXS"], s["TABLE"] - s["RULE"]
for mode in ["orig", "sel_fixed", "holes_fixed"]:
    x = np.array([draw(mode) for _ in range(1000)])
    m = x.mean(0); q = np.quantile(x, [.025, .975], axis=0)
    print(f"{mode:12s} mean {m.round(4)} lo {q[0].round(4)} hi {q[1].round(4)}  shift-corrected hi {(q[1] + pt - m).round(4)} lo {(q[0] + pt - m).round(4)}")
# random 10/10 splits of the seeds, no resampling: distribution of M over the arbitrary split
M = []
for _ in range(1000):
    p = rng.permutation(20)
    s, _, _ = scores(ok[..., p[:10]], ok[..., p[10:]])
    M.append((s["RULE"] - s["FIX8"], s["RULE"] - s["FIXS"], s["TABLE"] - s["RULE"]))
M = np.array(M)
print("random splits mean", M.mean(0).round(4), "q2.5", np.quantile(M, .025, axis=0).round(4), "q97.5", np.quantile(M, .975, axis=0).round(4))
# leave one hole out
for i in range(H):
    k = [j for j in range(H) if j != i]
    s, _, _ = scores(ok[:, :, :, :, :, k][..., SEL], ok[:, :, :, :, :, k][..., TEST])
    print(f"without hole {i}: RULE {s['RULE']:.3f} FIX8 {s['FIX8']:.3f} FIXS {s['FIXS']:.3f} TABLE {s['TABLE']:.3f} M {s['TABLE']-s['RULE']:.3f}")
# per-hole test scores
te = ok[..., TEST]
print("per hole RULE", te[:, :, :, :, NE].mean((0, 1, 2, 3, 5)).round(3), "FIX8", te[:, :, :, :, 4].mean((0, 1, 2, 3, 5)).round(3))
