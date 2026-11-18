"""Applies the decision rules of PROTOKOL.md to results/gate1.npz. Run: python analyze_gate.py"""
import numpy as np

from gate1 import DELAY, ETA, KEYS, LAG, PERIOD
from robot import DEPTH, RIM_Z

D = np.load("results/gate1.npz")["data"]  # T, h, tau, eta, hole, kind, seed, key
k = {n: D[..., i] for i, n in enumerate(KEYS)}


def insert(c):
    return ((RIM_Z - k["end_z"]) >= 0.9 * DEPTH) & (k["lat"] <= c) & (k["tilt"] <= np.arctan(2 * c / DEPTH))


def wilson(s, n=100, z=1.96):
    p = s
    d = 1 + z**2 / n
    m = (p + z**2 / (2 * n)) / d
    r = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return m - r, m + r


def table(sr, it):
    print("      h\\eta " + " ".join(f"{e:5g}" for e in ETA) + "  best")
    for ih, h in enumerate(DELAY):
        row = sr[it, ih]
        print(f"  {int(h * 1000):4d} ms   " + " ".join(f"{v:5.2f}" for v in row) + f"  {row.max():.2f}")


def rules(sr, label):
    print(f"\n=== Decision, {label} ===")
    R = [(i, j, l) for i in range(len(PERIOD)) for j, h in enumerate(DELAY) for l, t in enumerate(LAG)
         if h <= 0.1 and t <= 0.05]
    drops = []
    for i, j, l in R:
        best, ideal = sr[i, j, l].max(), sr[i, 0, 0].max()
        lo_i, _ = wilson(ideal)
        _, hi = wilson(best)
        drops.append((ideal - best, ideal - best >= 0.10 and hi < lo_i, PERIOD[i], DELAY[j], LAG[l], best, ideal))
    d = max(drops, key=lambda x: x[0])
    print(f"1a: largest drop {d[0]:.2f} at T={d[2]} h={d[3]} tau={d[4]} (best {d[5]:.2f} vs ideal {d[6]:.2f});",
          "PASS" if any(x[1] for x in drops) else "FAIL")
    meanR = np.mean([sr[i, j, l] for i, j, l in R], axis=0)
    rob = int(meanR.argmax())
    reg = np.array([sr[i, j, l].max() - sr[i, j, l, rob] for i, j, l in R])
    pass_b = reg.max() >= 0.10 and reg.mean() >= 0.03
    print("mean SR over R by eta:", dict(zip(ETA, np.round(meanR, 3))))
    print(f"1b: eta_rob {ETA[rob]}; max regret {reg.max():.3f}; mean regret {reg.mean():.3f};", "PASS" if pass_b else "FAIL")
    # 1c: analytic rule, nearest grid value.
    reg_rule = []
    for i, j, l in R:
        ideal_eta = ETA[int(sr[i, 0, 0].argmax())]
        lim = np.inf if DELAY[j] + LAG[l] == 0 else 1 / (2 * (DELAY[j] + LAG[l]))
        e = min(ideal_eta, lim)
        idx = int(np.argmin(np.abs(np.log(np.array(ETA)) - np.log(e))))
        reg_rule.append(sr[i, j, l].max() - sr[i, j, l, idx])
    reg_rule = np.array(reg_rule)
    print(f"1c (reported always, applies only if 1b passes): rule regret mean {reg_rule.mean():.3f} max {reg_rule.max():.3f}")


sr5 = insert(0.005).mean((4, 5, 6))
paper = ((k["end_p"] <= 0.02) & (k["end_r"] <= 0.2)).mean((4, 5, 6))
print("Validity, paper SR, h=0 tau=0 T=8, by eta:", dict(zip(ETA, np.round(paper[0, 0, 0], 3))))
for il, t in enumerate(LAG):
    for it, T in enumerate(PERIOD):
        print(f"\nSR_insert c=5mm, T={T}, tau={int(t * 1000)} ms")
        table(sr5[:, :, il], it)
for c in [0.002, 0.005, 0.010]:
    rules(insert(c).mean((4, 5, 6)), f"c={c * 1000:g} mm" + (" (primary)" if c == 0.005 else " (secondary)"))
rules(paper, "paper SR (secondary)")
print("\nBy disturbance kind, c=5mm, T=4, tau=50ms")
for kd, n in enumerate(["D1", "D2"]):
    print(n)
    s = insert(0.005)[:, :, :, :, :, kd].mean((4, 5))
    table(s[:, :, 1] , 1)
