"""The late-disturbance grid on learned fields, paired with the analytic arm, as PROTOKOL.md fixes it.

Run: python gate_learned.py    (pbenv; writes results/gate_learned.npz)
"""
import itertools
import multiprocessing as mp
import os

for name in ["OMP_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OPENBLAS_NUM_THREADS"]:
    os.environ[name] = "1"

import numpy as np

from learned import LearnedRef
import gate1 as G
import gate1g as Gg
import gate_rule as Gr
import robot as Rb

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = [0, 1, 2, 3, None]  # models 0-2 paper recipe, 3 weak, None analytic
ETA = [4, 5, 6.5, 8, 10, 12, 16, 20]
DELAY = [0.02, 0.04, 0.07, 0.09]
LAG = [0.0, 0.025, 0.04]
PERIOD = [8.0, 4.0]
GAP = [0.4, 0.25]
SEEDS = 20
ROBOT = None
MODELS = {}


def field(arm, ref, hole_i, T):
    if arm is None:
        return ref
    if arm not in MODELS:
        MODELS[arm] = dict(np.load(os.path.join(HERE, "models", f"model{arm}.npz")))
    return LearnedRef(ref, MODELS[arm], hole_i, T)


def work(job):
    """job: arm, T, h, tau, gap, index into ETA, where len(ETA) means the rule."""
    global ROBOT
    if ROBOT is None:
        ROBOT = Rb.Panda()
    arm, T, h, tau, gap, ie = job
    eta = Gr.rule(h, tau) if ie == len(ETA) else ETA[ie]
    out = np.zeros((len(Gr.HOLES), SEEDS, len(G.KEYS)))
    und = np.zeros((len(Gr.HOLES), len(G.KEYS)))
    for ih, hole in enumerate(Gr.HOLES):
        ref = Rb.reference_for(ROBOT, hole, T)
        f = field(arm, ref, ih, T)
        r = Rb.run(ROBOT, f, hole, eta, h, tau, None, tf=T + 4.0)
        und[ih] = [r[x] for x in G.KEYS]
        t_d = (ref.dt * Gg.rim_index(ref) + h + tau if r["t_rim"] is None else r["t_rim"]) - gap
        for s in range(SEEDS):
            w, v = Gr.draw(ROBOT, ref, ih, s, gap)
            r = Rb.run(ROBOT, f, hole, eta, h, tau, (t_d, w, v), tf=T + 4.0)
            out[ih, s] = [r[x] for x in G.KEYS]
    return out, und


if __name__ == "__main__":
    jobs = list(itertools.product(ARMS, PERIOD, DELAY, LAG, GAP, range(len(ETA) + 1)))
    with mp.Pool(9) as pool:
        res = []
        for i, r in enumerate(pool.imap(work, jobs, chunksize=1)):
            res.append(r)
            if i % 40 == 0:
                print(i, len(jobs), flush=True)
    shape = (len(ARMS), len(PERIOD), len(DELAY), len(LAG), len(GAP), len(ETA) + 1)
    np.savez(os.path.join(HERE, "results", "gate_learned.npz"), keys=np.array(G.KEYS),
             data=np.array([r[0] for r in res]).reshape(shape + res[0][0].shape),
             und=np.array([r[1] for r in res]).reshape(shape + res[0][1].shape))
