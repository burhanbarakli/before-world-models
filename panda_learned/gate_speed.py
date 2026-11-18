"""The speed gate of PROTOKOL_KAPI.md: slows the MVF near the rim while the error is large.

Run: python gate_speed.py    (pbenv; writes results/gate_speed.npz)
"""
import itertools
import multiprocessing as mp
import os

import gate_learned as Gl  # sets the thread limits first

import numpy as np

import field_se3 as F
import gate1 as G
import gate1g as Gg
import gate_rule as Gr
import robot as Rb

LO = [0.01, 0.02, 0.04, 0.08]
BAND = 0.12
ROBOT = None


class Gated:
    """A field with alpha(x) on the MVF, in the last straight descent above the rim."""

    def __init__(self, f, lo):
        self.f, self.lo = f, lo
        self.dt, self.vmax, self.p, self.R = f.dt, f.vmax, f.p, f.R
        self.goal_R, self.goal_p = f.goal_R, f.goal_p

    def field(self, R, p):
        c, m, D, i = self.f.field(R, p)
        if 0 <= p[2] - Rb.RIM_Z <= BAND:
            a = float(np.clip((2 * self.lo - F.norm(c[0], c[1])) / self.lo, 0, 1))
            m = (a * m[0], a * m[1])
        return c, m, D, i


def work(job):
    """job: arm, T, h, tau, gap, option, where 0 is no gate and i > 0 means LO[i - 1]."""
    global ROBOT
    if ROBOT is None:
        ROBOT = Rb.Panda()
    arm, T, h, tau, gap, opt = job
    eta = Gr.rule(h, tau)
    out = np.zeros((len(Gr.HOLES), Gl.SEEDS, len(G.KEYS)))
    und = np.zeros((len(Gr.HOLES), len(G.KEYS)))
    for ih, hole in enumerate(Gr.HOLES):
        ref = Rb.reference_for(ROBOT, hole, T)
        f = Gl.field(arm, ref, ih, T)
        r = Rb.run(ROBOT, f, hole, eta, h, tau, None, tf=T + 4.0)
        und[ih] = [r[x] for x in G.KEYS]
        t_d = (ref.dt * Gg.rim_index(ref) + h + tau if r["t_rim"] is None else r["t_rim"]) - gap
        g = f if opt == 0 else Gated(f, LO[opt - 1])
        for s in range(Gl.SEEDS):
            w, v = Gr.draw(ROBOT, ref, ih, s, gap)
            r = Rb.run(ROBOT, g, hole, eta, h, tau, (t_d, w, v), tf=T + 4.0)
            out[ih, s] = [r[x] for x in G.KEYS]
    return out, und


if __name__ == "__main__":
    jobs = list(itertools.product(Gl.ARMS, Gl.PERIOD, Gl.DELAY, Gl.LAG, Gl.GAP, range(len(LO) + 1)))
    with mp.Pool(9) as pool:
        res = []
        for i, r in enumerate(pool.imap(work, jobs, chunksize=1)):
            res.append(r)
            if i % 40 == 0:
                print(i, len(jobs), flush=True)
    shape = (len(Gl.ARMS), len(Gl.PERIOD), len(Gl.DELAY), len(Gl.LAG), len(Gl.GAP), len(LO) + 1)
    np.savez(os.path.join(Gl.HERE, "results", "gate_speed.npz"), keys=np.array(G.KEYS),
             data=np.array([r[0] for r in res]).reshape(shape + res[0][0].shape),
             und=np.array([r[1] for r in res]).reshape(shape + res[0][1].shape))
