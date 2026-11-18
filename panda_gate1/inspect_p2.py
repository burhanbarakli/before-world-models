"""P2 of inspect_sim.py with the right sign: delay h puts the disturbance h earlier on the path.

Run: python inspect_p2.py    (appends to results/inspect.txt)
"""
import itertools
import multiprocessing as mp

import numpy as np
import inspect_sim as S

if __name__ == "__main__":
    jobs = [("P2", 8.0, 0.0, 0.0, 1, ih, kd, s, -0.1)
            for ih, kd, s in itertools.product(S.HOLES5, [0, 1], range(10))]
    with mp.Pool(4) as pool:
        res = pool.map(S.job, jobs, chunksize=4)
    line = f"\nP2 corrected sign, eta=1 T=8, h=0, disturbance 100 ms earlier: SR_insert {np.mean([r[2] for r in res]):.2f}\n"
    open("results/inspect.txt", "a").write(line)
    print(line)
