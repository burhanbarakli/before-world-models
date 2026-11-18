"""Disturbance close to the rim, as PROTOKOL_GEC.md fixes it.

Run: python gate1g.py    (writes results/gate1g.npz)
"""
import itertools
import multiprocessing as mp

import numpy as np
import field_se3 as F
import gate1 as G
import robot as Rb

ETA = [2, 3, 5, 8, 12, 20]
DELAY = [0.0, 0.01, 0.02, 0.05, 0.1]
LAG = [0.0, 0.05]
PERIOD = [8.0, 4.0]
GAP = [0.5, 0.3, 0.2]
SCALE = 0.2
SEEDS = 20
ROBOT = None


def rim_index(ref):
    return int(np.argmax(ref.p[:, 2] < Rb.RIM_Z))


def draw(robot, ref, hole_i, seed, gap):
    """Direction for one seed, the same across gaps unless the disturbed pose is out of reach."""
    T = ref.dt * (len(ref.p) - 1)
    rng = np.random.default_rng([hole_i, 20, seed, int(T)])
    i = rim_index(ref) - int(round(gap / ref.dt))
    while True:
        w, v = Rb.disturbance(rng, SCALE)
        Rb.ref_q0(robot, ref)
        robot.ik(ref.R[i], ref.p[i])
        e = robot.ik(ref.R[i] @ F.so3_exp(w), ref.p[i] + ref.R[i] @ v)
        if e[0] < 1e-3 and e[1] < 1e-3:
            return w, v


def work(job):
    global ROBOT
    if ROBOT is None:
        ROBOT = Rb.Panda()
    T, h, tau, gap, eta = job
    out = np.zeros((len(Rb.HOLES), SEEDS, len(G.KEYS)))
    for ih, hole in enumerate(Rb.HOLES):
        ref = Rb.reference_for(ROBOT, hole, T)
        t_rim = Rb.run(ROBOT, ref, hole, eta, h, tau, None, tf=T + 4.0)["t_rim"]
        t_d = (ref.dt * rim_index(ref) + h + tau if t_rim is None else t_rim) - gap
        for s in range(SEEDS):
            w, v = draw(ROBOT, ref, ih, s, gap)
            r = Rb.run(ROBOT, ref, hole, eta, h, tau, (t_d, w, v), tf=T + 4.0)
            out[ih, s] = [r[x] for x in G.KEYS]
    return out


if __name__ == "__main__":
    jobs = list(itertools.product(PERIOD, DELAY, LAG, GAP, ETA))
    with mp.Pool(9) as pool:
        res = []
        for i, r in enumerate(pool.imap(work, jobs, chunksize=1)):
            res.append(r)
            if i % 20 == 0:
                print(i, len(jobs), flush=True)
    shape = (len(PERIOD), len(DELAY), len(LAG), len(GAP), len(ETA)) + res[0].shape
    np.savez("results/gate1g.npz", data=np.array(res).reshape(shape), keys=np.array(G.KEYS))
