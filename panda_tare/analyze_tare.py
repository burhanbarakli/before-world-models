"""The decision rule of PROTOKOL.md on results/tare.npz.

Run: python analyze_tare.py [path] > results/analysis_tare.txt
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
B_REPS, DELTA, LEVEL = 2000, 0.5, 100 - 5 / 3
DOKUN, M2R, TARE = 0, 1, 2
RANK = {"invalid": -1, "suffices": 0, "small": 1, "none": 2, "gap": 3}  # more room for a model = higher


def outcome(s_dokun, D, lo, hi):
    if s_dokun < 0.85:
        return "invalid: S(DOKUN-KAHIN) below 0.85"
    if hi < DELTA:
        return "suffices: the hand-made rule suffices at this level"
    if D < DELTA:
        return "small: a small margin cannot be excluded; no model, the burden is on the model"
    if lo > 0:
        return "gap: an information gap remains"
    return "none: no decision"


def report(path):
    d = np.load(path)
    keys = list(d["keys"])
    X = d["data"]  # (level, arm, delay, e, c, policy, hole, seed, key)
    k = lambda name: X[..., keys.index(name)]
    ok = k("ok")
    t = np.where(ok > 0, k("t_in"), float(d["period"]) + 8.0)
    t[np.isnan(ok)] = np.nan
    nL, nA, nh, ns = X.shape[0], X.shape[1], X.shape[6], X.shape[7]
    names = list(d["levels"])
    print(f"data: {np.isnan(ok).sum()} missing of {ok.size}; seeds {list(d['seeds'])}")

    def m(x, lv, a, h, s, pol):
        return np.nanmean(x[lv][a][:, :, :, :, pol][..., h, :][..., s])

    def one(a, h, s):
        return np.array([[m(t, lv, a, h, s, TARE) - m(t, lv, a, h, s, DOKUN),
                          m(t, lv, a, h, s, M2R) - m(t, lv, a, h, s, DOKUN), m(ok, lv, a, h, s, DOKUN)]
                         for lv in range(nL)])

    A, H, Sd = np.arange(nA), np.arange(nh), np.arange(ns)
    point = one(A, H, Sd)
    rng = np.random.default_rng(0)
    boots = np.array([one(rng.choice(A, nA), rng.choice(H, nh), rng.choice(Sd, ns)) for _ in range(B_REPS)])
    # second interval: (model, hole) cells resampled jointly, seeds fixed
    cells = [(a, h) for a in A for h in H]

    pre = {(lv, pol): np.array([np.nanmean(t[lv][a][:, :, :, pol][..., h, :]) for a, h in cells])
           for lv in range(nL) for pol in (DOKUN, M2R, TARE)}
    boots2 = []
    for _ in range(B_REPS):
        idx = rng.integers(0, len(cells), len(cells))
        boots2.append([[pre[(lv, TARE)][idx].mean() - pre[(lv, DOKUN)][idx].mean(),
                        pre[(lv, M2R)][idx].mean() - pre[(lv, DOKUN)][idx].mean()] for lv in range(nL)])
    boots2 = np.array(boots2)
    a = (100 - LEVEL) / 2
    lo, hi = np.percentile(boots, [a, 100 - a], axis=0)
    lo2, hi2 = np.percentile(boots2, [a, 100 - a], axis=0)
    print(f"=== TARE against DOKUN-KAHIN per level, models 0-2, seeds 500-501 ({LEVEL:.2f}% intervals) ===")
    word = {}
    for lv in range(nL):
        nm = names[lv]
        print(f"{nm}: t DOKUN {m(t, lv, A, H, Sd, DOKUN):.2f}  TARE {m(t, lv, A, H, Sd, TARE):.2f}  M2R "
              f"{m(t, lv, A, H, Sd, M2R):.2f}   S DOKUN {point[lv, 2]:.3f}  TARE {m(ok, lv, A, H, Sd, TARE):.3f}  M2R "
              f"{m(ok, lv, A, H, Sd, M2R):.3f}")
        o1 = outcome(point[lv, 2], point[lv, 0], lo[lv, 0], hi[lv, 0])
        o2 = outcome(point[lv, 2], point[lv, 0], lo2[lv, 0], hi2[lv, 0])
        print(f"    DT {point[lv, 0]:+.3f}  models x holes x seeds [{lo[lv, 0]:+.3f}, {hi[lv, 0]:+.3f}] -> {o1.split(':')[0]}"
              f";  model-hole cells [{lo2[lv, 0]:+.3f}, {hi2[lv, 0]:+.3f}] -> {o2.split(':')[0]}")
        w = max([o1.split(":")[0], o2.split(":")[0]], key=lambda x: RANK[x])
        word[nm] = w
        print(f"    Outcome {nm} (conservative of the two): {w}")
        print(f"    M2R - DOKUN on the same seeds (descriptive): {point[lv, 1]:+.3f}  [{lo[lv, 1]:+.3f}, {hi[lv, 1]:+.3f}]")
    print("\nReading (pre-registered):")
    if word["S1"] == "suffices":
        print("   S1 suffices: the learned-estimator door that panda_sensor opened at S1 closes, under the physical "
              "assumption that a re-tare just before contact is possible")
    else:
        print(f"   S1 {word['S1']}: the learned-estimator protocol at S1 stays open; its rival is TARE")
    for nm in ("S2", "S3"):
        lv = names.index(nm)
        best = "TARE" if point[lv, 0] <= point[lv, 1] else "M2R"
        print(f"   {nm} {word[nm]}: the rival of any learned-estimator protocol here is {best}")

    print("\nDT by cell (s):           c = 5: e = 3    e = 6   e = 10    c = 2: e = 3    e = 6   e = 10")
    for lv in range(nL):
        row = [np.nanmean(t[lv][:, :, ie, ic, TARE]) - np.nanmean(t[lv][:, :, ie, ic, DOKUN])
               for ic in range(2) for ie in range(3)]
        print(f"   {names[lv]}                  " + "  ".join(f"{x:+.3f}" for x in row[:3]) + "          " +
              "  ".join(f"{x:+.3f}" for x in row[3:]))
    for lv in range(nL):
        print(f"   {names[lv]} by delay: " + "  ".join(
            f"{(h + tau) * 1000:.0f} ms {np.nanmean(t[lv][:, i, :, :, TARE]) - np.nanmean(t[lv][:, i, :, :, DOKUN]):+.3f}"
            for i, (h, tau) in enumerate(d["delays"])))
    for lv in range(nL):
        print(f"   {names[lv]} by model: " + "  ".join(
            f"{a_}: {np.nanmean(t[lv][a_][..., TARE, :, :]) - np.nanmean(t[lv][a_][..., DOKUN, :, :]):+.3f}" for a_ in A))

    print("\nTARE first measurement and tare (medians over runs with a measurement):")
    for lv in range(nL):
        sl = (lv, slice(None), slice(None), slice(None), slice(None), TARE)
        r1, rt, de = k("r_first")[sl], k("r_true")[sl], k("dir_err")[sl]
        eL, ai = k("est_last")[sl], k("aims")[sl]
        has = (r1 >= 0) & (rt >= 0)
        print(f"   {names[lv]}: | |r-hat| - |r| | {np.median(np.abs(r1[has] - rt[has])) * 1000:.2f} mm, direction error "
              f"{np.median(de[de >= 0]):.1f} deg (90% {np.percentile(de[de >= 0], 90):.1f}), last estimate error "
              f"{np.median(eL[eL >= 0]) * 1000:.2f} mm, aims {np.nanmean(ai):.2f}, tare error |F| "
              f"{np.median(k('tare_err_f')[sl]):.4f} N, ticks {np.nanmin(k('n_tare')[sl]):.0f}-{np.nanmax(k('n_tare')[sl]):.0f}")
    print("\ncalibration used by TARE: " + str(d["calt"].tolist()))


if __name__ == "__main__":
    report(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "tare.npz"))
