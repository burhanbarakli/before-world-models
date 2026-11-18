"""Panda with a peg and a real hole: contact, compliance and the field shift of PROTOKOL.md."""
import os
import sys
import tempfile
from collections import deque

for name in ["OMP_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OPENBLAS_NUM_THREADS"]:
    os.environ[name] = "1"

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "panda_gate1"))
sys.path.insert(0, os.path.join(HERE, "..", "panda_learned"))

import numpy as np
import pybullet as p
import pybullet_data

import field_se3 as F
import robot as Rb

PEG_R, PEG_LINK = 0.010, 12
OUTER, N_RING = 0.045, 24
CLEARANCES = [0.005, 0.002]
F_MAX, SIGMA_F, FILTER_S = 50.0, 0.5, 0.02
PUSH_S = 0.1
CTRL_HZ = 100
PARK = [0.0, 2.0, -2.0]

# Set in the pilot (PROTOKOL.md, Pilot)
SIM_HZ = 1000
ADMIT = 0.004  # m/s per N, translational, at the tool tip
TAU_ADMIT = 0.01  # s, low pass on the force the compliance sees
K_CONTACT, D_CONTACT = 1e4, 280.0  # PyBullet contact stiffness and damping, on the peg and the holders
F_T, V_S = 5.0, 0.01  # pilot: highest REFLEKS SR, ties to the default F_t

PEG = """
  <link name="peg">
    <inertial><origin xyz="0 0 {h}"/><mass value="0.1"/>
      <inertia ixx="5e-4" ixy="0" ixz="0" iyy="5e-4" iyz="0" izz="5e-6"/></inertial>
    <collision><origin xyz="0 0 {h}"/><geometry><cylinder radius="{r}" length="{l}"/></geometry></collision>
  </link>
  <joint name="peg_joint" type="fixed">
    <parent link="panda_grasptarget"/><child link="peg"/><origin xyz="0 0 0"/>
  </joint>
</robot>
"""


def peg_urdf():
    root = os.path.join(pybullet_data.getDataPath(), "franka_panda")
    with open(os.path.join(root, "panda.urdf")) as f:
        s = f.read().replace("package://meshes", os.path.join(root, "meshes"))
    s = s[:s.rindex("</robot>")] + PEG.format(h=Rb.TOOL[2] / 2, r=PEG_R, l=Rb.TOOL[2])
    fd, path = tempfile.mkstemp(suffix=".urdf")
    with os.fdopen(fd, "w") as f:
        f.write(s)
    return path


class Panda(Rb.Panda):
    """Rb.Panda with a peg link and one static holder per clearance; only the peg collides."""

    def __init__(self, sim_hz=SIM_HZ):
        self.sim_hz = sim_hz
        self.c = p.connect(p.DIRECT)
        p.setGravity(0, 0, -9.81, physicsClientId=self.c)
        p.setTimeStep(1 / sim_hz, physicsClientId=self.c)
        path = peg_urdf()
        self.r = p.loadURDF(path, useFixedBase=True, physicsClientId=self.c)
        os.remove(path)
        n = p.getNumJoints(self.r, physicsClientId=self.c)
        assert p.getJointInfo(self.r, PEG_LINK, physicsClientId=self.c)[12] == b"peg"
        self.movable = [j for j in range(n) if p.getJointInfo(self.r, j, physicsClientId=self.c)[2] != p.JOINT_FIXED]
        for link in range(-1, n):
            g = 1 if link == PEG_LINK else 0
            p.setCollisionFilterGroupMask(self.r, link, g, 2 * g, physicsClientId=self.c)
        p.changeDynamics(self.r, PEG_LINK, contactStiffness=K_CONTACT, contactDamping=D_CONTACT, physicsClientId=self.c)
        self.holders = {c: self.holder(PEG_R + c) for c in CLEARANCES}
        self.reset(Rb.Q_HOME)

    def holder(self, ri):
        """A block of thickness DEPTH with a 24-gon hole of inradius ri, one static box per side, parked away."""
        rc, hw = (ri + OUTER) / 2, OUTER * np.tan(np.pi / N_RING) * 1.05
        box = p.createCollisionShape(p.GEOM_BOX, halfExtents=[(OUTER - ri) / 2, hw, Rb.DEPTH / 2], physicsClientId=self.c)
        parts = []
        for t in 2 * np.pi * np.arange(N_RING) / N_RING:
            b = p.createMultiBody(0, box, basePosition=PARK, physicsClientId=self.c)
            p.setCollisionFilterGroupMask(b, -1, 2, 1, physicsClientId=self.c)  # the peg only, not each other
            p.changeDynamics(b, -1, lateralFriction=1.0, contactStiffness=K_CONTACT, contactDamping=D_CONTACT,
                             physicsClientId=self.c)
            parts.append((b, rc * np.cos(t), rc * np.sin(t), p.getQuaternionFromEuler([0, 0, t])))
        return parts

    def place(self, c, xy):
        """The holder of clearance c at xy, the others parked. c = None parks all."""
        for k, parts in self.holders.items():
            for b, dx, dy, q in parts:
                pos = [xy[0] + dx, xy[1] + dy, Rb.RIM_Z - Rb.DEPTH / 2] if k == c else PARK
                p.resetBasePositionAndOrientation(b, pos, q, physicsClientId=self.c)

    def force(self):
        """Total contact force on the peg, world frame."""
        f = np.zeros(3)
        for cp in p.getContactPoints(bodyA=self.r, linkIndexA=PEG_LINK, physicsClientId=self.c):
            f += cp[9] * np.array(cp[7]) + cp[10] * np.array(cp[11]) + cp[12] * np.array(cp[13])
        return f

    def qd_of(self, Jp, R, w, v):
        return Jp @ np.concatenate([v, R @ w])


