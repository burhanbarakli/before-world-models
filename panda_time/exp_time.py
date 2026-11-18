"""The two settings of PROTOKOL.md. A: single shot, KAHIN / REFLEKS-H / MOMENT. B: a persistent offset over
5-trial sequences, KAHIN / HAFIZA.

Run: python exp_time.py A|B     (.pbenv; writes results/exp_time_A.npz or results/exp_time_B.npz)
"""
import itertools
import multiprocessing as mp
import os
import sys

import timesim as Ts  # sets the paths first

import contact as C
import numpy as np

import gate_learned as Gl
import gate_rule as Gr
import gate_speed as Gs
import robot as Rb

ARMS_A, ARM_B = [0, 1, 2], 0
PERIOD = [8.0, 4.0]
DELAYS = [(0.02, 0.0), (0.04, 0.025), (0.09, 0.04)]
GAPS = [None, 0.25]
ERRORS_A, ERRORS_B = [0.0, 0.003, 0.006, 0.010], [0.003, 0.006, 0.010]
CLEAR = [0.005, 0.002]
POL_A, POL_B = ["KAHIN", "REFLEKS-H", "MOMENT"], ["KAHIN", "HAFIZA"]
N_TRIALS, SIGMA_J = 5, 0.001
SEEDS = [int(x) for x in os.environ.get("EXP_SEEDS", "").split(",") if x] or list(range(200, 220))  # tests only
SEEDS_B = SEEDS[:10]  # pilot P5: A + B over 14 h, B seeds to 10 (the one allowed reduction)
SCALE, L_GATE = 0.2, 0.02
ROBOT = None


def params(kw):
    """Tuning, from timesim (set by the pilot) unless given."""
    out = dict(v_s=Ts.V_S, pitch=Ts.PITCH, v_l=Ts.V_L, n_w=Ts.N_W)
    out.update({k: v for k, v in kw.items() if k in out})
    return out


def shift_for(policy, s0, c, pr):
    if policy in ("KAHIN", "REFLEKS-H"):
        return Ts.Spiral(s0, c, C.F_T, pr["v_s"], pr["pitch"])
    return Ts.Moment(s0, c, C.F_T, pr["v_s"], pr["pitch"], pr["v_l"], pr["n_w"])


def setup(arm, hole_i, T):
    hole = Gr.HOLES[hole_i]
    ref = Rb.reference_for(ROBOT, hole, T)
    return hole, ref, Gs.Gated(Gl.field(arm, ref, hole_i, T), L_GATE)


def draw_A(hole_i, seed, T):
    rng = np.random.default_rng([hole_i, 70, seed, int(T)])
    th = rng.uniform(0, 2 * np.pi)
    mu = rng.uniform(0.2, 0.8)
    w, v = Rb.disturbance(rng, SCALE)
    return np.array([np.cos(th), np.sin(th), 0.0]), mu, w, v, int(rng.integers(2**31))


def episode_A(arm, T, h, tau, gap, err, c, policy, hole_i, seed, **kw):
    hole, ref, f = setup(arm, hole_i, T)
    u, mu, w, v, ns = draw_A(hole_i, seed, T)
    e = err * u
    s0 = e if policy == "KAHIN" else np.zeros(3)
    push = None if gap is None else (C.push_height(ref, gap), w, v)
    return Ts.run_t(ROBOT, f, hole, e, c, Gr.rule(h, tau), h, tau, shift_for(policy, s0, c, params(kw)), push,
                    np.random.default_rng(ns), mu, tf=T + 8.0)


def draw_seq(hole_i, seed, T):
    rng = np.random.default_rng([hole_i, 80, seed, int(T)])
    th = rng.uniform(0, 2 * np.pi)
    return np.array([np.cos(th), np.sin(th), 0.0]), rng.uniform(0.2, 0.8)


def draw_trial(hole_i, seed, T, k):
    rng = np.random.default_rng([hole_i, 81, seed, int(T), k])
    jit = np.array([*rng.normal(0, SIGMA_J, 2), 0.0])
    w, v = Rb.disturbance(rng, SCALE)
    return jit, w, v, int(rng.integers(2**31))


