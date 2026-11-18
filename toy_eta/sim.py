#!/usr/bin/env python3
"""Toy test: does a learned forward model select BCSDM's eta better than cheap alternatives?

Analytic GVF(x; eta) = MVF(x) + eta*CVF(x) in R^2, no neural field. See README.md.

Subcommands:
  test       sanity tests (decay rate, field on demo, discrete delay limit, grey-box self-fit)
  stability  oscillation onset versus delay (question 2)
  sweep      eta* versus delay/lag (question 1)
  run        main experiment (selectors A-F, fixed eta and schedule); writes tables.npz
"""
import argparse
import json
import math
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")

import numpy as np

# ---------------------------------------------------------------- fixed design constants
DT = 0.02
V_DEMO = 0.6            # peak demo speed, m/s
VMAX = 1.2              # clip, > max demo speed
L_DEMO = 2.0            # arc length of every demo, m
HORIZON = 350           # 7 s
ETAS = 0.25 * 2.0 ** np.arange(9)          # 0.25 ... 64
SCHED_LEVELS = 0.5 * (2 * math.sqrt(2)) ** np.arange(5)  # 0.5 1.41 4 11.3 32
SIGMA_ACT = 0.01        # actuator velocity noise, m/s
SIGMA_OBS = 0.0002      # position sensor noise, m
GATE_W = 0.025          # gate half width, m
GOAL_R = 0.03           # goal radius, m
STRIDE = 4              # steps per displacement in the mimicking metric
# score weights, fixed before any selector was evaluated
W_MIM, W_GATE, W_GOAL, W_SMOOTH = 2.0, 1.0, 1.0, 0.1
KHIST = 12              # command history in the MLP input (0.24 s), also max grey-box delay
BUDGETS = [200, 1000, 5000]
BETA = 1.0              # uncertainty penalty: score = mean_J + BETA*std_J over members
N_EVAL_STARTS = 6
N_MODEL_STARTS = 6
FAMILIES = ["ideal", "delay", "lag", "gain", "friction", "drift", "delay+lag", "all"]
EXC_ETAS = [1.0, 4.0, 16.0, 2.0, 8.0, 0.5]
EXC_NOISE = 0.03        # command noise in excitation, m/s


# ---------------------------------------------------------------- demos
class Demo:
    def __init__(self, raw_fn, n=200):
        u = np.linspace(0, 1, 4000)
        p = raw_fn(u)
        seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
        s = np.r_[0, np.cumsum(seg)]
        p = (p - p[0]) * L_DEMO / s[-1]
        s = s * L_DEMO / s[-1]
        self.s = np.linspace(0, L_DEMO, n)
        self.P = np.c_[np.interp(self.s, s, p[:, 0]), np.interp(self.s, s, p[:, 1])]
        self.cstep = 6
        self.Pc = self.P[:: self.cstep]
        self.win = np.arange(-self.cstep, self.cstep + 1)
        self.d = np.diff(self.P, axis=0)
        self.dd = (self.d ** 2).sum(1)
        self.t = self.d / np.sqrt(self.dd)[:, None]
        self.n = np.c_[-self.t[:, 1], self.t[:, 0]]
        x = self.s / L_DEMO
        ramp = 0.35 + 0.65 * np.sin(0.5 * np.pi * np.minimum(x / 0.25, 1.0))
        taper = np.minimum(np.sqrt(np.maximum(1 - x, 0) / 0.25), 1.0)
        self.speed = V_DEMO * ramp * taper
        self.speed[-1] = 0.0
        self.goal = self.P[-1].copy()
        mid = 0.5 * (self.speed[1:] + self.speed[:-1])
        self.T = float((np.diff(self.s) / np.maximum(mid, 1e-3)).sum())
        vel = np.r_[self.t, self.t[-1:]] * self.speed[:, None]
        self.tv_ref = float(np.linalg.norm(np.diff(vel, axis=0), axis=1).sum()) + V_DEMO

    def project(self, y):
        """Nearest point on the polyline. Returns xstar, tangent, arclength, speed."""
        # coarse-to-fine nearest vertex: exact except within a few mm of the medial axis
        ic = ((y[:, None, :] - self.Pc) ** 2).sum(-1).argmin(1) * self.cstep
        w = np.clip(ic[:, None] + self.win, 0, len(self.P) - 1)
        i = w[np.arange(len(y)), ((y[:, None, :] - self.P[w]) ** 2).sum(-1).argmin(1)]
        m = len(self.d) - 1
        j0 = np.clip(i - 1, 0, m)
        j1 = np.clip(i, 0, m)
        r0 = y - self.P[j0]
        r1 = y - self.P[j1]
        t0 = np.clip((r0 * self.d[j0]).sum(1) / self.dd[j0], 0, 1)
        t1 = np.clip((r1 * self.d[j1]).sum(1) / self.dd[j1], 0, 1)
        c0 = self.P[j0] + t0[:, None] * self.d[j0]
        c1 = self.P[j1] + t1[:, None] * self.d[j1]
        pick = ((y - c0) ** 2).sum(1) <= ((y - c1) ** 2).sum(1)
        j = np.where(pick, j0, j1)
        tt = np.where(pick, t0, t1)
        xs = np.where(pick[:, None], c0, c1)
        sp = self.speed[j] * (1 - tt) + self.speed[j + 1] * tt
        arc = self.s[j] + tt * (self.s[j + 1] - self.s[j])
        return xs, self.t[j], arc, sp

    def distance(self, y):
        return np.linalg.norm(y - self.project(y)[0], axis=1)