class Shift:
    """The field shift s-hat: fixed at s0, plus a spiral search after contact when search is on."""

    def __init__(self, s0, search, c, f_t=F_T, v_s=V_S):
        self.s0, self.s = np.asarray(s0, float), np.asarray(s0, float).copy()
        self.search, self.f_t, self.v_s = search, f_t, v_s
        self.b = 2 * c / (2 * np.pi)
        self.state, self.count, self.th = "idle", 0, 0.0
        self.t_contact = None

    def update(self, t, z, fz, dt):
        if not self.search or self.state == "done":
            return self.s
        if z < Rb.RIM_Z - 0.005:
            self.state = "done"
            return self.s
        if self.state == "idle":
            self.count = self.count + 1 if (z - Rb.RIM_Z <= 0.02 and fz >= self.f_t) else 0
            if self.count >= 5:
                self.state, self.t_contact = "search", t
            return self.s
        r = self.b * self.th
        self.th += self.v_s * dt / np.hypot(r, self.b)
        if self.b * self.th > 0.015:
            self.th = 0.0
        r = self.b * self.th
        self.s = self.s0 + r * np.array([np.cos(self.th), np.sin(self.th), 0.0])
        return self.s


class Shifted:
    """Field evaluated at p - s, with the bookkeeping of the wrapped field."""

    def __init__(self, f, shift):
        self.f, self.shift = f, shift
        self.dt, self.vmax, self.p, self.R = f.dt, f.vmax, f.p, f.R
        self.goal_R, self.goal_p = f.goal_R, f.goal_p

    def field(self, R, pos):
        return self.f.field(R, pos - self.shift.s)


def push_height(ref, gap):
    """Height of the reference gap seconds before it crosses the rim."""
    import gate1g as Gg
    return float(ref.p[Gg.rim_index(ref) - int(round(gap / ref.dt)), 2])


