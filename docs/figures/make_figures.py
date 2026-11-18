"""Figures for docs/index.md (English) and docs/tr/index.md (Turkish). Run: python make_figures.py (needs numpy,
matplotlib). Writes figures/en/*.png and figures/tr/*.png.

Numbers in fig_contact and fig_sensor are copied from the experiment READMEs (panda_contact, panda_sensor,
panda_tare); the other two figures are illustrations computed here.
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({"font.size": 11, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "text.color": INK, "figure.facecolor": SURF, "axes.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 160,
                     "savefig.bbox": "tight"})

TXT = {
    "tr": dict(demo="gösterim (demo)", path="robotun izlediği yol", weak="  (zayıf çekim: geç kavuşur)",
               strong="  (güçlü çekim: hemen kavuşur)", calm="ηh = 0.4: sakin", ring="ηh = 1.2: salınır, söner",
               grow="ηh = 1.8: salınım büyür", time="zaman (s)", dev="yoldan sapma",
               dtitle="Aynı çekim gücü (η = 4), farklı gecikme h: düzeltme geç gelince aşırı düzeltir",
               cnames=["Hiçbir şey yapma\n(TABAN)", "Basit spiral arama\n(el kuralı)", "Deliğin yerini bilen\n(ideal, KAHİN)"],
               cgap="   ← ideale yalnız 1.6 puan uzak", pct=lambda v: f"%{v:.1f}",
               cticks=["%0", "%20", "%40", "%60", "%80", "%100"],
               cx="deliğe sokma başarısı (deliğin yeri 3–10 mm yanlış bilinirken)",
               levels=["S0\nkusursuz ölçüm", "S1\niyi bilek\nalgılayıcısı", "S2\nsıradan\nalgılayıcı",
                       "S3\nbilek\nalgılayıcısı yok"],
               m2r="moment kuralı (MOMENT-2R)", tare="+ temastan önce sıfırla (TARE)", thr="eşik 0.5 s",
               sy="ideale göre gecikme (s)", stitle="Deliği bulma süresinde el kuralının ideale göre farkı"),
    "en": dict(demo="demonstration", path="path the robot follows", weak="  (weak pull: joins late)",
               strong="  (strong pull: joins at once)", calm="ηh = 0.4: calm", ring="ηh = 1.2: rings, dies out",
               grow="ηh = 1.8: oscillation grows", time="time (s)", dev="deviation from the path",
               dtitle="Same pull (η = 4), different delay h: a late correction overcorrects",
               cnames=["Do nothing\n(BASELINE)", "Simple spiral search\n(hand rule)", "Knows where the hole is\n(ideal, ORACLE)"],
               cgap="   ← only 1.6 points from the ideal", pct=lambda v: f"{v:.1f}%",
               cticks=["0%", "20%", "40%", "60%", "80%", "100%"],
               cx="insertion success (hole position known 3–10 mm wrong)",
               levels=["S0\nperfect\nmeasurement", "S1\ngood wrist\nsensor", "S2\nordinary\nsensor",
                       "S3\nno wrist\nsensor"],
               m2r="moment rule (MOMENT-2R)", tare="+ re-zero before contact (TARE)", thr="threshold 0.5 s",
               sy="slower than the ideal (s)", stitle="Hole-finding time: how far the hand rule is from the ideal"),
}

# --- demo curve and its guiding field -------------------------------------------------------------------------
S = np.linspace(0, 2 * np.pi, 600)
CURVE = np.c_[S, 0.6 * np.sin(S)]
TAN = np.gradient(CURVE, axis=0)
TAN /= np.linalg.norm(TAN, axis=1, keepdims=True)


def field(p, eta):
    i = np.argmin(np.sum((CURVE - p) ** 2, axis=1))
    m = TAN[i]  # mimicking part: the demo's direction at the nearest point
    c = CURVE[i] - p  # contracting part: back towards the curve, proportional to the distance
    return m + eta * c


def roll(p, eta, dt=0.01, n=900):
    out = [p]
    for _ in range(n):
        p = p + dt * field(p, eta)
        out.append(p)
        if p[0] > 2 * np.pi:
            break
    return np.array(out)


def fig_field(L, out):
    t = TXT[L]
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    xs, ys = np.meshgrid(np.linspace(0.2, 6.1, 15), np.linspace(-1.6, 1.6, 9))
    for ax, eta in zip(axs, (0.5, 4.0)):
        V = np.array([field(np.array([x, y]), eta) for x, y in zip(xs.ravel(), ys.ravel())])
        V /= np.linalg.norm(V, axis=1, keepdims=True)
        ax.quiver(xs, ys, V[:, 0], V[:, 1], color=INK2, alpha=0.45, width=0.004, scale=28)
        ax.plot(CURVE[:, 0], CURVE[:, 1], color=INK, lw=2.5, label=t["demo"])
        for y0 in (1.4, -1.3):
            tr = roll(np.array([0.3, y0]), eta)
            ax.plot(tr[:, 0], tr[:, 1], color=BLUE, lw=2)
            ax.plot(*tr[0], "o", color=BLUE, ms=8, mec=SURF, mew=2)
        ax.set_title(f"η = {eta:g}" + (t["weak"] if eta < 1 else t["strong"]),
                     fontsize=11, color=INK)
        ax.set_xlabel("x")
        ax.grid(color=GRID, lw=0.6)
        ax.set_aspect("equal")
    axs[0].set_ylabel("y")
    axs[0].plot([], [], color=BLUE, lw=2, label=t["path"])
    axs[0].legend(loc="lower left", frameon=False, fontsize=9)
    fig.savefig(os.path.join(out, "fig_field.png"))
    plt.close(fig)


def fig_delay(L, out):
    t_ = TXT[L]
    eta, dt, T = 4.0, 0.001, 4.0
    fig, ax = plt.subplots(figsize=(8, 3.4))
    for h, col, name in ((0.1, AQUA, t_["calm"]), (0.3, BLUE, t_["ring"]), (0.45, ORANGE, t_["grow"])):
        n, d = int(T / dt), int(h / dt)
        x = np.ones(n)
        for k in range(1, n):
            x[k] = x[k - 1] - dt * eta * (x[k - 1 - d] if k - 1 - d >= 0 else 1.0)
        t = np.arange(n) * dt
        ax.plot(t, x, color=col, lw=2, label=name)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.legend(frameon=False, loc="upper right", fontsize=9.5)
    ax.set_ylim(-1.8, 1.8)
    ax.set_xlim(0, T)
    ax.set_xlabel(t_["time"])
    ax.set_ylabel(t_["dev"])
    ax.set_title(t_["dtitle"], fontsize=11)
    ax.grid(color=GRID, lw=0.6)
    fig.savefig(os.path.join(out, "fig_delay.png"))
    plt.close(fig)


def fig_contact(L, out):
    t = TXT[L]
    names = t["cnames"]
    vals = [0.618, 0.942, 0.959]
    fig, ax = plt.subplots(figsize=(8, 2.8))
    y = np.arange(3)[::-1]
    ax.barh(y, vals, color=[INK2, BLUE, ORANGE], height=0.55)
    for yi, v, extra in zip(y, vals, ["", t["cgap"], ""]):
        ax.text(v + 0.01, yi, t["pct"](v * 100) + extra, va="center", color=INK)
    ax.set_yticks(y, names)
    ax.set_xlim(0, 1.45)
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0], t["cticks"])
    ax.set_xlabel(t["cx"])
    ax.grid(axis="x", color=GRID, lw=0.6)
    fig.savefig(os.path.join(out, "fig_contact.png"))
    plt.close(fig)


def fig_sensor(L, out):
    t = TXT[L]
    levels = t["levels"]
    m2r = [0.21, 1.68, 3.78, 4.59]
    tare = [None, 0.24, 1.72, 3.18]
    x = np.arange(4)
    w = 0.36
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    ax.bar(x - w / 2 - 0.01, m2r, w, color=BLUE, label=t["m2r"])
    ax.bar(x[1:] + w / 2 + 0.01, tare[1:], w, color=AQUA, label=t["tare"])
    for xi, v in zip(x, m2r):
        ax.text(xi - w / 2, v + 0.08, f"{v:.2f}", ha="center", fontsize=9, color=INK)
    for xi, v in zip(x[1:], tare[1:]):
        ax.text(xi + w / 2, v + 0.08, f"{v:.2f}", ha="center", fontsize=9, color=INK)
    ax.axhline(0.5, color=ORANGE, lw=1.5, ls="--")
    ax.text(3.62, 0.62, t["thr"], color=INK, fontsize=9, ha="right")
    ax.set_xticks(x, levels)
    ax.set_ylabel(t["sy"])
    ax.set_title(t["stitle"], fontsize=11)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.grid(axis="y", color=GRID, lw=0.6)
    fig.savefig(os.path.join(out, "fig_sensor.png"))
    plt.close(fig)


if __name__ == "__main__":
    for L in TXT:
        out = os.path.join(HERE, L)
        os.makedirs(out, exist_ok=True)
        fig_field(L, out)
        fig_delay(L, out)
        fig_contact(L, out)
        fig_sensor(L, out)
