"""The contact experiment of PROTOKOL.md: TABAN, REFLEKS and KAHIN on a real hole with a position error.

Run: python exp_contact.py    (.pbenv; writes results/exp_contact.npz)
"""
import itertools
import multiprocessing as mp
import os

import contact as C  # sets the thread limits and the paths first

import numpy as np

import gate_learned as Gl
import gate_rule as Gr
import gate_speed as Gs
import robot as Rb

ARMS = [0, 1, 2, None]  # models 0-2 paper recipe, None analytic
PERIOD = [8.0, 4.0]
DELAYS = [(0.02, 0.0), (0.04, 0.025), (0.09, 0.04)]
GAPS = [None, 0.25]  # no disturbance, or a push 0.25 s before the reference crosses the rim
ERRORS = [0.0, 0.003, 0.006, 0.010]
POLICIES = ["TABAN", "REFLEKS", "KAHIN"]
SEEDS = [int(x) for x in os.environ.get("EXP_SEEDS", "").split(",") if x] or list(range(100, 120))  # override for tests only
SCALE = 0.2
L_GATE = 0.02
ROBOT = None


def draw(hole_i, seed, T):
    """Everything random in one run, the same across arms, delays, clearances, errors and policies."""
    rng = np.random.default_rng([hole_i, 50, seed, int(T)])
    th = rng.uniform(0, 2 * np.pi)
    mu = rng.uniform(0.2, 0.8)
    w, v = Rb.disturbance(rng, SCALE)
    return np.array([np.cos(th), np.sin(th), 0.0]), mu, w, v, int(rng.integers(2**31))


def make_shift(policy, e, c, f_t=None, v_s=None):
    f_t = C.F_T if f_t is None else f_t
    v_s = C.V_S if v_s is None else v_s
    if policy == "TABAN":
        return C.Shift(np.zeros(3), False, c, f_t, v_s)
    if policy == "REFLEKS":
        return C.Shift(np.zeros(3), True, c, f_t, v_s)
    return C.Shift(e, True, c, f_t, v_s)


def episode(robot, arm, T, h, tau, gap, err, c, policy, hole_i, seed, f_t=None, v_s=None, **kw):
    hole = Gr.HOLES[hole_i]
    ref = Rb.reference_for(robot, hole, T)
    f = Gs.Gated(Gl.field(arm, ref, hole_i, T), L_GATE)
    u, mu, w, v, ns = draw(hole_i, seed, T)
    e = err * u
    push = None if gap is None else (C.push_height(ref, gap), w, v)
    return C.run(robot, f, hole, e, c, Gr.rule(h, tau), h, tau, make_shift(policy, e, c, f_t, v_s), push,
                 np.random.default_rng(ns), mu, tf=T + 8.0, **kw)


def work(job):
    global ROBOT
    if ROBOT is None:
        ROBOT = C.Panda()
    arm, T, (h, tau), gap, err, c, policy = job
    out = np.zeros((len(Gr.HOLES), len(SEEDS), len(C.KEYS)))
    for ih in range(len(Gr.HOLES)):
        for js, s in enumerate(SEEDS):
            r = episode(ROBOT, arm, T, h, tau, gap, err, c, policy, ih, s)
            out[ih, js] = [float(r[k]) for k in C.KEYS]
    return job, out


def jobs():
    return [j for j in itertools.product(ARMS, PERIOD, DELAYS, GAPS, ERRORS, C.CLEARANCES, POLICIES)
            if not (j[4] == 0.0 and j[6] == "KAHIN")]


def main(path, js=None):
    js = jobs() if js is None else js
    shape = (len(ARMS), len(PERIOD), len(DELAYS), len(GAPS), len(ERRORS), len(C.CLEARANCES), len(POLICIES),
             len(Gr.HOLES), len(SEEDS), len(C.KEYS))
    data = np.full(shape, np.nan)
    with mp.Pool(9) as pool:
        for i, (j, out) in enumerate(pool.imap_unordered(work, js, chunksize=1)):
            idx = (ARMS.index(j[0]), PERIOD.index(j[1]), DELAYS.index(j[2]), GAPS.index(j[3]), ERRORS.index(j[4]),
                   C.CLEARANCES.index(j[5]), POLICIES.index(j[6]))
            data[idx] = out
            if i % 20 == 0:
                print(i, len(js), flush=True)
    np.savez(path, data=data, keys=np.array(C.KEYS),
             arms=np.array([-1 if a is None else a for a in ARMS]), period=PERIOD, delays=np.array(DELAYS),
             gaps=np.array([-1.0 if g is None else g for g in GAPS]), errors=ERRORS, clearances=C.CLEARANCES,
             policies=np.array(POLICIES), seeds=SEEDS,
             mu=np.array([[[draw(ih, s, T)[1] for s in SEEDS] for ih in range(len(Gr.HOLES))] for T in PERIOD]))


if __name__ == "__main__":
    main(os.path.join(C.HERE, "results", "exp_contact.npz"))
