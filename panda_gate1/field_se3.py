"""Analytic GVF on SE(3) = SO(3) x R3 with the paper's metric tr(Rdot'Rdot) + 100 pdot'pdot.

Tangent vectors are (w, v): w is the body angular velocity, v the world linear velocity.
"""
import numpy as np

W_R, W_P = 2.0, 100.0  # |(w, v)|^2 = 2 |w|^2 + 100 |v|^2
N_POINTS = 501
UPSAMPLE = 3
EPS = 1e-10


def hat(w):
    return np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])


def so3_exp(w):
    t = np.linalg.norm(w)
    K = hat(w)
    if t < 1e-8:
        return np.eye(3) + K
    return np.eye(3) + np.sin(t) / t * K + (1 - np.cos(t)) / t**2 * K @ K


def so3_log(R):
    c = np.clip((np.trace(R) - 1) / 2, -1, 1)
    t = np.arccos(c)
    if t < 1e-8:
        return np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / 2
    if np.pi - t < 1e-6:
        A = (R + np.eye(3)) / 2
        i = int(np.argmax(np.diag(A)))
        u = A[i] / np.sqrt(max(A[i, i], EPS))
        return u / np.linalg.norm(u) * t
    return t / (2 * np.sin(t)) * np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])


def norm(w, v):
    return np.sqrt(W_R * w @ w + W_P * v @ v)


def distance(R1, p1, R2, p2):
    return norm(so3_log(R1.T @ R2), p2 - p1)


def bezier(p0, p1, p2, p3, u):
    u = u[:, None]
    return (1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u**2 * p2 + u**3 * p3


def make_reference(hole, rim_z, depth, p_start, R_start, R_down, T):
    """Curved approach arriving vertically 0.12 m above the hole, then a straight descent."""
    n = 4000
    via = np.array([hole[0], hole[1], rim_z + 0.12])
    goal = np.array([hole[0], hole[1], rim_z - depth])
    u = np.linspace(0, 1, n)
    curve = bezier(p_start, p_start + np.array([0.12, 0, 0.02]), via + np.array([0, 0, 0.14]), via, u)
    line = via + (goal - via) * u[1:, None]
    path = np.concatenate([curve, line])
    arc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    L = arc[-1]
    # Speed profile: nonzero at the start so x0 is not an equilibrium, zero at the goal.
    t = np.linspace(0, T, 20001)
    w = 0.15 * (1 - t / T) + 6 * (t / T) * (1 - t / T)
    s = np.concatenate([[0.0], np.cumsum((w[1:] + w[:-1]) / 2 * np.diff(t))])
    s *= L / s[-1]
    tt = np.linspace(0, T, N_POINTS * UPSAMPLE - (UPSAMPLE - 1))
    ss = np.interp(tt, t, s)
    p = np.stack([np.interp(ss, arc, path[:, i]) for i in range(3)], 1)
    frac = np.clip(ss / arc[n - 1], 0, 1)
    frac = frac * frac * (3 - 2 * frac)
    xi = so3_log(R_start.T @ R_down)
    R = np.stack([R_start @ so3_exp(f * xi) for f in frac])
    return Reference(R, p, tt[1] - tt[0], frac, xi)


class Reference:
    def __init__(self, R, p, dt, frac, xi):
        self.R, self.p, self.dt = R, p, dt
        self.v = np.gradient(p, dt, axis=0)
        self.v[-1] = 0.0
        self.w = np.gradient(frac, dt)[:, None] * xi  # constant axis, so body = world along it
        self.w[-1] = 0.0
        self.R_T = np.transpose(R, (0, 2, 1))
        speed = np.sqrt(W_R * np.sum(self.w**2, 1) + W_P * np.sum(self.v**2, 1))
        self.vmax = 3.0 * speed.max()
        self.goal_R, self.goal_p = R[-1], p[-1]

    def nearest(self, R, p):
        tr = np.einsum("ijk,kj->i", self.R_T, R.T.T)  # trace(Ri' R)
        ang = np.arccos(np.clip((tr - 1) / 2, -1, 1))
        d2 = W_R * ang**2 + W_P * np.sum((self.p - p) ** 2, 1)
        return int(np.argmin(d2)), float(np.sqrt(d2.min()))

    def field(self, R, p):
        """Returns c = CVF and m = MVF as (w, v) pairs, and D."""
        i, D = self.nearest(R, p)
        xi = so3_log(R.T @ self.R[i])
        c = (xi, self.p[i] - p)
        m = (so3_exp(xi / 2) @ self.w[i], self.v[i].copy())
        return c, m, D, i


def clip(w, v, vmax):
    n = norm(w, v)
    if n <= vmax:
        return w, v
    return w * vmax / n, v * vmax / n
