"""Panda in PyBullet, velocity controlled through J-dagger, with injected delay and lag."""
import os
from collections import deque

import numpy as np
import pybullet as p
import pybullet_data

import field_se3 as F

SIM_HZ, CTRL_HZ = 500, 100
SUB = SIM_HZ // CTRL_HZ
ARM = list(range(7))
EE_LINK = 11
TOOL = [0.0, 0.0, 0.25]
FORCE = [87, 87, 87, 87, 12, 12, 12]
QD_MAX = np.array([2.175, 2.175, 2.175, 2.175, 2.61, 2.61, 2.61])
Q_HOME = [0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785]
P_START = np.array([0.30, 0.0, 0.45])
TILT_START = np.array([0.0, 0.5, 0.0])
RIM_Z, DEPTH = 0.25, 0.06
HOLES = [(0.38, -0.16), (0.42, -0.08), (0.46, 0.0), (0.42, 0.08), (0.38, 0.16)]
R_DOWN = np.diag([1.0, -1.0, -1.0])


class Panda:
    def __init__(self):
        self.c = p.connect(p.DIRECT)
        p.setGravity(0, 0, -9.81, physicsClientId=self.c)
        p.setTimeStep(1 / SIM_HZ, physicsClientId=self.c)
        urdf = os.path.join(pybullet_data.getDataPath(), "franka_panda/panda.urdf")
        self.r = p.loadURDF(urdf, useFixedBase=True, physicsClientId=self.c,
                            flags=p.URDF_USE_SELF_COLLISION * 0)
        self.movable = [j for j in range(p.getNumJoints(self.r, physicsClientId=self.c))
                        if p.getJointInfo(self.r, j, physicsClientId=self.c)[2] != p.JOINT_FIXED]
        for link in range(-1, p.getNumJoints(self.r, physicsClientId=self.c)):
            p.setCollisionFilterGroupMask(self.r, link, 0, 0, physicsClientId=self.c)
        self.reset(Q_HOME)

    def reset(self, q):
        for j, a in zip(ARM, q):
            p.resetJointState(self.r, j, a, 0.0, physicsClientId=self.c)
        for j in (9, 10):
            p.resetJointState(self.r, j, 0.0, 0.0, physicsClientId=self.c)

    def q(self):
        return np.array([s[0] for s in p.getJointStates(self.r, ARM, physicsClientId=self.c)])

    def pose(self):
        s = p.getLinkState(self.r, EE_LINK, computeForwardKinematics=1, physicsClientId=self.c)
        R = np.array(p.getMatrixFromQuaternion(s[5])).reshape(3, 3)
        return R, np.array(s[4]) + R @ np.array(TOOL)

    def jacobian(self):
        n = len(self.movable)
        q = [s[0] for s in p.getJointStates(self.r, self.movable, physicsClientId=self.c)]
        lin, ang = p.calculateJacobian(self.r, EE_LINK, TOOL, q, [0.0] * n, [0.0] * n, physicsClientId=self.c)
        return np.vstack([np.array(lin)[:, :7], np.array(ang)[:, :7]])

    def ik(self, R_t, p_t, iters=200):
        """Damped least squares on the true kinematics, in place. Returns the final pose error."""
        for _ in range(iters):
            R, pos = self.pose()
            ew = R @ F.so3_log(R.T @ R_t)
            ev = p_t - pos
            err = np.concatenate([ev, ew])
            if np.linalg.norm(err) < 1e-5:
                break
            J = self.jacobian()
            dq = J.T @ np.linalg.solve(J @ J.T + 1e-4 * np.eye(6), err)
            self.reset(self.q() + 0.5 * dq)
        R, pos = self.pose()
        return np.linalg.norm(p_t - pos), np.linalg.norm(F.so3_log(R.T @ R_t))

    def command(self, qd):
        p.setJointMotorControlArray(self.r, ARM, p.VELOCITY_CONTROL, targetVelocities=list(qd),
                                    forces=FORCE, physicsClientId=self.c)

    def twist_to_qd(self, R, w, v):
        V = np.concatenate([v, R @ w])
        qd = np.linalg.pinv(self.jacobian(), rcond=1e-3) @ V
        scale = np.max(np.abs(qd) / QD_MAX)
        return qd / max(scale, 1.0)


def reference_for(robot, hole, T):
    """Common start above the rim, tilted away from the insertion direction."""
    return F.make_reference(hole, RIM_Z, DEPTH, P_START, R_DOWN @ F.so3_exp(TILT_START), R_DOWN, T)


def disturbance(rng, scale):
    """Random direction in se(3), unit in the metric, times scale."""
    z = rng.normal(size=6)
    w, v = z[:3], z[3:]
    n = F.norm(w, v)
    return w / n * scale, v / n * scale


def run(robot, ref, hole, eta, h, tau, dist=None, tf=15.0):
    """One closed-loop episode. dist = (time, w, v). Returns the summary of the run."""
    robot.reset(ref_q0(robot, ref))
    dt = 1 / CTRL_HZ
    buf = deque([np.zeros(7)] * int(round(h / dt)))
    qd_f = np.zeros(7)
    a = dt / tau if tau > 0 else 1.0
    goal = np.array([hole[0], hole[1], RIM_Z - DEPTH])
    max_lat, max_tilt = 0.0, 0.0
    t_rim = None
    applied = dist is None
    for k in range(int(tf * CTRL_HZ)):
        t = k * dt
        if not applied and t >= dist[0]:
            R, pos = robot.pose()
            Rn = R @ F.so3_exp(dist[1])
            pn = pos + R @ dist[2]
            robot.ik(Rn, pn)
            applied = True
        R, pos = robot.pose()
        c, m, D, i = ref.field(R, pos)
        w, v = F.clip(m[0] + eta * c[0], m[1] + eta * c[1], ref.vmax)
        buf.append(robot.twist_to_qd(R, w, v))
        qd = buf.popleft()
        qd_f = qd_f + a * (qd - qd_f)
        robot.command(qd_f)
        for _ in range(SUB):
            p.stepSimulation(physicsClientId=robot.c)
        R, pos = robot.pose()
        if pos[2] < RIM_Z:
            t_rim = t + dt if t_rim is None else t_rim
            max_lat = max(max_lat, float(np.hypot(pos[0] - hole[0], pos[1] - hole[1])))
            tilt = float(np.arccos(np.clip(-R[2, 2], -1, 1)))
            max_tilt = max(max_tilt, tilt)
    R, pos = robot.pose()
    return dict(lat=max_lat, tilt=max_tilt, end_z=float(pos[2]), goal_z=float(goal[2]), t_rim=t_rim,
                end_p=float(np.linalg.norm(pos - goal)), end_r=float(np.sqrt(2) * np.linalg.norm(F.so3_log(R.T @ ref.goal_R))),
                D_end=float(F.distance(R, pos, ref.goal_R, ref.goal_p)))


def ref_q0(robot, ref):
    """Joint start that reaches the reference start, seeded from Q_HOME."""
    robot.reset(Q_HOME)
    e = robot.ik(ref.R[0], ref.p[0])
    assert e[0] < 1e-3
    return robot.q()


def insert_ok(res, c):
    """Primary success rule of PROTOKOL.md for a clearance of c metres."""
    deep = (RIM_Z - res["end_z"]) >= 0.9 * DEPTH
    return deep and res["lat"] <= c and res["tilt"] <= np.arctan(2 * c / DEPTH)


def paper_ok(res):
    return res["end_p"] <= 0.02 and res["end_r"] <= 0.2
