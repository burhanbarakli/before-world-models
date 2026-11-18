"""Applies the decision rules of PROTOKOL.md to results/schedule.npz. Run: python analyze.py"""
import numpy as np
from scipy.stats import wilcoxon

from schedule import FIXED, PAIR, POLICIES, RHO

R = np.load("results/schedule.npz")
SH = R["shapes"]
NF, NA, NP = len(FIXED), len(RHO), len(PAIR)
IF = np.arange(NF)
IA = np.arange(NF, NF + NA)
IP = np.arange(NF + NA, NF + NA + NP)


def tuned(score_tune, idx):
    """Best policy index per shape, within idx, by the tuning score."""
    return idx[score_tune[:, idx].argmin(1)]


def holm(p):
    order = np.argsort(p)
    adj, run = np.zeros(len(p)), 0.0
    for r, i in enumerate(order):
        run = max(run, (len(p) - r) * p[i])
        adj[i] = min(run, 1.0)
    return adj


def analyse(split, metric="dtw"):
    M = R[f"{split}_{metric}"]  # shape, policy, demo (3 tuning, then 3 test)
    tune, test = M[:, :, :3].mean(2), M[:, :, 3:].mean(2)
    n = len(SH)
    rows = np.arange(n)
    res = {}
    sel = {"F_letter": tuned(tune, IF), "A": tuned(tune, IA), "P": tuned(tune, IP)}
    glob = IF[tune[:, IF].mean(0).argmin()]
    scores = {k: test[rows, v] for k, v in sel.items()}
    scores["F_global"] = test[:, glob]
    scores["F_oracle"] = test[:, IF].min(1)
    res["scores"] = scores
    res["sel"] = sel
    res["global_eta"] = POLICIES[glob][1]
    g = test[:, IF]
    res["headroom"] = float(np.median((g.max(1) - g.min(1)) / g.min(1)))
    base = scores["F_letter"]
    res["gain"] = {k: float(np.median((base - scores[k]) / base)) for k in ["A", "P", "F_oracle", "F_global"]}
    res["wins"] = {k: int(np.sum(scores[k] < base)) for k in ["A", "P"]}
    p = [wilcoxon(base, scores[k], alternative="greater").pvalue for k in ["A", "P"]]
    res["p_holm"] = dict(zip(["A", "P"], holm(np.array(p))))
    res["etas"] = [float(POLICIES[i][1]) for i in sel["F_letter"]]
    return res


def boot(gain_fn, n=5000, seed=0):
    rng = np.random.default_rng(seed)
    v = gain_fn()
    idx = rng.integers(0, len(v), (n, len(v)))
    m = np.median(v[idx], axis=1)
    return float(np.median(v)), float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))


def report():
    print("Median over 26 shapes. Unit: rad unless stated.\n")
    for split in ["main", "rot"]:
        for metric in ["dtw", "fre"]:
            r = analyse(split, metric)
            print(f"[{split} / {metric}] headroom {r['headroom']:.3f}  global eta {r['global_eta']}")
            for k, v in r["scores"].items():
                print(f"   {k:9s} median {np.median(v):.4f}  mean {v.mean():.4f}")
            print(f"   gain vs F_letter: {({k: round(v, 4) for k, v in r['gain'].items()})}")
            print(f"   shapes better: {r['wins']} of 26   Holm p: {({k: round(v, 5) for k, v in r['p_holm'].items()})}")
            for k in ["A", "P"]:
                base, s = r["scores"]["F_letter"], r["scores"][k]
                med, lo, hi = boot(lambda: (base - s) / base)
                print(f"   {k}: gain {med:.3f}, 95% bootstrap CI of the median [{lo:.3f}, {hi:.3f}]")
            print("   tuned fixed eta histogram:", {e: r["etas"].count(e) for e in FIXED if e in r["etas"]})
            print()

    print("Noise floor: DTW of the reference demo itself to the held-out test demos")
    for split in ["main", "rot"]:
        print(f"   {split}: median {np.median(R[f'{split}_floor'][:, 3:].mean(1)):.4f}")
    print("\nArrival within 4T, share of runs, test demos")
    for split in ["main", "rot"]:
        a = R[f"{split}_arrive"][:, :, 3:].mean((0, 2))
        print(f"   {split} fixed:", dict(zip(FIXED, np.round(a[IF], 2))))

    # Secondary: E and Q under the 0.3 rad offset start (last column), not a decision input.
    print("\nSecondary, 0.3 rad offset start, best in family per shape (in-sample, descriptive)")
    for key in ["E", "Q"]:
        for split in ["main", "rot"]:
            M = R[f"{split}_{key}"][:, :, -1]
            f, a, p = M[:, IF].min(1), M[:, IA].min(1), M[:, IP].min(1)
            print(f"   {key} {split}: fixed {np.median(f):.4f}  A {np.median(a):.4f}  P {np.median(p):.4f}"
                  f"   gain A {np.median((f - a) / f):.3f}  P {np.median((f - p) / f):.3f}")
    print("\nSame, on held-out test-demo starts")
    for key in ["E", "Q"]:
        M = R[f"main_{key}"][:, :, 3:6].mean(2)
        f, a, p = M[:, IF].min(1), M[:, IA].min(1), M[:, IP].min(1)
        print(f"   {key}: fixed {np.median(f):.4f}  A {np.median(a):.4f}  P {np.median(p):.4f}"
              f"   gain A {np.median((f - a) / f):.3f}  P {np.median((f - p) / f):.3f}")

    print("\nPer shape, main split, DTW test")
    r = analyse("main")
    s = r["scores"]
    for i, n in enumerate(SH):
        print(f"   {n:18s} F {s['F_letter'][i]:.4f} (eta {r['etas'][i]:>5})  A {s['A'][i]:.4f}  P {s['P'][i]:.4f}")


if __name__ == "__main__":
    report()