def run(robot, f, hole, e, c, eta, h, tau, shift, push=None, noise=None, mu=0.5, tf=15.0,
        collide=True, admit=ADMIT, tau_admit=TAU_ADMIT, trace=None):
    """One episode. e: hole position error (true hole = hole + e). c: clearance, picks the holder.
    shift: Shift. push: (z_d, w, v) applied as a PUSH_S long external twist once the tip passes z_d.
    noise: Generator for the force sensor. Returns the summary of the run."""
    robot.reset(Rb.ref_q0(robot, f))
    true = np.array([hole[0] + e[0], hole[1] + e[1]])
    robot.place(c if collide else None, true)
    p.changeDynamics(robot.r, PEG_LINK, lateralFriction=mu, physicsClientId=robot.c)
    g = Shifted(f, shift)
    dt, sub = 1 / CTRL_HZ, robot.sim_hz // CTRL_HZ
    buf = deque([np.zeros(7)] * int(round(h / dt)))
    qd_f = np.zeros(7)
    a = dt / tau if tau > 0 else 1.0
    win = deque([np.zeros(3)] * int(round(FILTER_S * robot.sim_hz)))
    f_filt, f_meas, f_adm = np.zeros(3), np.zeros(3), np.zeros(3)
    b_adm = min(1.0, 1 / (robot.sim_hz * tau_admit)) if tau_admit > 0 else 1.0
    f_max, f_sum, n_contact = 0.0, 0.0, 0
    push_left, t_push = 0, None
    lat, t_rim, t_in = 0.0, None, None
    z_goal = Rb.RIM_Z - 0.9 * Rb.DEPTH
    zs = []
    for k in range(int(tf * CTRL_HZ)):
        t = k * dt
        R, pos = robot.pose()
        if push is not None and t_push is None and pos[2] <= push[0]:
            t_push, push_left = t, int(round(PUSH_S / dt))
        shift.update(t, pos[2], f_meas[2], dt)
        cf, m, _, _ = g.field(R, pos)
        w, v = F.clip(m[0] + eta * cf[0], m[1] + eta * cf[1], g.vmax)
        Jp = np.linalg.pinv(robot.jacobian(), rcond=1e-3)
        buf.append(robot.qd_of(Jp, R, w, v))
        qd = buf.popleft()
        qd_f = qd_f + a * (qd - qd_f)
        qd_c = qd_f
        if push_left > 0:
            qd_c = qd_c + robot.qd_of(Jp, R, push[1] / PUSH_S, R @ push[2] / PUSH_S)
            push_left -= 1
        for _ in range(sub):
            qd_s = qd_c + Jp[:, :3] @ (admit * f_adm)  # compliance in the inner loop, at the simulation rate
            robot.command(qd_s / max(np.max(np.abs(qd_s) / Rb.QD_MAX), 1.0))
            p.stepSimulation(physicsClientId=robot.c)
            f_raw = robot.force()
            f_adm = f_adm + b_adm * (f_raw - f_adm)
            f_filt = f_filt + (f_raw - win.popleft()) / len(win)  # BUG kept as run: len is 19 here, reads 20/19 high (Sapma 5)
            win.append(f_raw)
            f_max = max(f_max, float(np.linalg.norm(f_filt)))
        if np.linalg.norm(f_filt) > 0.5:
            f_sum, n_contact = f_sum + float(np.linalg.norm(f_filt)), n_contact + 1
        f_meas = f_filt + (noise.normal(0, SIGMA_F, 3) if noise is not None else 0.0)
        R, pos = robot.pose()
        zs.append(pos[2])
        if trace is not None:
            trace.append((t, pos[2], *f_filt))
        if pos[2] < Rb.RIM_Z:
            t_rim = t + dt if t_rim is None else t_rim
            lat = max(lat, float(np.hypot(pos[0] - true[0], pos[1] - true[1])))
        if t_in is None and pos[2] <= z_goal:
            t_in = t + dt
    R, pos = robot.pose()
    zs = np.array(zs)
    w2 = int(2 * CTRL_HZ)
    jam = bool(pos[2] > z_goal and np.ptp(zs[-w2:]) < 0.001)
    return dict(end_z=float(pos[2]), deep=bool(pos[2] <= z_goal), f_max=f_max, ok=bool(pos[2] <= z_goal and f_max <= F_MAX),
                t_in=tf if t_in is None else t_in, jam=jam, t_rim=t_rim, lat=lat,
                pushed=t_push is not None, t_push=-1.0 if t_push is None else t_push,
                t_contact=-1.0 if shift.t_contact is None else shift.t_contact,
                s_err=float(np.linalg.norm(shift.s[:2] - np.asarray(e[:2]))),
                f_mean=f_sum / max(n_contact, 1),
                end_lat=float(np.hypot(pos[0] - true[0], pos[1] - true[1])))


KEYS = ["end_z", "deep", "f_max", "ok", "t_in", "jam", "lat", "pushed", "t_push", "t_contact", "s_err", "f_mean",
        "end_lat"]
