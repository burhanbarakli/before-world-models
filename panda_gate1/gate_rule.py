"""The fresh-condition test of eta = min(20, 0.6 / (h + tau)), as PROTOKOL_KURAL.md fixes it.

Run: python gate_rule.py    (writes results/gate_rule.npz)
"""
import itertools
import multiprocessing as mp

import numpy as np
import field_se3 as F
import gate1 as G
import gate1g as Gg
import robot as Rb

HOLES = [(0.40, -0.12), (0.44, -0.04), (0.44, 0.04), (0.40, 0.12), (0.36, -0.08)]
ETA = [3, 4, 5, 6.5, 8, 10, 12, 16, 20]
DELAY = [0.015, 0.035, 0.07, 0.09]
LAG = [0.0, 0.025, 0.04]
PERIOD = [8.0, 6.0, 4.0]
GAP = [0.4, 0.25]
K, CAP = 0.6, 20.0
SEEDS = 20
ROBOT = None


def rule(h, tau):
    return min(CAP, K / (h + tau))


def draw(robot, ref, hole_i, seed, gap):
    T = ref.dt * (len(ref.p) - 1)
    rng = np.random.default_rng([hole_i, 30, seed, int(T)])
    i = Gg.rim_index(ref) - int(round(gap / ref.dt))
    while True:
        w, v = Rb.disturbance(rng, Gg.SCALE)
        Rb.ref_q0(robot, ref)
        robot.ik(ref.R[i], ref.p[i])
        e = robot.ik(ref.R[i] @ F.so3_exp(w), ref.p[i] + ref.R[i] @ v)
        if e[0] < 1e-3 and e[1] < 1e-3:
            return w, v


def work(job):
    """job: T, h, tau, gap, index into ETA, where len(ETA) means the rule."""
    global ROBOT
    if ROBOT is None:
        ROBOT = Rb.Panda()
    T, h, tau, gap, ie = job
    eta = rule(h, tau) if ie == len(ETA) else ETA[ie]
    out = np.zeros((len(HOLES), SEEDS, len(G.KEYS)))
    for ih, hole in enumerate(HOLES):
        ref = Rb.reference_for(ROBOT, hole, T)
        t_rim = Rb.run(ROBOT, ref, hole, eta, h, tau, None, tf=T + 4.0)["t_rim"]
        t_d = (ref.dt * Gg.rim_index(ref) + h + tau if t_rim is None else t_rim) - gap
        for s in range(SEEDS):
            w, v = draw(ROBOT, ref, ih, s, gap)
            r = Rb.run(ROBOT, ref, hole, eta, h, tau, (t_d, w, v), tf=T + 4.0)
            out[ih, s] = [r[x] for x in G.KEYS]
    return out


if __name__ == "__main__":
    jobs = list(itertools.product(PERIOD, DELAY, LAG, GAP, range(len(ETA) + 1)))
    with mp.Pool(9) as pool:
        res = []
        for i, r in enumerate(pool.imap(work, jobs, chunksize=1)):
            res.append(r)
            if i % 40 == 0:
                print(i, len(jobs), flush=True)
    shape = (len(PERIOD), len(DELAY), len(LAG), len(GAP), len(ETA) + 1) + res[0].shape
    np.savez("results/gate_rule.npz", data=np.array(res).reshape(shape), keys=np.array(G.KEYS))
