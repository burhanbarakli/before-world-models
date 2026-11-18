"""Run: python test_se3.py"""
import numpy as np
import field_se3 as F
import robot as Rb

rng = np.random.default_rng(0)
def rand_R(s=1.0): return F.so3_exp(rng.normal(size=3) * s)

for _ in range(200):
    w = rng.normal(size=3); w *= rng.uniform(.01, 3) / np.linalg.norm(w)
    assert np.abs(F.so3_log(F.so3_exp(w)) - w).max() < 1e-7

rb = Rb.Panda()
ref = Rb.reference_for(rb, Rb.HOLES[2], 8.0)
# Reference starts where the arm is, ends in the hole, and has zero end speed.
assert np.linalg.norm(ref.goal_p - [*Rb.HOLES[2], Rb.RIM_Z - Rb.DEPTH]) < 1e-9 and np.abs(ref.v[-1]).max() == 0
# Velocities consistent with the discrete curve: forward body rotation over one sample.
i = 700
dw = F.so3_log(ref.R[i].T @ ref.R[i + 1]) / ref.dt
assert np.abs(dw - (ref.w[i] + ref.w[i + 1]) / 2).max() < 1e-3
# On the curve: c = 0, m = reference velocity.
c, m, D, j = ref.field(ref.R[300], ref.p[300])
assert j == 300 and D < 1e-6 and np.abs(m[1] - ref.v[300]).max() < 1e-12
# Transport is an isometry, and nearest beats brute force.
x_R = ref.R[400] @ F.so3_exp(rng.normal(size=3) * .2); x_p = ref.p[400] + rng.normal(size=3) * .02
c, m, D, j = ref.field(x_R, x_p)
assert abs(np.linalg.norm(m[0]) - np.linalg.norm(ref.w[j])) < 1e-9
brute = min(F.distance(x_R, x_p, ref.R[k], ref.p[k]) for k in range(0, len(ref.p), 1))
assert abs(D - brute) < 1e-5, (D, brute)
assert abs(F.norm(*c) - D) < 1e-6
# Pure CVF flow shrinks D at unit rate in the ideal limit.
R, p_ = x_R.copy(), x_p.copy(); dt = 1e-3
D0 = ref.field(R, p_)[2]
for _ in range(100):
    c, _m, _D, _ = ref.field(R, p_)
    R = R @ F.so3_exp(c[0] * dt); p_ = p_ + c[1] * dt
assert abs(ref.field(R, p_)[2] / D0 - np.exp(-.1)) < .01, ref.field(R, p_)[2] / D0
# Jacobian against finite differences of the true pose.
rb.reset(Rb.Q_HOME); J = rb.jacobian(); q0 = rb.q(); e = 1e-4
R0, p0 = rb.pose()
for k in range(7):
    q = q0.copy(); q[k] += e; rb.reset(q); R1, p1 = rb.pose()
    assert np.abs((p1 - p0) / e - J[:3, k]).max() < 2e-3
    assert np.abs(R0 @ F.so3_log(R0.T @ R1) / e - J[3:, k]).max() < 2e-3
print('T ref: L', np.sum(np.linalg.norm(np.diff(ref.p, axis=0), axis=1)), 'vmax', ref.vmax, 'peak v', np.linalg.norm(ref.v, axis=1).max())
rb.reset(Rb.Q_HOME); print('home tool', np.round(rb.pose()[1], 3), np.round(rb.pose()[0][2], 3))
print('reachable start ok')
print('all ok')
