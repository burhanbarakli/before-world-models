"""Exploratory reading of results/gate1.npz; does not enter the decision. Run: python inspect_gate.py"""
import numpy as np

from gate1 import DELAY, ETA, KEYS, LAG, PERIOD
from robot import DEPTH, HOLES, RIM_Z

D = np.load("results/gate1.npz")["data"]  # T, h, tau, eta, hole, kind, seed, key
k = {n: D[..., i] for i, n in enumerate(KEYS)}
C = 0.005
deep = (RIM_Z - k["end_z"]) >= 0.9 * DEPTH
lat_ok = k["lat"] <= C
tilt_ok = k["tilt"] <= np.arctan(2 * C / DEPTH)
ok = deep & lat_ok & tilt_ok
sr = ok.mean((4, 5, 6))


def idx(lst, v):
    return int(np.argmin(np.abs(np.array(lst) - v)))


print("Success by hole, all cells of the realistic set R, eta >= 2")
R = [(i, j, l) for i in range(2) for j, h in enumerate(DELAY) for l, t in enumerate(LAG) if h <= 0.1 and t <= 0.05]
for ih, hole in enumerate(HOLES):
    print(hole, np.round(np.mean([ok[i, j, l, 2:, ih].mean() for i, j, l in R]), 3))

print("\nMargin at eta=5 over R: worst lateral [mm], worst tilt [deg], limit tilt [deg]")
e5 = ETA.index(5)
lat = np.max([k["lat"][i, j, l, e5] for i, j, l in R])
tilt = np.max([k["tilt"][i, j, l, e5] for i, j, l in R])
print(round(lat * 1000, 2), round(np.degrees(tilt), 2), round(np.degrees(np.arctan(2 * C / DEPTH)), 2))

print("\nWhich criterion fails (fraction failing depth, lateral, tilt)")
for T, h, t in [(4.0, 0.2, 0.0), (4.0, 0.05, 0.15), (8.0, 0.3, 0.05)]:
    i, j, l = idx(PERIOD, T), idx(DELAY, h), idx(LAG, t)
    for e in [1, 2, 3, 5, 8]:
        m = ETA.index(e)
        print(f"T={T} h={h} tau={t} eta={e}: SR {sr[i, j, l, m]:.2f}  "
              f"depth {1 - deep[i, j, l, m].mean():.2f}  lat {1 - lat_ok[i, j, l, m].mean():.2f}  "
              f"tilt {1 - tilt_ok[i, j, l, m].mean():.2f}  med lat {1000 * np.median(k['lat'][i, j, l, m]):.1f} mm  "
              f"med end_p {1000 * np.median(k['end_p'][i, j, l, m]):.1f} mm")


def rules(hmax, tmax, label):
    S = [(i, j, l) for i in range(2) for j, h in enumerate(DELAY) for l, t in enumerate(LAG) if h <= hmax and t <= tmax]
    best = np.array([sr[c].max() for c in S])
    ideal = np.array([sr[c[0], 0, 0].max() for c in S])
    mean = np.mean([sr[c] for c in S], axis=0)
    rob = int(mean.argmax())
    reg = best - np.array([sr[c][rob] for c in S])
    rr = []
    for c, b in zip(S, best):
        i, j, l = c
        e_ideal = ETA[int(sr[i, 0, 0].argmax())]
        lim = np.inf if DELAY[j] + LAG[l] == 0 else 1 / (2 * (DELAY[j] + LAG[l]))
        rr.append(b - sr[c][int(np.argmin(np.abs(np.log(ETA) - np.log(min(e_ideal, lim)))))])
    rr = np.array(rr)
    print(f"{label:24s} drop {(ideal - best).max():.2f}  eta_rob {ETA[rob]}  regret mean {reg.mean():.3f} max {reg.max():.2f}"
          f"  rule regret mean {rr.mean():.3f} max {rr.max():.2f}")


print("\nDecision quantities for wider assumed sets (exploratory)")
rules(0.1, 0.05, "R: h<=100 tau<=50")
rules(0.15, 0.05, "h<=150 tau<=50")
rules(0.2, 0.05, "h<=200 tau<=50")
rules(0.1, 0.15, "h<=100 tau<=150")
rules(0.2, 0.15, "h<=200 tau<=150")
rules(0.3, 0.15, "whole grid")
