"""Pilot of PROTOKOL.md: P1 regression (S0 vs panda_rival), P3 trigger threshold, P4 calibration (+ P2 sensor check
from the same runs), P5 tuning of M2R, P6 time.

Run: python pilot_sensor.py     (.pbenv; writes results/pilot_sensor.txt and results/pilot_sensor.npz)
"""
import multiprocessing as mp
import os
import time

import sensor as S  # sets the paths

import numpy as np

import exp_time as X

SEEDS = [930, 931, 932, 933, 934]
OUT = os.path.join(S.HERE, "results", "pilot_sensor.txt")
RIVAL = os.path.join(S.HERE, "..", "panda_rival", "results", "rival.npz")
FTS = [5.0, 10.0, 15.0]
GRID = [(n, r) for n in (5, 10, 20) for r in (0.001, 0.002, 0.004)]


def say(f, s):
    print(s, flush=True)
    f.write(s + "\n")
    f.flush()


def tt(r):
    return r["t_in"] if r["ok"] else S.T + 8.0


def p1(job):
    X.init()
    d, err, c, pol, ih, s = job
    r = S.episode("S0", 0, d[0], d[1], err, c, pol, ih, s)
    return job, tt(r)


def p3(job):
    X.init()
    lv, ft, d, c, ih, s = job
    r = S.episode(lv, 0, d[0], d[1], 0.0, c, "DOKUN", ih, s, ft=ft)
    return job, r["t_contact"] >= 0


def p4(job):
    X.init()
    lv, ft, c, err, ih, s = job
    r = S.episode(lv, None, 0.02, 0.0, err, c, "M2R", ih, s, ft=ft, cal=None, n_w=5, r_min=0.002)
    return job, (r["r_first"], r["r_true"], r["dir_err"])


def p5(job):
    X.init()
    lv, ft, cal, n_w, r_min, d, err, c, ih, s = job
    r = S.episode(lv, 0, d[0], d[1], err, c, "M2R", ih, s, ft=ft, cal=cal, n_w=n_w, r_min=r_min)
    return job, tt(r), r["ok"]


