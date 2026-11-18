"""Analytic guidance vector field of BCSDM on the two-sphere, batched in numpy.

Conventions follow the paper: GVF = m + eta c (eq 19), discrete system with clipping (eq 20).
"""
import warnings

import numpy as np
import pyLasaDataset as lasa

# Accelerate's matmul raises spurious FP flags on Apple silicon; results are finite and tested.
warnings.filterwarnings("ignore", "(divide by zero|overflow|invalid value) encountered in matmul")

SHAPES = [n for n in lasa.DataSet.names if not n.startswith("Multi_Models")]
DT = 0.005
VMAX_FACTOR = 3.0
EPS = 1e-9


def normalize(a):
    return a / np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), EPS)


def dist(a, b):
    return np.arctan2(np.linalg.norm(np.cross(a, b), axis=-1), np.sum(a * b, axis=-1))


def exp_map(x, v):
    t = np.linalg.norm(v, axis=-1, keepdims=True)
    return normalize(np.cos(t) * x + np.sinc(t / np.pi) * v)


def log_map(x, y):
    """Tangent at x pointing along the minimal geodesic to y, with norm d(x, y)."""
    d = dist(x, y)[..., None]
    w = y - np.sum(x * y, axis=-1, keepdims=True) * x
    return w * d / np.maximum(np.linalg.norm(w, axis=-1, keepdims=True), EPS)


def transport(a, b, v):
    """Parallel transport of v in T_a along the minimal geodesic from a to b."""
    return v - np.sum(b * v, axis=-1, keepdims=True) / (1 + np.sum(a * b, axis=-1, keepdims=True)) * (a + b)


def map_shape(name):
    """All 7 demos of a shape on S2 as (demos, points, 3), plus each demo's own time step.

    Same bounding-box centre and scale for every demo of a shape, max radius 1 rad.
    """
    d = getattr(lasa.DataSet, name)
    p = np.stack([k.pos.T for k in d.demos]).astype(float)
    centre = (p.reshape(-1, 2).min(0) + p.reshape(-1, 2).max(0)) / 2
    q = p - centre
    q = q / np.linalg.norm(q, axis=-1).max()
    pole = np.array([0.0, 0.0, 1.0])
    v = np.concatenate([q, np.zeros(q.shape[:-1] + (1,))], -1)
    return exp_map(pole, v), np.array([k.t[0, -1] / (k.t.shape[1] - 1) for k in d.demos])


def smooth(a, k=5):
    pad = k // 2
    b = np.concatenate([a[:1].repeat(pad, 0), a, a[-1:].repeat(pad, 0)])
    return np.stack([np.convolve(b[:, i], np.ones(k) / k, "valid") for i in range(a.shape[1])], 1)


class Field:
    """Reference curve on S2 with exact nearest point on its great-circle segments."""

    def __init__(self, curve, dt):
        self.x = curve
        vel = np.gradient(curve, dt, axis=0)
        vel = smooth(vel)
        vel -= np.sum(vel * curve, -1, keepdims=True) * curve
        vel[-1] = 0.0
        self.vel = vel
        self.a, self.b = curve[:-1], curve[1:]
        self.seg = np.maximum(dist(self.a, self.b), 1e-12)
        self.cum = np.concatenate([[0.0], np.cumsum(self.seg)])
        self.length = self.cum[-1]
        self.goal = curve[-1]
        self.T = dt * (len(curve) - 1)
        self.vmax = VMAX_FACTOR * np.linalg.norm(vel, axis=1).max()
        self.tan = log_map(self.a, self.b) / self.seg[:, None]
        self.nrm = np.cross(self.a, self.tan)

    def nearest(self, x):
        """x (n,3). Returns D, c (= CVF), m (= MVF), s in [0, 1], at_start, at_end."""
        c1 = x @ self.nrm.T
        along = np.arctan2(x @ self.tan.T, x @ self.a.T)
        frac = np.clip(along / self.seg, 0.0, 1.0)
        # Interior distance to the great circle, otherwise the closer endpoint.
        d_line = np.abs(np.arcsin(np.clip(c1, -1, 1)))
        d_a = np.arccos(np.clip(x @ self.a.T, -1, 1))
        d_b = np.arccos(np.clip(x @ self.b.T, -1, 1))
        inside = (along >= 0) & (along <= self.seg)
        d_all = np.where(inside, d_line, np.minimum(d_a, d_b))
        idx = d_all.argmin(1)
        rows = np.arange(len(x))
        f = frac[rows, idx][:, None]
        a, tangent = self.a[idx], self.tan[idx]
        arc = f * self.seg[idx][:, None]
        star = np.cos(arc) * a + np.sin(arc) * tangent
        star = normalize(star)
        c = log_map(x, star)
        D = np.linalg.norm(c, axis=1)
        vstar = (1 - f) * self.vel[idx] + f * self.vel[idx + 1]
        vstar = vstar - np.sum(vstar * star, -1, keepdims=True) * star
        m = transport(star, x, vstar)
        s = (self.cum[idx] + f[:, 0] * self.seg[idx]) / self.length
        return D, c, m, s


