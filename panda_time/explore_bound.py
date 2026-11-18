"""EXPLORATORY, not in PROTOKOL.md: how much of D_A and D_B a model could take at best.

A: DOKUN-KAHIN knows e exactly, but only from the first contact trigger on (the best an in-episode estimator that
   reads contact could do). Model 0, all of A's other axes, the same draws as exp_time A.
B: SABIT-KAHIN knows the persistent offset exactly but not the trial's jitter, and runs MOMENT for the rest (the best
   a cross-trial model could do). Model 0, seeds 200-204, the same draws as exp_time B.

Run: python explore_bound.py     (.pbenv; writes results/explore_bound.npz)
"""
import itertools
import multiprocessing as mp
import os

import timesim as Ts

import contact as C
import numpy as np

import exp_time as X
import gate_rule as Gr

SEEDS_A, SEEDS_B = X.SEEDS, X.SEEDS_B[:5]


class Touch(Ts.Spiral):
    """s-hat = 0 until the first trigger, then s0 = s = e and KAHIN from there (its own trigger and spiral)."""

    def __init__(self, e, c, f_t, v_s, pitch):
        super().__init__(np.zeros(3), c, f_t, v_s, pitch)
        self.e, self.jumped = np.asarray(e, float), False

    def update(self, t, z, f, m, dt):
        if not self.jumped and self.state == "idle" and z >= Rb_rim() - 0.005:
            if self.trigger(z, f[2]):
                self.jumped, self.count, self.t_contact = True, 0, t
                self.s0, self.s = self.e.copy(), self.e.copy()
            return self.s
        return super().update(t, z, f, m, dt)


def Rb_rim():
    import robot as Rb
    return Rb.RIM_Z


def work_A(job):
    X.init()
    T, (h, tau), gap, err, c = job
    out = np.zeros((5, len(SEEDS_A), len(Ts.KEYS)))
    pr = X.params({})
    for ih in range(5):
        for js, s in enumerate(SEEDS_A):
            hole, ref, f = X.setup(0, ih, T)
            u, mu, w, v, ns = X.draw_A(ih, s, T)
            e = err * u
            push = None if gap is None else (C.push_height(ref, gap), w, v)
            r = Ts.run_t(X.ROBOT, f, hole, e, c, Gr.rule(h, tau), h, tau, Touch(e, c, C.F_T, pr["v_s"], pr["pitch"]),
                         push, np.random.default_rng(ns), mu, tf=T + 8.0)
            out[ih, js] = [float(r[k]) for k in Ts.KEYS]
    return ("A", job), out


def work_B(job):
    X.init()
    T, (h, tau), gap, err, c = job
    out = np.zeros((5, len(SEEDS_B), X.N_TRIALS, len(Ts.KEYS)))
    pr = X.params({})
    for ih in range(5):
        for js, s in enumerate(SEEDS_B):
            hole, ref, f = X.setup(X.ARM_B, ih, T)
            u, mu = X.draw_seq(ih, s, T)
            for k in range(X.N_TRIALS):
                jit, w, v, ns = X.draw_trial(ih, s, T, k)
                e = err * u + jit
                push = None if gap is None else (C.push_height(ref, gap), w, v)
                r = Ts.run_t(X.ROBOT, f, hole, e, c, Gr.rule(h, tau), h, tau,
                             X.shift_for("HAFIZA", err * u, c, pr), push, np.random.default_rng(ns), mu, tf=T + 8.0)
                out[ih, js, k] = [float(r[q]) for q in Ts.KEYS]
    return ("B", job), out


def main():
    grid = list(itertools.product(X.PERIOD, X.DELAYS, X.GAPS, X.ERRORS_B, X.CLEAR))
    lists = [X.PERIOD, X.DELAYS, X.GAPS, X.ERRORS_B, X.CLEAR]
    A = np.full((2, 3, 2, 3, 2, 5, len(SEEDS_A), len(Ts.KEYS)), np.nan)
    B = np.full((2, 3, 2, 3, 2, 5, len(SEEDS_B), X.N_TRIALS, len(Ts.KEYS)), np.nan)
    tasks = [(work_A, j) for j in grid] + [(work_B, j) for j in grid]
    with mp.Pool(9) as pool:
        for i, ((kind, j), out) in enumerate(pool.imap_unordered(run_task, tasks, chunksize=1)):
            (A if kind == "A" else B)[X.index(lists, j)] = out
            print(i, len(tasks), flush=True)
    np.savez(os.path.join(Ts.HERE, "results", "explore_bound.npz"), A=A, B=B, keys=np.array(Ts.KEYS),
             seeds_A=SEEDS_A, seeds_B=SEEDS_B)


def run_task(t):
    return t[0](t[1])


if __name__ == "__main__":
    main()