def sequence_B(arm, T, h, tau, gap, err, c, policy, hole_i, seed, **kw):
    """N_TRIALS insertions with the same offset err * u plus a fresh jitter each. HAFIZA starts at 0 and then uses
    the mean of the offsets found by its successful trials. Returns the list of run summaries."""
    hole, ref, f = setup(arm, hole_i, T)
    u, mu = draw_seq(hole_i, seed, T)
    pr, found, out = params(kw), [], []
    for k in range(N_TRIALS):
        jit, w, v, ns = draw_trial(hole_i, seed, T, k)
        e = err * u + jit
        if policy == "KAHIN":
            s0 = e
        else:
            s0 = np.array([*np.mean(found, axis=0), 0.0]) if found else np.zeros(3)
        push = None if gap is None else (C.push_height(ref, gap), w, v)
        r = Ts.run_t(ROBOT, f, hole, e, c, Gr.rule(h, tau), h, tau, shift_for(policy, s0, c, pr), push,
                     np.random.default_rng(ns), mu, tf=T + 8.0)
        r["hafiza_err"] = float(np.linalg.norm(s0[:2] - e[:2]))
        if r["ok"]:
            found.append([r["end_dx"], r["end_dy"]])
        out.append(r)
    return out


KEYS_B = Ts.KEYS + ["hafiza_err"]


def init():
    global ROBOT
    if ROBOT is None:
        ROBOT = C.Panda()


def work_A(job):
    init()
    arm, T, (h, tau), gap, err, c, policy = job
    out = np.zeros((len(Gr.HOLES), len(SEEDS), len(Ts.KEYS)))
    for ih in range(len(Gr.HOLES)):
        for js, s in enumerate(SEEDS):
            r = episode_A(arm, T, h, tau, gap, err, c, policy, ih, s)
            out[ih, js] = [float(r[k]) for k in Ts.KEYS]
    return job, out


def work_B(job):
    init()
    T, (h, tau), gap, err, c, policy = job
    out = np.zeros((len(Gr.HOLES), len(SEEDS_B), N_TRIALS, len(KEYS_B)))
    for ih in range(len(Gr.HOLES)):
        for js, s in enumerate(SEEDS_B):
            for k, r in enumerate(sequence_B(ARM_B, T, h, tau, gap, err, c, policy, ih, s)):
                out[ih, js, k] = [float(r[q]) for q in KEYS_B]
    return job, out


def jobs_A():
    return [j for j in itertools.product(ARMS_A, PERIOD, DELAYS, GAPS, ERRORS_A, CLEAR, POL_A)
            if not (j[4] == 0.0 and j[6] == "KAHIN")]


def jobs_B():
    return list(itertools.product(PERIOD, DELAYS, GAPS, ERRORS_B, CLEAR, POL_B))


def index(lists, j):
    return tuple(L.index(x) for L, x in zip(lists, j))


def main(setting, path, js=None):
    if setting == "A":
        lists = [ARMS_A, PERIOD, DELAYS, GAPS, ERRORS_A, CLEAR, POL_A]
        js, work, tail, keys = (jobs_A() if js is None else js), work_A, (len(Gr.HOLES), len(SEEDS), len(Ts.KEYS)), Ts.KEYS
    else:
        lists = [PERIOD, DELAYS, GAPS, ERRORS_B, CLEAR, POL_B]
        js, work, tail, keys = (jobs_B() if js is None else js), work_B, (len(Gr.HOLES), len(SEEDS_B), N_TRIALS, len(KEYS_B)), KEYS_B
    data = np.full(tuple(len(L) for L in lists) + tail, np.nan)
    with mp.Pool(9) as pool:
        for i, (j, out) in enumerate(pool.imap_unordered(work, js, chunksize=1)):
            data[index(lists, j)] = out
            if i % 10 == 0:
                print(setting, i, len(js), flush=True)
    np.savez(path, data=data, keys=np.array(keys), period=PERIOD, delays=np.array(DELAYS),
             gaps=np.array([-1.0 if g is None else g for g in GAPS]), clearances=CLEAR, seeds=SEEDS if setting == "A" else SEEDS_B,
             errors=ERRORS_A if setting == "A" else ERRORS_B, policies=np.array(POL_A if setting == "A" else POL_B),
             arms=np.array(ARMS_A if setting == "A" else [ARM_B]),
             tuning=np.array([Ts.V_S, Ts.PITCH, Ts.V_L, Ts.N_W], float))


if __name__ == "__main__":
    s = sys.argv[1]
    main(s, os.path.join(Ts.HERE, "results", f"exp_time_{s}.npz"))
