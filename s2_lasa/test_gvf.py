"""Unit tests of the sphere geometry and of the field. Run: python test_gvf.py"""
import numpy as np
import gvf_s2 as g

rng = np.random.default_rng(0)


def tangent(x):
    v = rng.normal(size=x.shape)
    return v - np.sum(v * x, -1, keepdims=True) * x


def test_exp_log():
    x = g.normalize(rng.normal(size=(200, 3)))
    v = tangent(x)
    v = v / np.linalg.norm(v, axis=1, keepdims=True) * rng.uniform(0.01, 2.5, (200, 1))
    assert np.abs(g.log_map(x, g.exp_map(x, v)) - v).max() < 1e-9


def test_transport_isometry_and_geodesic_velocity():
    a = g.normalize(rng.normal(size=(200, 3)))
    b = g.normalize(a + 0.7 * rng.normal(size=(200, 3)))
    v = tangent(a)
    w = g.transport(a, b, v)
    assert np.abs(np.linalg.norm(w, axis=1) - np.linalg.norm(v, axis=1)).max() < 1e-9
    assert np.abs(np.sum(w * b, 1)).max() < 1e-9
    # The geodesic's own velocity is parallel: Gamma(log_a b) = -log_b a.
    assert np.abs(g.transport(a, b, g.log_map(a, b)) + g.log_map(b, a)).max() < 1e-9


def test_nearest_against_brute_force():
    curve, dt = g.map_shape("Sshape")
    f = g.Field(curve[0], dt[0])
    dense = np.concatenate(
        [g.normalize((1 - t) * f.a[::5] + t * f.b[::5]) for t in np.linspace(0, 1, 6)]
    )
    dense = np.concatenate([dense, f.x])
    x = g.exp_map(f.x[::50], 0.3 * tangent(f.x[::50]))
    D, c, m, s = f.nearest(x)
    brute = g.dist(x[:, None], dense[None]).min(1)
    assert (D <= brute + 1e-9).all()
    assert np.abs(D - brute).max() < 1e-3
    assert np.abs(np.sum(c * x, 1)).max() < 1e-9
    assert np.abs(np.sum(m * x, 1)).max() < 1e-9
    assert (s >= 0).all() and (s <= 1).all()


def test_on_curve_recovers_demo():
    curve, dt = g.map_shape("GShape")
    f = g.Field(curve[0], dt[0])
    D, c, m, s = f.nearest(f.x[100:900:37])
    assert D.max() < 1e-6
    assert np.abs(m - f.vel[100:900:37]).max() < 1e-6
    assert np.abs(s - f.cum[100:900:37] / f.length).max() < 1e-9


def test_dtw_frechet():
    curve, dt = g.map_shape("Angle")
    a = g.resample(curve[0], 60)
    b = g.resample(curve[1], 60)
    assert g.dtw(a, a) < 1e-6 and g.frechet(a, a) < 1e-6
    assert abs(g.dtw(a, b) - g.dtw(b, a)) < 1e-9
    assert abs(g.frechet(a, b) - g.frechet(b, a)) < 1e-9
    assert g.dtw(a, b) <= g.frechet(a, b) + 1e-9


def test_all_shapes_load():
    assert len(g.SHAPES) == 26
    for n in g.SHAPES:
        c, dt = g.map_shape(n)
        assert c.shape == (7, 1000, 3)
        assert np.abs(np.linalg.norm(c, axis=-1) - 1).max() < 1e-9
        # Same goal across demos, as LASA defines it.
        assert g.dist(c[:, -1], c[0, -1][None]).max() < 1e-3


for k, fn in list(globals().items()):
    if k.startswith("test_"):
        fn()
        print("ok", k)
