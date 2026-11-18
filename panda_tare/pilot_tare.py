"""Pilot of PROTOKOL.md: P0 smoke test (tare offset vs the true sensor offset), P1 calibration of TARE.
Seeds 930-931 only.

Run: python pilot_tare.py    (.pbenv; writes results/pilot_tare.txt)
"""
import multiprocessing as mp
import os

import tare as TA  # sets the paths

import numpy as np

import exp_time as X

SEEDS = [930, 931]
OUT = os.path.join(TA.HERE, "results", "pilot_tare.txt")


def say(f, s):
    print(s, flush=True)
    f.write(s + "\n")
    f.flush()


def p0(job):
    X.init()
    lv, ih, s = job
    r = TA.episode(lv, 0, 0.02, 0.0, 0.006, 0.005, "TARE", ih, s, cal=None)
    return job, (r["tare_err_f"], r["tare_err_m"], r["n_tare"], r["ok"], r["t_in"])


def p1(job):
    X.init()
    lv, c, err, ih, s = job
    r = TA.episode(lv, None, 0.02, 0.0, err, c, "TARE", ih, s, cal=None)
    return job, (r["r_first"], r["r_true"], r["dir_err"])


def main():
    with open(OUT, "w") as f, mp.Pool(9) as pool:
        res = pool.map(p0, [(lv, ih, s) for lv in TA.LV for ih in range(5) for s in SEEDS])
        for lv in TA.LV:
            v = np.array([x for j, x in res if j[0] == lv])
            P = TA.S.LEVELS[lv]
            say(f, f"P0 {lv}: tare error |F| median {np.median(v[:, 0]):.4f} N (bias sd {P['bf']}, noise/sqrt(30) "
                   f"{P['sf'] * np.sqrt(3 / 30):.4f}), |tau_tip| median {np.median(v[:, 1]):.4f} Nm; ticks averaged "
                   f"{v[:, 2].min():.0f}-{v[:, 2].max():.0f}; ok {v[:, 3].mean():.2f}")
        js = [(lv, c, err, ih, s) for lv in TA.LV for c in X.CLEAR for err in (0.004, 0.006, 0.008, 0.010)
              for ih in range(5) for s in SEEDS]
        res = pool.map(p1, js)
        for lv in TA.LV:
            for c in X.CLEAR:
                pts = np.array([(v[0], v[1], v[2], j[2]) for j, v in res if j[0] == lv and j[1] == c and v[0] >= 0])
                n_all = len([1 for j, v in res if j[0] == lv and j[1] == c])
                if len(pts) < 3:
                    say(f, f"P1 {lv} c = {c * 1000:.0f} mm: {len(pts)} of {n_all} measured -> fixed step c")
                    continue
                A = np.c_[np.ones(len(pts)), pts[:, 0]]
                coef, *_ = np.linalg.lstsq(A, pts[:, 3], rcond=None)
                pred = A @ coef
                ss = np.sum((pts[:, 3] - pts[:, 3].mean()) ** 2)
                r2 = 1 - np.sum((pts[:, 3] - pred) ** 2) / ss if ss > 0 else 0.0
                use = r2 >= 0.5 and coef[1] != 0
                say(f, f"P1 {lv} c = {c * 1000:.0f} mm: {len(pts)} of {n_all} measured: d = {coef[0] * 1000:.2f} mm "
                       f"{coef[1]:+.3f} |r|, R2 {r2:.2f}, median error {np.median(np.abs(pts[:, 3] - pred)) * 1000:.2f} mm"
                       f" -> {'calibration ' + repr((float(coef[0]), float(coef[1]))) if use else 'fixed step c'}")
                has = pts[:, 1] >= 0
                dr = np.abs(pts[has, 0] - pts[has, 1]) * 1000
                de = pts[has & (pts[:, 2] >= 0), 2]
                say(f, f"   first measurement: | |r-hat| - |r| | median {np.median(dr):.2f} mm; direction error median "
                       f"{np.median(de):.1f} / 90% {np.percentile(de, 90):.1f} deg")


if __name__ == "__main__":
    main()