def make_demos():
    def s_curve(u):
        return np.c_[1.6 * u, 0.35 * np.sin(2 * np.pi * u)]

    def spiral(u):
        th = 1.5 * np.pi * u
        r = 0.55 + 0.25 * u
        return np.c_[r * np.cos(th), r * np.sin(th)]

    def wave(u):
        return np.c_[1.4 * u, 0.22 * np.sin(3 * np.pi * u) + 0.3 * u]

    return [Demo(s_curve), Demo(spiral), Demo(wave)]


# ---------------------------------------------------------------- plants
def ideal_params():
    return dict(d=0, T=0.0, k=1.0, delta=0.0, A=0.0, w=1.0, ph1=0.0, ph2=0.0)


def sample_params(fam, rng):
    p = ideal_params()
    on = {
        "ideal": [], "delay": ["d"], "lag": ["T"], "gain": ["k"], "friction": ["delta"],
        "drift": ["A"], "delay+lag": ["d", "T"], "all": ["d", "T", "k", "delta", "A"],
    }[fam]
    if "d" in on:
        p["d"] = int(round(rng.uniform(0.02, 0.2) / DT))
    if "T" in on:
        p["T"] = float(rng.uniform(0.03, 0.3))
    if "k" in on:
        p["k"] = float(rng.uniform(0.7, 1.25))
    if "delta" in on:
        p["delta"] = float(rng.uniform(0.02, 0.08))
    if "A" in on:
        p["A"] = float(rng.uniform(0.03, 0.1))
        p["w"] = float(rng.uniform(1.5, 4.0))
        p["ph1"] = float(rng.uniform(0, 2 * np.pi))
        p["ph2"] = float(rng.uniform(0, 2 * np.pi))
    return p


class Plant:
    """x_{t+1} = x_t + dt*(a_{t+1} + drift(x_t) + noise),
    a_{t+1} = a_t + alpha*(k*softthresh(u_{t-d}, delta) - a_t).
    Used for the true plant, and (with fitted params, no drift) for selectors B and C."""

    def __init__(self, starts, p, sig_act=0.0, sig_obs=0.0, rng=None):
        self.x = starts.astype(float).copy()
        self.B = len(starts)
        self.p = p
        self.a = np.zeros_like(self.x)
        self.d = int(p["d"])
        self.buf = np.zeros((self.d + 1,) + self.x.shape)
        self.i = 0
        self.alpha = 1.0 if p["T"] <= 0 else 1 - math.exp(-DT / p["T"])
        self.sa, self.so, self.rng = sig_act, sig_obs, rng

    def obs(self):
        if self.so > 0:
            return self.x + self.so * self.rng.standard_normal(self.x.shape)
        return self.x

    def step(self, u):
        p = self.p
        self.buf[self.i] = u
        self.i = (self.i + 1) % (self.d + 1)
        ud = self.buf[self.i]  # oldest entry = u_{t-d}
        if p["delta"] > 0:
            ud = np.sign(ud) * np.maximum(np.abs(ud) - p["delta"], 0)
        self.a = self.a + self.alpha * (p["k"] * ud - self.a)
        v = self.a
        if p["A"] > 0:
            dr = p["A"] * np.c_[np.sin(p["w"] * self.x[:, 1] + p["ph1"]),
                                np.cos(p["w"] * self.x[:, 0] + p["ph2"])]
            v = v + dr
        if self.sa > 0:
            v = v + self.sa * self.rng.standard_normal(self.x.shape)
        self.x = self.x + DT * v


class EnsMember:
    """Closed-loop rollout of one MLP: next_y = y + dt*(u + residual(history))."""

    def __init__(self, starts, net, sig_obs=0.0, rng=None):
        self.x = starts.astype(float).copy()
        self.B = len(starts)
        self.net = net
        self.hu = np.zeros((self.B, KHIST, 2))
        self.vh = np.zeros((self.B, 2, 2))
        self.so, self.rng = sig_obs, rng

    def obs(self):
        if self.so > 0:
            return self.x + self.so * self.rng.standard_normal(self.x.shape)
        return self.x

    def step(self, u):
        self.hu[:, 1:] = self.hu[:, :-1]
        self.hu[:, 0] = u
        f = np.concatenate([self.hu.reshape(self.B, -1), self.vh.reshape(self.B, -1), self.x], 1)
        res = np.clip(self.net.mean(f), -1.5 * VMAX, 1.5 * VMAX)
        v = u + res
        self.vh[:, 1] = self.vh[:, 0]
        self.vh[:, 0] = v
        self.x = self.x + DT * v


# ---------------------------------------------------------------- rollout and score
class Task:
    def __init__(self, demo, s_gate):
        self.demo = demo
        i = int(np.searchsorted(demo.s, s_gate))
        i = min(i, len(demo.t) - 1)
        self.pg, self.tg, self.ng = demo.P[i], demo.t[i], demo.n[i]


def sample_starts(demo, n, rng):
    s0 = rng.uniform(0, 0.05 * L_DEMO, n)
    i = np.searchsorted(demo.s, s0).clip(0, len(demo.t) - 1)
    return demo.P[i] + demo.n[i] * (rng.uniform(0.15, 0.30, n) * rng.choice([-1.0, 1.0], n))[:, None]


