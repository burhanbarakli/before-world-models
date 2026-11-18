"""Applies the rules of PROTOKOL.md to results/gate_learned.npz. Run: python analyze_learned.py [file]"""
import os
import sys

import numpy as np

import learned  # noqa: F401  puts panda_gate1 on the path
from analyze_g import insert
from gate_learned import DELAY, ETA, GAP, HERE, LAG, PERIOD

NE = len(ETA)
FIX8 = ETA.index(8)
SEL, TEST = np.arange(10), np.arange(10, 20)  # ok axes: model, T, h, tau, gap, eta, hole, seed
PAPER, WEAK, ANALYTIC = [0, 1, 2], [3], [4]


def pick(a, table):
    """Per-run success of a policy that picks table[model, T, h, tau] on axis 5 of a."""
    idx = table[:, :, :, :, None, None, None, None]
    return np.take_along_axis(a, np.broadcast_to(idx, a.shape[:5] + (1,) + a.shape[6:]), axis=5).squeeze(5)


def scores(sel, test):
    grid_sel, grid_test = sel[:, :, :, :, :, :NE], test[:, :, :, :, :, :NE]
    fixed = int(grid_sel.mean((0, 1, 2, 3, 4, 6, 7)).argmax())
    table = grid_sel.mean((4, 6, 7)).argmax(4)
    return dict(RULE=test[:, :, :, :, :, NE].mean(), FIX8=grid_test[:, :, :, :, :, FIX8].mean(),
                FIXS=grid_test[:, :, :, :, :, fixed].mean(), TABLE=pick(grid_test, table).mean(),
                ORACLE=grid_test.mean((6, 7)).max(5).mean()), fixed, table


def diffs(s):
    return np.array([s["RULE"] - s["FIX8"], s["RULE"] - s["FIXS"], s["TABLE"] - s["RULE"]])


def boot(ok, n=2000):
    rng = np.random.default_rng(0)
    A, H, S = ok.shape[0], ok.shape[6], ok.shape[7]
    out = []
    for _ in range(n):
        a = ok[rng.integers(A, size=A)][:, :, :, :, :, :, rng.integers(H, size=H)]
        s, _, _ = scores(a[..., SEL[rng.integers(len(SEL), size=len(SEL))]],
                         a[..., TEST[rng.integers(len(TEST), size=len(TEST))]])
        out.append(diffs(s))
    return np.array(out)


def report(ok, label, und=None):
    s, fixed, table = scores(ok[..., SEL], ok[..., TEST])
    d = diffs(s)
    print(f"\n=== {label} ===")
    print("test half: " + "  ".join(f"S({k}) {v:.3f}" for k, v in s.items()) + f"  (SABIT* eta {ETA[fixed]})")
    print(f"KURAL-SABIT8 {d[0]:.3f}  KURAL-SABIT* {d[1]:.3f}  M {d[2]:.3f}")
    swap, _, _ = scores(ok[..., TEST], ok[..., SEL])
    print(f"halves swapped: M {swap['TABLE'] - swap['RULE']:.3f}, KURAL-SABIT8 {swap['RULE'] - swap['FIX8']:.3f}")
    if und is None:
        return s, table
    b = boot(ok)
    q = np.quantile(b, [0.025, 0.975], axis=0)
    c = q + (d - b.mean(0))
    print(f"bootstrap mean {b.mean(0).round(4)}")
    print(f"recentred 95%: KURAL-SABIT8 [{c[0, 0]:.3f}, {c[1, 0]:.3f}]  KURAL-SABIT* [{c[0, 1]:.3f}, {c[1, 1]:.3f}]  M [{c[0, 2]:.3f}, {c[1, 2]:.3f}]")
    p = 2 * d - q[::-1]
    print(f"pivot 95%, not used: M [{p[0, 2]:.3f}, {p[1, 2]:.3f}]  KURAL-SABIT* [{p[0, 1]:.3f}, {p[1, 1]:.3f}]")
    A = und >= 0.90
    G = s["ORACLE"] - s["FIX8"] >= 0.03
    B = c[0, 0] > 0 and c[0, 1] > 0
    U = c[1, 2]
    M = d[2]
    print(f"A {'PASS' if A else 'FAIL'} ({und:.3f})  G {'PASS' if G else 'FAIL'}  B {'PASS' if B else 'FAIL'}  U {U:.3f}")
    if not A:
        out = "field inadequate; the rule question is inconclusive"
    elif not G:
        out = "inconclusive: one eta suffices under these conditions"
    elif not B:
        out = "rule did not carry over to the learned field"
    elif M >= 0.03:
        out = "rule helps but does not suffice; field error opens room for a model"
    elif U >= 0.03:
        out = "rule supported; a small margin cannot be excluded"
    else:
        out = "rule suffices on the learned field; no eta-selecting model needed"
    print("Outcome:", out)
    return s, table


