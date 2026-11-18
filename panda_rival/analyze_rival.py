"""The decision rule of PROTOKOL.md on results/rival.npz.

Run: python analyze_rival.py [path] > results/analysis_rival.txt
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
B_REPS, DELTA = 2000, 0.5
DOKUN, MOMENT2, KAHIN, MOMENT, MOMENT2F = 0, 1, 2, 3, 4


def outcome(s_dokun, D, lo, hi):
    if s_dokun < 0.85:
        return "invalid: S(DOKUN-KAHIN) below 0.85, the bound policy is examined"
    if hi < DELTA:
        return "the hand-made rival suffices; no model for position estimation during contact"
    if D < DELTA:
        return "a small margin cannot be excluded; no model, the burden is on the model"
    if lo > 0:
        return "an information gap remains: a learned estimator in a separate protocol, rival MOMENT-2"
    return "D2 >= delta but its lower bound is not above 0: no decision, reported"


def report(path):
    d = np.load(path)
    keys = list(d["keys"])
    X = d["data"]  # (arm, T, delay, gap, e, c, policy, hole, seed, key)
    ok = X[..., keys.index("ok")]
    tf = (np.array(d["period"]) + 8.0)[None, :, None, None, None, None, None, None, None]
    t = np.where(ok > 0, X[..., keys.index("t_in")], tf)  # every failed run counts as tf
    t[np.isnan(ok)] = np.nan
    nA, nh, ns = X.shape[0], X.shape[7], X.shape[8]

    def m(x, a, h, s, pol):
        return np.nanmean(x[a][:, :, :, :, 1:, :, pol][..., h, :][..., s])

    def one(a, h, s):
        return np.array([m(t, a, h, s, MOMENT2) - m(t, a, h, s, DOKUN), m(ok, a, h, s, DOKUN),
                         m(t, a, h, s, MOMENT2F) - m(t, a, h, s, DOKUN)])

    A, H, Sd = np.arange(nA), np.arange(nh), np.arange(ns)
    point = one(A, H, Sd)
    rng = np.random.default_rng(0)
    boots = np.array([one(rng.choice(A, nA), rng.choice(H, nh), rng.choice(Sd, ns)) for _ in range(B_REPS)])
    lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
    sh = point - boots.mean(0)
    print("=== MOMENT-2 against DOKUN-KAHIN, models 0-2, e > 0, both clearances (primary) ===")
    print(f"t: DOKUN {m(t, A, H, Sd, DOKUN):.2f}  MOMENT-2 {m(t, A, H, Sd, MOMENT2):.2f}   "
          f"S: DOKUN {m(ok, A, H, Sd, DOKUN):.3f}  MOMENT-2 {m(ok, A, H, Sd, MOMENT2):.3f}")
    print(f"D2 = t(MOMENT-2) - t(DOKUN), s   {point[0]:+.3f}  percentile [{lo[0]:+.3f}, {hi[0]:+.3f}]  "
          f"recentred [{lo[0] + sh[0]:+.3f}, {hi[0] + sh[0]:+.3f}]  pivot [{2 * point[0] - hi[0]:+.3f}, "
          f"{2 * point[0] - lo[0]:+.3f}]")
    print("Outcome:", outcome(point[1], point[0], lo[0], hi[0]))
    print(f"as registered, MOMENT-2F (fixed step c, Sapma 1): t {m(t, A, H, Sd, MOMENT2F):.2f}  "
          f"S {m(ok, A, H, Sd, MOMENT2F):.3f}  D2F {point[2]:+.3f}  percentile [{lo[2]:+.3f}, {hi[2]:+.3f}]")
    print("Outcome as registered:", outcome(point[1], point[2], lo[2], hi[2]))

    print("\nD2 by cell (s):        e = 3    e = 6    e = 10       D2F: e = 3    e = 6    e = 10")
    for ic, c in enumerate(d["clearances"]):
        row = [np.nanmean(t[:, :, :, :, ie, ic, P]) - np.nanmean(t[:, :, :, :, ie, ic, DOKUN])
               for P in (MOMENT2, MOMENT2F) for ie in (1, 2, 3)]
        print(f"   c = {c * 1000:.0f} mm          " + "  ".join(f"{x:+.3f}" for x in row[:3]) + "          " +
              "  ".join(f"{x:+.3f}" for x in row[3:]))
    for i, (h, tau) in enumerate(d["delays"]):
        print(f"   h + tau = {(h + tau) * 1000:.0f} ms: D2 {np.nanmean(t[:, :, i, :, 1:, :, MOMENT2]) - np.nanmean(t[:, :, i, :, 1:, :, DOKUN]):+.3f}")
    for i, g in enumerate(d["gaps"]):
        lab = "no disturbance" if g < 0 else f"push {g} s"
        print(f"   {lab}: D2 {np.nanmean(t[:, :, :, i, 1:, :, MOMENT2]) - np.nanmean(t[:, :, :, i, 1:, :, DOKUN]):+.3f}")

    z = (slice(0, 1), slice(None), slice(None), slice(None), slice(1, None), slice(None))
    tm = {n: np.nanmean(t[z + (p,)]) for n, p in [("KAHIN", KAHIN), ("DOKUN", DOKUN), ("MOMENT2", MOMENT2), ("MOMENT", MOMENT)]}
    sm = {n: np.nanmean(ok[z + (p,)]) for n, p in [("KAHIN", KAHIN), ("DOKUN", DOKUN), ("MOMENT2", MOMENT2), ("MOMENT", MOMENT)]}
    print("\nmodel 0, e > 0 (descriptive): " + "  ".join(f"{n} t {tm[n]:.2f} S {sm[n]:.3f}" for n in tm))
    print(f"   improvement t(MOMENT) - t(MOMENT-2) {tm['MOMENT'] - tm['MOMENT2']:+.3f}   "
          f"out of reach t(DOKUN) - t(KAHIN) {tm['DOKUN'] - tm['KAHIN']:+.3f}   "
          f"MOMENT-2 - DOKUN {tm['MOMENT2'] - tm['DOKUN']:+.3f}")
    aims = X[..., keys.index("aims")][:, :, :, :, 1:, :, MOMENT2]
    e1 = X[..., keys.index("est_first")][:, :, :, :, 1:, :, MOMENT2]
    eL = X[..., keys.index("est_last")][:, :, :, :, 1:, :, MOMENT2]
    print("MOMENT-2 aims (mean) and estimate error first / last, mm (median, runs with an estimate):")
    for ie, e in enumerate(d["errors"][1:]):
        for ic, c in enumerate(d["clearances"]):
            a = aims[:, :, :, :, ie, ic].ravel()
            f1, fl = e1[:, :, :, :, ie, ic].ravel(), eL[:, :, :, :, ie, ic].ravel()
            has = f1 >= 0
            s = (f"{np.median(f1[has]) * 1000:5.2f} / {np.median(fl[has]) * 1000:5.2f}" if has.any() else "   none")
            print(f"   e = {e * 1000:2.0f} mm, c = {c * 1000:.0f} mm: aims {np.nanmean(a):.2f}   {s}   share {has.mean():.2f}")
    # e = 0: MOMENT-2 starts at s-hat = 0 = e, the same situation as KAHIN at e = 3 (audit point 4)
    for ic, c in enumerate(d["clearances"]):
        t0, tk = np.nanmean(t[0][:, :, :, 0, ic, MOMENT2]), np.nanmean(t[0][:, :, :, 1, ic, KAHIN])
        print(f"e = 0, model 0, c = {c * 1000:.0f} mm: t MOMENT-2 {t0:.3f} vs KAHIN at e = 3 {tk:.3f}: "
              f"false trigger cost {t0 - tk:+.3f}")

    # mu slices (protocol descriptive); mu is drawn in exp_time.draw_A from [hole, 70, seed, T]
    mu = np.zeros((len(d["period"]), nh, ns))
    for iT, T_ in enumerate(d["period"]):
        for ih in range(nh):
            for js, sd in enumerate(d["seeds"]):
                r = np.random.default_rng([ih, 70, int(sd), int(T_)])
                r.uniform(0, 2 * np.pi)
                mu[iT, ih, js] = r.uniform(0.2, 0.8)
    q = np.quantile(mu, [1 / 3, 2 / 3])
    gap = t[:, :, :, :, 1:, :, MOMENT2] - t[:, :, :, :, 1:, :, DOKUN]  # (arm, T, delay, gap, e, c, hole, seed)
    M = np.broadcast_to(mu[None, :, None, None, None, None], gap.shape)
    for lab, sel in [("low", M < q[0]), ("mid", (M >= q[0]) & (M < q[1])), ("high", M >= q[1])]:
        print(f"   mu {lab} third: D2 {np.nanmean(gap[sel]):+.3f}")

    # where D2 comes from (audit point 6): no direction at the first measurement, and re-aims exhausted
    r1 = X[..., keys.index("r_first")][:, :, :, :, 1:, :, MOMENT2]  # -1: never measured (went straight in)
    n = np.sum(~np.isnan(gap))
    for lab, sel in [("first |r| < R_MIN = 2 mm (straight to spiral)", (r1 >= 0) & (r1 < 0.002)), ("aims = 4 (re-aims exhausted)", aims == 4)]:
        print(f"   {lab}: share {np.mean(sel):.3f}, contributes {np.nansum(gap[sel]) / n:+.3f} s of D2")


if __name__ == "__main__":
    report(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "rival.npz"))
