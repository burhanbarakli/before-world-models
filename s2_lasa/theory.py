"""Numerical checks T1-T6 from PROTOKOL.md. Run: python theory.py"""
import json

import numpy as np
import gvf_s2 as g

rng = np.random.default_rng(1)
OUT = {}


def fields(names=None):
    res = {}
    for n in names or g.SHAPES:
        c, dt = g.map_shape(n)
        res[n] = g.Field(c[0], dt[0])
    return res


def great_circle(length=3.0, speed=0.2, n=1000):
    """Reference with no curvature: a constant-speed arc on the equator, zero speed at the end."""
    t = np.linspace(0, length, n)
    curve = np.stack([np.cos(t), np.sin(t), 0 * t], 1)
    return g.Field(curve, length / speed / (n - 1))


def offset_starts(f, n, lo, hi):
    i = rng.integers(50, 900, n)
    x = f.x[i]
    t = rng.normal(size=x.shape)
    t -= np.sum(t * x, 1, keepdims=True) * x
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    return g.exp_map(x, t * rng.uniform(lo, hi, (n, 1)))


def schedule(kind, n, dt, steps):
    if kind == "switch":
        hold = max(1, int(round(0.1 / dt)))
        k = steps // hold + 2
        e = np.exp(rng.uniform(np.log(0.25), np.log(30), (k, n)))
        return np.repeat(e, hold, 0)
    if kind == "sine":
        t = np.arange(steps + 1)[:, None] * dt
        return 15.1 + 14.9 * np.sin(2 * np.pi * rng.uniform(0.1, 3, (1, n)) * t + rng.uniform(0, 6, (1, n)))
    raise ValueError(kind)


def t1():
    """Ddot + eta(t) D <= 0, no clipping, for arbitrary eta(t) and for eta(D)."""
    rows = []
    fs = fields()
    for kind in ["switch", "sine", "state"]:
        for dt in [0.005, 0.0025, 0.00125]:
            res, jumps, total = [], 0, 0
            for f in fs.values():
                n, steps = 12, int(1.0 / dt)
                x = offset_starts(f, n, 0.05, 0.4)
                e = schedule(kind, n, dt, steps) if kind != "state" else None
                for k in range(steps):
                    D, c, m, s = f.nearest(x)
                    eta = e[k] if e is not None else np.clip(0.3 * np.linalg.norm(m, axis=1) / np.maximum(D, 1e-9), 1, 30)
                    x = g.exp_map(x, (m + eta[:, None] * c) * dt)
                    D2, _, _, s2 = f.nearest(x)
                    # Exclude crossings of the nearest-point discontinuity and curve endpoints.
                    smooth = (np.abs(s2 - s) < 3 * 0.05 * dt * 30) & (s > 0.002) & (s < 0.998) & (D > 1e-3)
                    r = (D2 - D) / dt + eta * D
                    res.append(r[smooth])
                    jumps += int((~smooth).sum())
                    total += n
            r = np.concatenate(res)
            rows.append(dict(kind=kind, dt=dt, p50=float(np.median(r)), p999=float(np.quantile(r, 0.999)),
                             max=float(r.max()), excluded=jumps / total))
    OUT["T1"] = rows


def t2():
    """Near-curve discrete step, no clipping. Great circle, so no curvature floor."""
    f = great_circle()
    rows = []
    dt = 0.005
    for a in [0.5, 0.9, 1.1, 1.5, 1.9, 2.1, 2.5]:
        x = np.stack([np.cos(1.0) * 0.9998, np.sin(1.0) * 0.9998, 0.02])[None]
        x = g.normalize(x)
        seq, sign = [], []
        for k in range(14):
            D, c, m, s = f.nearest(x)
            seq.append(float(D[0]))
            sign.append(float(np.sign(x[0, 2])))
            x = g.exp_map(x, (m + a / dt * c) * dt)
        flips = int(np.sum(np.diff(sign) != 0))
        rows.append(dict(eta_dt=a, ratio_last_over_first=seq[8] / seq[0], flips=flips, predicted_factor=abs(1 - a)))
    # Switching with sup eta dt < 2 must still contract.
    x = g.normalize(np.array([[np.cos(1.0), np.sin(1.0), 0.02]]))
    d0 = f.nearest(x)[0][0]
    prod = 1.0
    for k in range(40):
        a = float(rng.choice([0.2, 1.0, 1.9]))
        D, c, m, s = f.nearest(x)
        x = g.exp_map(x, (m + a / dt * c) * dt)
        prod *= abs(1 - a)
    OUT["T2"] = dict(rows=rows, switching=dict(d_end_over_d0=float(f.nearest(x)[0][0] / d0), product=prod))


def t3():
    """Terminal region: m = 0, d_k = d_0 prod(1 - eta_k dt)."""
    f = great_circle()
    rows = []
    dt = 0.005
    for name, fn in [("a/k", lambda k: 0.5 / (k + 1)), ("a/k^2", lambda k: 0.5 / (k + 1) ** 2), ("const", lambda k: 0.05)]:
        t_end = f.x[-1]
        x = g.exp_map(t_end, (g.log_map(f.x[-2:-1], t_end[None])[0] / f.seg[-1] * 0.1)[None])
        d0 = g.dist(x, t_end[None])[0]
        pred, sat = d0, True
        for k in range(200000 if name == "a/k" else 20000):
            D, c, m, s = f.nearest(x)
            sat &= s[0] >= 1 - 1e-12 and np.linalg.norm(m) < 1e-12
            a = fn(k)
            x = g.exp_map(x, (m + a / dt * c) * dt)
            pred *= 1 - a
        rows.append(dict(law=name, d_end=float(g.dist(x, t_end[None])[0]), predicted=float(pred), stayed_terminal=bool(sat)))
    OUT["T3"] = rows


