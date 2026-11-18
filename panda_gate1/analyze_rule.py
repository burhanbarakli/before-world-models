"""Applies the rules of PROTOKOL_KURAL.md to results/gate_rule.npz. Run: python analyze_rule.py [file]"""
import sys

import numpy as np

from analyze_g import insert
from gate_rule import DELAY, ETA, GAP, LAG, PERIOD, rule

NE = len(ETA)
FIX8 = ETA.index(8)
SEL, TEST = np.arange(10), np.arange(10, 20)  # ok axes: T, h, tau, gap, eta, hole, seed


def pick(a, table):
    """Per-run success of a policy that picks table[T, h, tau] on axis 4 of a."""
    idx = table[:, :, :, None, None, None, None]
    return np.take_along_axis(a, np.broadcast_to(idx, a.shape[:4] + (1,) + a.shape[5:]), axis=4).squeeze(4)


def scores(sel, test):
    """sel and test: float or bool, full eta axis including the rule at index NE."""
    grid_sel = sel[:, :, :, :, :NE]
    grid_test = test[:, :, :, :, :NE]
    fixed = int(grid_sel.mean((0, 1, 2, 3, 5, 6)).argmax())
    table = grid_sel.mean((3, 5, 6)).argmax(3)
    return dict(RULE=test[:, :, :, :, NE].mean(), FIX8=grid_test[:, :, :, :, FIX8].mean(),
                FIXS=grid_test[:, :, :, :, fixed].mean(), TABLE=pick(grid_test, table).mean(),
                ORACLE=grid_test.mean((5, 6)).max(4).mean()), fixed, table


def boot(ok, n=2000):
    rng = np.random.default_rng(0)
    H, S = ok.shape[5], ok.shape[6]
    out = []
    for _ in range(n):
        h = rng.integers(H, size=H)
        a = ok[:, :, :, :, :, h]
        s, _, _ = scores(a[..., SEL[rng.integers(len(SEL), size=len(SEL))]],
                         a[..., TEST[rng.integers(len(TEST), size=len(TEST))]])
        out.append((s["RULE"] - s["FIX8"], s["RULE"] - s["FIXS"], s["TABLE"] - s["RULE"]))
    return np.quantile(np.array(out), [0.025, 0.975], axis=0)


def report(ok, label, full):
    s, fixed, table = scores(ok[..., SEL], ok[..., TEST])
    print(f"\n=== {label} ===")
    print("test half: " + "  ".join(f"S({k}) {v:.3f}" for k, v in s.items()) + f"  (SABIT* eta {ETA[fixed]})")
    M = s["TABLE"] - s["RULE"]
    print(f"KURAL-SABIT8 {s['RULE'] - s['FIX8']:.3f}  KURAL-SABIT* {s['RULE'] - s['FIXS']:.3f}  M {M:.3f}")
    swap, _, _ = scores(ok[..., TEST], ok[..., SEL])
    print(f"halves swapped: M {swap['TABLE'] - swap['RULE']:.3f}, KURAL-SABIT8 {swap['RULE'] - swap['FIX8']:.3f}")
    if not full:
        return
    q = boot(ok)
    print(f"95%: KURAL-SABIT8 [{q[0, 0]:.3f}, {q[1, 0]:.3f}]  KURAL-SABIT* [{q[0, 1]:.3f}, {q[1, 1]:.3f}]  M [{q[0, 2]:.3f}, {q[1, 2]:.3f}]")
    G = s["ORACLE"] - s["FIX8"] >= 0.03
    B = q[0, 0] > 0 and q[0, 1] > 0
    U = q[1, 2]
    print(f"G {'PASS' if G else 'FAIL'}  B {'PASS' if B else 'FAIL'}  U {U:.3f}")
    if not G:
        out = "inconclusive: one eta suffices under these conditions"
    elif not B:
        out = "rule not confirmed"
    elif M >= 0.03:
        out = "rule helps but does not suffice; room for a model stays open"
    elif U >= 0.03:
        out = "rule supported; a small margin cannot be excluded"
    else:
        out = "rule confirmed; no eta-selecting model needed on this task"
    print("Outcome:", out)


def slices(ok):
    te = ok[..., TEST]
    _, _, table = scores(ok[..., SEL], te)
    tab = pick(te[:, :, :, :, :NE], table)
    print("\nSlices, c=5 mm, test half:        KURAL  SABIT8  TABLO")
    def row(name, m):
        print(f"  {name:28s} {te[:, :, :, :, NE].mean((4, 5))[m].mean():.3f}  {te[:, :, :, :, FIX8].mean((4, 5))[m].mean():.3f}   {tab.mean((4, 5))[m].mean():.3f}")
    shape = te.shape[:4]
    I = np.indices(shape)
    for i, T in enumerate(PERIOD):
        row(f"T={T}", I[0] == i)
    for g, d in enumerate(GAP):
        row(f"gap={d}", I[3] == g)
    s = np.array(DELAY)[I[1]] + np.array(LAG)[I[2]]
    for lo, hi in [(0, 0.05), (0.05, 0.09), (0.09, 0.2)]:
        row(f"h+tau in [{lo}, {hi})", (s >= lo) & (s < hi))
    print("\nTABLO eta by (h, tau), rule value after the slash")
    for i, T in enumerate(PERIOD):
        print(f"  T={T}")
        for j, h in enumerate(DELAY):
            print(f"    h={int(h * 1000):3d}: " + "  ".join(f"{ETA[table[i, j, l]]:g}/{rule(h, t):.1f}" for l, t in enumerate(LAG)))


if __name__ == "__main__":
    D = np.load(sys.argv[1] if len(sys.argv) > 1 else "results/gate_rule.npz")["data"]
    report(insert(D, 0.005), "c=5 mm (primary)", True)
    slices(insert(D, 0.005))
    report(insert(D, 0.002), "c=2 mm (secondary)", False)
    report(insert(D, 0.010), "c=10 mm (secondary)", False)