def rollout(plant, task, etas, horizon=HORIZON, cmd_noise=0.0, rng=None, record=False):
    """etas: (B,) fixed, or (B,3) per-arc-length-segment. Returns per-trajectory cost parts."""
    demo = task.demo
    B = plant.B
    idx = np.arange(B)
    sched = etas.ndim == 2
    anchor = plant.x.copy()
    tan_anchor = None
    num = np.zeros(B)
    den = np.zeros(B)
    tv = np.zeros(B)
    uprev = None
    gate = np.full(B, 1.0)
    prev = plant.x.copy()
    side_prev = (prev - task.pg) @ task.tg
    tail = np.zeros(B)
    tail_n = 10
    Xs, Us, Ys = [], [], []
    for t in range(horizon):
        y = plant.obs()
        xs, tan, arc, sp = demo.project(y)
        eta = etas[idx, np.minimum((3 * arc / L_DEMO).astype(int), 2)] if sched else etas
        v = sp[:, None] * tan + eta[:, None] * (xs - y)
        n = np.linalg.norm(v, axis=1, keepdims=True)
        u = v * np.minimum(1.0, VMAX / np.maximum(n, 1e-9))
        if cmd_noise > 0:
            u = u + cmd_noise * rng.standard_normal(u.shape)
        if uprev is not None:
            tv += np.linalg.norm(u - uprev, axis=1)
        uprev = u
        if tan_anchor is None:
            tan_anchor = tan
        if record:
            Xs.append(plant.x.copy())
            Us.append(u.copy())
            Ys.append(y.copy())
        plant.step(u)
        x = plant.x
        side = (x - task.pg) @ task.tg
        cross = (side_prev < 0) & (side >= 0) | (side_prev > 0) & (side <= 0)
        if cross.any():
            f = side_prev[cross] / (side_prev[cross] - side[cross])
            pc = prev[cross] + f[:, None] * (x[cross] - prev[cross])
            lat = np.abs((pc - task.pg) @ task.ng)
            gate[cross] = np.minimum(gate[cross], lat)
        prev = x
        side_prev = side
        if (t + 1) % STRIDE == 0:
            dx = x - anchor
            nd = np.linalg.norm(dx, axis=1)
            num += nd - (dx * tan_anchor).sum(1)
            den += nd
            anchor = x.copy()
            tan_anchor = None
        if t >= horizon - tail_n:
            tail += np.linalg.norm(x - demo.goal, axis=1) / tail_n
    S = num / np.maximum(den, 1e-6)
    G = np.where(gate <= GATE_W, 0.0, 0.5 + 0.5 * np.clip((gate - GATE_W) / (3 * GATE_W), 0, 1))
    R = np.where(tail <= GOAL_R, 0.0, 0.5 + 0.5 * np.clip((tail - GOAL_R) / (3 * GOAL_R), 0, 1))
    U = np.log1p(tv / demo.tv_ref)
    J = W_MIM * S + W_GATE * G + W_GOAL * R + W_SMOOTH * U
    out = dict(J=J, S=S, G=G, R=R, U=U, gate=gate, tail=tail)
    if record:
        out["X"] = np.array(Xs + [plant.x.copy()])
        out["U_"] = np.array(Us)
        out["Y"] = np.array(Ys + [plant.obs()])
    return out


def eval_table(make_plant, task, starts, cands):
    """Mean J over starts for each candidate. cands: (C,) or (C,3). Returns (C,), parts."""
    C, M = len(cands), len(starts)
    st = np.tile(starts, (C, 1))
    et = np.repeat(cands, M, axis=0)
    r = rollout(make_plant(st), task, et)
    return r["J"].reshape(C, M).mean(1), r


# ---------------------------------------------------------------- data logging
def collect(p, demo, task, n_transitions, rng):
    """Field rollouts on the true plant with several eta values plus small command noise."""
    n_ep = max(3, int(round(n_transitions / 330)))
    length = n_transitions // n_ep
    eps = []
    for e in range(n_ep):
        st = sample_starts(demo, 1, rng)
        plant = Plant(st, p, SIGMA_ACT, SIGMA_OBS, rng)
        r = rollout(plant, task, np.array([EXC_ETAS[e % len(EXC_ETAS)]]), horizon=length,
                    cmd_noise=EXC_NOISE, rng=rng, record=True)
        eps.append((r["U_"][:, 0], r["Y"][:, 0]))
    return eps


# ---------------------------------------------------------------- selector C: grey box
T_GRID = np.array([0, 0.01, 0.02, 0.03, 0.045, 0.06, 0.08, 0.1, 0.13, 0.16, 0.2, 0.25, 0.3, 0.4, 0.5])
DELTA_GRID = np.array([0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.1])


def fit_grey(eps):
    """Grid over (d, T, delta), closed-form least squares for gain k, on observed velocity."""
    best = (np.inf, None)
    alphas = np.where(T_GRID > 0, 1 - np.exp(-DT / np.maximum(T_GRID, 1e-9)), 1.0)
    F = {}  # (episode) -> filtered commands (N, nd, nT, 2)
    for ie, (U, Y) in enumerate(eps):
        st = np.sign(U)[:, None, :] * np.maximum(np.abs(U)[:, None, :] - DELTA_GRID[None, :, None], 0)
        N = len(U)
        out = np.zeros((N, len(DELTA_GRID), len(T_GRID), 2))
        a = np.zeros((len(DELTA_GRID), len(T_GRID), 2))
        al = alphas[None, :, None]
        for t in range(N):
            a = a + al * (st[t][:, None, :] - a)
            out[t] = a
        F[ie] = out
    for d in range(KHIST + 1):
        Sff = 0.0
        Sfv = 0.0
        Svv = 0.0
        for ie, (U, Y) in enumerate(eps):
            V = np.diff(Y, axis=0) / DT
            if d >= len(U):
                continue
            f = F[ie][: len(U) - d]
            v = V[d:]
            Sff = Sff + (f ** 2).sum((0, 3))
            Sfv = Sfv + (f * v[:, None, None, :]).sum((0, 3))
            # transitions before the delay has elapsed: model predicts zero velocity
            Svv = Svv + (V ** 2).sum()
            # those early samples contribute no f terms, so SSE stays comparable across d
        k = Sfv / np.maximum(Sff, 1e-9)
        k = np.clip(k, 0.2, 2.0)
        sse = Svv - 2 * k * Sfv + k * k * Sff
        i, j = np.unravel_index(np.argmin(sse), sse.shape)
        if sse[i, j] < best[0]:
            best = (float(sse[i, j]), dict(d=d, T=float(T_GRID[j]), k=float(k[i, j]),
                                           delta=float(DELTA_GRID[i]), A=0.0, w=1.0, ph1=0.0, ph2=0.0))
    return best[1]


