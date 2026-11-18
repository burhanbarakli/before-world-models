"""Exploratory, added after seeing the pre-registered result; not part of the decision rules.

A's floor of 1 kept it out of the low-eta range where most shapes were tuned. A2 lowers the floor
to 0.25. F_low extends the fixed grid below its edge, since 0.25 was the most selected value.
Run: python explore.py
"""
import multiprocessing as mp

import numpy as np
import gvf_s2 as g
from schedule import RHO, SPLITS, lateral_start

POL = [("A2", r) for r in RHO] + [("F", 0.05), ("F", 0.1)]


def fn(p):
    if p[0] == "F":
        return lambda D, mn, s: np.full_like(D, p[1])
    return lambda D, mn, s: np.clip(p[1] * mn / np.maximum(D, 1e-9), 0.25, 30.0)


def one(name):
    curves, dt = g.map_shape(name)
    out = {}
    for split, (ref, tune, test) in SPLITS.items():
        f = g.Field(curves[ref], dt[ref])
        others = list(tune) + list(test)
        st = np.stack([curves[i, 0] for i in others] + [lateral_start(f)[0]])
        d = np.zeros((len(POL), 6))
        E, Q = np.zeros((len(POL), 7)), np.zeros((len(POL), 7))
        for ip, p in enumerate(POL):
            path, done, e, q = g.rollout(f, st, fn(p))
            E[ip], Q[ip] = e, q
            for j, i in enumerate(others):
                d[ip, j] = g.dtw(g.resample(path[:, j]), g.resample(curves[i]))
        out[split] = (d, E, Q)
    return out


if __name__ == "__main__":
    with mp.Pool(9) as pool:
        res = pool.map(one, g.SHAPES, chunksize=1)
    R = np.load("results/schedule.npz")
    IF, nr = np.arange(10), len(RHO)
    for split in SPLITS:
        d = np.stack([r[split][0] for r in res])
        E = np.stack([r[split][1] for r in res])
        Q = np.stack([r[split][2] for r in res])
        M = R[f"{split}_dtw"]
        tune, test = M[:, :, :3].mean(2), M[:, :, 3:].mean(2)
        rows = np.arange(26)
        base = test[rows, IF[tune[:, IF].argmin(1)]]
        t2, te = d[:, :nr, :3].mean(2), d[:, :nr, 3:].mean(2)
        a2 = te[rows, t2.argmin(1)]
        print(f"[{split}] DTW test: F_letter {np.median(base):.4f}  A2 {np.median(a2):.4f}"
              f"  gain {np.median((base - a2) / base):.3f}  shapes better {int((a2 < base).sum())}/26")
        low = d[:, nr:, 3:].mean(2)
        print(f"   fixed below grid, median test DTW: eta .05 {np.median(low[:, 0]):.4f}  eta .1 {np.median(low[:, 1]):.4f}"
              f"  eta .25 {np.median(test[:, 0]):.4f}")
        for key, X in [("E", E), ("Q", Q)]:
            F = R[f"{split}_{key}"]
            for label, c in [("offset", [6]), ("test", [3, 4, 5])]:
                f = F[:, IF][:, :, c].mean(2).min(1)
                a = X[:, :nr][:, :, c].mean(2).min(1)
                print(f"   {key} {label}: fixed {np.median(f):.4f}  A2 {np.median(a):.4f}  gain {np.median((f - a) / f):.3f}")
