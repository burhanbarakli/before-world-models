"""The T = 15 arm of Sapma 2, then the decision on R over T in {4, 8, 15}.

Run: python gate1_t15.py    (writes results/gate1_T15.npz, results/analysis_T15.txt)
"""
import itertools
import multiprocessing as mp

import numpy as np

import gate1 as G
from robot import DEPTH, RIM_Z

DELAY = [d for d in G.DELAY if d <= 0.1]
LAG = [t for t in G.LAG if t <= 0.05]
ETA = np.array(G.ETA)
C = 0.005


def insert(a, c=C):
    k = {n: a[..., i] for i, n in enumerate(G.KEYS)}
    return ((RIM_Z - k["end_z"]) >= 0.9 * DEPTH) & (k["lat"] <= c) & (k["tilt"] <= np.arctan(2 * c / DEPTH))


def paper(a):
    k = {n: a[..., i] for i, n in enumerate(G.KEYS)}
    return (k["end_p"] <= 0.02) & (k["end_r"] <= 0.2)


def wilson(p, n=100, z=1.96):
    d = 1 + z**2 / n
    m = (p + z**2 / (2 * n)) / d
    r = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return m - r, m + r


def decide(cells, out):
    """cells: dict (T, h, tau) -> SR by eta, for the whole of R."""
    keys = list(cells)
    best = np.array([cells[c].max() for c in keys])
    ideal = np.array([cells[(c[0], 0.0, 0.0)].max() for c in keys])
    d1a = [(i - b >= 0.10) and wilson(b)[1] < wilson(i)[0] for i, b in zip(ideal, best)]
    meanR = np.mean([cells[c] for c in keys], axis=0)
    rob = int(meanR.argmax())
    reg = best - np.array([cells[c][rob] for c in keys])
    rr = []
    for c, b in zip(keys, best):
        e_ideal = ETA[int(cells[(c[0], 0.0, 0.0)].argmax())]
        lim = np.inf if c[1] + c[2] == 0 else 1 / (2 * (c[1] + c[2]))
        rr.append(b - cells[c][int(np.argmin(np.abs(np.log(ETA) - np.log(min(e_ideal, lim)))))])
    i = int(np.argmax(ideal - best))
    out(f"1a: largest drop {(ideal - best).max():.2f} at {keys[i]}; {'PASS' if any(d1a) else 'FAIL'}")
    out(f"mean SR over R by eta: {dict(zip(ETA.tolist(), np.round(meanR, 3).tolist()))}")
    out(f"1b: eta_rob {ETA[rob]}; max regret {reg.max():.3f}; mean regret {reg.mean():.3f}; "
        f"{'PASS' if reg.max() >= 0.10 and reg.mean() >= 0.03 else 'FAIL'}")
    out(f"1c, rule regret mean {np.mean(rr):.3f} max {np.max(rr):.3f}")


if __name__ == "__main__":
    jobs = list(itertools.product([15.0], DELAY, LAG, G.ETA))
    with mp.Pool(9) as pool:
        res = pool.map(G.work, jobs, chunksize=1)
    data = np.array(res).reshape((len(DELAY), len(LAG), len(G.ETA)) + res[0].shape)
    np.savez("results/gate1_T15.npz", data=data, keys=np.array(G.KEYS))

    lines = []
    def out(s=""):
        lines.append(str(s))
        print(s, flush=True)

    p = paper(data).mean((3, 4, 5))
    s = insert(data).mean((3, 4, 5))
    e5, e05 = G.ETA.index(5), G.ETA.index(0.5)
    a, b = wilson(p[0, 0, e5]), wilson(p[0, 0, e05])
    out(f"Validity T=15, paper SR by eta: {dict(zip(G.ETA, np.round(p[0, 0], 3).tolist()))}")
    out(f"eta 5 interval {np.round(a, 3)}, eta .5 interval {np.round(b, 3)}; {'PASS' if a[0] > b[1] else 'FAIL'}")
    out("\nSR_insert c=5 mm, T=15")
    for il, t in enumerate(LAG):
        for ih, h in enumerate(DELAY):
            out(f"  h {int(h * 1000):3d} tau {int(t * 1000):2d}  " + " ".join(f"{v:5.2f}" for v in s[ih, il]))

    old = insert(np.load("results/gate1.npz")["data"]).mean((4, 5, 6))
    cells = {}
    for it, T in enumerate(G.PERIOD):
        for j, h in enumerate(G.DELAY):
            for l, t in enumerate(G.LAG):
                if h <= 0.1 and t <= 0.05:
                    cells[(T, h, t)] = old[it, j, l]
    for j, h in enumerate(DELAY):
        for l, t in enumerate(LAG):
            cells[(15.0, h, t)] = s[j, l]
    out("\nDecision, R over T in {4, 8, 15}, c=5 mm")
    decide(cells, out)
    open("results/analysis_T15.txt", "w").write("\n".join(lines) + "\n")