def grey_velocity(p, U):
    """Predicted velocity sequence for a logged command sequence."""
    plant = Plant(np.zeros((1, 2)), p)
    out = np.zeros_like(U)
    for t in range(len(U)):
        x0 = plant.x.copy()
        plant.step(U[t][None])
        out[t] = (plant.x - x0)[0] / DT
    return out


# ---------------------------------------------------------------- selector D: MLP ensemble
def features(eps):
    Xs, Ts = [], []
    for U, Y in eps:
        N = len(U)
        V = np.diff(Y, axis=0) / DT
        for t in range(N):
            hu = np.zeros((KHIST, 2))
            m = min(KHIST, t + 1)
            hu[:m] = U[t::-1][:m]
            vh = np.zeros((2, 2))
            if t >= 1:
                vh[0] = V[t - 1]
            if t >= 2:
                vh[1] = V[t - 2]
            Xs.append(np.r_[hu.ravel(), vh.ravel(), Y[t]])
            Ts.append(V[t] - U[t])
    return np.array(Xs), np.array(Ts)


class Net:
    def __init__(self, Ws, bs, xm, xs, ym, ys):
        self.Ws, self.bs, self.xm, self.xs, self.ym, self.ys = Ws, bs, xm, xs, ym, ys

    def mean(self, f):
        h = (f - self.xm) / self.xs
        for W, b in zip(self.Ws[:-1], self.bs[:-1]):
            h = np.maximum(h @ W + b, 0)
        return (h @ self.Ws[-1] + self.bs[-1])[:, :2] * self.ys + self.ym


