"""Exploratory, not pre-registered: which S1 error component makes M2R slow. M2R and DOKUN at S1 with one group of
error terms switched off, model 0, pilot seeds 930-934 (not the main seeds), all delays, e > 0, c, 5 holes.

Run: python explore/components.py   (.pbenv) -> results/explore_components.txt
"""
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import sensor as S  # noqa: E402

import numpy as np  # noqa: E402

import exp_time as X  # noqa: E402

GROUPS = {"full": [], "no bias": ["bf", "bt"], "no noise": ["sf", "st"], "no geometry": ["dl", "phi", "k"],
          "bias only": ["sf", "st", "dl", "phi", "k"]}
SEEDS = [930, 931, 932, 933, 934]


def work(job):
    X.init()
    g, d, err, c, pol, ih, s = job
    base = dict(S.LEVELS["S1"])
    S.LEVELS["S1x"] = {k: (0.0 if k in GROUPS[g] else v) for k, v in base.items()}
    S.FT["S1x"], S.NW["S1x"], S.RMIN["S1x"], S.CAL["S1x"] = S.FT["S1"], S.NW["S1"], S.RMIN["S1"], S.CAL["S1"]
    r = S.episode("S1x", 0, d[0], d[1], err, c, pol, ih, s)
    return job, (r["t_in"] if r["ok"] else S.T + 8.0), r["ok"]


if __name__ == "__main__":
    js = [(g, d, e, c, p, ih, s) for g in GROUPS for d in X.DELAYS for e in (0.003, 0.006, 0.010) for c in X.CLEAR
          for p in (("DOKUN", "M2R") if g == "full" else ("M2R",)) for ih in range(5) for s in SEEDS]
    with mp.Pool(6) as pool:
        res = pool.map(work, js, chunksize=4)
    out = []
    dok = np.mean([t for j, t, _ in res if j[4] == "DOKUN"])
    out.append(f"S1, model 0, pilot seeds 930-934, e > 0 (exploratory). DOKUN t {dok:.2f}")
    for g in GROUPS:
        t = [x for j, x, _ in res if j[0] == g and j[4] == "M2R"]
        ok = [o for j, _, o in res if j[0] == g and j[4] == "M2R"]
        c2 = [x for j, x, _ in res if j[0] == g and j[4] == "M2R" and j[3] == 0.002]
        out.append(f"   M2R {g:12s}: t {np.mean(t):.2f}  S {np.mean(ok):.3f}  D2 {np.mean(t) - dok:+.3f}  (c = 2 only: t {np.mean(c2):.2f})")
    txt = "\n".join(out)
    print(txt)
    with open(os.path.join(HERE, "results", "explore_components.txt"), "w") as f:
        f.write(txt + "\n")
