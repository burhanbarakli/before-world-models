"""The decision rules of PROTOKOL.md on results/exp_time_A.npz and results/exp_time_B.npz.

Run: python analyze_time.py [A.npz B.npz] > results/analysis_time.txt
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
B_REPS, DELTA, LEVEL = 2000, 0.5, 97.5
KAHIN, REFH, MOMENT = 0, 1, 2
HAFIZA = 1


def interval(point, boots):
    a = (100 - LEVEL) / 2
    lo, hi = np.percentile(boots, [a, 100 - a], axis=0)
    shift = point - boots.mean(0)
    return (lo, hi), (lo + shift, hi + shift), (2 * point - hi, 2 * point - lo)


def outcome(s_kahin, D, lo, hi):
    if s_kahin < 0.85:
        return "invalid: S(KAHIN) below 0.85, the setup is examined"
    if hi < DELTA:
        return "the modelless rival suffices for time here; no model"
    if D < DELTA:
        return "a small margin cannot be excluded; no model, the burden is on the model"
    if lo > 0:
        return "position knowledge leaves time the modelless rival cannot take: this setting's model is a candidate"
    return "D >= delta but its lower bound is not above 0: no decision, reported"


def fmt(name, p, pct, rec, piv, i=None):
    g = (lambda x: x) if i is None else (lambda x: x[i])
    return (f"{name:34s} {g(p):+.3f}  percentile [{g(pct[0]):+.3f}, {g(pct[1]):+.3f}]  "
            f"recentred [{g(rec[0]):+.3f}, {g(rec[1]):+.3f}]  pivot [{g(piv[0]):+.3f}, {g(piv[1]):+.3f}]")


def setting_A(path, rng):
    d = np.load(path)
    keys = list(d["keys"])
    X = d["data"]  # (arm, T, delay, gap, e, c, policy, hole, seed, key)
    ok = X[..., keys.index("ok")]
    tf = (np.array(d["period"]) + 8.0)[None, :, None, None, None, None, None, None, None]
    t = np.where(ok > 0, X[..., keys.index("t_in")], tf)  # PROTOKOL: every failed run counts as tf (Sapma 6)
    t[np.isnan(ok)] = np.nan
    nA, nh, ns = X.shape[0], X.shape[7], X.shape[8]

    def m(x, arms, holes, seeds, c=None):
        y = x[arms][:, :, :, :, 1:][..., holes, :][..., seeds]
        if c is not None:
            y = y[:, :, :, :, :, [c]]
        return y.mean(axis=(0, 1, 2, 3, 4, 5, 7, 8))  # one value per policy

    def one(a, h, s):
        T, S = m(t, a, h, s), m(ok, a, h, s)
        return np.array([T[MOMENT] - T[KAHIN], T[REFH] - T[KAHIN], T[MOMENT] - T[REFH], S[KAHIN]])

    A, H, Sd = np.arange(nA), np.arange(nh), np.arange(ns)
    point = one(A, H, Sd)
    boots = np.array([one(rng.choice(A, nA), rng.choice(H, nh), rng.choice(Sd, ns)) for _ in range(B_REPS)])
    pct, rec, piv = interval(point, boots)
    T, S = m(t, A, H, Sd), m(ok, A, H, Sd)
    print("=== A, single shot: paper arm, e > 0, both clearances (primary) ===")
    print("t: " + "  ".join(f"{n} {x:.2f}" for n, x in zip(d["policies"], T)) + "   S: " +
          "  ".join(f"{n} {x:.3f}" for n, x in zip(d["policies"], S)))
    print(fmt("D_A = t(MOMENT) - t(KAHIN), s", point, pct, rec, piv, 0))
    print("Outcome A:", outcome(S[KAHIN], point[0], pct[0][0], pct[1][0]))
    print(fmt("t(REFLEKS-H) - t(KAHIN), s", point, pct, rec, piv, 1))
    print(fmt("t(MOMENT) - t(REFLEKS-H), s", point, pct, rec, piv, 2))
    for ic, c in enumerate(d["clearances"]):
        Tc, Sc = m(t, A, H, Sd, ic), m(ok, A, H, Sd, ic)
        print(f"   c = {c * 1000:.0f} mm: t " + "  ".join(f"{x:.2f}" for x in Tc) + "   S " +
              "  ".join(f"{x:.3f}" for x in Sc) + f"   D_A {Tc[MOMENT] - Tc[KAHIN]:+.3f}")
    ue = X[..., keys.index("u_err")][:, :, :, :, :, :, MOMENT]
    print("MOMENT direction error, deg (median / 90%, share with a direction):")
    for ie, e in enumerate(d["errors"]):
        for ic, c in enumerate(d["clearances"]):
            u = ue[:, :, :, :, ie, ic].ravel()
            has = u >= 0
            if has.any():
                print(f"   e = {e * 1000:.0f} mm, c = {c * 1000:.0f} mm: {np.median(u[has]):5.1f} / "
                      f"{np.percentile(u[has], 90):5.1f}   {has.mean():.2f}")
    t0 = t[:, :, :, :, 0].mean(axis=(0, 1, 2, 3, 4, 6, 7))
    print(f"e = 0 (false trigger cost): t REFLEKS-H {t0[REFH]:.2f}  MOMENT {t0[MOMENT]:.2f}")
    ta = X[..., keys.index("t_in")]
    Ta = ta[:, :, :, :, 1:].mean(axis=(0, 1, 2, 3, 4, 5, 7, 8))
    print(f"as run (t_in, only runs not reaching depth count as tf): D_A {Ta[MOMENT] - Ta[KAHIN]:+.3f}")
    print("slices, t:                               KAHIN  REFLEKS-H  MOMENT")
    def line(label, x):
        print(f"   {label:36s} " + "  ".join(f"{v:.2f}" for v in x))
    y = t[:, :, :, :, 1:]
    for i, T_ in enumerate(d["period"]):
        line(f"T = {T_}", y[:, i].mean(axis=(0, 1, 2, 3, 4, 6, 7)))
    for i, (h, tau) in enumerate(d["delays"]):
        line(f"h + tau = {h + tau:.3f}", y[:, :, i].mean(axis=(0, 1, 2, 3, 4, 6, 7)))
    for i, g in enumerate(d["gaps"]):
        line("no disturbance" if g < 0 else f"push {g} s", y[:, :, :, i].mean(axis=(0, 1, 2, 3, 4, 6, 7)))
    for i, e in enumerate(d["errors"][1:]):
        line(f"e = {e * 1000:.0f} mm", y[:, :, :, :, i].mean(axis=(0, 1, 2, 3, 4, 6, 7)))
    over = (X[..., keys.index("f_max")] > 50)[:, :, :, :, 1:].mean(axis=(0, 1, 2, 3, 4, 5, 7, 8))
    print("over F_max: " + "  ".join(f"{n} {x:.3f}" for n, x in zip(d["policies"], over)))


def setting_B(path, rng):
    d = np.load(path)
    keys = list(d["keys"])
    X = d["data"]  # (T, delay, gap, e, c, policy, hole, seed, trial, key)
    ok = X[..., keys.index("ok")]
    tf = (np.array(d["period"]) + 8.0)[:, None, None, None, None, None, None, None, None]
    t = np.where(ok > 0, X[..., keys.index("t_in")], tf)  # PROTOKOL: every failed run counts as tf (Sapma 6)
    nh, ns = X.shape[6], X.shape[7]

    def m(x, holes, seeds):
        return x[..., holes, :, :][..., seeds, :].mean(axis=(0, 1, 2, 3, 4, 6, 7, 8))

    def one(h, s):
        T, S = m(t, h, s), m(ok, h, s)
        return np.array([T[HAFIZA] - T[KAHIN], S[KAHIN]])

    H, Sd = np.arange(nh), np.arange(ns)
    point = one(H, Sd)
    boots = np.array([one(rng.choice(H, nh), rng.choice(Sd, ns)) for _ in range(B_REPS)])
    pct, rec, piv = interval(point, boots)
    T, S = m(t, H, Sd), m(ok, H, Sd)
    print("\n=== B, persistent offset: model 0, 5-trial sequences (primary) ===")
    print("t: " + "  ".join(f"{n} {x:.2f}" for n, x in zip(d["policies"], T)) + "   S: " +
          "  ".join(f"{n} {x:.3f}" for n, x in zip(d["policies"], S)))
    print(fmt("D_B = t(HAFIZA) - t(KAHIN), s", point, pct, rec, piv, 0))
    print("Outcome B:", outcome(S[KAHIN], point[0], pct[0][0], pct[1][0]))
    ta = X[..., keys.index("t_in")].mean(axis=(0, 1, 2, 3, 4, 6, 7, 8))
    print(f"as run (t_in, only runs not reaching depth count as tf): D_B {ta[HAFIZA] - ta[KAHIN]:+.3f}")
    by = t.mean(axis=(0, 1, 2, 3, 4, 6, 7))  # (policy, trial)
    print("t by trial:  " + "  ".join(f"{k + 1}: K {by[KAHIN, k]:.2f} H {by[HAFIZA, k]:.2f}" for k in range(by.shape[1])))
    he = X[..., keys.index("hafiza_err")][:, :, :, :, :, HAFIZA]
    print("HAFIZA offset error by trial, mm (median): " +
          "  ".join(f"{np.median(he[..., k]) * 1000:.2f}" for k in range(he.shape[-1])))
    for ic, c in enumerate(d["clearances"]):
        Tc = t[:, :, :, :, ic].mean(axis=(0, 1, 2, 3, 5, 6, 7))
        print(f"   c = {c * 1000:.0f} mm: t KAHIN {Tc[KAHIN]:.2f} HAFIZA {Tc[HAFIZA]:.2f}  D_B {Tc[HAFIZA] - Tc[KAHIN]:+.3f}")


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "exp_time_A.npz")
    b = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "results", "exp_time_B.npz")
    setting_A(a, np.random.default_rng(0))
    setting_B(b, np.random.default_rng(1))
