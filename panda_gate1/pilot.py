import time, numpy as np, robot as Rb
rb = Rb.Panda()
for T in [8.0, 4.0]:
    for hole in Rb.HOLES:
        ref = Rb.reference_for(rb, hole, T)
        for eta, h, tau in [(5, 0, 0), (0.5, 0, 0)]:
            r = Rb.run(rb, ref, hole, eta, h, tau)
            print(T, hole, eta, {k: round(v, 4) for k, v in r.items() if k != 'goal_z'}, Rb.insert_ok(r, .005), Rb.paper_ok(r), flush=True)
