"""Fixed eta against eta schedules on 26 LASA shapes, as PROTOKOL.md fixes it.

Run: python schedule.py    (writes results/schedule.npz)
"""
import itertools
import multiprocessing as mp

import numpy as np
import gvf_s2 as g

FIXED = [0.25, 0.5, 1, 2, 3, 5, 8, 12, 20, 30]
RHO = [0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1.2, 2, 4]
PAIR = [(a, b) for a, b in itertools.product([0.25, 0.5, 1, 2, 5, 10], repeat=2) if a <= b]
POLICIES = [("F", e) for e in FIXED] + [("A", r) for r in RHO] + [("P", p) for p in PAIR]
SPLITS = {"main": (0, (1, 2, 3), (4, 5, 6)), "rot": (3, (4, 5, 6), (0, 1, 2))}
OFFSET = 0.3


def eta_fn(policy):
    kind, p = policy
    if kind == "F":
        return lambda D, mn, s: np.full_like(D, float(p))
    if kind == "A":
        return lambda D, mn, s: np.clip(p * mn / np.maximum(D, 1e-9), 1.0, 30.0)
    a, b = p
    return lambda D, mn, s: a + (b - a) * s**2


def lateral_start(f):
    """Start 0.3 rad to the side of the reference start, on the left of its direction."""
    x, t = f.x[0], f.tan[0]
    return g.exp_map(x[None], (np.cross(x, t) * OFFSET)[None])


def one_shape(name):
    curves, dt = g.map_shape(name)
    res = {}
    for split, (ref, tune, test) in SPLITS.items():
        f = g.Field(curves[ref], dt[ref])
        others = list(tune) + list(test)
        starts = np.stack([curves[i, 0] for i in others] + [lateral_start(f)[0]])
        dtw = np.zeros((len(POLICIES), len(others)))
        fre = dtw.copy()
        arrive = dtw.copy()
        E = np.zeros((len(POLICIES), len(starts)))
        Q = E.copy()
        for ip, pol in enumerate(POLICIES):
            path, done, e, q = g.rollout(f, starts, eta_fn(pol))
            E[ip], Q[ip] = e, q
            for j, i in enumerate(others):
                a, b = g.resample(path[:, j]), g.resample(curves[i])
                dtw[ip, j], fre[ip, j], arrive[ip, j] = g.dtw(a, b), g.frechet(a, b), done[j]
        # Noise floor: the reference demo itself scored against each held-out demo.
        floor = [g.dtw(g.resample(curves[ref]), g.resample(curves[i])) for i in others]
        res[split] = dict(dtw=dtw, fre=fre, arrive=arrive, E=E, Q=Q, floor=np.array(floor))
    print(name, flush=True)
    return res


if __name__ == "__main__":
    with mp.Pool(9) as pool:
        out = pool.map(one_shape, g.SHAPES, chunksize=1)
    save = {}
    for split in SPLITS:
        for key in ["dtw", "fre", "arrive", "E", "Q", "floor"]:
            save[f"{split}_{key}"] = np.stack([o[split][key] for o in out])
    np.savez("results/schedule.npz", shapes=np.array(g.SHAPES), **save)
