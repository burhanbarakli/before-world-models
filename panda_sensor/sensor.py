"""PROTOKOL.md: MOMENT-2 against DOKUN-KAHIN under force-torque sensor error levels S1-S3 (S0: the ideal model of
panda_rival). The sensor sits at the flange, L above the tip; the tip moment is computed from the flange wrench.

Run: python sensor.py      (.pbenv; writes results/sensor.npz, checkpoint results/sensor.npz.partial.pkl)
"""
import itertools
import multiprocessing as mp
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "panda_rival"))

import rival as Rv  # sets the other paths

import numpy as np

import contact as C
import exp_time as X
import gate_rule as Gr
import timesim as Ts

L_ARM = 0.35  # m, flange (sensor) to peg tip: 0.25 m peg + about 0.10 m Franka hand (assumption)
# sf, st: white noise per control tick (N, Nm); bf, bt: post-tare bias, N(0, .) per axis per run;
# dl: lever error, U(+-, m); phi: yaw misalignment, U(+-, deg); k: torque scale error, U(+-)
LEVELS = {
    "S1": dict(sf=0.05, st=0.002, bf=0.1, bt=0.003, dl=0.001, phi=1.0, k=0.01),
    "S2": dict(sf=0.2, st=0.005, bf=0.5, bt=0.01, dl=0.003, phi=3.0, k=0.03),
    "S3": dict(sf=1.0, st=0.05, bf=2.0, bt=0.1, dl=0.005, phi=5.0, k=0.10),
}
LV = ["S0", "S1", "S2", "S3"]
ARMS = [0, 1, 2]
T = 8.0
ERRORS = [0.0, 0.003, 0.006, 0.010]
POLICIES = ["DOKUN", "M2R", "M2T", "M2O", "M2", "M2C"]  # M2C: calibration kept although R2 < 0.5 (Sapma 3)
SEEDS = [int(x) for x in os.environ.get("EXP_SEEDS", "").split(",") if x] or list(range(400, 420))  # tests only
SEEDS_DESC = SEEDS  # P6 may cut M2T / M2O to 10 seeds

# Set in the pilot (per level S1-S3), results/pilot_sensor.txt
FT = {"S1": 5.0, "S2": 5.0, "S3": 5.0}  # trigger threshold, N (P3)
CAL = {"S1": {0.005: None, 0.002: None}, "S2": {0.005: None, 0.002: None},
       "S3": {0.005: None, 0.002: None}}  # P4: R2 < 0.5 everywhere -> fixed step c
NW = {"S1": 5, "S2": 5, "S3": 5}  # P5
RMIN = {"S1": 0.001, "S2": 0.004, "S3": 0.002}  # P5
# M2C (Sapma 3): the P4 least-squares fits kept regardless of R2 (from results/pilot_sensor.npz)
CALC = {"S1": {0.005: (0.01143528866710808, -0.3956374058375315), 0.002: (0.010853567237145222, -0.5687247908202918)},
        "S2": {0.005: (0.008330907279205666, -0.017744579654492363), 0.002: (0.007413222543096853, -0.023471301343288856)},
        "S3": {0.005: (0.008089158022331356, -0.001280163230024424), 0.002: (0.007085378310662588, -0.001254350651426194)}}


class Sensor:
    """One run's sensor: biases and calibration residuals drawn once, noise every tick. oracle: the trigger sees the
    noisy force, the moment is the true one scaled so that -tau_y / F_z gives the true contact offset."""

    def __init__(self, level, rng, oracle=False):
        P = LEVELS[level]
        self.P, self.rng, self.oracle = P, rng, oracle
        self.bF, self.bT = rng.normal(0, P["bf"], 3), rng.normal(0, P["bt"], 3)
        self.dL = rng.uniform(-P["dl"], P["dl"])
        ph = np.radians(rng.uniform(-P["phi"], P["phi"]))
        self.k = rng.uniform(-P["k"], P["k"])
        self.R = np.array([[np.cos(ph), -np.sin(ph), 0.0], [np.sin(ph), np.cos(ph), 0.0], [0.0, 0.0, 1.0]])
        self.f_true, self.m_true = np.zeros(3), np.zeros(3)

    def __call__(self, f, m):
        self.f_true, self.m_true = np.array(f, float), np.array(m, float)
        P, r = self.P, self.rng
        lever = np.array([0.0, 0.0, -L_ARM])  # tip minus sensor
        tau_f = self.m_true + np.cross(lever, self.f_true)
        F = self.R @ (self.f_true + self.bF + r.normal(0, P["sf"], 3))
        Tf = self.R @ ((1 + self.k) * (tau_f + self.bT + r.normal(0, P["st"], 3)))
        Tt = Tf - np.cross(np.array([0.0, 0.0, -(L_ARM + self.dL)]), F)
        if self.oracle:
            fz = self.f_true[2]
            return F, (self.m_true * F[2] / fz if abs(fz) > 1e-6 else self.m_true.copy())
        return F, Tt


