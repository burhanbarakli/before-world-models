"""Field error of a trained model on fresh samples. Touches no success measure.

Run: python field_error.py model.npz    (pbenv)
"""
import sys

import numpy as np

import make_data as M
from learned import Net, metric

SCALE = 0.2


def ball(rng, ref, n):
    """States a disturbance of metric size up to SCALE can reach from the reference."""
    i = rng.integers(len(ref.p), size=n)
    z = rng.normal(size=(n, 6))
    z /= metric(z)[:, None]
    z *= SCALE * rng.uniform(size=(n, 1))
    R = ref.R[i] @ M.exp_batch(z[:, :3])
    p = ref.p[i] + (ref.R[i] @ z[:, 3:, None])[..., 0]
    return R, p


def errors(d, hole, R, p, ref):
    xi, dp, mw, mv, D = M.targets(ref, R, p)
    Rf, pf = R.astype(np.float32), p.astype(np.float32)
    c_net, m_net = Net(d, "c", hole), Net(d, "m", hole)
    ce = np.concatenate(c_net(Rf, pf), 1) - np.concatenate([xi, dp], 1)
    me = np.concatenate(m_net(Rf, pf), 1) - np.concatenate([mw, mv], 1)
    return ce, me, D


def main(path, n=20000):
    d = np.load(path)
    rng = np.random.default_rng([41, 0])
    refs = M.references()
    vmax = max(np.sqrt(2 * (r.w**2).sum(1) + 100 * (r.v**2).sum(1)).max() for r in refs)
    print(f"model {path}\nspeed max at T=8: {vmax:.3f}")
    def row(name, ce, me):
        c, m = metric(ce), metric(me)
        print(f"{name:22s} c rms {np.sqrt((c**2).mean()):.4f} p95 {np.quantile(c, .95):.4f}   "
              f"m rms {np.sqrt((m**2).mean()):.4f} p95 {np.quantile(m, .95):.4f}   "
              f"m/speed {np.sqrt((m**2).mean()) / vmax:.4f}  mse c {(c**2).mean():.2e} m {(m**2).mean():.2e}")
    for name, draw in [("paper sampling", lambda r: M.sample(rng, r, n)), ("disturbance ball", lambda r: ball(rng, r, n))]:
        C, Me = [], []
        for ih, ref in enumerate(refs):
            R, p = draw(ref)
            ce, me, _ = errors(d, ih, R, p, ref)
            C.append(ce); Me.append(me)
            row(f"  {name} hole {ih}", ce, me)
        row(name, np.concatenate(C), np.concatenate(Me))
    # On the reference: the CVF should vanish, what remains is the offset the tube bound speaks of.
    print("on the reference, per hole: |c_v| mm rms / max; below the 0.12 m via point")
    for ih, ref in enumerate(refs):
        i = np.linspace(0, len(ref.p) - 1, 501).round().astype(int)
        ce, me, _ = errors(d, ih, ref.R[i], ref.p[i], ref)
        low = ref.p[i, 2] < 0.37
        print(f"  hole {ih}: all {1000 * np.sqrt((ce[:, 3:]**2).sum(1).mean()):.2f} / {1000 * np.linalg.norm(ce[:, 3:], axis=1).max():.2f}"
              f"   low {1000 * np.sqrt((ce[low, 3:]**2).sum(1).mean()):.2f} / {1000 * np.linalg.norm(ce[low, 3:], axis=1).max():.2f}"
              f"   m_v err low, mm/s {1000 * np.sqrt((me[low, 3:]**2).sum(1).mean()):.2f}")


if __name__ == "__main__":
    main(sys.argv[1])
