"""Pilot checks M1-M6 and the REFLEKS tuning of PROTOKOL.md, on seeds 900 and up.

Run: python pilot.py > results/pilot.txt    (.pbenv)
"""
import itertools
import multiprocessing as mp
import time

import contact as C

import numpy as np

import exp_contact as X
import gate_learned as Gl
import gate_rule as Gr
import gate_speed as Gs
import robot as Rb

PILOT = list(range(900, 905))
TUNE_SEEDS = list(range(900, 910))
F_TS = [3.0, 5.0, 8.0]
V_SS = [0.01, 0.02, 0.04]
ROBOT = None


def m1():
    """Collisions off, no compliance, no disturbance: the same as the contactless run."""
    old, new = Rb.Panda(), C.Panda()
    worst = [0.0, 0.0]
    for arm, ih, T, (h, tau) in itertools.product([None, 0], range(5), [8.0, 4.0], [(0.02, 0.0), (0.09, 0.04)]):
        hole = Gr.HOLES[ih]
        ref = Rb.reference_for(old, hole, T)
        f = Gs.Gated(Gl.field(arm, ref, ih, T), X.L_GATE)
        a = Rb.run(old, f, hole, Gr.rule(h, tau), h, tau, None, tf=T + 4.0)
        b = C.run(new, f, hole, np.zeros(3), 0.005, Gr.rule(h, tau), h, tau, X.make_shift("TABAN", 0, 0.005), None,
                  None, 0.5, tf=T + 4.0, collide=False, admit=0.0)
        worst = [max(worst[0], abs(a["lat"] - b["lat"])), max(worst[1], abs(a["end_z"] - b["end_z"]))]
    print(f"M1 regression, 40 runs: worst |lat diff| {worst[0] * 1000:.3f} mm, |end_z diff| {worst[1] * 1000:.3f} mm "
          f"-> {'pass' if worst[0] < 0.0005 else 'FAIL'}")


def cases(robot, err, c, T_list, delay, policy="TABAN"):
    res = []
    for T, ih, s in itertools.product(T_list, range(5), PILOT):
        tr = []
        r = X.episode(robot, None, T, *delay, None, err, c, policy, ih, s, trace=tr)
        tr = np.array(tr)
        last = tr[-200:, 4]
        r["osc"] = bool(last.std() > max(1.0, 0.1 * abs(last.mean())))
        res.append(r)
    return res


def m2_m5():
    out = {}
    for hz in [C.SIM_HZ, 2 * C.SIM_HZ]:
        rb = C.Panda(hz)
        t0 = time.time()
        a = cases(rb, 0.0, 0.005, [8.0], (0.02, 0.0))
        b = cases(rb, 0.015, 0.002, [4.0, 8.0], (0.09, 0.04))
        out[hz] = (a, b, (time.time() - t0) / (len(a) + len(b)))
    a, b, _ = out[C.SIM_HZ]
    sr = np.mean([r["ok"] for r in a])
    print(f"M2 passable, 25 runs: TABAN SR {sr:.2f} -> {'pass' if sr >= 0.95 else 'FAIL'}")
    wall = [r["end_z"] >= Rb.RIM_Z - 0.001 and r["t_rim"] is None for r in b]
    print(f"M3 wall, 50 runs: held {np.mean(wall):.2f}, deepest end_z {min(r['end_z'] for r in b):.4f} "
          f"-> {'pass' if all(wall) else 'FAIL'}")
    fm = max(r["f_max"] for r in a + b)
    osc = np.mean([r["osc"] for r in a + b])
    for T in [4.0, 8.0]:
        sel = b[:25] if T == 4.0 else b[25:]
        print(f"   M3 T={T}: f_max mean {np.mean([r['f_max'] for r in sel]):.1f} max {max(r['f_max'] for r in sel):.1f}, "
              f"pressing force mean {np.mean([r['f_mean'] for r in sel]):.1f}")
    print(f"M4 contact: largest filtered force {fm:.1f} N (F_max {C.F_MAX}), sustained oscillation {osc:.2f} "
          f"-> {'pass' if fm < C.F_MAX and osc == 0 else 'FAIL'}")
    a2, b2, _ = out[2 * C.SIM_HZ]
    d_sr = abs(sr - np.mean([r["ok"] for r in a2]))
    d_wall = abs(np.mean(wall) - np.mean([r["end_z"] >= Rb.RIM_Z - 0.001 and r["t_rim"] is None for r in b2]))
    f1 = np.mean([r["f_max"] for r in a + b])
    f2 = np.mean([r["f_max"] for r in a2 + b2])
    print(f"M5 half step: SR diff {d_sr:.2f}, wall diff {d_wall:.2f}, mean f_max {f1:.1f} vs {f2:.1f} "
          f"({abs(f2 - f1) / f1 * 100:.0f}%) -> {'pass' if max(d_sr, d_wall) <= 0.05 and abs(f2 - f1) <= 0.2 * f1 else 'FAIL'}")
    print(f"   seconds per run: {out[C.SIM_HZ][2]:.2f} at {C.SIM_HZ} Hz, {out[2 * C.SIM_HZ][2]:.2f} at {2 * C.SIM_HZ} Hz")


