"""Exploratory runs after the validity check failed; nothing here enters the Gate 1 decision.

P1  Does a short settling time reproduce the paper's eta = .5 failure? (paper SR, T close to tf)
P2  Does the rise of SR with delay at low eta come from the disturbance landing earlier on the path?
P3  How much field error opens a window for eta? m_hat = m + rho |m| u(x), u smooth, unit in the metric.

Run: python inspect_sim.py    (writes results/inspect.txt)
"""
import itertools
import multiprocessing as mp

import numpy as np
import field_se3 as F
import robot as Rb
import gate1 as G

ROBOT = None
HOLES5 = range(len(Rb.HOLES))


class Biased:
    """Wraps a Reference; adds a smooth error to the MVF, proportional to its speed."""

    def __init__(self, ref, rho, seed):
        self.ref, self.rho = ref, rho
        self.vmax = ref.vmax
        self.goal_R, self.goal_p = ref.goal_R, ref.goal_p
        self.R, self.p, self.dt = ref.R, ref.p, ref.dt
        rng = np.random.default_rng(seed)
        self.k = rng.normal(size=(6, 3)) / 0.10  # correlation length about 10 cm
        self.phi = rng.uniform(0, 2 * np.pi, size=6)

    def field(self, R, p):
        c, m, D, i = self.ref.field(R, p)
        u = np.sin(self.k @ p + self.phi)
        w, v = u[:3], u[3:]
        s = self.rho * F.norm(*m) / max(F.norm(w, v), 1e-9)
        return c, (m[0] + s * w, m[1] + s * v), D, i


def ep(robot, ref, hole, eta, h, tau, d, tf=15.0):
    return Rb.run(robot, ref, hole, eta, h, tau, d, tf=tf)


def job(a):
    global ROBOT
    if ROBOT is None:
        ROBOT = Rb.Panda()
    name, T, h, tau, eta, ih, kind, seed, extra = a
    hole = Rb.HOLES[ih]
    ref = Rb.reference_for(ROBOT, hole, T)
    t, w, v = G.draw(ROBOT, ref, ih, kind, seed)
    run_ref = Biased(ref, extra, 1000 + ih + 7 * seed) if name == "P3" else ref
    if name == "P2":
        t = t + extra
    r = ep(ROBOT, run_ref, hole, eta, h, tau, (t, w, v))
    return a, Rb.paper_ok(r), Rb.insert_ok(r, 0.005), r["lat"], r["end_p"]


def rate(res, **sel):
    """Mean success for jobs whose fields match sel."""
    keys = ["name", "T", "h", "tau", "eta", "ih", "kind", "seed", "extra"]
    rows = [r for r in res if all(r[0][keys.index(n)] == v for n, v in sel.items())]
    return np.mean([r[1] for r in rows]), np.mean([r[2] for r in rows]), np.median([r[3] for r in rows]) * 1000


if __name__ == "__main__":
    jobs = []
    for T, eta, ih, s in itertools.product([8.0, 12.0, 14.0, 15.0], [0.5, 5], HOLES5, range(4)):
        jobs.append(("P1", T, 0.0, 0.0, eta, ih, 0, s, 0.0))
    for ih, kd, s in itertools.product(HOLES5, [0, 1], range(10)):
        jobs.append(("P2", 8.0, 0.0, 0.0, 1, ih, kd, s, 0.1))  # no delay, disturbance 100 ms later
    for rho, T, (h, tau), eta, ih, kd, s in itertools.product(
            [0.1, 0.3, 0.5], [8.0, 4.0], [(0.0, 0.0), (0.1, 0.05)], G.ETA, HOLES5, [0, 1], range(4)):
        jobs.append(("P3", T, h, tau, eta, ih, kd, s, rho))
    with mp.Pool(9) as pool:
        res = pool.map(job, jobs, chunksize=4)
    out = ["P1 paper SR, D1 only, no delay (paper: eta .5 -> .416, eta 5 -> .992)"]
    for T in [8.0, 12.0, 14.0, 15.0]:
        out.append(f"  T={T}: eta .5 {rate(res, name='P1', T=T, eta=0.5)[0]:.2f}   eta 5 {rate(res, name='P1', T=T, eta=5)[0]:.2f}")
    out.append(f"\nP2 eta=1 T=8, h=0, disturbance 100 ms later: SR_insert {rate(res, name='P2')[1]:.2f}"
               " (grid: h=0 .86, h=100 ms 1.00)")
    out.append("\nP3 SR_insert with field error, by rho, T, (h, tau); 40 runs per cell")
    out.append("                           " + " ".join(f"{e:5g}" for e in G.ETA))
    for rho, T, (h, tau) in itertools.product([0.1, 0.3, 0.5], [8.0, 4.0], [(0.0, 0.0), (0.1, 0.05)]):
        row = [rate(res, name="P3", extra=rho, T=T, h=h, tau=tau, eta=e)[1] for e in G.ETA]
        out.append(f"  rho {rho} T {T} h {h} tau {tau}:  " + " ".join(f"{v:5.2f}" for v in row))
    open("results/inspect.txt", "w").write("\n".join(out) + "\n")
