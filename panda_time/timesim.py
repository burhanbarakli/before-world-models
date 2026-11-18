"""The time protocol (PROTOKOL.md): contact.run plus a moment measurement and the new search policies.

contact.py is not changed; run_t is its loop with the moment about the tip added and a shift that sees it.
"""
import os
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "panda_contact"))

import contact as C  # sets thread limits and the paths of panda_gate1 and panda_learned

import numpy as np
import pybullet as p

import field_se3 as F
import robot as Rb

SIGMA_M = C.SIGMA_F * C.PEG_R  # 0.005 Nm
CAP = 0.015  # search radius cap, m
R_MIN = 0.002  # below this contact offset the moment gives no direction

# Set in the pilot (P4)
V_S, PITCH = 0.02, 2.0  # REFLEKS-H: spiral speed m/s, pitch in units of c (pilot P4)
V_L, N_W = 0.01, 5  # MOMENT: line speed m/s, averaging window in ticks (pilot P4)


def contacts(robot, tip):
    """Total contact force on the peg and its moment about the tip, world frame (plain floats: few contacts)."""
    fx = fy = fz = mx = my = mz = 0.0
    tx, ty, tz = float(tip[0]), float(tip[1]), float(tip[2])
    for cp in p.getContactPoints(bodyA=robot.r, linkIndexA=C.PEG_LINK, physicsClientId=robot.c):
        n, d1, d2, fn, f1, f2 = cp[7], cp[11], cp[13], cp[9], cp[10], cp[12]
        gx = fn * n[0] + f1 * d1[0] + f2 * d2[0]
        gy = fn * n[1] + f1 * d1[1] + f2 * d2[1]
        gz = fn * n[2] + f1 * d1[2] + f2 * d2[2]
        rx, ry, rz = cp[5][0] - tx, cp[5][1] - ty, cp[5][2] - tz
        fx, fy, fz = fx + gx, fy + gy, fz + gz
        mx, my, mz = mx + ry * gz - rz * gy, my + rz * gx - rx * gz, mz + rx * gy - ry * gx
    return np.array([fx, fy, fz]), np.array([mx, my, mz])


class Spiral:
    """KAHIN (s0 = e) and REFLEKS-H (s0 = 0): fixed s0, an Archimedean spiral around it after contact."""

    def __init__(self, s0, c, f_t, v_s, pitch):
        self.s0, self.s = np.asarray(s0, float), np.asarray(s0, float).copy()
        self.f_t, self.v_s = f_t, v_s
        self.b = pitch * c / (2 * np.pi)
        self.state, self.count, self.th = "idle", 0, 0.0
        self.t_contact, self.u = None, None

    def trigger(self, z, fz):
        self.count = self.count + 1 if (z - Rb.RIM_Z <= 0.02 and fz >= self.f_t) else 0
        return self.count >= 5

    def spiral(self, dt):
        r = self.b * self.th
        self.th += self.v_s * dt / np.hypot(r, self.b)
        if self.b * self.th > CAP:
            self.th = 0.0
        r = self.b * self.th
        self.s = self.s0 + r * np.array([np.cos(self.th), np.sin(self.th), 0.0])

    def update(self, t, z, f, m, dt):
        if self.state == "done":
            return self.s
        if z < Rb.RIM_Z - 0.005:
            self.state = "done"
            return self.s
        if self.state == "idle":
            if self.trigger(z, f[2]):
                self.state, self.t_contact = "search", t
            return self.s
        self.spiral(dt)
        return self.s


class Moment(Spiral):
    """MOMENT (and HAFIZA with s0 = the remembered offset): after the trigger, average force and moment over n_w
    ticks, take the hole direction opposite to the contact point, search along it at v_l up to CAP, then fall back
    to the spiral around s0. No direction (|r| < R_MIN) goes to the spiral at once."""

    def __init__(self, s0, c, f_t, v_s, pitch, v_l, n_w):
        super().__init__(s0, c, f_t, v_s, pitch)
        self.v_l, self.n_w = v_l, n_w
        self.acc_f, self.acc_m, self.n, self.d = np.zeros(3), np.zeros(3), 0, 0.0

    def update(self, t, z, f, m, dt):
        if self.state == "done":
            return self.s
        if z < Rb.RIM_Z - 0.005:
            self.state = "done"
            return self.s
        if self.state == "idle":
            if self.trigger(z, f[2]):
                self.state, self.t_contact = "measure", t
            return self.s
        if self.state == "measure":
            self.acc_f, self.acc_m, self.n = self.acc_f + f, self.acc_m + m, self.n + 1
            if self.n >= self.n_w:
                fz = self.acc_f[2] / self.n
                tx, ty = self.acc_m[0] / self.n, self.acc_m[1] / self.n
                r = np.array([-ty / fz, tx / fz]) if fz > 1e-6 else np.zeros(2)
                if np.linalg.norm(r) < R_MIN:
                    self.state = "search"
                else:
                    self.u = np.array([*(-r / np.linalg.norm(r)), 0.0])
                    self.state = "line"
            return self.s
        if self.state == "line":
            self.d += self.v_l * dt
            if self.d >= CAP:
                self.state, self.s = "search", self.s0.copy()
            else:
                self.s = self.s0 + self.d * self.u
            return self.s
        self.spiral(dt)
        return self.s


