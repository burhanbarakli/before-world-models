"""Applies the rules of PROTOKOL_GEC.md to results/gate1g.npz. Run: python analyze_g.py [file]"""
import itertools
import sys

import numpy as np

import gate1 as G
from gate1g import DELAY, ETA, GAP, LAG, PERIOD
from robot import DEPTH, RIM_Z

ETA_A = np.array(ETA, float)
TRAIN, TEST = np.arange(10), np.arange(10, 20)


def insert(a, c):
    k = {n: a[..., i] for i, n in enumerate(G.KEYS)}
    return ((RIM_Z - k["end_z"]) >= 0.9 * DEPTH) & (k["lat"] <= c) & (k["tilt"] <= np.arctan(2 * c / DEPTH))


def wilson(p, n=100, z=1.96):
    d = 1 + z**2 / n
    m = (p + z**2 / (2 * n)) / d
    r = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return m - r, m + r


def nearest(e):
    return int(np.argmin(np.abs(np.log(ETA_A) - np.log(e))))


def rule_table(sr, k):
    """Eta index for each (T, h, tau). sr has axes T, h, tau, gap, eta."""
    out = np.zeros(sr.shape[:3], int)
    for i, j, l in np.ndindex(*out.shape):
        e_ideal = ETA_A[int(sr[i, 0, 0].mean(0).argmax())]
        s = DELAY[j] + LAG[l]
        out[i, j, l] = nearest(min(e_ideal, np.inf if s == 0 else k / s))
    return out


def score(ok, table):
    """Per run success of a policy; table gives the eta index for (T, h, tau). Shape: T, h, tau, gap, hole, seed."""
    pick = table[:, :, :, None, None, None, None]
    return np.take_along_axis(ok, np.broadcast_to(pick, ok.shape[:4] + (1,) + ok.shape[5:]), axis=4).squeeze(4)


def rules(ok, label):
    sr = ok.mean((5, 6))
    print(f"\n=== {label} ===")
    drops = []
    for i, j, l, g in itertools.product(*map(range, sr.shape[:4])):
        best, ideal = sr[i, j, l, g].max(), sr[i, 0, 0, g].max()
        drops.append((ideal - best, ideal - best >= 0.10 and wilson(best)[1] < wilson(ideal)[0],
                      PERIOD[i], DELAY[j], LAG[l], GAP[g], best, ideal))
    d = max(drops, key=lambda x: x[0])
    pass_a = any(x[1] for x in drops)
    print(f"2a: largest drop {d[0]:.2f} at T={d[2]} h={d[3]} tau={d[4]} gap={d[5]} (best {d[6]:.2f}, ideal {d[7]:.2f});",
          "PASS" if pass_a else "FAIL")
    mean = sr.mean((0, 1, 2, 3))
    rob = int(mean.argmax())
    reg = sr.max(4) - sr[..., rob]
    pass_b = reg.max() >= 0.10 and reg.mean() >= 0.03
    print("mean SR by eta:", dict(zip(ETA, np.round(mean, 3).tolist())))
    print(f"2b: eta_rob {ETA[rob]}; max regret {reg.max():.3f}; mean regret {reg.mean():.3f};", "PASS" if pass_b else "FAIL")

    tr = ok[..., TRAIN].mean((5, 6))
    te = ok[..., TEST]
    fixed = np.full(sr.shape[:3], int(tr.mean((0, 1, 2, 3)).argmax()))
    rule = {k: rule_table(tr, k) for k in (0.5, 1.0)}
    best_k = max(rule, key=lambda k: score(ok[..., TRAIN], rule[k]).mean())
    table = tr.mean(3).argmax(3)
    oracle = te.mean((5,)).mean(5).max(4)
    policies = {"SABIT": fixed, "KURAL": rule[best_k], "TABLO": table}
    S = {n: score(te, t) for n, t in policies.items()}
    oracle_mean = oracle.mean()
    print(f"selection half: eta_rob {ETA[fixed[0, 0, 0]]}, k {best_k}")
    print(f"test half: " + "  ".join(f"S({n}) {v.mean():.3f}" for n, v in S.items()) + f"  S(KAHIN) {oracle_mean:.3f}")
    print("KURAL eta, T=8:", ETA_A[rule[best_k][0]].tolist())
    print("KURAL eta, T=4:", ETA_A[rule[best_k][1]].tolist())
    print("TABLO eta, T=8:", ETA_A[table[0]].tolist())
    print("TABLO eta, T=4:", ETA_A[table[1]].tolist())
    M = S["TABLO"].mean() - S["KURAL"].mean()
    diff = (S["TABLO"].astype(float) - S["KURAL"].astype(float)).mean((0, 1, 2, 3))  # hole, seed
    rng = np.random.default_rng(0)
    H, N = diff.shape
    boot = [diff[rng.integers(H, size=H)][:, rng.integers(N, size=N)].mean() for _ in range(2000)]
    print(f"M {M:.3f}, bootstrap 95% [{np.quantile(boot, .025):.3f}, {np.quantile(boot, .975):.3f}]")
    r_fixed, r_rule = oracle_mean - S["SABIT"].mean(), oracle_mean - S["KURAL"].mean()
    halves = r_rule <= r_fixed / 2
    print(f"regret against oracle: SABIT {r_fixed:.3f}, KURAL {r_rule:.3f}; rule halves it: {halves}")
    if not pass_b:
        out = "2b failed: one eta suffices, no model on this benchmark"
    elif M >= 0.03:
        out = "2b passed, M >= .03: room above the rule, Gate 1 passed"
    elif halves:
        out = "2b passed, rule suffices: no model needed"
    else:
        out = "2b passed, M < .03, rule does not halve regret: no model needed"
    print("Outcome:", out)


def tables(sr):
    for it, T in enumerate(PERIOD):
        for ig, g in enumerate(GAP):
            print(f"\nSR_insert c=5mm, T={T}, gap={g}")
            print("  h   tau  " + " ".join(f"{e:5g}" for e in ETA) + "  best")
            for (ih, h), (il, t) in itertools.product(enumerate(DELAY), enumerate(LAG)):
                row = sr[it, ih, il, ig]
                print(f" {int(h * 1000):3d}  {int(t * 1000):3d}  " + " ".join(f"{v:5.2f}" for v in row) + f"  {row.max():.2f}")


if __name__ == "__main__":
    D = np.load(sys.argv[1] if len(sys.argv) > 1 else "results/gate1g.npz")["data"]
    ok5 = insert(D, 0.005)
    sr = ok5.mean((5, 6))
    gain = sr[:, 0, 0].max(2) - sr[:, 0, 0, :, ETA.index(2)]
    print(f"Validity: largest SR(best) - SR(eta 2) at h=0 tau=0 is {gain.max():.2f};", "PASS" if gain.max() >= 0.30 else "FAIL")
    tables(sr)
    for c in [0.002, 0.005, 0.010]:
        rules(insert(D, c), f"c={c * 1000:g} mm" + (" (primary)" if c == 0.005 else " (secondary)"))