def tune_job(job):
    global ROBOT
    if ROBOT is None:
        ROBOT = C.Panda()
    f_t, v_s, err, gap, ih, s = job
    r = X.episode(ROBOT, None, 8.0, 0.02, 0.0, gap, err, 0.005, "REFLEKS", ih, s, f_t=f_t, v_s=v_s)
    return job, r["ok"], r["t_in"]


def time_job(job):
    global ROBOT
    if ROBOT is None:
        ROBOT = C.Panda()
    t0 = time.time()
    arm, T, delay, gap, err, c, policy = job
    for ih, s in itertools.product(range(5), [900, 901]):
        X.episode(ROBOT, arm, T, *delay, gap, err, c, policy, ih, s)
    return (time.time() - t0) / 10


def tune_and_time():
    grid = list(itertools.product(F_TS, V_SS, [0.003, 0.006], [None, 0.25], range(5), TUNE_SEEDS))
    sample = [(0, 8.0, (0.09, 0.04), 0.25, 0.010, 0.005, "REFLEKS"), (None, 4.0, (0.02, 0.0), None, 0.0, 0.002, "TABAN"),
              (1, 8.0, (0.04, 0.025), None, 0.006, 0.002, "KAHIN"), (2, 4.0, (0.09, 0.04), 0.25, 0.003, 0.005, "TABAN"),
              (None, 8.0, (0.02, 0.0), 0.25, 0.010, 0.002, "REFLEKS"), (0, 4.0, (0.04, 0.025), None, 0.006, 0.005, "REFLEKS"),
              (1, 8.0, (0.02, 0.0), None, 0.0, 0.005, "TABAN"), (2, 8.0, (0.09, 0.04), 0.25, 0.010, 0.002, "KAHIN")]
    with mp.Pool(9) as pool:
        res = pool.map(tune_job, grid, chunksize=4)
        t0 = time.time()
        per_run = pool.map(time_job, sample, chunksize=1)
        wall = time.time() - t0
    print("REFLEKS tuning, e in {3, 6} mm, c = 5, T = 8, h = 20, analytic, 200 runs per setting: SR, mean t_in")
    best = None
    for f_t, v_s in itertools.product(F_TS, V_SS):
        sel = [r for r in res if r[0][0] == f_t and r[0][1] == v_s]
        sr, ti = np.mean([r[1] for r in sel]), np.mean([r[2] for r in sel])
        print(f"   F_t {f_t:4.1f}  v_s {v_s:.2f}: SR {sr:.3f}  t_in {ti:.2f}")
        default = (f_t, v_s) == (C.F_T, C.V_S)
        key = (sr, default, -ti)
        if best is None or key > best[0]:
            best = (key, f_t, v_s)
    print(f"   chosen: F_t {best[1]}, v_s {best[2]} (highest SR, ties to the protocol default, then faster)")
    n = len(X.jobs()) * 100
    est = n * np.mean(per_run) / 9 / 3600
    print(f"M6 time: {np.mean(per_run):.2f} s per run (8 jobs, {wall:.0f} s wall), {n} runs -> about {est:.1f} h on 9 "
          f"processes -> {'pass' if np.mean(per_run) <= 3.0 else 'FAIL'}")


if __name__ == "__main__":
    m1()
    m2_m5()
    tune_and_time()
