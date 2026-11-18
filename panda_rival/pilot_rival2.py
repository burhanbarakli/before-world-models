"""Second pilot (PROTOKOL.md Sapma 1): P1 again with the sign clause dropped (calibration used when R2 >= 0.5 and
b != 0), then P3 tuning of the calibrated MOMENT-2. Same seeds and grid as pilot_rival.py.

Run: python pilot_rival2.py     (.pbenv; writes results/pilot_rival2.txt)
"""
import multiprocessing as mp
import os
import time

import rival as Rv  # sets the paths

import numpy as np

import exp_time as X
import pilot_rival as P

OUT = os.path.join(Rv.HERE, "results", "pilot_rival2.txt")


def main():
    with open(OUT, "w") as f, mp.Pool(9) as pool:
        res = pool.map(P.p1, [(c, err, ih, s) for c in X.CLEAR for err in (0.004, 0.006, 0.008, 0.010)
                              for ih in range(5) for s in P.SEEDS])
        cal = {}
        for c in X.CLEAR:
            pts = np.array([(r, err) for cc, err, r in res if cc == c and r >= 0])
            A = np.c_[np.ones(len(pts)), pts[:, 0]]
            coef, *_ = np.linalg.lstsq(A, pts[:, 1], rcond=None)
            pred = A @ coef
            r2 = 1 - np.sum((pts[:, 1] - pred) ** 2) / np.sum((pts[:, 1] - pts[:, 1].mean()) ** 2)
            use = r2 >= 0.5 and coef[1] != 0
            cal[c] = (float(coef[0]), float(coef[1])) if use else None
            P.say(f, f"P1 c = {c * 1000:.0f} mm, {len(pts)} with a measurement: d = {coef[0] * 1000:.3f} mm + "
                     f"{coef[1]:.4f} |r|, R2 {r2:.3f}, median error {np.median(np.abs(pts[:, 1] - pred)) * 1000:.2f} mm"
                     f" -> {'calibration' if use else 'fixed step c'}")
        t0, n0, chosen_v, chosen_n = time.time(), 0, [], []
        for d_ in X.DELAYS:
            scores = []
            for v_s, n_w in P.GRID:
                js = [(arm, d_, err, c, gap, ih, s, v_s, n_w, cal[c]) for arm in (None, 0)
                      for err in (0.003, 0.006, 0.010) for c in X.CLEAR for gap in X.GAPS for ih in range(5)
                      for s in P.SEEDS]
                out = pool.map(P.p3, js)
                n0 += len(out)
                t, sr = float(np.mean([x[0] for x in out])), float(np.mean([x[1] for x in out]))
                scores.append(((v_s, n_w), t, sr))
                P.say(f, f"   h + tau {sum(d_) * 1000:.0f} ms, v_s {v_s * 1000:.0f} mm/s, n_w {n_w:2d}: t {t:.2f}  SR {sr:.3f}")
            best = min(x[1] for x in scores)
            (v_s, n_w), _, _ = min([x for x in scores if x[1] <= best + 0.01], key=lambda x: (x[0][0], x[0][1]))
            chosen_v.append(v_s)
            chosen_n.append(n_w)
            P.say(f, f"P3 h + tau {sum(d_) * 1000:.0f} ms chosen: v_s {v_s * 1000:.0f} mm/s, n_w {n_w}")
        P.say(f, f"P4 time: {(time.time() - t0) * 9 / n0:.2f} s per run at T = 8")
        P.say(f, f"chosen: V_S {chosen_v}, N_W {chosen_n}, CAL {cal}")


if __name__ == "__main__":
    main()
