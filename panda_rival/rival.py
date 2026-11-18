"""PROTOKOL.md: MOMENT-2 (re-aiming, distance from |r|, local fallback) against DOKUN-KAHIN (knows e from the first
trigger on), with the same move mechanics. KAHIN and MOMENT of panda_time as descriptive references on model 0.

Run: python rival.py      (.pbenv; writes results/rival.npz)
"""
import itertools
import multiprocessing as mp
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "panda_time"))

import timesim as Ts  # sets the other paths

import contact as C
import numpy as np

import exp_time as X
import gate_rule as Gr
import robot as Rb

ARMS = [0, 1, 2]
ERRORS = [0.0, 0.003, 0.006, 0.010]
POLICIES = ["DOKUN", "MOMENT2", "KAHIN", "MOMENT", "MOMENT2F"]  # MOMENT2F: fixed step c, as registered (Sapma 1)
SEEDS = [int(x) for x in os.environ.get("EXP_SEEDS", "").split(",") if x] or list(range(300, 320))  # tests only
SEEDS_REF = SEEDS  # pilot P4 may cut the descriptive KAHIN / MOMENT runs to 10 seeds
SETTLE_V, SETTLE_N, SETTLE_T, N_AIM = 0.002, 5, 0.5, 4

# Set in the pilot
V_S = [0.01, 0.01, 0.005]  # fallback spiral speed per delay index, m/s (P3, pilot_rival2)
N_W = [5, 5, 5]  # MOMENT-2 averaging window per delay index, ticks (P3, pilot_rival2)
CAL = {0.005: (0.015308598436978994, -0.9746718485308907),
       0.002: (0.013595577174897837, -1.2231190241407184)}  # {c: (a, b)} distance calibration d = a + b |r|, or None for the fixed step c (P1, pilot_rival2)
V_S_F = [0.01, 0.01, 0.01]  # MOMENT2F tuning, first pilot (results/pilot_rival_1.txt)
N_W_F = [5, 5, 5]


class Touch(Ts.Spiral):
    """DOKUN-KAHIN: s-hat = 0 until the first trigger, then s0 = s = e and KAHIN from there."""

    def __init__(self, e, c, f_t, v_s):
        super().__init__(np.zeros(3), c, f_t, v_s, 2.0)
        self.e, self.jumped = np.asarray(e, float), False

    def update(self, t, z, f, m, dt):
        if not self.jumped and self.state == "idle" and z >= Rb.RIM_Z - 0.005:
            if self.trigger(z, f[2]):
                self.jumped, self.count, self.t_contact = True, 0, t
                self.s0, self.s = self.e.copy(), self.e.copy()
            return self.s
        return super().update(t, z, f, m, dt)


class Moment2(Ts.Spiral):
    """MOMENT-2. Measure n_w ticks after the trigger; jump to tip + d-hat u-hat; when the tip settles and still
    presses on the rim, measure again (at most N_AIM aims); no direction or N_AIM reached -> spiral around s-hat."""

    def __init__(self, hole_xy, c, f_t, v_s, n_w, cal, r_min=None):
        super().__init__(np.zeros(3), c, f_t, v_s, 2.0)
        self.r_min = Ts.R_MIN if r_min is None else r_min  # panda_sensor tunes it; default as run here
        self.h, self.c, self.n_w, self.cal = np.asarray(hole_xy, float), c, n_w, cal
        self.tip, self.prev, self.speed = None, None, 0.0
        self.acc_f, self.acc_m, self.n = np.zeros(3), np.zeros(3), 0
        self.aims, self.est, self.r_first = 0, [], None
        self.slow, self.t_set = 0, 0.0

    def see(self, pos):
        self.prev, self.tip = self.tip, np.array(pos[:2], float)

    def distance(self, r):
        if self.cal is None:
            return self.c
        a, b = self.cal
        return float(np.clip(a + b * r, 0.0, Ts.CAP))

    def to_spiral(self):
        self.state, self.s0, self.th = "search", self.s.copy(), 0.0

    def update(self, t, z, f, m, dt):
        if self.prev is not None:
            self.speed = float(np.linalg.norm(self.tip - self.prev)) / dt
        if self.state == "done":
            return self.s
        if z < Rb.RIM_Z - 0.005:
            self.state = "done"
            return self.s
        pressing = z - Rb.RIM_Z <= 0.02 and f[2] >= self.f_t
        if self.state == "idle":
            if self.trigger(z, f[2]):
                self.state, self.t_contact = "measure", t
            return self.s
        if self.state == "measure":
            self.acc_f, self.acc_m, self.n = self.acc_f + f, self.acc_m + m, self.n + 1
            if self.n >= self.n_w:
                fz = self.acc_f[2] / self.n
                tx, ty = self.acc_m[0] / self.n, self.acc_m[1] / self.n
                r = np.array([-ty / fz, tx / fz]) if fz > 1e-6 else np.zeros(2)
                self.acc_f, self.acc_m, self.n = np.zeros(3), np.zeros(3), 0
                if self.r_first is None:
                    self.r_first = float(np.linalg.norm(r))
                if np.linalg.norm(r) < self.r_min:
                    self.to_spiral()
                    return self.s
                u = -r / np.linalg.norm(r)
                if self.u is None:
                    self.u = np.array([*u, 0.0])
                est = self.tip - self.h + self.distance(float(np.linalg.norm(r))) * u
                self.est.append(est)
                self.s = np.array([*est, 0.0])
                self.aims += 1
                self.state, self.slow, self.t_set = "settle", 0, t
            return self.s
        if self.state == "settle":
            self.slow = self.slow + 1 if self.speed < SETTLE_V else 0
            if (self.slow >= SETTLE_N or t - self.t_set >= SETTLE_T) and pressing:
                if self.aims >= N_AIM:
                    self.to_spiral()
                else:
                    self.state = "measure"
            return self.s
        self.spiral(dt)
        return self.s


