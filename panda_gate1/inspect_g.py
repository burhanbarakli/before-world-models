"""Is M a learnable structure or a coarse constant? Exploratory, written after seeing analysis_g.txt.

Selection on seeds 0-9, score on seeds 10-19, as in PROTOKOL_GEC.md. Run: python inspect_g.py
"""
import numpy as np

import analyze_g as A
from gate1g import DELAY, ETA, LAG

D = np.load("results/gate1g.npz")["data"]
KS = [0.3, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0, 1.2, 1.5, 2.0]


def boot(a, b):
    d = (a.astype(float) - b.astype(float)).mean((0, 1, 2, 3))
    rng = np.random.default_rng(0)
    H, N = d.shape
    s = [d[rng.integers(H, size=H)][:, rng.integers(N, size=N)].mean() for _ in range(2000)]
    return d.mean(), np.quantile(s, 0.025), np.quantile(s, 0.975)


def by_sum(tr):
    """Best eta for each value of h + tau, the same for both T."""
    sums = sorted({round(h + t, 3) for h in DELAY for t in LAG})
    best = {s: 0 for s in sums}
    for s in sums:
        cells = [(j, l) for j, h in enumerate(DELAY) for l, t in enumerate(LAG) if round(h + t, 3) == s]
        best[s] = int(np.mean([tr[:, j, l].mean((0, 1)) for j, l in cells], axis=0).argmax())
    table = np.zeros(tr.shape[:3], int)
    for i, j, l in np.ndindex(*table.shape):
        table[i, j, l] = best[round(DELAY[j] + LAG[l], 3)]
    return table, {s: ETA[b] for s, b in best.items()}


def plain(k, shape):
    """eta = k / (h + tau), nearest grid value; no knowledge of T."""
    table = np.zeros(shape, int)
    for i, j, l in np.ndindex(*shape):
        s = DELAY[j] + LAG[l]
        table[i, j, l] = A.nearest(np.inf if s == 0 else k / s) if s else len(ETA) - 1
    return table


for c in [0.005, 0.002, 0.010]:
    ok = A.insert(D, c)
    tr, te = ok[..., A.TRAIN].mean((5, 6)), ok[..., A.TEST]
    shape = tr.shape[:3]
    table = tr.mean(3).argmax(3)
    Tb = A.score(te, table)
    print(f"\n=== c={c * 1000:g} mm ===")
    print(f"S(TABLO) {Tb.mean():.3f}")
    print("k    train  test   (eta = k/(h+tau), capped at 20, T not used)")
    scores = {}
    for k in KS:
        t = plain(k, shape)
        scores[k] = A.score(ok[..., A.TRAIN], t).mean()
        print(f"{k:4g} {scores[k]:.3f}  {A.score(te, t).mean():.3f}")
    k = max(scores, key=scores.get)
    P = A.score(te, plain(k, shape))
    print(f"k chosen on the selection half: {k}; S {P.mean():.3f}; M {boot(Tb, P)[0]:.3f} [{boot(Tb, P)[1]:.3f}, {boot(Tb, P)[2]:.3f}]")
    t2, best = by_sum(tr)
    S2 = A.score(te, t2)
    print(f"Table on h+tau only, both T: S {S2.mean():.3f}; TABLO minus it {boot(Tb, S2)[0]:.3f}; table {best}")
