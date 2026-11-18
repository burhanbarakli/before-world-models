"""Why SR_insert sits at .80 for T = 15. Exploratory. Run: python inspect_t15.py"""
import numpy as np
import gate1 as G
from robot import DEPTH, RIM_Z

D = np.load("results/gate1_T15.npz")["data"]  # h, tau, eta, hole, kind, seed, key
k = {n: D[..., i] for i, n in enumerate(G.KEYS)}
C = 0.005
depth = RIM_Z - k["end_z"]
deep = depth >= 0.9 * DEPTH
lat = k["lat"] <= C
tilt = k["tilt"] <= np.arctan(2 * C / DEPTH)
ok = deep & lat & tilt
e = G.ETA.index(5)
print("h=0 tau=0 eta=5: fail depth", 1 - deep[0, 0, e].mean(), "lat", 1 - lat[0, 0, e].mean(), "tilt", 1 - tilt[0, 0, e].mean())
print("SR by hole", ok[0, 0, e].mean((1, 2)), "by kind", ok[0, 0, e].mean((0, 2)))
print("depth reached [mm], target 60, need 54: min/median/max",
      np.round(1000 * np.array([depth[0, 0, e].min(), np.median(depth[0, 0, e]), depth[0, 0, e].max()]), 2))
print("by kind, median depth", np.round(1000 * np.median(depth[0, 0, e], axis=(0, 2)), 2))
print("lat [mm] over all eta>=2, R: max", round(1000 * k["lat"][:, :, 2:].max(), 1))
print("\nWith the lateral and tilt criteria only (no depth), by eta, h=0 tau=0:", np.round((lat & tilt)[0, 0].mean((1, 2, 3)), 2))
print("With lateral and tilt only, h=100 tau=50:", np.round((lat & tilt)[4, 1].mean((1, 2, 3)), 2))
print("Fraction reaching depth 54 mm by h, tau=0, eta=5:", np.round(deep[:, 0, e].mean((1, 2, 3)), 2))
print("With depth need 50 mm:", np.round((depth >= 0.05)[:, 0, e].mean((1, 2, 3)), 2))
