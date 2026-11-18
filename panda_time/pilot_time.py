"""Pilot of PROTOKOL.md: P1 moment direction, P2 memory estimate, P3 regression, P4 tuning, P5 time.

Run: python pilot_time.py     (.pbenv; writes results/pilot_time.txt)
"""
import itertools
import multiprocessing as mp
import os
import time

import timesim as Ts

import contact as C
import numpy as np

import exp_time as X
import gate_rule as Gr

SEEDS = [910, 911, 912, 913, 914]
OUT = os.path.join(Ts.HERE, "results", "pilot_time.txt")
GRID_R = [(v, p) for v in (0.01, 0.02, 0.04) for p in (2.0, 1.5, 1.0)]
GRID_M = [(v, n) for v in (0.01, 0.02, 0.04) for n in (5, 10, 20)]
DEFAULT = dict(v_s=0.01, pitch=2.0, v_l=0.02, n_w=10)


def say(f, s):
    print(s, flush=True)
    f.write(s + "\n")
    f.flush()


def one(job):
    """(policy, arm, err, c, gap, hole, seed, kw) -> summary plus the true e."""
    X.init()
    policy, arm, err, c, gap, ih, s, kw = job
    r = X.episode_A(arm, 8.0, 0.02, 0.0, gap, err, c, policy, ih, s, **kw)
    r["e"] = err * X.draw_A(ih, s, 8.0)[0]
    return job, r


def p3(job):
    X.init()
    ih, s, err, gap = job
    hole, ref, f = X.setup(None, ih, 8.0)
    u, mu, w, v, ns = X.draw_A(ih, s, 8.0)
    e = err * u
    push = None if gap is None else (C.push_height(ref, gap), w, v)
    a = C.run(X.ROBOT, f, hole, e, 0.005, Gr.rule(0.02, 0), 0.02, 0, C.Shift(np.zeros(3), True, 0.005, C.F_T, 0.01),
              push, np.random.default_rng(ns), mu, tf=16.0)
    b = Ts.run_t(X.ROBOT, f, hole, e, 0.005, Gr.rule(0.02, 0), 0.02, 0,
                 Ts.Spiral(np.zeros(3), 0.005, C.F_T, 0.01, 2.0), push, np.random.default_rng(ns), mu, tf=16.0)
    return abs(a["end_z"] - b["end_z"]), a["ok"] == b["ok"]


def grid_jobs(policy, kw):
    return [(policy, arm, err, c, gap, ih, s, kw) for arm in (None, 0) for err in (0.003, 0.006, 0.010)
            for c in X.CLEAR for gap in X.GAPS for ih in range(5) for s in SEEDS]


def mean_t(res):
    return float(np.mean([r["t_in"] for _, r in res])), float(np.mean([r["ok"] for _, r in res]))


def pick(scores):
    """scores: list of (setting, t, sr, speed). Lowest t; within 0.01 s the slower one."""
    best = min(t for _, t, _, _ in scores)
    tied = [x for x in scores if x[1] <= best + 0.01]
    return min(tied, key=lambda x: x[3])


def main():
    with open(OUT, "w") as f, mp.Pool(9) as pool:
        # P3
        d = pool.map(p3, [(ih, s, err, gap) for ih in range(5) for s in SEEDS[:2] for err, gap in
                          [(0.006, None), (0.010, 0.25)]])
        worst = max(x[0] for x in d)
        say(f, f"P3 regression, {len(d)} runs: worst |end_z diff| {worst * 1000:.3f} mm, same outcome "
               f"{all(x[1] for x in d)} -> {'pass' if worst < 0.001 and all(x[1] for x in d) else 'FAIL'}")
        # P1
        res = pool.map(one, [("MOMENT", None, err, 0.005, None, ih, s, DEFAULT) for err in (0.006, 0.010)
                             for ih in range(5) for s in SEEDS[:4]])
        ue = np.array([r["u_err"] for _, r in res])
        has = ue >= 0
        say(f, f"P1 moment direction, {len(res)} runs: direction found {has.mean():.2f}, error median "
               f"{np.median(ue[has]):.1f} deg, 90% {np.percentile(ue[has], 90):.1f} deg -> "
               f"{'pass' if np.median(ue[has]) <= 45 else 'FAIL'}")
        # P4, REFLEKS-H then MOMENT on the chosen spiral
        t0, n0 = time.time(), 0
        scores = []
        for v, pt in GRID_R:
            res = pool.map(one, grid_jobs("REFLEKS-H", dict(DEFAULT, v_s=v, pitch=pt)))
            n0 += len(res)
            t, sr = mean_t(res)
            scores.append(((v, pt), t, sr, v))
            say(f, f"   REFLEKS-H v_s {v:.2f} pitch {pt:.1f}c: mean t {t:.2f}  SR {sr:.3f}")
        (vs, pt), _, _, _ = pick(scores)
        say(f, f"P4 REFLEKS-H chosen: v_s {vs}, pitch {pt}c")
        scores, all_res = [], []
        for v, n in GRID_M:
            res = pool.map(one, grid_jobs("MOMENT", dict(v_s=vs, pitch=pt, v_l=v, n_w=n)))
            n0 += len(res)
            all_res += res
            t, sr = mean_t(res)
            scores.append(((v, n), t, sr, v))
            say(f, f"   MOMENT v_l {v:.2f} n_w {n:2d}: mean t {t:.2f}  SR {sr:.3f}")
        (vl, nw), _, _, _ = pick(scores)
        say(f, f"P4 MOMENT chosen: v_l {vl}, n_w {nw}")
        wall = time.time() - t0
        # P2 on the successful MOMENT tuning runs
        for c in X.CLEAR:
            errs = [np.hypot(r["end_dx"] - r["e"][0], r["end_dy"] - r["e"][1]) for j, r in all_res
                    if r["ok"] and j[3] == c]
            say(f, f"P2 memory estimate, c = {c * 1000:.0f} mm, {len(errs)} successful runs: error median "
                   f"{np.median(errs) * 1000:.2f} mm, 90% {np.percentile(errs, 90) * 1000:.2f} mm -> "
                   f"{'pass' if np.median(errs) <= c else 'FAIL'}")
        # P5
        spr = wall * 9 / n0
        total = (len(X.jobs_A()) * 100 + len(X.jobs_B()) * 100 * X.N_TRIALS) * spr * 14 / 16 / 9 / 3600
        say(f, f"P5 time: {spr:.2f} s per run at T = 8 (tf 16), about {total:.1f} h for A + B on 9 processes "
               f"(scaled to mean tf 14) -> {'pass' if total <= 14 else 'B seeds to 10'}")
        say(f, f"chosen: V_S {vs}, PITCH {pt}, V_L {vl}, N_W {nw}")


if __name__ == "__main__":
    main()
