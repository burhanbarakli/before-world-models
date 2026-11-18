"""T1 diagnosis on a smooth curve: does the residual vanish with both dt and curve spacing?

On LASA the T1 residual did not fall with dt. Here the velocity is the analytic tangent and the
starts stay inside the curve's reach, so no nearest-point jump can occur.
Run: python t1b.py
"""
import json

import numpy as np
import gvf_s2 as g


def curve(n, speed=1.0):
    u = np.linspace(0, 1, 200001)
    lon, lat = 2.5 * u, 0.3 * np.sin(7.5 * u)
    p = np.stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], 1)
    arc = np.concatenate([[0], np.cumsum(g.dist(p[:-1], p[1:]))])
    t = np.linspace(0, arc[-1], n)
    uu = np.interp(t, arc, u)
    f = lambda w: np.stack([np.cos(.3 * np.sin(7.5 * w)) * np.cos(2.5 * w), np.cos(.3 * np.sin(7.5 * w)) * np.sin(2.5 * w), np.sin(.3 * np.sin(7.5 * w))], 1)
    x = f(uu)
    tan = g.normalize(f(uu + 1e-6) - f(uu - 1e-6))
    tan -= np.sum(tan * x, 1, keepdims=True) * x
    F = g.Field(x, arc[-1] / speed / (n - 1))
    F.vel = g.normalize(tan) * speed
    return F


def residual(F, kind, dt, seed=0):
    rng = np.random.default_rng(seed)
    i = rng.integers(len(F.x) // 10, 8 * len(F.x) // 10, 40)
    x = F.x[i]
    t = rng.normal(size=x.shape)
    t -= np.sum(t * x, 1, keepdims=True) * x
    x = g.exp_map(x, g.normalize(t) * rng.uniform(0.05, 0.25, (40, 1)))
    out = []
    steps = int(0.4 / dt)
    e = np.exp(rng.uniform(np.log(0.25), np.log(30), (steps // max(1, int(0.05 / dt)) + 2, 40)))
    for k in range(steps):
        D, c, m, s = F.nearest(x)
        eta = e[k // max(1, int(0.05 / dt))] if kind == "switch" else np.clip(0.3 * np.linalg.norm(m, axis=1) / np.maximum(D, 1e-9), 1, 30)
        x = g.exp_map(x, (m + eta[:, None] * c) * dt)
        D2 = F.nearest(x)[0]
        keep = D > 1e-2
        out.append(((D2 - D) / dt + eta * D)[keep])
    r = np.concatenate(out)
    return dict(kind=kind, dt=dt, p999=float(np.quantile(r, 0.999)), max=float(r.max()), n=int(r.size))


rows = []
for n, dt in [(1000, 0.005), (1000, 0.00125), (4000, 0.00125), (16000, 0.00125), (16000, 0.0003125)]:
    F = curve(n)
    for kind in ["switch", "state"]:
        r = residual(F, kind, dt)
        r["points"] = n
        r["spacing"] = float(F.seg.mean())
        rows.append(r)
        print(r, flush=True)
json.dump(rows, open("results/t1b.json", "w"), indent=1)
