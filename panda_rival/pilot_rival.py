"""Pilot of PROTOKOL.md: P1 distance calibration, P2 regression, P3 tuning, P4 time.

Run: python pilot_rival.py     (.pbenv; writes results/pilot_rival.txt)
"""
import multiprocessing as mp
import os
import time

import rival as Rv  # sets the paths

import numpy as np

import exp_time as X
import explore_bound as Eb
import timesim as Ts
import contact as C
import gate_rule as Gr

SEEDS = [920, 921, 922, 923, 924]
OUT = os.path.join(Rv.HERE, "results", "pilot_rival.txt")
GRID = [(v, n) for v in (0.005, 0.01, 0.02) for n in (5, 10)]


def say(f, s):
    print(s, flush=True)
    f.write(s + "\n")
    f.flush()


def p1(job):
    X.init()
    c, err, ih, s = job
    r = Rv.episode(None, 8.0, 0.02, 0.0, None, err, c, "MOMENT2", ih, s, v_s=0.02, n_w=5, cal=None)
    return c, err, r["r_first"]


def p2(job):
    X.init()
    ih, s, err, c = job
    hole, ref, f = X.setup(0, ih, 8.0)
    u, mu, w, v, ns = X.draw_A(ih, s, 8.0)
    e = err * u
    out = []
    for sh in (Eb.Touch(e, c, C.F_T, 0.02, 2.0), Rv.Touch(e, c, C.F_T, 0.02)):
        out.append(Ts.run_t(X.ROBOT, f, hole, e, c, Gr.rule(0.02, 0), 0.02, 0, sh, None,
                            np.random.default_rng(ns), mu, tf=16.0))
    return abs(out[0]["end_z"] - out[1]["end_z"]), out[0]["ok"] == out[1]["ok"]


def p3(job):
    X.init()
    arm, d, err, c, gap, ih, s, v_s, n_w, cal = job
    r = Rv.episode(arm, 8.0, d[0], d[1], gap, err, c, "MOMENT2", ih, s, v_s=v_s, n_w=n_w, cal=cal)
    ok = r["ok"]
    return (r["t_in"] if ok else 16.0), ok


def main():
    with open(OUT, "w") as f, mp.Pool(9) as pool:
        # P1
        res = pool.map(p1, [(c, err, ih, s) for c in X.CLEAR for err in (0.004, 0.006, 0.008, 0.010)
                            for ih in range(5) for s in SEEDS])
        cal = {}
        for c in X.CLEAR:
            pts = np.array([(r, err) for cc, err, r in res if cc == c and r >= 0])
            A = np.c_[np.ones(len(pts)), pts[:, 0]]
            coef, *_ = np.linalg.lstsq(A, pts[:, 1], rcond=None)
            pred = A @ coef
            r2 = 1 - np.sum((pts[:, 1] - pred) ** 2) / np.sum((pts[:, 1] - pts[:, 1].mean()) ** 2)
            use = r2 >= 0.5 and coef[1] > 0
            cal[c] = (float(coef[0]), float(coef[1])) if use else None
            by = "  ".join(f"e {e * 1000:.0f}: |r| {np.median(pts[pts[:, 1] == e, 0]) * 1000:.1f}"
                           for e in (0.004, 0.006, 0.008, 0.010) if np.any(pts[:, 1] == e))
            say(f, f"P1 c = {c * 1000:.0f} mm, {len(pts)} of {len([1 for x in res if x[0] == c])} with a measurement: "
                   f"d = {coef[0] * 1000:.2f} mm + {coef[1]:.3f} |r|, R2 {r2:.2f}, median error "
                   f"{np.median(np.abs(pts[:, 1] - pred)) * 1000:.2f} mm -> {'calibration' if use else 'fixed step c'}")
            say(f, f"   median |r| by e (mm): {by}")
        # P2
        d = pool.map(p2, [(ih, s, err, c) for ih in range(5) for s in SEEDS[:2] for err, c in
                          [(0.010, 0.002), (0.006, 0.005)]])
        worst = max(x[0] for x in d)
        say(f, f"P2 regression, {len(d)} runs: worst |end_z diff| {worst * 1000:.3f} mm, same outcome "
               f"{all(x[1] for x in d)} -> {'pass' if worst < 0.001 and all(x[1] for x in d) else 'FAIL'}")
        # P3
        t0, n0, chosen_v, chosen_n = time.time(), 0, [], []
        for d_ in X.DELAYS:
            scores = []
            for v_s, n_w in GRID:
                js = [(arm, d_, err, c, gap, ih, s, v_s, n_w, cal[c]) for arm in (None, 0)
                      for err in (0.003, 0.006, 0.010) for c in X.CLEAR for gap in X.GAPS for ih in range(5)
                      for s in SEEDS]
                out = pool.map(p3, js)
                n0 += len(out)
                t, sr = float(np.mean([x[0] for x in out])), float(np.mean([x[1] for x in out]))
                scores.append(((v_s, n_w), t, sr))
                say(f, f"   h + tau {sum(d_) * 1000:.0f} ms, v_s {v_s * 1000:.0f} mm/s, n_w {n_w:2d}: t {t:.2f}  SR {sr:.3f}")
            best = min(x[1] for x in scores)
            (v_s, n_w), _, _ = min([x for x in scores if x[1] <= best + 0.01], key=lambda x: (x[0][0], x[0][1]))
            chosen_v.append(v_s)
            chosen_n.append(n_w)
            say(f, f"P3 h + tau {sum(d_) * 1000:.0f} ms chosen: v_s {v_s * 1000:.0f} mm/s, n_w {n_w}")
        spr = (time.time() - t0) * 9 / n0
        total = len(Rv.jobs()) * 100 * spr * 14 / 16 / 9 / 3600
        say(f, f"P4 time: {spr:.2f} s per run at T = 8, about {total:.1f} h on 9 processes -> "
               f"{'pass' if total <= 12 else 'descriptive KAHIN / MOMENT to 10 seeds'}")
        say(f, f"chosen: V_S {chosen_v}, N_W {chosen_n}, CAL {cal}")


if __name__ == "__main__":
    main()