def train_ensemble(eps, rng, n_members=3, hidden=64, max_steps=3000):
    import torch
    torch.set_num_threads(1)
    X, Y = features(eps)
    xm, xs = X.mean(0), X.std(0) + 1e-3
    ym, ys = Y.mean(0), Y.std(0) + 1e-3
    Xn = torch.tensor((X - xm) / xs, dtype=torch.float32)
    Yn = torch.tensor((Y - ym) / ys, dtype=torch.float32)
    N = len(Xn)
    nets = []
    for m in range(n_members):
        torch.manual_seed(int(rng.integers(1 << 31)))
        perm = rng.permutation(N)
        nval = max(10, N // 10)
        val, tr = perm[:nval], perm[nval:]
        tr = tr[rng.integers(0, len(tr), len(tr))]  # bootstrap
        net = torch.nn.Sequential(torch.nn.Linear(X.shape[1], hidden), torch.nn.ReLU(),
                                  torch.nn.Linear(hidden, hidden), torch.nn.ReLU(),
                                  torch.nn.Linear(hidden, 4))
        opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-5)
        bs = min(128, max(16, len(tr) // 4))

        def nll(xb, yb):
            o = net(xb)
            mu, lv = o[:, :2], o[:, 2:].clamp(-8, 4)
            return (0.5 * lv + 0.5 * (yb - mu) ** 2 * torch.exp(-lv)).sum(1).mean()

        best, best_state, since = np.inf, None, 0
        for step in range(max_steps):
            ib = rng.integers(0, len(tr), bs)
            loss = nll(Xn[tr[ib]], Yn[tr[ib]])
            opt.zero_grad()
            loss.backward()
            opt.step()
            if (step + 1) % 50 == 0:
                with torch.no_grad():
                    lv = nll(Xn[val], Yn[val]).item()
                if lv < best:
                    best, since = lv, 0
                    best_state = [p.detach().numpy().copy() for p in net.parameters()]
                else:
                    since += 1
                    if since >= 8:
                        break
        Ws = [a.T.astype(np.float64) for a in best_state[0::2]]
        bs_ = [a.astype(np.float64) for a in best_state[1::2]]
        nets.append(Net(Ws, bs_, xm, xs, ym, ys))
    return nets


def ens_tables(nets, task, starts, cands, rng):
    Js = []
    for net in nets:
        J, _ = eval_table(lambda st: EnsMember(st, net, SIGMA_OBS, rng), task, starts, cands)
        Js.append(J)
    Js = np.array(Js)
    return Js.mean(0), Js.std(0)


# ---------------------------------------------------------------- prediction error (question 3)
def ens_open_loop(nets, U, Y, t0s, H):
    """Mean-of-members H-step prediction from logged history with logged commands."""
    preds = 0
    for net in nets:
        m = EnsMember(Y[t0s], net)
        for b, t in enumerate(t0s):
            hu = U[t - KHIST:t][::-1]
            m.hu[b] = hu
            m.vh[b, 0] = (Y[t] - Y[t - 1]) / DT
            m.vh[b, 1] = (Y[t - 1] - Y[t - 2]) / DT
        for h in range(H):
            m.step(U[t0s + h])
        preds = preds + m.x / len(nets)
    return preds


def prediction_errors(p_true, p_grey, nets, demo, task, rng, res):
    """RMSE, m, of position after H steps with logged commands, plus closed-loop gap."""
    for eta in (2.0, 8.0):
        st = sample_starts(demo, 2, rng)
        r = rollout(Plant(st, p_true, SIGMA_ACT, SIGMA_OBS, rng), task, np.full(2, eta), record=True)
        e = {}
        for b in range(2):
            U, Y = r["U_"][:, b], r["Y"][:, b]
            vg = grey_velocity(p_grey, U)
            for H in (1, 10, 50):
                t0s = np.arange(KHIST + 2, HORIZON - H, 5)
                pg = Y[t0s] + DT * np.array([vg[t:t + H].sum(0) for t in t0s])
                pn = Y[t0s] + DT * np.array([U[t:t + H].sum(0) for t in t0s])
                pd = ens_open_loop(nets, U, Y, t0s, H)
                tg = Y[t0s + H]
                for name, q in (("C", pg), ("D", pd), ("B", pn)):
                    e.setdefault((name, H), []).append(((q - tg) ** 2).sum(1).mean())
        rc = rollout(Plant(st, p_grey, 0, SIGMA_OBS, rng), task, np.full(2, eta), record=True)
        rd = [rollout(EnsMember(st, n, SIGMA_OBS, rng), task, np.full(2, eta), record=True) for n in nets]
        rn = rollout(Plant(st, ideal_params(), 0, SIGMA_OBS, rng), task, np.full(2, eta), record=True)
        cl = {"C": rc["X"], "D": np.mean([q["X"] for q in rd], 0), "B": rn["X"]}
        for name, q in cl.items():
            e[(name, "cl")] = [((q - r["X"]) ** 2).sum(-1).mean()]
        for k_, v in e.items():
            res[(k_[0], k_[1], eta)] = float(np.sqrt(np.mean(v)))


# ---------------------------------------------------------------- one randomised instance
def schedules():
    g = np.array(np.meshgrid(SCHED_LEVELS, SCHED_LEVELS, SCHED_LEVELS, indexing="ij"))
    return g.reshape(3, -1).T


def make_instance(seed, fam_i, i, demos):
    rng = np.random.default_rng([seed, fam_i, i])
    fam = FAMILIES[fam_i]
    demo_i = i % len(demos)
    demo = demos[demo_i]
    task = Task(demo, rng.uniform(0.45, 0.75) * L_DEMO)
    return rng, fam, demo_i, demo, task, sample_params(fam, rng)


def run_instance(args):
    seed, fam_i, i, do_sched = args
    t0 = time.time()
    demos = make_demos()
    rng, fam, demo_i, demo, task, p = make_instance(seed, fam_i, i, demos)
    eta_c = ETAS
    sch_c = schedules()
    ev = sample_starts(demo, N_EVAL_STARTS, rng)
    md = sample_starts(demo, N_MODEL_STARTS, rng)
    e_paired = sample_starts(demo, 3, rng)  # column 0 is the single-start E, all 3 give E_multi
    e_unpaired = sample_starts(demo, len(eta_c), rng)
    mk_true = lambda st: Plant(st, p, SIGMA_ACT, SIGMA_OBS, rng)
    mk_nom = lambda st: Plant(st, ideal_params(), 0, SIGMA_OBS, rng)

    out = dict(seed=seed, family=fam_i, i=i, demo=demo_i, **{"p_" + k: v for k, v in p.items()})
    Jt, rt = eval_table(mk_true, task, ev, eta_c)
    out["J_true"] = Jt
    for k_ in ("S", "G", "R", "U"):
        out["true_" + k_] = rt[k_].reshape(len(eta_c), -1).mean(1)
    _, re_ = eval_table(mk_true, task, e_paired, eta_c)
    out["J_E_m"] = re_["J"].reshape(len(eta_c), 3)
    out["J_E_unpaired"] = rollout(mk_true(e_unpaired), task, eta_c)["J"]
    out["Jh_B"], _ = eval_table(mk_nom, task, md, eta_c)
    if do_sched:
        Jts, rts = eval_table(mk_true, task, ev, sch_c)
        out["S_true"] = Jts
        out["S_true_fail"] = (rts["G"] + rts["R"] > 0).reshape(len(sch_c), -1).mean(1)
        _, re_ = eval_table(mk_true, task, e_paired, sch_c)
        out["S_E_m"] = re_["J"].reshape(len(sch_c), 3)
        out["S_E_unpaired"] = rollout(mk_true(sample_starts(demo, len(sch_c), rng)), task, sch_c)["J"]
        out["Sh_B"], _ = eval_table(mk_nom, task, md, sch_c)
    # one nested excitation log: smaller budgets are prefixes in episode count terms, so
    # draw each independently to keep budgets honest about episode shape.
    for N in BUDGETS:
        eps = collect(p, demo, task, N, rng)
        pg = fit_grey(eps)
        for k_ in ("d", "T", "k", "delta"):
            out[f"fit_{k_}_{N}"] = pg[k_]
        out[f"Jh_C_{N}"], _ = eval_table(lambda st: Plant(st, pg, 0, SIGMA_OBS, rng), task, md, eta_c)
        nets = train_ensemble(eps, rng)
        m, s = ens_tables(nets, task, md, eta_c, rng)
        out[f"Jh_Dm_{N}"], out[f"Jh_Ds_{N}"] = m, s
        if do_sched:
            out[f"Sh_C_{N}"], _ = eval_table(lambda st: Plant(st, pg, 0, SIGMA_OBS, rng), task, md, sch_c)
            m, s = ens_tables(nets, task, md, sch_c, rng)
            out[f"Sh_Dm_{N}"], out[f"Sh_Ds_{N}"] = m, s
        res = {}
        prediction_errors(p, pg, nets, demo, task, rng, res)
        for (name, H, eta), val in res.items():
            out[f"pe_{name}_{H}_{N}_{eta:g}"] = val
    out["secs"] = time.time() - t0
    return out


# ---------------------------------------------------------------- post-hoc: C plus linear drift map
class GreyDrift(Plant):
    """Grey box plus a ridge-fitted RBF map of position to velocity bias. Added after the main
    results showed D's advantage over C sits in the drift plants. Not in the original design."""

    def __init__(self, starts, p, drift, sig_obs=0.0, rng=None):
        super().__init__(starts, p, 0.0, sig_obs, rng)
        self.drift = drift

    def step(self, u):
        dx = DT * self.drift(self.x)
        super().step(u)
        self.x = self.x + dx


def fit_drift(pg, eps, lam=1.0, m=5):
    Y = np.concatenate([e[1][:-1] for e in eps])
    R = np.concatenate([np.diff(e[1], axis=0) / DT - grey_velocity(pg, e[0]) for e in eps])
    lo, hi = Y.min(0), Y.max(0)
    cx, cy = np.meshgrid(np.linspace(lo[0], hi[0], m), np.linspace(lo[1], hi[1], m))
    C = np.c_[cx.ravel(), cy.ravel()]
    sig2 = max(((hi - lo) / (m - 1)).max() ** 2, 1e-4)
    phi = lambda x: np.exp(-((x[:, None] - C) ** 2).sum(-1) / (2 * sig2))
    P = phi(Y)
    W = np.linalg.solve(P.T @ P + lam * np.eye(len(C)), P.T @ R)
    return lambda x: phi(x) @ W


def cplus_one(args):
    seed, fam_i, i = args
    demos = make_demos()
    rng, fam, demo_i, demo, task, p = make_instance(seed, fam_i, i, demos)
    sample_starts(demo, N_EVAL_STARTS, rng)
    md = sample_starts(demo, N_MODEL_STARTS, rng)
    out = dict(seed=seed, family=fam_i, i=i, p_T=p["T"], p_A=p["A"])
    for N in BUDGETS:
        eps = collect(p, demo, task, N, rng)
        pg = fit_grey(eps)
        dr = fit_drift(pg, eps)
        mk = lambda st: GreyDrift(st, pg, dr, SIGMA_OBS, rng)
        out[f"Jh_Cp_{N}"], _ = eval_table(mk, task, md, ETAS)
        out[f"Sh_Cp_{N}"], _ = eval_table(mk, task, md, schedules())
    return out


def cmd_cplus(a):
    import multiprocessing as mp
    jobs = [(s, f, i) for s in range(a.seed, a.seed + a.seeds) for f in range(len(FAMILIES)) for i in range(a.n)]
    with mp.get_context("spawn").Pool(a.workers) as pool:
        res = pool.map(run_cplus_safe, jobs, chunksize=4)
    res.sort(key=lambda r: (r["seed"], r["family"], r["i"]))
    np.savez_compressed(os.path.join(a.out, "cplus.npz"), **{k: np.array([r[k] for r in res], dtype=float) for k in res[0]})


run_cplus_safe = cplus_one


# ---------------------------------------------------------------- subcommands
def cmd_test(a):
    demos = make_demos()
    print("demo durations (s):", [round(d.T, 2) for d in demos], "tv_ref:", [round(d.tv_ref, 2) for d in demos])
    d = demos[0]
    # 1. field on the demo equals the demo velocity, CVF vanishes
    xs, tan, arc, sp = d.project(d.P[20:180])
    assert np.abs(xs - d.P[20:180]).max() < 1e-9
    # 2. distance decays at rate eta (ideal plant, unclipped)
    ok = True
    line = Demo(lambda u: np.c_[2.0 * u, 0 * u])
    for eta in (1.0, 2.0, 4.0, 8.0):
        st = line.P[[20]] + 0.04 * line.n[20]
        r = rollout(Plant(st, ideal_params()), Task(line, 1.0), np.array([eta]), horizon=60, record=True)
        D = line.distance(r["X"][:, 0])
        m = (D < 0.035) & (D > 1e-5)
        rate = -np.polyfit(np.arange(m.sum()) * DT, np.log(D[m]), 1)[0]
        expect = -math.log(1 - eta * DT) / DT
        print(f"straight demo eta={eta}: decay {rate:.3f}, discrete expectation {expect:.3f}, continuous {eta}")
        ok &= abs(rate - expect) / expect < 0.02
    assert ok, "decay rate test failed"
    # on a curve, Euler steps leave a steady outer-side offset ~ kappa*ds^2/(2*eta*dt)
    for eta in (1.0, 4.0, 16.0):
        st = d.P[[10]] + 0.0 * d.n[10]
        r = rollout(Plant(st, ideal_params()), Task(d, 1.0), np.array([eta]), horizon=200, record=True)
        print(f"curved demo eta={eta}: max D when started on demo {d.distance(r['X'][:, 0]).max():.5f} m")
    # 3. discrete delay limit: x_{t+1} = x_t - eta*dt*x_{t-d}
    for dd in (1, 5, 10):
        lim = 2 * math.sin(math.pi / (2 * (2 * dd + 1))) / DT
        for factor, stable in ((0.97, True), (1.03, False)):
            x = np.zeros(4000 + dd + 1)
            x[: dd + 1] = 1.0
            for t in range(dd, 4000 + dd):
                x[t + 1] = x[t] - factor * lim * DT * x[t - dd]
            late, mid = np.abs(x[-200:]).max(), np.abs(x[1000:1200]).max()
            assert (late < mid) == stable, (dd, factor, late, mid)
        print(f"d={dd}: discrete limit eta={lim:.2f}, eta*h={lim * dd * DT:.3f}, eta*(h+dt/2)={lim * (dd + .5) * DT:.3f}")
    # 4. grey box recovers a known plant
    rng = np.random.default_rng(0)
    p = dict(d=6, T=0.12, k=0.85, delta=0.04, A=0.0, w=1.0, ph1=0.0, ph2=0.0)
    task = Task(d, 1.2)
    eps = collect(p, d, task, 5000, rng)
    print("grey-box fit of d=6 T=.12 k=.85 delta=.04:", {k: round(v, 3) for k, v in fit_grey(eps).items() if k in "dTk" or k == "delta"})
    # 5. grey model equals plant when given true params
    st = sample_starts(d, 4, rng)
    r1 = rollout(Plant(st, p), task, np.full(4, 3.0))
    r2 = rollout(Plant(st, dict(p)), task, np.full(4, 3.0))
    assert np.allclose(r1["J"], r2["J"])
    # 6. J(eta) on ideal plant by parts
    print("J by eta on ideal plant, mean over 3 demos, 20 tasks (design check, no selector involved):")
    tot = []
    for i in range(60):
        rng, fam, di, dm, task, _ = make_instance(999, 0, i, demos)
        st = sample_starts(dm, 4, rng)
        J, r = eval_table(lambda s: Plant(s, ideal_params(), SIGMA_ACT, SIGMA_OBS, rng), task, st, ETAS)
        tot.append([r[k].reshape(len(ETAS), -1).mean(1) for k in ("J", "S", "G", "R", "U")])
    tot = np.mean(tot, 0)
    print("eta   ", " ".join(f"{e:7.2f}" for e in ETAS))
    for n, row in zip(("J", "S", "G", "R", "U"), tot):
        print(f"{n:6s}", " ".join(f"{v:7.3f}" for v in row))
    print("OK")


def linear_limit(dd, T):
    """Smallest eta making the discrete linear loop unstable (spectral radius > 1):
    x+ = x + dt*a+, a+ = a + alpha*(-eta*x_{t-d} - a). Same update as Plant."""
    alpha = 1.0 if T <= 0 else 1 - math.exp(-DT / T)

    def rho(eta):
        n = 2 + dd
        A = np.zeros((n, n))  # state x, a, x_{t-1} ... x_{t-d}
        src = 0 if dd == 0 else 1 + dd
        A[1, 1] = 1 - alpha
        A[1, src] -= alpha * eta
        A[0, :] = DT * A[1, :]
        A[0, 0] += 1
        if dd > 0:
            A[2, 0] = 1
            for i in range(1, dd):
                A[2 + i, 1 + i] = 1
        return np.abs(np.linalg.eigvals(A)).max()

    grid = np.geomspace(0.2, 2000, 4000)
    r = np.array([rho(e) for e in grid[::20]])
    i = np.argmax(r > 1 + 1e-9)
    if not (r > 1 + 1e-9).any():
        return None
    lo, hi = grid[::20][max(i - 1, 0)], grid[::20][i]
    for _ in range(40):
        mid = math.sqrt(lo * hi)
        lo, hi = (mid, hi) if rho(mid) <= 1 + 1e-9 else (lo, mid)
    return hi


def cmd_stability(a):
    """Oscillation onset, simulated on the demos, noise free. Onset = smallest eta above
    which the command total variation stays > 2.5 x the demo's on every larger grid eta.
    A distance threshold is not used: delay alone gives a tracking offset at bends."""
    demos = make_demos()
    etas = np.geomspace(0.5, 300, 100)
    rows = []
    for T in (0.0, 0.1, 0.3):
        for dd in (0, 1, 2, 3, 5, 7, 10, 15, 20):
            p = ideal_params()
            p["d"], p["T"] = dd, T
            onsets, amps = [], []
            for dm in demos:
                i = 15
                st = np.tile(dm.P[i] + 0.02 * dm.n[i], (len(etas), 1))
                r = rollout(Plant(st, p), Task(dm, 1.2), etas, horizon=int(dm.T * 2.0 / DT), record=True)
                ratio = np.expm1(r["U"])
                bad = ratio > 2.5
                onsets.append(float(etas[len(etas) - np.argmin(bad[::-1])]) if bad[-1] and not bad.all() else None)
                X = r["X"]
                late = X[int(1.0 / DT): int(0.7 * dm.T / DT)]
                D = np.array([dm.distance(q) for q in late])
                amps.append(float(np.sqrt((D[:, -1] ** 2).mean())))
            h = dd * DT
            vals = [o for o in onsets if o is not None]
            lin = linear_limit(dd, T)
            row = dict(T=T, d=dd, h=round(h, 3), eta_onset_sim=round(min(vals), 2) if vals else None,
                       eta_onset_each_demo=onsets, eta_lim_linear_discrete=round(lin, 2) if lin else None,
                       eta_times_h_sim=round(min(vals) * h, 3) if vals and h else None,
                       eta_times_h_linear=round(lin * h, 3) if lin and h else None,
                       eta_lim_pi_over_2h=round(math.pi / 2 / h, 2) if h else None,
                       rms_D_at_eta300=round(max(amps), 4), vmax_times_h=round(VMAX * h, 4))
            rows.append(row)
            print(row, flush=True)
    os.makedirs(a.out, exist_ok=True)
    json.dump(rows, open(os.path.join(a.out, "stability.json"), "w"), indent=1)


def sweep_one(args):
    kind, val, i, seed = args
    demos = make_demos()
    rng = np.random.default_rng([seed, 77, int(val * 1000), i, 0 if kind == "delay" else 1])
    demo = demos[i % 3]
    task = Task(demo, rng.uniform(0.45, 0.75) * L_DEMO)
    p = ideal_params()
    if kind == "delay":
        p["d"] = int(round(val / DT))
    else:
        p["T"] = val
    st = sample_starts(demo, N_EVAL_STARTS, rng)
    Jt, r = eval_table(lambda s: Plant(s, p, SIGMA_ACT, SIGMA_OBS, rng), task, st, ETAS)
    fail = ((r["G"] + r["R"]) > 0).reshape(len(ETAS), -1).mean(1)
    return kind, val, Jt, fail


def cmd_sweep(a):
    import multiprocessing as mp
    jobs = []
    for kind, vals in (("delay", (0, .04, .08, .12, .16, .2, .3)), ("lag", (0, .05, .1, .2, .3, .5))):
        for v in vals:
            jobs += [(kind, float(v), i, a.seed) for i in range(a.n)]
    with mp.get_context("spawn").Pool(a.workers) as pool:
        res = pool.map(sweep_one, jobs, chunksize=8)
    rows = []
    for kind, v in sorted({(r[0], r[1]) for r in res}):
        J = np.array([r[2] for r in res if r[0] == kind and r[1] == v])
        fl = np.array([r[3] for r in res if r[0] == kind and r[1] == v])
        best = J.argmin(1)
        row = dict(kind=kind, value=v, eta_star_of_mean_J=float(ETAS[J.mean(0).argmin()]),
                   geo_mean_eta_star=float(np.exp(np.log(ETAS[best]).mean())),
                   min_mean_J=float(J.mean(0).min()), mean_oracle_J=float(J.min(1).mean()),
                   mean_J=[round(float(x), 3) for x in J.mean(0)],
                   fail=[round(float(x), 2) for x in fl.mean(0)])
        rows.append(row)
        print(row, flush=True)
    os.makedirs(a.out, exist_ok=True)
    json.dump(rows, open(os.path.join(a.out, "sweep.json"), "w"), indent=1)


def cmd_run(a):
    import multiprocessing as mp
    fams = range(len(FAMILIES)) if a.families is None else [FAMILIES.index(f) for f in a.families.split(",")]
    jobs = []
    for seed in range(a.seed, a.seed + a.seeds):
        for f in fams:
            for i in range(a.n):
                jobs.append((seed, f, i, (i % a.sched_every == 0) if a.sched_every else False))
    print(len(jobs), "instances", flush=True)
    t0 = time.time()
    res = []
    with mp.get_context("spawn").Pool(a.workers) as pool:
        for k, r in enumerate(pool.imap_unordered(run_instance, jobs, chunksize=1)):
            res.append(r)
            if (k + 1) % max(1, len(jobs) // 20) == 0:
                print(k + 1, f"{time.time() - t0:.0f}s", flush=True)
    res.sort(key=lambda r: (r["seed"], r["family"], r["i"]))
    keys = sorted({k for r in res for k in r})
    tables = {}
    for k in keys:
        vals = [r.get(k) for r in res]
        shape = next(np.shape(v) for v in vals if v is not None)
        tables[k] = np.array([np.full(shape, np.nan) if v is None else v for v in vals], dtype=float)
    os.makedirs(a.out, exist_ok=True)
    np.savez_compressed(os.path.join(a.out, "tables.npz"), **tables)
    json.dump(dict(args=vars(a), etas=ETAS.tolist(), sched_levels=SCHED_LEVELS.tolist(), families=FAMILIES,
                   budgets=BUDGETS, weights=dict(mim=W_MIM, gate=W_GATE, goal=W_GOAL, smooth=W_SMOOTH),
                   beta=BETA, wall_seconds=time.time() - t0),
              open(os.path.join(a.out, "meta.json"), "w"), indent=1)
    print("done", f"{time.time() - t0:.0f}s", "mean secs per instance", np.mean([r["secs"] for r in res]))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("test", "stability", "sweep", "run", "cplus"):
        q = sp.add_parser(name)
        q.add_argument("--out", default=os.path.join(here, "results"))
        q.add_argument("--seed", type=int, default=0)
        q.add_argument("--workers", type=int, default=9)
        if name == "sweep":
            q.add_argument("--n", type=int, default=30)
        if name in ("run", "cplus"):
            q.add_argument("--seeds", type=int, default=3)
            q.add_argument("--n", type=int, default=9, help="instances per family per seed")
        if name == "run":
            q.add_argument("--sched_every", type=int, default=1, help="schedule experiment on every k-th instance, 0=off")
            q.add_argument("--families", default=None)
    a = ap.parse_args()
    {"test": cmd_test, "stability": cmd_stability, "sweep": cmd_sweep, "run": cmd_run, "cplus": cmd_cplus}[a.cmd](a)


if __name__ == "__main__":
    main()
