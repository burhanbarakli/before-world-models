"""EXPLORATORY report on results/explore_bound.npz against the main runs (protocol time: failures count as tf)."""
import numpy as np

B_REPS = 2000


def tt(X, keys, tf_axis_shape):
    ok = X[..., keys.index("ok")]
    t = np.where(ok > 0, X[..., keys.index("t_in")], tf_axis_shape)
    t[np.isnan(ok)] = np.nan
    return t, ok


E = np.load("results/explore_bound.npz")
A = np.load("results/exp_time_A.npz")
Bm = np.load("results/exp_time_B.npz")
k = list(E["keys"])
tfA = np.array([16.0, 12.0])[:, None, None, None, None, None, None]
tD, okD = tt(E["A"], k, tfA)  # (T, delay, gap, e, c, hole, seed)
ka = list(A["keys"])
XA = A["data"][0][:, :, :, 1:]  # model 0, e > 0: (T, delay, gap, e, c, policy, hole, seed, key)
tA, okA = tt(XA, ka, np.array([16.0, 12.0])[:, None, None, None, None, None, None, None])
tK, tM = tA[..., 0, :, :], tA[..., 2, :, :]
rng = np.random.default_rng(0)


def boot(f, nh, ns):
    pt = f(np.arange(nh), np.arange(ns))
    b = np.array([f(rng.choice(nh, nh), rng.choice(ns, ns)) for _ in range(B_REPS)])
    return pt, np.percentile(b, [1.25, 98.75], axis=0)


def sub(x, h, s):
    return x[..., h, :][..., s].mean()


print("EXPLORATORY. A, model 0, e > 0, both c (protocol time):")
print(f"   t: KAHIN {tK.mean():.2f}  DOKUN-KAHIN {tD.mean():.2f}  MOMENT {tM.mean():.2f}   "
      f"S: KAHIN {okA[..., 0, :, :].mean():.3f}  DOKUN {okD.mean():.3f}  MOMENT {okA[..., 2, :, :].mean():.3f}")
for name, f in [("D_A model 0 = MOMENT - KAHIN", lambda h, s: sub(tM, h, s) - sub(tK, h, s)),
                ("unreachable = DOKUN - KAHIN", lambda h, s: sub(tD, h, s) - sub(tK, h, s)),
                ("reachable = MOMENT - DOKUN", lambda h, s: sub(tM, h, s) - sub(tD, h, s))]:
    pt, (lo, hi) = boot(f, 5, tD.shape[-1])
    print(f"   {name:32s} {pt:+.3f}  [{lo:+.3f}, {hi:+.3f}]")
for ic, c in enumerate([5, 2]):
    for ie, e in enumerate([3, 6, 10]):
        a, d, m = tK[:, :, :, ie, ic].mean(), tD[:, :, :, ie, ic].mean(), tM[:, :, :, ie, ic].mean()
        print(f"   c = {c} mm, e = {e:2d} mm: KAHIN {a:.2f}  DOKUN {d:.2f}  MOMENT {m:.2f}   reachable {m - d:+.2f}")
for i, dl in enumerate(["20 ms", "65 ms", "130 ms"]):
    print(f"   h + tau = {dl}: reachable {tM[:, i].mean() - tD[:, i].mean():+.2f}  unreachable {tD[:, i].mean() - tK[:, i].mean():+.2f}")

kb = list(Bm["keys"])
ns = E["B"].shape[6]
tS, okS = tt(E["B"], k, np.array([16.0, 12.0])[:, None, None, None, None, None, None, None])
XB = Bm["data"][..., :ns, :, :]  # same seeds 200..204
tB, okB = tt(XB, kb, np.array([16.0, 12.0])[:, None, None, None, None, None, None, None, None])
tBK, tBH = tB[..., 0, :, :, :], tB[..., 1, :, :, :]
print("\nEXPLORATORY. B, model 0, seeds 200-204 (protocol time):")
print(f"   t: KAHIN {tBK.mean():.2f}  SABIT-KAHIN {tS.mean():.2f}  HAFIZA {tBH.mean():.2f}")
def subb(x, h, s):
    return x[..., h, :, :][..., s, :].mean()
for name, f in [("D_B these seeds = HAFIZA - KAHIN", lambda h, s: subb(tBH, h, s) - subb(tBK, h, s)),
                ("unreachable = SABIT - KAHIN", lambda h, s: subb(tS, h, s) - subb(tBK, h, s)),
                ("reachable = HAFIZA - SABIT", lambda h, s: subb(tBH, h, s) - subb(tS, h, s))]:
    pt, (lo, hi) = boot(f, 5, ns)
    print(f"   {name:32s} {pt:+.3f}  [{lo:+.3f}, {hi:+.3f}]")
print("   by trial: " + "  ".join(f"{q + 1}: K {tBK[..., q].mean():.2f} S {tS[..., q].mean():.2f} H {tBH[..., q].mean():.2f}"
                                  for q in range(tS.shape[-1])))
for ic, c in enumerate([5, 2]):
    print(f"   c = {c} mm: KAHIN {tBK[:, :, :, :, ic].mean():.2f}  SABIT {tS[:, :, :, :, ic].mean():.2f}  "
          f"HAFIZA {tBH[:, :, :, :, ic].mean():.2f}")
# A between-trial learner has no data at trial 1: only trials 2-5 can be taken, weighted as in D_B (mean of 5)
f = lambda h, s: (subb(tBH[..., 1:], h, s) - subb(tS[..., 1:], h, s)) * 4 / 5
pt, (lo, hi) = boot(f, 5, ns)
print(f"   reachable by a between-trial learner (trials 2-5, in D_B units) {pt:+.3f}  [{lo:+.3f}, {hi:+.3f}]")
f = lambda h, s: (subb(tBH[..., :1], h, s) - subb(tS[..., :1], h, s)) / 5
pt, (lo, hi) = boot(f, 5, ns)
print(f"   trial 1 (no data yet, out of reach), in D_B units         {pt:+.3f}  [{lo:+.3f}, {hi:+.3f}]")
