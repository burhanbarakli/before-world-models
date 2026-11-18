"""Why does hole 5 stall? Traces joint margins and manipulability in a failing episode."""
import numpy as np, pybullet as p
import robot as Rb, field_se3 as F
from gate1 import draw
LOW = np.array([-2.9671,-1.8326,-2.9671,-3.1416,-2.9671,-0.0873,-2.9671]); HIGH = np.array([2.9671,1.8326,2.9671,0.0,2.9671,3.8223,2.9671])
rb = Rb.Panda()
hole = Rb.HOLES[4]; ref = Rb.reference_for(rb, hole, 8.0)
d = draw(rb, ref, 4, 0, 0)
# Same loop as Rb.run, with h = 50 ms, tracing.
orig = rb.command; log = []
def spy(qd):
    q = rb.q(); J = rb.jacobian(); log.append((q.copy(), np.sqrt(np.linalg.det(J @ J.T)), np.min(np.linalg.svd(J, compute_uv=False)), np.abs(qd).max()))
    orig(qd)
rb.command = spy
r = Rb.run(rb, ref, hole, 5, 0.05, 0.0, d)
print({k: round(v, 4) for k, v in r.items()})
q = np.array([l[0] for l in log])
for t in [0, 100, 200, 300, 400, 500, 600, 700, 800, 1000, 1499]:
    print(t, 'q', np.round(q[t], 3), 'manip %.4f smin %.4f qdmax %.3f' % log[t][1:], 'margin', round(float(np.min(np.minimum(q[t] - LOW, HIGH - q[t]))), 3), 'joint', int(np.argmin(np.minimum(q[t] - LOW, HIGH - q[t]))))
# Static reach: are the goal poses of every hole reachable by IK from the start seed, and how close to limits?
for i, h in enumerate(Rb.HOLES):
    ref = Rb.reference_for(rb, h, 8.0)
    Rb.ref_q0(rb, ref); margins = []
    smin = []
    for j in range(0, len(ref.p), 100):
        e = rb.ik(ref.R[j], ref.p[j]); q = rb.q()
        margins.append(np.minimum(q - LOW, HIGH - q).min()); smin.append(np.linalg.svd(rb.jacobian(), compute_uv=False).min())
    print('hole', h, 'ik end err', np.round(e, 5), 'min joint margin %.3f' % min(margins), 'min sigma %.3f' % min(smin), 'end q', np.round(rb.q(), 2))
