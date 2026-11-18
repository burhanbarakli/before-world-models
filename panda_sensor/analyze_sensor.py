"""The decision rule of PROTOKOL.md on results/sensor.npz.

Run: python analyze_sensor.py [path] > results/analysis_sensor.txt
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
B_REPS, DELTA, LEVEL = 2000, 0.5, 100 - 5 / 3  # three tests, Bonferroni: 98.33% two-sided
DOKUN, M2R, M2T, M2O, M2, M2C = 0, 1, 2, 3, 4, 5
TESTED = [1, 2, 3]  # S1, S2, S3


def outcome(s_dokun, D, lo, hi):
    if s_dokun < 0.85:
        return "invalid: S(DOKUN-KAHIN) below 0.85, the trigger does not work at this level"
    if hi < DELTA:
        return "suffices: the hand-made rival suffices with this sensor"
    if D < DELTA:
        return "small: a small margin cannot be excluded; no model, the burden is on the model"
    if lo > 0:
        return "gap: an information gap remains"
    return "none: D2 >= delta but its lower bound is not above 0, no decision"


def report(path):
    d = np.load(path)
    keys = list(d["keys"])
    X = d["data"]  # (level, arm, delay, e, c, policy, hole, seed, key)
    k = lambda name: X[..., keys.index(name)]
    ok = k("ok")
    t = np.where(ok > 0, k("t_in"), float(d["period"]) + 8.0)  # every failed run counts as tf
    t[np.isnan(ok)] = np.nan
    nA, nh, ns = X.shape[1], X.shape[6], X.shape[7]
    names = list(d["levels"])

    def m(x, lv, a, h, s, pol):
        return np.nanmean(x[lv][a][:, :, 1:, :, pol][..., h, :][..., s])

    def one(a, h, s):
        return np.array([[m(t, lv, a, h, s, M2R) - m(t, lv, a, h, s, DOKUN), m(ok, lv, a, h, s, DOKUN),
                          m(t, lv, a, h, s, M2C) - m(t, lv, a, h, s, DOKUN)] for lv in TESTED])

    A, H, Sd = np.arange(nA), np.arange(nh), np.arange(ns)
    point = one(A, H, Sd)
    rng = np.random.default_rng(0)
    boots = np.array([one(rng.choice(A, nA), rng.choice(H, nh), rng.choice(Sd, ns)) for _ in range(B_REPS)])
    a = (100 - LEVEL) / 2
    lo, hi = np.percentile(boots, [a, 100 - a], axis=0)
    sh = point - boots.mean(0)
    print(f"=== M2R against DOKUN-KAHIN per sensor level, models 0-2, e > 0 (primary, {LEVEL:.2f}% intervals) ===")
    res = {}
    for i, lv in enumerate(TESTED):
        nm = names[lv]
        print(f"{nm}: t DOKUN {m(t, lv, A, H, Sd, DOKUN):.2f}  M2R {m(t, lv, A, H, Sd, M2R):.2f}   "
              f"S DOKUN {m(ok, lv, A, H, Sd, DOKUN):.3f}  M2R {m(ok, lv, A, H, Sd, M2R):.3f}")
        print(f"    D2 {point[i, 0]:+.3f}  percentile [{lo[i, 0]:+.3f}, {hi[i, 0]:+.3f}]  recentred "
              f"[{lo[i, 0] + sh[i, 0]:+.3f}, {hi[i, 0] + sh[i, 0]:+.3f}]  pivot [{2 * point[i, 0] - hi[i, 0]:+.3f}, "
              f"{2 * point[i, 0] - lo[i, 0]:+.3f}]")
        res[nm] = outcome(point[i, 1], point[i, 0], lo[i, 0], hi[i, 0])
        print(f"    Outcome {nm}: {res[nm]}")
        print(f"    M2C (weak calibration kept, Sapma 3): t {m(t, lv, A, H, Sd, M2C):.2f}  S {m(ok, lv, A, H, Sd, M2C):.3f}"
              f"  D2C {point[i, 2]:+.3f}  [{lo[i, 2]:+.3f}, {hi[i, 2]:+.3f}] -> "
              f"{outcome(point[i, 1], point[i, 2], lo[i, 2], hi[i, 2])}")
    word = {n: r.split(":")[0] for n, r in res.items()}
    wordC = {names[lv]: outcome(point[i, 1], point[i, 2], lo[i, 2], hi[i, 2]).split(":")[0] for i, lv in enumerate(TESTED)}
    print("\nCombined (pre-registered reading):")
    if word["S1"] == "gap" or word["S2"] == "gap":
        low = "S1" if word["S1"] == "gap" else "S2"
        print(f"   gap at {low}: a learned estimator against M2R in a separate protocol at {low}; no world model")
    elif word["S1"] == "suffices" and word["S2"] == "suffices":
        if word["S3"] == "suffices":
            print("   S1, S2, S3 suffice: the door for position estimation during contact closes, sensor error included,"
                  " even without a wrist sensor")
        elif word["S3"] == "gap":
            print("   S1, S2 suffice, S3 gap: a model has a place only on a robot without a wrist F/T sensor; its "
                  "hand-made counterpart is hardware")
        else:
            print(f"   S1, S2 suffice, S3 {word['S3']}: the door closes with a wrist sensor; S3 as reported")
    else:
        print("   " + ", ".join(f"{n} {w}" for n, w in word.items()) + ": no model where 'small'; see the levels")

    for n in word:
        if word[n] == "gap" and wordC[n] != "gap":
            print(f"   {n}: M2R gap but M2C {wordC[n]}: the rival of any learned-estimator protocol at {n} is M2C (Sapma 3)")
    print("\nD2 by cell (s), per level:      c = 5: e = 3    e = 6   e = 10    c = 2: e = 3    e = 6   e = 10")
    for lv in TESTED:
        row = [np.nanmean(t[lv][:, :, ie, ic, M2R]) - np.nanmean(t[lv][:, :, ie, ic, DOKUN])
               for ic in range(2) for ie in (1, 2, 3)]
        print(f"   {names[lv]}                          " + "  ".join(f"{x:+.3f}" for x in row[:3]) + "          " +
              "  ".join(f"{x:+.3f}" for x in row[3:]))
    for lv in TESTED:
        print(f"   {names[lv]} by delay: " + "  ".join(
            f"{(h + tau) * 1000:.0f} ms {np.nanmean(t[lv][:, i, 1:, :, M2R]) - np.nanmean(t[lv][:, i, 1:, :, DOKUN]):+.3f}"
            for i, (h, tau) in enumerate(d["delays"])))

    print("\nmodel 0, e > 0 (descriptive): t of DOKUN / M2O / M2R / M2T and the split of the gap")
    for lv in TESTED:
        tm = {p: np.nanmean(t[lv][0][:, 1:, :, i]) for p, i in [("DOKUN", DOKUN), ("M2O", M2O), ("M2R", M2R), ("M2T", M2T)]}
        sm = {p: np.nanmean(ok[lv][0][:, 1:, :, i]) for p, i in [("DOKUN", DOKUN), ("M2O", M2O), ("M2R", M2R), ("M2T", M2T)]}
        print(f"   {names[lv]}: " + "  ".join(f"{p} {tm[p]:.2f} ({sm[p]:.3f})" for p in tm) +
              f"   rule M2O-DOKUN {tm['M2O'] - tm['DOKUN']:+.3f}  sensor M2R-M2O {tm['M2R'] - tm['M2O']:+.3f}"
              f"  transfer M2T-M2R {tm['M2T'] - tm['M2R']:+.3f}")
    s0 = (np.nanmean(t[0][0][:, 1:, :, M2]), np.nanmean(t[0][0][:, 1:, :, DOKUN]))
    print(f"   S0 (ideal, new seeds): M2 {s0[0]:.2f}  DOKUN {s0[1]:.2f}  D2 {s0[0] - s0[1]:+.3f}")

    print("\nM2R first measurement and estimates (e > 0, all models; medians over runs with a measurement):")
    rmin = d["rmin"]
    for i, lv in enumerate(TESTED):
        r1, rt, de = k("r_first")[lv][:, :, 1:, :, M2R], k("r_true")[lv][:, :, 1:, :, M2R], k("dir_err")[lv][:, :, 1:, :, M2R]
        e1, eL, ai = k("est_first")[lv][:, :, 1:, :, M2R], k("est_last")[lv][:, :, 1:, :, M2R], k("aims")[lv][:, :, 1:, :, M2R]
        has = (r1 >= 0) & (rt >= 0)
        print(f"   {names[lv]}: | |r-hat| - |r| | {np.median(np.abs(r1[has] - rt[has])) * 1000:.2f} mm, direction error "
              f"{np.median(de[de >= 0]):.1f} deg (90% {np.percentile(de[de >= 0], 90):.1f}), estimate error first / last "
              f"{np.median(e1[e1 >= 0]) * 1000:.2f} / {np.median(eL[eL >= 0]) * 1000:.2f} mm, aims {np.nanmean(ai):.2f}, "
              f"no direction {np.mean((r1 >= 0) & (r1 < rmin[i])):.3f}, measured {np.mean(r1 >= 0):.3f}")
    print("\ne = 0, model 0 (false triggers): M2R t and trigger share")
    for lv in TESTED:
        tc = k("t_contact")[lv][0][:, 0, :, M2R]
        print(f"   {names[lv]}: t {np.nanmean(t[lv][0][:, 0, :, M2R]):.2f}, triggered {np.nanmean(tc >= 0):.3f}")
    print("\npilot values: F_t " + str([float(x) for x in d["ft"]]) + ", n_w " + str([int(x) for x in d["nw"]]) + ", R_MIN " +
          str([float(x) for x in d["rmin"]]) + ", cal " + str(d["cal"].tolist()))


if __name__ == "__main__":
    report(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "sensor.npz"))
