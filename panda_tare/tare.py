"""PROTOKOL.md: TARE (MOMENT-2R that re-zeros the wrench on free-air readings just before contact) against
DOKUN-KAHIN under panda_sensor's sensor levels S1-S3. Two seeds only (500-501), at the user's request.

Run: python tare.py        (.pbenv; writes results/tare.npz, checkpoint results/tare.npz.partial.pkl)
"""
import itertools
import multiprocessing as mp
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "panda_sensor"))

import sensor as S  # sets the other paths

import numpy as np

import exp_time as X
import gate_rule as Gr
import rival as Rv
import timesim as Ts

LV = ["S1", "S2", "S3"]
ARMS = [0, 1, 2]
ERRORS = [0.003, 0.006, 0.010]
POLICIES = ["DOKUN", "M2R", "TARE"]
SEEDS = [int(x) for x in os.environ.get("EXP_SEEDS", "").split(",") if x] or [500, 501]
NB, Z_TARE = 30, 0.003  # ticks averaged, minimum tip height above the rim while averaging (m)
R_MIN_T, N_W_T = 0.002, 5
CALT = {"S1": {0.005: (0.01425272833306575, -0.8249490046463626), 0.002: (0.012727604467607796, -1.0583793799386598)},
        "S2": {0.005: None, 0.002: None}, "S3": {0.005: None, 0.002: None}}  # P1 (R2 S1 .84/.84, S2 .28/.32, S3 .03/.01)


class TareM2(S.Moment2S):
    """MOMENT-2R that subtracts the mean of the last NB idle readings taken with the tip > Z_TARE above the rim.
    The trigger keeps the raw F_z, as DOKUN-KAHIN's."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.buf_f, self.buf_m = [], []
        self.off_f, self.off_m, self.raw_fz = np.zeros(3), np.zeros(3), 0.0

    def trigger(self, z, fz):
        return super().trigger(z, self.raw_fz)

    def update(self, t, z, f, m, dt):
        f, m = np.asarray(f, float), np.asarray(m, float)
        self.raw_fz = float(f[2])
        if self.state == "idle" and z - Rv.Rb.RIM_Z > Z_TARE:
            self.buf_f, self.buf_m = (self.buf_f + [f])[-NB:], (self.buf_m + [m])[-NB:]
            self.off_f, self.off_m = np.mean(self.buf_f, 0), np.mean(self.buf_m, 0)
        return super().update(t, z, f - self.off_f, m - self.off_m, dt)


def episode(lv, arm, h, tau, err, c, policy, hole_i, seed, cal="default"):
    if policy != "TARE":
        return S.episode(lv, arm, h, tau, err, c, policy, hole_i, seed)
    di = X.DELAYS.index((h, tau))
    hole, ref, f = X.setup(arm, hole_i, S.T)
    u, mu, w, v, ns = X.draw_A(hole_i, seed, S.T)
    e = err * u
    sens = S.Sensor(lv, np.random.default_rng([ns, 7]))
    cal = CALT[lv][c] if cal == "default" else cal
    sh = TareM2(hole[:2], c, S.FT[lv], Rv.V_S[di], N_W_T, cal, r_min=R_MIN_T, sensor=sens)
    r = Ts.run_t(X.ROBOT, f, hole, e, c, Gr.rule(h, tau), h, tau, sh, None, np.random.default_rng(ns), mu,
                 tf=S.T + 8.0, meas=sens)
    est = sh.est
    r["aims"] = float(sh.aims)
    r["est_first"] = float(np.linalg.norm(est[0] - e[:2])) if est else -1.0
    r["est_last"] = float(np.linalg.norm(est[-1] - e[:2])) if est else -1.0
    r["r_first"] = -1.0 if sh.r_first is None else sh.r_first
    r["r_true"] = -1.0 if sh.r_true is None else sh.r_true
    r["dir_err"] = -1.0 if sh.dir_err is None else sh.dir_err
    # P0 / descriptive: how far the subtracted offset is from what the sensor adds at zero true wrench
    zero_f = sens.R @ sens.bF
    zero_m = sens.R @ ((1 + sens.k) * sens.bT) - np.cross(np.array([0.0, 0.0, -(S.L_ARM + sens.dL)]), zero_f)
    r["tare_err_f"] = float(np.linalg.norm(sh.off_f - zero_f))
    r["tare_err_m"] = float(np.linalg.norm(sh.off_m - zero_m))
    r["n_tare"] = float(len(sh.buf_f))
    return r


KEYS = S.KEYS + ["tare_err_f", "tare_err_m", "n_tare"]


def work(job):
    X.init()
    lv, arm, d, err, c, policy = job
    out = np.full((5, len(SEEDS), len(KEYS)), np.nan)
    for ih in range(5):
        for js, s in enumerate(SEEDS):
            r = episode(lv, arm, d[0], d[1], err, c, policy, ih, s)
            out[ih, js] = [float(r.get(k, np.nan)) for k in KEYS]
    return job, out


def jobs():
    return list(itertools.product(LV, ARMS, X.DELAYS, ERRORS, X.CLEAR, POLICIES))


def main(path):
    js = jobs()
    lists = [LV, ARMS, X.DELAYS, ERRORS, X.CLEAR, POLICIES]
    data = np.full(tuple(len(L) for L in lists) + (5, len(SEEDS), len(KEYS)), np.nan)
    part = path + ".partial.pkl"
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
    np.savez(path, data=data, keys=np.array(KEYS), levels=LV, arms=ARMS, period=S.T, delays=np.array(X.DELAYS),
             errors=ERRORS, clearances=X.CLEAR, policies=np.array(POLICIES), seeds=SEEDS,
             calt=np.array([[CALT[l][c] or (np.nan, np.nan) for c in X.CLEAR] for l in LV]),
             rmin_m2r=np.array([S.RMIN[l] for l in LV]))


if __name__ == "__main__":
    main(os.path.join(HERE, "results", "tare.npz"))