class Moment2S(Rv.Moment2):
    """MOMENT-2 that also records the first measurement's true and measured contact offset (P2, descriptive)."""

    def __init__(self, *a, sensor=None, f_m=0.0, **k):
        super().__init__(*a, **k)
        self.sensor, self.f_m = sensor, f_m  # f_m: measure only ticks with F_z >= f_m (Sapma 2), at most 0.5 s wait
        self.prev_state, self.t_ms = "idle", 0.0
        self.af, self.am, self.tf, self.tm = np.zeros(3), np.zeros(3), np.zeros(3), np.zeros(3)
        self.r_true, self.dir_err = None, None

    def update(self, t, z, f, m, dt):
        if self.state == "measure" and self.prev_state != "measure":
            self.t_ms = t
        self.prev_state = self.state
        if self.state == "measure" and f[2] < self.f_m and t - self.t_ms < 0.5 and z >= Rv.Rb.RIM_Z - 0.005:
            if self.prev is not None:
                self.speed = float(np.linalg.norm(self.tip - self.prev)) / dt
            return self.s  # wait for the press force to build up
        first = self.r_first is None
        if first and self.state == "measure":
            self.af, self.am = self.af + f, self.am + m
            if self.sensor is not None:
                self.tf, self.tm = self.tf + self.sensor.f_true, self.tm + self.sensor.m_true
            else:
                self.tf, self.tm = self.tf + f, self.tm + m
        s = super().update(t, z, f, m, dt)
        if first and self.r_first is not None:
            rm = np.array([-self.am[1], self.am[0]]) / self.af[2] if self.af[2] > 1e-6 else np.zeros(2)
            rt = np.array([-self.tm[1], self.tm[0]]) / self.tf[2] if self.tf[2] > 1e-6 else np.zeros(2)
            self.r_true = float(np.linalg.norm(rt))
            if np.linalg.norm(rm) > 0 and np.linalg.norm(rt) > 0:
                cs = rm @ rt / np.linalg.norm(rm) / np.linalg.norm(rt)
                self.dir_err = float(np.degrees(np.arccos(np.clip(cs, -1, 1))))
        return s


