"""Samples CVF and MVF targets around the five references at T = 8, as in the paper's appendix C-B.

Run: python make_data.py seed n_per_hole out.npz    (pbenv; needs field_se3 and robot from panda_gate1)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "panda_gate1"))
import field_se3 as F
import robot as Rb

HOLES = [(0.40, -0.12), (0.44, -0.04), (0.44, 0.04), (0.40, 0.12), (0.36, -0.08)]
T0 = 8.0
SD_P, SD_R = 0.05, 0.1
UNIFORM = 0.1
NX = 501


def exp_batch(w):
    t = np.linalg.norm(w, axis=1)
    a, b = np.ones_like(t), np.full_like(t, 0.5)
    m = t > 1e-8
    a[m] = np.sin(t[m]) / t[m]
    b[m] = (1 - np.cos(t[m])) / t[m] ** 2
    K = np.zeros((len(w), 3, 3))
    K[:, 0, 1], K[:, 0, 2], K[:, 1, 0] = -w[:, 2], w[:, 1], w[:, 2]
    K[:, 1, 2], K[:, 2, 0], K[:, 2, 1] = -w[:, 0], -w[:, 1], w[:, 0]
    return np.eye(3) + a[:, None, None] * K + b[:, None, None] * K @ K


def log_batch(R):
    c = np.clip((np.trace(R, axis1=1, axis2=2) - 1) / 2, -1, 1)
    t = np.arccos(c)
    v = np.stack([R[:, 2, 1] - R[:, 1, 2], R[:, 0, 2] - R[:, 2, 0], R[:, 1, 0] - R[:, 0, 1]], 1)
    out = v / 2
    m = t > 1e-8
    near = np.pi - t < 1e-6
    k = m & ~near
    out[k] = (t[k] / (2 * np.sin(t[k])))[:, None] * v[k]
    for i in np.where(near)[0]:
        out[i] = F.so3_log(R[i])
    return out


def references(T=T0):
    return [Rb.reference_for(None, h, T) for h in HOLES]


def targets(ref, R, p, chunk=20000):
    """Vectorised Reference.field: returns xi, dp, m_w, m_v, D."""
    n = len(R)
    Rr, Rp = ref.R.reshape(-1, 9), ref.p
    out = [np.zeros((n, 3)) for _ in range(4)] + [np.zeros(n)]
    for s in range(0, n, chunk):
        e = min(n, s + chunk)
        tr = R[s:e].reshape(-1, 9) @ Rr.T
        ang = np.arccos(np.clip((tr - 1) / 2, -1, 1))
        d2 = F.W_R * ang**2 + F.W_P * ((p[s:e, None] - Rp[None]) ** 2).sum(2)
        i = d2.argmin(1)
        xi = log_batch(np.transpose(R[s:e], (0, 2, 1)) @ ref.R[i])
        out[0][s:e], out[1][s:e] = xi, ref.p[i] - p[s:e]
        out[2][s:e] = (exp_batch(xi / 2) @ ref.w[i][..., None])[..., 0]
        out[3][s:e] = ref.v[i]
        out[4][s:e] = np.sqrt(d2[np.arange(e - s), i])
    return out


def uniform_rotations(rng, n):
    q = rng.normal(size=(n, 4))
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    w, x, y, z = q.T
    return np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
                     2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
                     2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], 1).reshape(-1, 3, 3)


def sample(rng, ref, n):
    n_uni = n // 10
    n_gmm = n - n_uni
    idx = np.linspace(0, len(ref.p) - 1, NX).round().astype(int)
    pick = rng.choice(idx, n_gmm)
    R_g = ref.R[pick] @ exp_batch(rng.normal(0, SD_R, (n_gmm, 3)))
    p_g = ref.p[pick] + rng.normal(0, SD_P, (n_gmm, 3))
    lo, hi = ref.p.min(0) - UNIFORM, ref.p.max(0) + UNIFORM
    return np.concatenate([R_g, uniform_rotations(rng, n_uni)]), np.concatenate([p_g, rng.uniform(lo, hi, (n_uni, 3))])


def main(seed, n, path):
    rng = np.random.default_rng([40, seed])
    refs = references()
    res = {k: [] for k in ["x", "c", "m", "hole", "D"]}
    for ih, ref in enumerate(refs):
        R, p = sample(rng, ref, n)
        xi, dp, mw, mv, D = targets(ref, R, p)
        res["x"].append(np.concatenate([R.reshape(-1, 9), p], 1).astype(np.float32))
        res["c"].append(np.concatenate([xi, dp], 1).astype(np.float32))
        res["m"].append(np.concatenate([mw, mv], 1).astype(np.float32))
        res["hole"].append(np.full(n, ih, dtype=np.int8))
        res["D"].append(D.astype(np.float32))
    idx = np.linspace(0, len(refs[0].p) - 1, NX).round().astype(int)
    Xd = np.stack([np.concatenate([r.R[idx].reshape(-1, 9), r.p[idx]], 1) for r in refs]).astype(np.float32)
    demo_c = np.zeros(Xd.shape[:2] + (6,), np.float32)
    demo_m = np.stack([np.concatenate([r.w[idx], r.v[idx]], 1) for r in refs]).astype(np.float32)
    np.savez(path, Xd=Xd, demo_c=demo_c, demo_m=demo_m, **{k: np.concatenate(v) for k, v in res.items()})


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
