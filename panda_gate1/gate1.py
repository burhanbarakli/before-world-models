"""Success against eta, delay, lag and speed, as PROTOKOL.md fixes it.

Run: python gate1.py    (writes results/gate1.npz)
"""
import itertools
import multiprocessing as mp

import numpy as np
import field_se3 as F
import robot as Rb

ETA = [0.5, 1, 2, 3, 5, 8, 12, 20]
DELAY = [0.0, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3]
LAG = [0.0, 0.05, 0.15]
PERIOD = [8.0, 4.0]
KINDS = [(0.5, None), (0.2, 0.6)]  # (scale, time as a fraction of T, or None for t = 1 s)
SEEDS = 10
KEYS = ["lat", "tilt", "end_z", "end_p", "end_r"]
ROBOT = None


def draw(robot, ref, hole_i, kind, seed):
    """Disturbance for one seed; redrawn while the disturbed pose is out of IK reach."""
    scale, frac = KINDS[kind]
    T = ref.dt * (len(ref.p) - 1)
    t = 1.0 if frac is None else frac * T
    rng = np.random.default_rng([hole_i, kind, seed, int(T)])
    i = int(t / ref.dt)
    while True:
        w, v = Rb.disturbance(rng, scale)
        Rb.ref_q0(robot, ref)
        robot.ik(ref.R[i], ref.p[i])
        e = robot.ik(ref.R[i] @ F.so3_exp(w), ref.p[i] + ref.R[i] @ v)
        if e[0] < 1e-3 and e[1] < 1e-3:
            return t, w, v


def work(job):
    global ROBOT
    if ROBOT is None:
        ROBOT = Rb.Panda()
    T, h, tau, eta = job
    out = np.zeros((len(Rb.HOLES), len(KINDS), SEEDS, len(KEYS)))
    for ih, hole in enumerate(Rb.HOLES):
        ref = Rb.reference_for(ROBOT, hole, T)
        for k, s in itertools.product(range(len(KINDS)), range(SEEDS)):
            d = draw(ROBOT, ref, ih, k, s)
            r = Rb.run(ROBOT, ref, hole, eta, h, tau, d)
            out[ih, k, s] = [r[x] for x in KEYS]
    return out


if __name__ == "__main__":
    jobs = list(itertools.product(PERIOD, DELAY, LAG, ETA))
    with mp.Pool(9) as pool:
        res = []
        for i, r in enumerate(pool.imap(work, jobs, chunksize=1)):
            res.append(r)
            if i % 20 == 0:
                print(i, len(jobs), flush=True)
    shape = (len(PERIOD), len(DELAY), len(LAG), len(ETA)) + res[0].shape
    np.savez("results/gate1.npz", data=np.array(res).reshape(shape), keys=np.array(KEYS))