def rollout(field, x0, eta_fn, dt=DT, tmax=None, vmax="field", stop=1e-3, keep_every=4):
    """Integrate (20). eta_fn(D, mnorm, s) -> eta, one value per batch element.

    Returns the kept path (t, n, 3), a done mask per kept step, and integrated E and Q.
    """
    vmax = field.vmax if vmax == "field" else (np.inf if vmax is None else vmax)
    x = np.atleast_2d(x0).copy()
    n_steps = int(round((tmax if tmax is not None else 4 * field.T) / dt))
    done = np.zeros(len(x), bool)
    E, Q = np.zeros(len(x)), np.zeros(len(x))
    path = [x.copy()]
    for k in range(n_steps):
        D, c, m, s = field.nearest(x)
        mn = np.linalg.norm(m, axis=1)
        eta = eta_fn(D, mn, s)
        v = m + eta[:, None] * c if np.ndim(eta) else m + eta * c
        vn = np.maximum(np.linalg.norm(v, axis=1, keepdims=True), EPS)
        u = v / vn * np.minimum(vn, vmax)
        mhat = m / np.maximum(mn, EPS)[:, None] * (mn > 1e-6)[:, None]
        live = ~done
        E += live * (np.linalg.norm(u, axis=1) - np.sum(u * mhat, 1)) * dt
        Q += live * (D**2 + 0.05 * np.sum((u - m) ** 2, 1)) * dt
        x_new = exp_map(x, u * dt)
        x = np.where(done[:, None], x, x_new)
        done |= dist(x, field.goal[None]) < stop
        if (k + 1) % keep_every == 0:
            path.append(x.copy())
        if done.all():
            break
    if (k + 1) % keep_every:
        path.append(x.copy())
    return np.stack(path), done, E, Q


def resample(path, n=200):
    d = np.concatenate([[0.0], np.cumsum(dist(path[:-1], path[1:]))])
    if d[-1] < 1e-9:
        return np.repeat(path[:1], n, 0)
    keep = np.concatenate([[True], np.diff(d) > 0])
    t = np.linspace(0, d[-1], n)
    return normalize(np.stack([np.interp(t, d[keep], path[keep, i]) for i in range(3)], 1))


def dtw(a, b):
    """Symmetric DTW on geodesic cost, mean cost per alignment step."""
    C = np.arccos(np.clip(a @ b.T, -1, 1))
    n, m = C.shape
    A = np.full((n + 1, m + 1), np.inf)
    L = np.zeros((n + 1, m + 1))
    A[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            opts = (A[i - 1, j - 1], A[i - 1, j], A[i, j - 1])
            k = int(np.argmin(opts))
            A[i, j] = C[i - 1, j - 1] + opts[k]
            L[i, j] = 1 + (L[i - 1, j - 1], L[i - 1, j], L[i, j - 1])[k]
    return A[n, m] / L[n, m]


def frechet(a, b):
    C = np.arccos(np.clip(a @ b.T, -1, 1))
    n, m = C.shape
    F = np.zeros_like(C)
    F[0, 0] = C[0, 0]
    F[1:, 0] = np.maximum.accumulate(C[1:, 0])
    F[1:, 0] = np.maximum(F[1:, 0], C[0, 0])
    F[0, 1:] = np.maximum(np.maximum.accumulate(C[0, 1:]), C[0, 0])
    for i in range(1, n):
        for j in range(1, m):
            F[i, j] = max(C[i, j], min(F[i - 1, j], F[i - 1, j - 1], F[i, j - 1]))
    return F[-1, -1]