def episode(arm, T, h, tau, gap, err, c, policy, hole_i, seed, v_s=None, n_w=None, cal="default", tf_extra=8.0):
    di = X.DELAYS.index((h, tau))
    v_s = V_S[di] if v_s is None else v_s
    n_w = N_W[di] if n_w is None else n_w
    cal = (CAL or {}).get(c) if cal == "default" else cal
    hole, ref, f = X.setup(arm, hole_i, T)
    u, mu, w, v, ns = X.draw_A(hole_i, seed, T)
    e = err * u
    push = None if gap is None else (C.push_height(ref, gap), w, v)
    if policy == "DOKUN":
        sh = Touch(e, c, C.F_T, v_s)
    elif policy == "MOMENT2":
        sh = Moment2(hole[:2], c, C.F_T, v_s, n_w, cal)
    elif policy == "MOMENT2F":
        sh = Moment2(hole[:2], c, C.F_T, V_S_F[di], N_W_F[di], None)
    else:  # panda_time's KAHIN and MOMENT, its tuning
        sh = X.shift_for(policy, e if policy == "KAHIN" else np.zeros(3), c, X.params({}))
    r = Ts.run_t(X.ROBOT, f, hole, e, c, Gr.rule(h, tau), h, tau, sh, push, np.random.default_rng(ns), mu,
                 tf=T + tf_extra)
    est = getattr(sh, "est", [])
    r["aims"] = float(getattr(sh, "aims", 0))
    r["est_first"] = float(np.linalg.norm(est[0] - e[:2])) if est else -1.0
    r["est_last"] = float(np.linalg.norm(est[-1] - e[:2])) if est else -1.0
    r["r_first"] = -1.0 if getattr(sh, "r_first", None) is None else sh.r_first
    return r


KEYS = Ts.KEYS + ["aims", "est_first", "est_last", "r_first"]


def work(job):
    X.init()
    arm, T, (h, tau), gap, err, c, policy = job
    seeds = SEEDS_REF if policy in ("KAHIN", "MOMENT") else SEEDS
    out = np.full((5, len(SEEDS), len(KEYS)), np.nan)
    for ih in range(5):
        for js, s in enumerate(seeds):
            r = episode(arm, T, h, tau, gap, err, c, policy, ih, s)
            out[ih, js] = [float(r[k]) for k in KEYS]
    return job, out


def jobs():
    js = []
    for arm, T, d, g, e, c, p in itertools.product(ARMS, X.PERIOD, X.DELAYS, X.GAPS, ERRORS, X.CLEAR, POLICIES):
        if p in ("DOKUN", "MOMENT2", "MOMENT2F") and e > 0:
            js.append((arm, T, d, g, e, c, p))
        elif p == "MOMENT2" and e == 0 and arm == 0:
            js.append((arm, T, d, g, e, c, p))
        elif p in ("KAHIN", "MOMENT") and e > 0 and arm == 0:
            js.append((arm, T, d, g, e, c, p))
    return js


def main(path, js=None):
    js = jobs() if js is None else js
    lists = [ARMS, X.PERIOD, X.DELAYS, X.GAPS, ERRORS, X.CLEAR, POLICIES]
    data = np.full(tuple(len(L) for L in lists) + (5, len(SEEDS), len(KEYS)), np.nan)
    part = path + ".partial.pkl"  # checkpoint after every job; a restart resumes (Sapma 3)
    done = {}
    if os.path.exists(part):
        with open(part, "rb") as fh:
            done = pickle.load(fh)
        print("resuming,", len(done), "jobs from the checkpoint", flush=True)
    todo = [j for j in js if j not in done]
    with mp.Pool(9) as pool:
        for i, (j, out) in enumerate(pool.imap_unordered(work, todo, chunksize=1)):
            done[j] = out
            with open(part + ".tmp", "wb") as fh:
                pickle.dump(done, fh)
            os.replace(part + ".tmp", part)
            if i % 10 == 0:
                print(len(done), len(js), flush=True)
    for j in js:
        data[X.index(lists, j)] = done[j]
    np.savez(path, data=data, keys=np.array(KEYS), arms=ARMS, period=X.PERIOD, delays=np.array(X.DELAYS),
             gaps=np.array([-1.0 if g is None else g for g in X.GAPS]), errors=ERRORS, clearances=X.CLEAR,
             policies=np.array(POLICIES), seeds=SEEDS, seeds_ref=SEEDS_REF, v_s=np.array(V_S), n_w=np.array(N_W), v_s_f=np.array(V_S_F), n_w_f=np.array(N_W_F),
             cal=np.array([CAL.get(c, (np.nan, np.nan)) if CAL else (np.nan, np.nan) for c in X.CLEAR]))


if __name__ == "__main__":
    main(os.path.join(HERE, "results", "rival.npz"))