def run_t(robot, f, hole, e, c, eta, h, tau, shift, push=None, noise=None, mu=0.5, tf=15.0,
          admit=C.ADMIT, tau_admit=C.TAU_ADMIT, meas=None):
    """contact.run with the moment about the tip measured through the same filter. Returns contact.run's summary
    plus end_dx, end_dy (end tip position minus the nominal hole) and u_err (deg, direction error, -1 if none)."""
    robot.reset(Rb.ref_q0(robot, f))
    true = np.array([hole[0] + e[0], hole[1] + e[1]])
    robot.place(c, true)
    p.changeDynamics(robot.r, C.PEG_LINK, lateralFriction=mu, physicsClientId=robot.c)
    g = C.Shifted(f, shift)
    dt, sub = 1 / C.CTRL_HZ, robot.sim_hz // C.CTRL_HZ
    buf = deque([np.zeros(7)] * int(round(h / dt)))
    qd_f = np.zeros(7)
    a = dt / tau if tau > 0 else 1.0
    nwin = int(round(C.FILTER_S * robot.sim_hz))
    win, mwin = deque([np.zeros(3)] * nwin), deque([np.zeros(3)] * nwin)
    f_filt, m_filt, f_meas, m_meas, f_adm = np.zeros(3), np.zeros(3), np.zeros(3), np.zeros(3), np.zeros(3)
    b_adm = min(1.0, 1 / (robot.sim_hz * tau_admit)) if tau_admit > 0 else 1.0
    f_max, f_sum, n_contact = 0.0, 0.0, 0
    push_left, t_push = 0, None
    lat, t_rim, t_in = 0.0, None, None
    z_goal = Rb.RIM_Z - 0.9 * Rb.DEPTH
    zs = []
    # the moment noise has its own stream, so the force noise is the same sequence as in contact.run
    noise_m = np.random.default_rng(noise.bit_generator.seed_seq.spawn(1)[0]) if noise is not None else None
    for k in range(int(tf * C.CTRL_HZ)):
        t = k * dt
        R, pos = robot.pose()
        if push is not None and t_push is None and pos[2] <= push[0]:
            t_push, push_left = t, int(round(C.PUSH_S / dt))
        if hasattr(shift, "see"):  # panda_rival: the policy may read the tip position (proprioception)
            shift.see(pos)
        shift.update(t, pos[2], f_meas, m_meas, dt)
        cf, m, _, _ = g.field(R, pos)
        w, v = F.clip(m[0] + eta * cf[0], m[1] + eta * cf[1], g.vmax)
        Jp = np.linalg.pinv(robot.jacobian(), rcond=1e-3)
        buf.append(robot.qd_of(Jp, R, w, v))
        qd = buf.popleft()
        qd_f = qd_f + a * (qd - qd_f)
        qd_c = qd_f
        if push_left > 0:
            qd_c = qd_c + robot.qd_of(Jp, R, push[1] / C.PUSH_S, R @ push[2] / C.PUSH_S)
            push_left -= 1
        for _ in range(sub):
            qd_s = qd_c + Jp[:, :3] @ (admit * f_adm)
            robot.command(qd_s / max(np.max(np.abs(qd_s) / Rb.QD_MAX), 1.0))
            p.stepSimulation(physicsClientId=robot.c)
            f_raw, m_raw = contacts(robot, pos)
            f_adm = f_adm + b_adm * (f_raw - f_adm)
            f_filt = f_filt + (f_raw - win.popleft()) / nwin
            m_filt = m_filt + (m_raw - mwin.popleft()) / nwin
            win.append(f_raw)
            mwin.append(m_raw)
            f_max = max(f_max, float(np.linalg.norm(f_filt)))
        if np.linalg.norm(f_filt) > 0.5:
            f_sum, n_contact = f_sum + float(np.linalg.norm(f_filt)), n_contact + 1
        if meas is None:
            f_meas = f_filt + (noise.normal(0, C.SIGMA_F, 3) if noise is not None else 0.0)
            m_meas = m_filt + (noise_m.normal(0, SIGMA_M, 3) if noise_m is not None else 0.0)
        else:  # panda_sensor: a sensor model maps the true filtered force and tip moment to the measurement
            f_meas, m_meas = meas(f_filt, m_filt)
        R, pos = robot.pose()
        zs.append(pos[2])
        if pos[2] < Rb.RIM_Z:
            t_rim = t + dt if t_rim is None else t_rim
            lat = max(lat, float(np.hypot(pos[0] - true[0], pos[1] - true[1])))
        if t_in is None and pos[2] <= z_goal:
            t_in = t + dt
    R, pos = robot.pose()
    zs = np.array(zs)
    jam = bool(pos[2] > z_goal and np.ptp(zs[-int(2 * C.CTRL_HZ):]) < 0.001)
    u_err = -1.0
    if shift.u is not None and np.linalg.norm(e[:2]) > 0:
        u_err = float(np.degrees(np.arccos(np.clip(shift.u[:2] @ e[:2] / np.linalg.norm(e[:2]), -1, 1))))
    return dict(end_z=float(pos[2]), deep=bool(pos[2] <= z_goal), f_max=f_max,
                ok=bool(pos[2] <= z_goal and f_max <= C.F_MAX), t_in=tf if t_in is None else t_in, jam=jam,
                t_rim=t_rim, lat=lat, pushed=t_push is not None, t_push=-1.0 if t_push is None else t_push,
                t_contact=-1.0 if shift.t_contact is None else shift.t_contact,
                s_err=float(np.linalg.norm(shift.s[:2] - np.asarray(e[:2]))), f_mean=f_sum / max(n_contact, 1),
                end_lat=float(np.hypot(pos[0] - true[0], pos[1] - true[1])),
                end_dx=float(pos[0] - hole[0]), end_dy=float(pos[1] - hole[1]), u_err=u_err)


KEYS = C.KEYS + ["end_dx", "end_dy", "u_err"]