def main():
    store = {}
    with open(OUT, "w") as f, mp.Pool(9) as pool:
        # P1: S0 against panda_rival's stored runs (seeds 300-301, model 0, T = 8, no push)
        R = np.load(RIVAL)
        K = list(R["keys"])
        ok = R["data"][..., K.index("ok")]
        tr = np.where(ok > 0, R["data"][..., K.index("t_in")], 16.0)
        iT, ig = list(R["period"]).index(8.0), list(R["gaps"]).index(-1.0)
        js = [(d, e, c, p, ih, s) for d in X.DELAYS for e in (0.003, 0.006, 0.010) for c in X.CLEAR
              for p in ("DOKUN", "M2") for ih in range(5) for s in (300, 301)]
        res = dict(pool.map(p1, js))
        worst, diffs = 0.0, []
        for di, d in enumerate(X.DELAYS):
            for ie, e in enumerate((0.003, 0.006, 0.010)):
                for ic, c in enumerate(X.CLEAR):
                    for ip, p in enumerate(("DOKUN", "M2")):
                        new = np.mean([res[(d, e, c, p, ih, s)] for ih in range(5) for s in (300, 301)])
                        old = np.mean(tr[0, iT, di, ig, ie + 1, ic, ip, :, :2])
                        diffs.append(new - old)
                        worst = max(worst, abs(new - old))
        say(f, f"P1 regression S0 vs panda_rival, 36 cells of 10 runs: mean diff {np.mean(diffs):+.3f} s, "
               f"worst |cell diff| {worst:.3f} s -> {'pass' if worst < 0.1 else 'FAIL (examine)'}")

        # P3: trigger threshold, false triggers at e = 0 (DOKUN, model 0); reference S0 at F_t = 5 N
        js = [(lv, ft, d, c, ih, s) for lv in ("S0", "S1", "S2", "S3") for ft in (FTS if lv != "S0" else [5.0])
              for d in X.DELAYS for c in X.CLEAR for ih in range(5) for s in SEEDS]
        res = pool.map(p3, js)
        rate = {}
        for (lv, ft, *_), hit in res:
            rate.setdefault((lv, ft), []).append(hit)
        rate = {k: float(np.mean(v)) for k, v in rate.items()}
        ref = rate[("S0", 5.0)]
        say(f, f"P3 false trigger rate at e = 0, S0 (F_t 5 N): {ref:.3f}; limit S0 + 0.02 = {ref + 0.02:.3f} (Sapma 1)")
        FT = {}
        for lv in ("S1", "S2", "S3"):
            ok_ft = [ft for ft in FTS if rate[(lv, ft)] <= ref + 0.02]
            FT[lv] = ok_ft[0] if ok_ft else 15.0
            say(f, f"   {lv}: " + "  ".join(f"F_t {ft:.0f}: {rate[(lv, ft)]:.3f}" for ft in FTS) +
                f" -> F_t {FT[lv]:.0f} N" + ("" if ok_ft else " (none within the limit, 15 N)"))

        # P4: calibration per level and c (panda_rival P1's procedure and budget); P2 from the same runs
        js = [(lv, FT[lv], c, err, ih, s) for lv in ("S1", "S2", "S3") for c in X.CLEAR
              for err in (0.004, 0.006, 0.008, 0.010) for ih in range(5) for s in SEEDS]
        res = pool.map(p4, js)
        CAL = {lv: {} for lv in ("S1", "S2", "S3")}
        for lv in ("S1", "S2", "S3"):
            for c in X.CLEAR:
                pts = np.array([(v[0], v[1], v[2], j[3]) for j, v in res if j[0] == lv and j[2] == c and v[0] >= 0])
                n_all = len([1 for j, v in res if j[0] == lv and j[2] == c])
                if len(pts) < 3:
                    CAL[lv][c] = None
                    say(f, f"P4 {lv} c = {c * 1000:.0f} mm: {len(pts)} of {n_all} with a measurement -> fixed step c")
                    continue
                A = np.c_[np.ones(len(pts)), pts[:, 0]]
                coef, *_ = np.linalg.lstsq(A, pts[:, 3], rcond=None)
                pred = A @ coef
                ss = np.sum((pts[:, 3] - pts[:, 3].mean()) ** 2)
                r2 = 1 - np.sum((pts[:, 3] - pred) ** 2) / ss if ss > 0 else 0.0
                use = r2 >= 0.5 and coef[1] != 0
                CAL[lv][c] = (float(coef[0]), float(coef[1])) if use else None
                say(f, f"P4 {lv} c = {c * 1000:.0f} mm: {len(pts)} of {n_all} with a measurement: d = {coef[0] * 1000:.2f} mm "
                       f"+ {coef[1]:.3f} |r|, R2 {r2:.2f}, median error {np.median(np.abs(pts[:, 3] - pred)) * 1000:.2f} mm "
                       f"-> {'calibration' if use else 'fixed step c'}")
                has = pts[:, 1] >= 0
                dr = np.abs(pts[has, 0] - pts[has, 1]) * 1000
                de = pts[has & (pts[:, 2] >= 0), 2]
                say(f, f"   P2 first measurement: | |r-hat| - |r| | median {np.median(dr):.2f} / 90% {np.percentile(dr, 90):.2f} mm;"
                       f" direction error median {np.median(de):.1f} / 90% {np.percentile(de, 90):.1f} deg")
                store[f"p4_{lv}_{c}"] = pts

        # P5: tuning of M2R, n_w x R_MIN per level
        t0, n0, NW, RMIN = time.time(), 0, {}, {}
        for lv in ("S1", "S2", "S3"):
            scores = []
            for n_w, r_min in GRID:
                js = [(lv, FT[lv], CAL[lv][c], n_w, r_min, d, err, c, ih, s) for d in X.DELAYS
                      for err in (0.003, 0.006, 0.010) for c in X.CLEAR for ih in range(5) for s in SEEDS]
                out = pool.map(p5, js)
                n0 += len(out)
                t, sr = float(np.mean([x[1] for x in out])), float(np.mean([x[2] for x in out]))
                scores.append(((n_w, r_min), t, sr))
                say(f, f"   {lv} n_w {n_w:2d}, R_MIN {r_min * 1000:.0f} mm: t {t:.4f}  SR {sr:.3f}")
            best = min(x[1] for x in scores)
            (n_w, r_min), _, _ = min([x for x in scores if x[1] <= best + 0.01], key=lambda x: (x[0][0], x[0][1]))
            NW[lv], RMIN[lv] = n_w, r_min
            store[f"p5_{lv}"] = np.array([(a, b, t, sr) for (a, b), t, sr in scores])
            say(f, f"P5 {lv} chosen: n_w {n_w}, R_MIN {r_min * 1000:.0f} mm")
        spr = (time.time() - t0) * 9 / n0
        total = len(S.jobs()) * 100 * spr / 9 / 3600
        say(f, f"P6 time: {spr:.2f} s per run, about {total:.1f} h on 9 processes -> "
               f"{'pass' if total <= 12 else 'M2T / M2O to 10 seeds'}")
        say(f, f"chosen: FT {FT}, CAL {CAL}, NW {NW}, RMIN {RMIN}")
    np.savez(os.path.join(S.HERE, "results", "pilot_sensor.npz"), **store)


if __name__ == "__main__":
    main()
