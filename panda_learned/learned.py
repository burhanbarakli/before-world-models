"""The trained field in NumPy, with the interface of field_se3.Reference, and its error measures."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "panda_gate1"))
import field_se3 as F

P0, PS = np.array([0.4, 0.0, 0.3], np.float32), 0.2
T0 = 8.0


class Net:
    def __init__(self, d, key, hole):
        self.layers = []
        j = 0
        while f"W_{key}{j}" in d:
            self.layers.append((d[f"W_{key}{j}"], d[f"b_{key}{j}"]))
            j += 1
        self.B = d[f"B_{key}"][hole]

    def __call__(self, R, p):
        """R: (n, 3, 3), p: (n, 3), float32. Returns w, v."""
        h = np.concatenate([R.reshape(-1, 9), (p - P0) / PS], 1)
        for W, b in self.layers[:-1]:
            h = np.maximum(h @ W.T + b, 0)
        W, b = self.layers[-1]
        t = (h @ W.T + b).reshape(-1, *self.B.shape)
        y = (t * self.B).sum(1)
        S = np.transpose(R, (0, 2, 1)) @ y[:, :9].reshape(-1, 3, 3)
        S = (S - np.transpose(S, (0, 2, 1))) / 2
        return np.stack([S[:, 2, 1], S[:, 0, 2], S[:, 1, 0]], 1), y[:, 9:]


class LearnedRef:
    """Reference for run(): the bookkeeping of ref, with the field replaced by the networks.

    The speed profile is a function of t / T, so the MVF scales exactly with 1 / T.
    """

    def __init__(self, ref, path_or_data, hole_i, T):
        d = np.load(path_or_data) if isinstance(path_or_data, str) else path_or_data
        self.ref = ref
        self.c_net, self.m_net = Net(d, "c", hole_i), Net(d, "m", hole_i)
        self.scale = T0 / T
        self.dt, self.vmax = ref.dt, ref.vmax
        self.p, self.R, self.goal_R, self.goal_p = ref.p, ref.R, ref.goal_R, ref.goal_p

    def field(self, R, p):
        Rf, pf = R[None].astype(np.float32), p[None].astype(np.float32)
        cw, cv = self.c_net(Rf, pf)
        mw, mv = self.m_net(Rf, pf)
        return (cw[0].astype(float), cv[0].astype(float)), \
               (self.scale * mw[0].astype(float), self.scale * mv[0].astype(float)), None, None


def metric(e):
    return np.sqrt(F.W_R * (e[:, :3] ** 2).sum(1) + F.W_P * (e[:, 3:] ** 2).sum(1))