def slices(ok, an):
    te, ta = ok[..., TEST], an[..., TEST]
    _, _, table = scores(ok[..., SEL], te)
    tab = pick(te[:, :, :, :, :, :NE], table)
    print("\nSlices, c=5 mm, test half, paper arm:  KURAL  SABIT8  TABLO  analytic KURAL")
    shape = te.shape[:5]
    I = np.indices(shape)
    r, f, a = te[:, :, :, :, :, NE].mean((5, 6)), te[:, :, :, :, :, FIX8].mean((5, 6)), ta[:, :, :, :, :, NE].mean((5, 6))
    t = tab.mean((5, 6))
    def row(name, m):
        print(f"  {name:30s} {r[m].mean():.3f}  {f[m].mean():.3f}   {t[m].mean():.3f}  {a[m[:1]].mean():.3f}")
    for i, T in enumerate(PERIOD):
        row(f"T={T}", I[1] == i)
    for g, d in enumerate(GAP):
        row(f"gap={d}", I[4] == g)
    s = np.array(DELAY)[I[2]] + np.array(LAG)[I[3]]
    for lo, hi in [(0, 0.05), (0.05, 0.09), (0.09, 0.2)]:
        row(f"h+tau in [{lo}, {hi})", (s >= lo) & (s < hi))
    print("\nM per model:", [round(float(t[k].mean() - r[k].mean()), 3) for k in range(len(t))])
    print("\nTABLO eta by (h, tau), model 0 | 1 | 2, T = 8 then 4")
    for i, T in enumerate(PERIOD):
        for j, h in enumerate(DELAY):
            print(f"  T={T:g} h={int(h * 1000):3d}: " + "   ".join(" ".join(f"{ETA[table[m, i, j, l]]:g}" for m in range(table.shape[0])) for l in range(len(LAG))))


def check_analytic(D):
    """The analytic arm must equal gate_rule.npz wherever the two grids meet; h 15 and 35 ran as 20 and 40."""
    path = os.path.join(HERE, "..", "panda_gate1", "results", "gate_rule.npz")
    old = np.load(path)["data"][[0, 2]]  # T = 8, 4 out of 8, 6, 4
    same = (D[4, :, :, :, :, :NE] == old[:, :, :, :, 1:9]).mean()
    print(f"analytic arm equals gate_rule grid: {same:.6f}")


if __name__ == "__main__":
    F = np.load(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "gate_learned.npz"))
    D, U = F["data"], F["und"]
    if len(sys.argv) <= 1:
        check_analytic(D)
    und = insert(U, 0.005)
    ok = insert(D, 0.005)
    report(ok[PAPER], "paper arm, c=5 mm (primary)", und[PAPER][:, :, :, :, :, NE].mean())
    report(ok[ANALYTIC], "analytic arm, c=5 mm")
    report(ok[WEAK], "weak arm, c=5 mm, descriptive")
    slices(ok[PAPER], ok[ANALYTIC])
    te = ok[..., TEST]
    print("\nCost of learning, analytic minus paper arm, test half")
    for name, i in [("KURAL", NE), ("SABIT8", FIX8)]:
        print(f"  {name}: {te[ANALYTIC][:, :, :, :, :, i].mean() - te[PAPER][:, :, :, :, :, i].mean():.3f}")
    print(f"undisturbed SR, KURAL: paper {und[PAPER][:, :, :, :, :, NE].mean():.3f}, weak {und[WEAK][:, :, :, :, :, NE].mean():.3f}, analytic {und[ANALYTIC][:, :, :, :, :, NE].mean():.3f}")
    for c in [0.002, 0.010]:
        report(insert(D, c)[PAPER], f"paper arm, c={c * 1000:g} mm (secondary)")
