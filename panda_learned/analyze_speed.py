"""Applies the rules of PROTOKOL_KAPI.md. Run: python analyze_speed.py [file]"""
import os
import sys

import numpy as np

import learned  # noqa: F401  puts panda_gate1 on the path
from analyze_g import insert
from gate_learned import DELAY, GAP, HERE, LAG, PERIOD
from gate_speed import LO

SEL, TEST = np.arange(10), np.arange(10, 20)  # ok axes: model, T, h, tau, gap, option, hole, seed
PAPER, WEAK, ANALYTIC = [0, 1, 2], [3], [4]
NOGATE, GATE0 = 0, 1 + LO.index(0.02)  # option axis: no gate, then the grid of LO


def pick(a, table):
    idx = table[:, :, :, :, None, None, None, None]
    return np.take_along_axis(a, np.broadcast_to(idx, a.shape[:5] + (1,) + a.shape[6:]), axis=5).squeeze(5)


def scores(sel, test):
    table = sel.mean((4, 6, 7)).argmax(4)
    return dict(RULE=test[:, :, :, :, :, NOGATE].mean(), GATE0=test[:, :, :, :, :, GATE0].mean(),
                TABLE=pick(test, table).mean(), RUN=test.max(5).mean())


def diffs(s):
    return np.array([s["GATE0"] - s["RULE"], s["TABLE"] - s["GATE0"], s["RUN"] - s["GATE0"]])


def boot(ok, n=2000):
    rng = np.random.default_rng(0)
    A, H = ok.shape[0], ok.shape[6]
    out = []
    for _ in range(n):
        a = ok[rng.integers(A, size=A)][:, :, :, :, :, :, rng.integers(H, size=H)]
        out.append(diffs(scores(a[..., SEL[rng.integers(10, size=10)]], a[..., TEST[rng.integers(10, size=10)]])))
    return np.array(out)


def report(ok, label, decide=False):
    s = scores(ok[..., SEL], ok[..., TEST])
    d = diffs(s)
    print(f"\n=== {label} ===")
    print("test half: " + "  ".join(f"S({k}) {v:.3f}" for k, v in s.items()))
    print(f"H {d[0]:.3f}  P {d[1]:.3f}  Q {d[2]:.3f}")
    print("S by L: " + "  ".join(f"{l}: {ok[..., TEST][:, :, :, :, :, 1 + i].mean():.3f}" for i, l in enumerate(LO)))
    if not decide:
        return
    b = boot(ok)
    q = np.quantile(b, [0.025, 0.975], axis=0)
    c = q + (d - b.mean(0))
    print(f"recentred 95%: H [{c[0, 0]:.3f}, {c[1, 0]:.3f}]  P [{c[0, 1]:.3f}, {c[1, 1]:.3f}]  Q [{c[0, 2]:.3f}, {c[1, 2]:.3f}]")
    if not (d[0] >= 0.03 and c[0, 0] > 0):
        out = "gate fails; no model on this task either"
    elif d[2] < 0.03:
        out = "gate suffices; even a perfect per-run predictor leaves no margin"
    elif d[1] >= 0.03:
        out = "per-condition selection leaves room; look for a simpler gate rule first"
    else:
        out = "no decision: Q contains chance; needs a held-out per-run predictor"
    print("Outcome:", out)


def slices(ok):
    te = ok[..., TEST]
    print("\nSlices, c=5 mm, test half, paper arm:  KURAL  KAPI0")
    r, g = te[:, :, :, :, :, NOGATE].mean((5, 6)), te[:, :, :, :, :, GATE0].mean((5, 6))
    I = np.indices(r.shape)
    def row(name, m):
        print(f"  {name:30s} {r[m].mean():.3f}  {g[m].mean():.3f}")
    for i, T in enumerate(PERIOD):
        row(f"T={T}", I[1] == i)
    for k, d in enumerate(GAP):
        row(f"gap={d}", I[4] == k)
    s = np.array(DELAY)[I[2]] + np.array(LAG)[I[3]]
    for lo, hi in [(0, 0.05), (0.05, 0.09), (0.09, 0.2)]:
        row(f"h+tau in [{lo}, {hi})", (s >= lo) & (s < hi))


def check_analytic(ok_new, path):
    """Delays of 70 and 90 ms ran identically in gate_rule, so no-gate analytic runs must equal its rule arm."""
    D = np.load(path)["data"][[0, 2]][:, 2:, :, :, 9]
    same = (np.load(ok_new)["data"][4, :, 2:, :, :, 0] == D).mean()
    print(f"analytic no-gate arm equals gate_rule rule arm at h = 70, 90: {same:.6f}")


def rescued(ok, path):
    """Analytic arm only: runs that fail at every eta of gate_rule, and what a gate does for them."""
    old = insert(np.load(path)["data"][[0, 2]][:, :, :, :, :9], 0.005)  # grid only; h 15, 35 ran as 20, 40
    fail = ~old.any(4)
    print(f"\nanalytic arm, runs failing at every eta: {fail.mean():.3f}; rescued by any gate: {(ok[0, ..., 1:, :, :].any(4) & fail).sum() / fail.sum():.3f}; by KAPI0: {(ok[0, ..., GATE0, :, :] & fail).sum() / fail.sum():.3f}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "gate_speed.npz")
    old = os.path.join(HERE, "..", "panda_gate1", "results", "gate_rule.npz")
    F = np.load(path)
    S, Un = F["data"], insert(F["und"], 0.005)
    if len(sys.argv) <= 1:
        check_analytic(path, old)
    print(f"undisturbed SR, KURAL: paper {Un[PAPER][:, :, :, :, :, NOGATE].mean():.3f}, weak {Un[WEAK][:, :, :, :, :, NOGATE].mean():.3f}, analytic {Un[ANALYTIC][:, :, :, :, :, NOGATE].mean():.3f}")
    for c, label in [(0.005, "c=5 mm"), (0.002, "c=2 mm"), (0.010, "c=10 mm")]:
        ok = insert(S, c)
        report(ok[PAPER], f"paper arm, {label}" + (" (primary)" if c == 0.005 else ""), c == 0.005)
        if c == 0.005:
            report(ok[ANALYTIC], "analytic arm, c=5 mm")
            report(ok[WEAK], "weak arm, c=5 mm")
            slices(ok[PAPER])
            rescued(ok[ANALYTIC], old)
            print(f"\nKAPI0 runs too shallow at tf, paper arm: {(S[PAPER][:, :, :, :, :, GATE0, :, :, 2] > 0.25 - 0.054).mean():.3f}; KURAL {(S[PAPER][:, :, :, :, :, NOGATE, :, :, 2] > 0.25 - 0.054).mean():.3f}")