def episode(lv, arm, h, tau, err, c, policy, hole_i, seed, ft=None, cal="default", n_w=None, r_min=None):
    di = X.DELAYS.index((h, tau))
    v_s = Rv.V_S[di]
    hole, ref, f = X.setup(arm, hole_i, T)
    u, mu, w, v, ns = X.draw_A(hole_i, seed, T)
    e = err * u
    if lv == "S0":
        sens, ft = None, C.F_T
    else:
        sens = Sensor(lv, np.random.default_rng([ns, 7]), oracle=(policy == "M2O"))
        ft = FT[lv] if ft is None else ft
    if policy == "DOKUN":
        sh = Rv.Touch(e, c, ft, v_s)
    elif policy == "M2":  # S0 reference: panda_rival's MOMENT-2 as run
        sh = Moment2S(hole[:2], c, ft, v_s, Rv.N_W[di], Rv.CAL[c], sensor=None)
    elif policy == "M2T":  # panda_rival's clean calibration and tuning, this level's sensor and trigger
        sh = Moment2S(hole[:2], c, ft, v_s, Rv.N_W[di], Rv.CAL[c], sensor=sens)
    elif policy == "M2O":  # true moment; clean calibration (the geometry it sees is the clean one), M2R's tuning
        sh = Moment2S(hole[:2], c, ft, v_s, NW[lv], Rv.CAL[c], r_min=RMIN[lv], sensor=sens)
    elif policy == "M2C":  # M2R's tuning with the weak calibration kept (carries the prior over |e|)
        sh = Moment2S(hole[:2], c, ft, v_s, NW[lv], CALC[lv][c], r_min=RMIN[lv], sensor=sens)
    else:  # M2R: recalibrated and retuned for this level
        cal = CAL[lv].get(c) if cal == "default" else cal
        sh = Moment2S(hole[:2], c, ft, v_s, NW[lv] if n_w is None else n_w, cal,
                      r_min=RMIN[lv] if r_min is None else r_min, sensor=sens)
    r = Ts.run_t(X.ROBOT, f, hole, e, c, Gr.rule(h, tau), h, tau, sh, None, np.random.default_rng(ns), mu,
                 tf=T + 8.0, meas=sens)
    est = getattr(sh, "est", [])
    r["aims"] = float(getattr(sh, "aims", 0))
    r["est_first"] = float(np.linalg.norm(est[0] - e[:2])) if est else -1.0
    r["est_last"] = float(np.linalg.norm(est[-1] - e[:2])) if est else -1.0
    r["r_first"] = -1.0 if getattr(sh, "r_first", None) is None else sh.r_first
    r["r_true"] = -1.0 if getattr(sh, "r_true", None) is None else sh.r_true
    r["dir_err"] = -1.0 if getattr(sh, "dir_err", None) is None else sh.dir_err
    return r


KEYS = Ts.KEYS + ["aims", "est_first", "est_last", "r_first", "r_true", "dir_err"]


def work(job):
    X.init()
    lv, arm, d, err, c, policy = job
    seeds = SEEDS_DESC if policy in ("M2T", "M2O") else SEEDS
    out = np.full((5, len(SEEDS), len(KEYS)), np.nan)
    for ih in range(5):
        for js, s in enumerate(seeds):
            r = episode(lv, arm, d[0], d[1], err, c, policy, ih, s)
            out[ih, js] = [float(r[k]) for k in KEYS]
    return job, out


def jobs():
    js = []
    for lv, arm, d, e, c, p in itertools.product(LV, ARMS, X.DELAYS, ERRORS, X.CLEAR, POLICIES):
        if lv == "S0":
            if p in ("DOKUN", "M2") and e > 0 and arm == 0:
                js.append((lv, arm, d, e, c, p))
        elif p in ("DOKUN", "M2R", "M2C") and e > 0:
            js.append((lv, arm, d, e, c, p))
        elif p in ("M2T", "M2O") and e > 0 and arm == 0:
            js.append((lv, arm, d, e, c, p))
        elif p == "M2R" and e == 0 and arm == 0:
            js.append((lv, arm, d, e, c, p))
    return js


def main(path, js=None):
    js = jobs() if js is None else js
    lists = [LV, ARMS, X.DELAYS, ERRORS, X.CLEAR, POLICIES]
    data = np.full(tuple(len(L) for L in lists) + (5, len(SEEDS), len(KEYS)), np.nan)
    part = path + ".partial.pkl"  # checkpoint after every job; a restart resumes
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
    np.savez(path, data=data, keys=np.array(KEYS), levels=LV, arms=ARMS, period=T, delays=np.array(X.DELAYS),
             errors=ERRORS, clearances=X.CLEAR, policies=np.array(POLICIES), seeds=SEEDS, seeds_desc=SEEDS_DESC,
             ft=np.array([FT[l] for l in LV[1:]]), nw=np.array([NW[l] for l in LV[1:]]),
             rmin=np.array([RMIN[l] for l in LV[1:]]),
             calc=np.array([[CALC[l][c] for c in X.CLEAR] for l in LV[1:]]),
             cal=np.array([[CAL[l].get(c) or (np.nan, np.nan) for c in X.CLEAR] for l in LV[1:]]),
             levels_def=np.array([[LEVELS[l][k] for k in ("sf", "st", "bf", "bt", "dl", "phi", "k")] for l in LV[1:]]))


if __name__ == "__main__":
    main(os.path.join(HERE, "results", "sensor.npz"))