def t4():
    """Tube eps_c + eps_m / eta_min under a worst-case error, with fixed and switching eta."""
    f = great_circle(length=2.5, speed=0.05)
    rows = []
    dt = 0.005
    for ec in [0.0, 0.02, 0.05]:
        for em in [0.0, 0.02, 0.05]:
            if ec == em == 0:
                continue
            for mode in ["0.5", "2", "5", "20", "switch[2,20]", "random_dir"]:
                eta_min = {"0.5": 0.5, "2": 2, "5": 5, "20": 20, "switch[2,20]": 2, "random_dir": 2}[mode]
                bound = ec + em / eta_min
                x = g.normalize(np.array([[np.cos(0.3), np.sin(0.3), 2 * bound + 0.01]]))
                peak = []
                steps = int(30 / dt)
                for k in range(steps):
                    D, c, m, s = f.nearest(x)
                    chat = c / np.maximum(D[:, None], 1e-9)
                    if mode == "switch[2,20]":
                        eta = 2.0 if (k // 40) % 2 == 0 else 20.0
                    else:
                        eta = float(mode) if mode != "random_dir" else 2.0
                    if mode == "random_dir":
                        z = rng.normal(size=3)
                        z -= (z @ x[0]) * x[0]
                        z /= np.linalg.norm(z)
                        e_m, e_c = em * z, ec * z
                    else:
                        e_m, e_c = -em * chat, -ec * chat
                    x = g.exp_map(x, (m + e_m + eta * (c + e_c)) * dt)
                    if k > steps * 0.7 and s[0] < 0.95:
                        peak.append(float(D[0]))
                rows.append(dict(ec=ec, em=em, mode=mode, bound=bound, late_max=max(peak)))
    OUT["T4"] = rows


def delayed(f, eta, d_steps, lag, dt, tmax=10.0):
    """Offset response with a command delay of d_steps and a first-order lag of time constant lag."""
    x = g.normalize(np.array([[np.cos(0.2), np.sin(0.2), 0.01]]))
    buf = []
    uf = None
    z = []
    for k in range(int(tmax / dt)):
        D, c, m, s = f.nearest(x)
        u = m + eta * c
        buf.append((x.copy(), u.copy()))
        if len(buf) <= d_steps:
            xo, uo = x, m
        else:
            xo, uo = buf.pop(0)
        cmd = g.transport(xo, x, uo)
        if lag > 0:
            uf = cmd if uf is None else g.transport(xprev, x, uf) + dt / lag * (cmd - g.transport(xprev, x, uf))
            cmd = uf
        xprev = x
        x = g.exp_map(x, cmd * dt)
        z.append(x[0, 2])
        if s[0] > 0.95 or abs(x[0, 2]) > 0.3:
            break
    return np.array(z)


def t5():
    f = great_circle(length=4.0, speed=0.1)
    dt = 0.002
    rows = []
    h = 0.2
    d = int(round(h / dt))
    for eh in [0.2, 1 / np.e - 0.02, 1 / np.e + 0.04, 0.7, 1.2, 1.5, np.pi / 2 - 0.03, np.pi / 2 + 0.03, 1.7, 2.2]:
        z = delayed(f, eh / h, d, 0.0, dt)
        crossings = int(np.sum(np.diff(np.sign(z)) != 0))
        peaks = np.abs(z)
        n = len(z) // 2
        rows.append(dict(eta_h=float(eh), zero_crossings=crossings, late_over_early=float(peaks[n:].max() / peaks[:n].max())))
    lag_rows = []
    T = 0.1
    for et in [0.15, 0.24, 0.27, 0.5, 2.0, 8.0]:
        z = delayed(f, et / T, 0, T, dt)
        lag_rows.append(dict(eta_T=et, zero_crossings=int(np.sum(np.diff(np.sign(z)) != 0)),
                             late_over_early=float(np.abs(z[len(z) // 2:]).max() / np.abs(z[: len(z) // 2]).max())))
    OUT["T5"] = dict(delay=rows, lag=lag_rows)


def t6():
    rows = []
    for name, f in fields(["Sshape", "GShape", "Worm", "NShape", "Zshape"]).items():
        x = offset_starts(f, 64, 0.02, 0.25)
        for eta in [0.5, 2, 5, 20]:
            D, c, m, s = f.nearest(x)
            me = np.mean(np.linalg.norm(eta * c, axis=1)) / np.linalg.norm(f.vel, axis=1).max()
            xx, slopes = x.copy(), []
            logs = []
            T = 0.6 / eta if eta > 1 else 0.6
            for k in range(int(T / g.DT)):
                DD, cc, mm, _ = f.nearest(xx)
                logs.append(np.log(np.maximum(DD, 1e-12)))
                v = mm + eta * cc
                vn = np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)
                xx = g.exp_map(xx, v / vn * np.minimum(vn, f.vmax) * g.DT)
            logs = np.array(logs)
            cr = float(np.median(-(logs[-1] - logs[0]) / (T - g.DT)))
            rows.append(dict(shape=name, eta=eta, ME=float(me), CR=cr))
    OUT["T6"] = rows


for fn in [t1, t2, t3, t4, t5, t6]:
    fn()
    print("done", fn.__name__, flush=True)
    json.dump(OUT, open("results/theory.json", "w"), indent=1)
