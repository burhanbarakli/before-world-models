"""The decision rules of PROTOKOL.md on results/exp_contact.npz.

Run: python analyze_contact.py [path] > results/analysis_contact.txt
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
B = 2000
C5, C2 = 0, 1
TABAN, REFLEKS, KAHIN = 0, 1, 2
NAMES = ["TABAN", "REFLEKS", "KAHIN"]


def load(path):
    d = np.load(path)
    keys = list(d["keys"])
    return d, keys


def score(ok, models, holes, seeds, c=C5, errs=(1, 2, 3)):
    """ok: (arm, T, delay, gap, e, c, policy, hole, seed). Mean over the cell grid, gaps weighted equally.
    Returns one value per policy."""
    x = ok[np.ix_(models)][:, :, :, :, list(errs), c][..., holes, :][..., seeds]
    return x.mean(axis=(0, 1, 2, 3, 4, 6, 7))


def stats(ok, models, rng, c=C5):
    holes, seeds = np.arange(ok.shape[7]), np.arange(ok.shape[8])
    def one(m, h, s):
        S = score(ok, m, h, s, c)
        S0 = score(ok, m, h, s, c, errs=(0,))
        return np.array([S0[TABAN], S0[TABAN] - S[TABAN], S[REFLEKS] - S[TABAN], S[KAHIN] - S[REFLEKS]]), S
    point, S = one(models, holes, seeds)
    boots = np.array([one(rng.choice(models, len(models)), rng.choice(holes, len(holes)),
                          rng.choice(seeds, len(seeds)))[0] for _ in range(B)])
    lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
    shift = point - boots.mean(0)
    return point, S, (lo, hi), (lo + shift, hi + shift), (2 * point - hi, 2 * point - lo)


def outcome(point, lo, hi, s_ref):
    G, K, R, W = point
    if G < 0.85:
        return "invalid: TABAN at e = 0 below 0.85, the setup is examined"
    if not (K >= 0.10 and lo[1] > 0):
        return "K failed: contact and these position errors are no problem, no model"
    if hi[3] < 0.03:
        return "no position-estimating model needed; " + ("REFLEKS suffices" if s_ref >= 0.85
                                                          else "REFLEKS below 0.85, the problem is not the position")
    if W < 0.03:
        return "a small margin cannot be excluded; no model, the burden is on the model"
    if lo[3] > 0:
        return "position knowledge leaves a margin: a simple estimator first, then a model"
    return "W >= 0.03 but its lower bound is not above 0: no row of the table applies, reported as no decision"


def mean_over(x, models, c=C5, errs=(1, 2, 3)):
    return x[np.ix_(models)][:, :, :, :, list(errs), c].mean(axis=(0, 1, 2, 3, 4, 6, 7))


def report(path):
    d, keys = load(path)
    data = d["data"]
    arms = list(d["arms"])
    ok = data[..., keys.index("ok")]
    paper = [arms.index(a) for a in (0, 1, 2)]
    analytic = [arms.index(-1)]
    rng = np.random.default_rng(0)
    point, S, pct, rec, piv = stats(ok, paper, rng)
    print("=== paper arm, c = 5 mm, e > 0 (primary) ===")
    print("S: " + "  ".join(f"{n} {s:.3f}" for n, s in zip(NAMES, S)))
    for i, n in enumerate(["G  S(TABAN, e=0)", "K  S_e0(TABAN) - S(TABAN)", "R  S(REFLEKS) - S(TABAN)",
                           "W  S(KAHIN) - S(REFLEKS)"]):
        print(f"{n:28s} {point[i]:+.3f}  percentile [{pct[0][i]:+.3f}, {pct[1][i]:+.3f}]  "
              f"recentred [{rec[0][i]:+.3f}, {rec[1][i]:+.3f}]  pivot [{piv[0][i]:+.3f}, {piv[1][i]:+.3f}]")
    print("Outcome:", outcome(point, *pct, S[REFLEKS]))

    t_in = data[..., keys.index("t_in")]
    ti = mean_over(t_in, paper)
    print(f"\narrival time, s (failures count as tf): " + "  ".join(f"{n} {t:.2f}" for n, t in zip(NAMES, ti)) +
          f"   REFLEKS - KAHIN {ti[REFLEKS] - ti[KAHIN]:+.2f}")
    if point[3] < 0.03 and ti[REFLEKS] - ti[KAHIN] >= 1.0:
        print("Time clause: W small but KAHIN saves at least 1 s; success does not open the model, "
              "a separate protocol with time as the target is needed")
    deep = data[..., keys.index("deep")]
    jam = data[..., keys.index("jam")]
    over = (data[..., keys.index("f_max")] > 50.0).astype(float)
    print("failure types, paper arm, c = 5, e > 0 (share of runs):")
    for i, n in enumerate(NAMES):
        print(f"   {n:8s} not deep {1 - mean_over(deep, paper)[i]:.3f}  jammed {mean_over(jam, paper)[i]:.3f}  "
              f"over F_max {mean_over(over, paper)[i]:.3f}")
    print(f"1 - S(KAHIN): {1 - S[KAHIN]:.3f}")

    for name, models in [("analytic arm", analytic)] + [(f"model {a}", [arms.index(a)]) for a in (0, 1, 2)]:
        Sa = score(ok, models, np.arange(5), np.arange(ok.shape[8]))
        S0 = score(ok, models, np.arange(5), np.arange(ok.shape[8]), errs=(0,))
        print(f"\n{name}: " + "  ".join(f"{n} {s:.3f}" for n, s in zip(NAMES, Sa)) +
              f"   TABAN e=0 {S0[TABAN]:.3f}   W {Sa[KAHIN] - Sa[REFLEKS]:+.3f}")

    point2, S2, pct2, _, _ = stats(ok, paper, np.random.default_rng(1), c=C2)
    print("\n=== paper arm, c = 2 mm (secondary) ===")
    print("S: " + "  ".join(f"{n} {s:.3f}" for n, s in zip(NAMES, S2)) +
          f"   G {point2[0]:.3f}  K {point2[1]:+.3f}  R {point2[2]:+.3f}  W {point2[3]:+.3f} "
          f"[{pct2[0][3]:+.3f}, {pct2[1][3]:+.3f}]")

    print("\nslices, paper arm, c = 5, e > 0:             TABAN  REFLEKS  KAHIN")
    x = ok[np.ix_(paper)][:, :, :, :, :, C5]
    def line(label, sub):
        print(f"   {label:38s} " + "  ".join(f"{v:.3f}" for v in sub))
    for i, T in enumerate(d["period"]):
        line(f"T = {T}", x[:, i, :, :, 1:].mean(axis=(0, 1, 2, 3, 5, 6)))
    for i, (h, tau) in enumerate(d["delays"]):
        line(f"h + tau = {h + tau:.3f}", x[:, :, i, :, 1:].mean(axis=(0, 1, 2, 3, 5, 6)))
    for i, g in enumerate(d["gaps"]):
        line("no disturbance" if g < 0 else f"push {g} s before the rim", x[:, :, :, i, 1:].mean(axis=(0, 1, 2, 3, 5, 6)))
    for i, e in enumerate(d["errors"]):
        line(f"e = {e * 1000:.0f} mm", x[:, :, :, :, i].mean(axis=(0, 1, 2, 3, 5, 6)))
    if "mu" in d:
        mu = d["mu"]  # (T, hole, seed)
        for lo_, hi_ in [(0.2, 0.4), (0.4, 0.6), (0.6, 0.8)]:
            m = (mu >= lo_) & (mu < hi_)
            y = x[:, :, :, :, 1:]  # (model, T, delay, gap, e, policy, hole, seed)
            w = np.broadcast_to(m[None, :, None, None, None, None], y.shape)
            line(f"mu in [{lo_}, {hi_})", (y * w).sum(axis=(0, 1, 2, 3, 4, 6, 7)) / w.sum(axis=(0, 1, 2, 3, 4, 6, 7)))
    pushed = data[..., keys.index("pushed")][np.ix_(paper)][:, :, :, 1]
    print(f"\npush applied in disturbed runs: {np.nanmean(pushed):.3f}")


if __name__ == "__main__":
    report(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "exp_contact.npz"))
