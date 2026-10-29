import numpy as np
import pytest

from f1tenth_research.metrics import calibration_gaps, cross_grip_swing, utilization, cv_r2, fit_ridge, r2_score

GRIPS = [1.0, 0.8, 0.6, 0.4]
# Poster risk-calibration table (N=100 per cell)
POSTER = {
    'oracle': dict(zip(GRIPS, [0.102, 0.119, 0.142, 0.185])),
    'phi': dict(zip(GRIPS, [0.094, 0.116, 0.154, 0.215])),
    'blind': dict(zip(GRIPS, [0.102, 0.126, 0.166, 0.239])),
}


def test_rho_definition():
    # 2 m/s on a 1 m radius circle: a_lat = v²/r = 4 = v·ω with ω = 2
    assert utilization(2.0, 2.0, 0.0, 1.0) == pytest.approx(4.0 / 9.81)
    assert utilization(1.0, 0.0, 3.0, 0.5) == pytest.approx(3.0 / (0.5 * 9.81))


def test_poster_gap_closure_is_44_percent():
    gaps = calibration_gaps(POSTER)
    assert gaps['phi_gap'][0.4] == pytest.approx(0.030)
    assert gaps['blind_gap'][0.4] == pytest.approx(0.054)
    assert gaps['gap_closed'][0.4] == pytest.approx(0.444, abs=1e-3)


def test_poster_cross_grip_variance_ratio():
    ratio = cross_grip_swing(POSTER['blind'], GRIPS) / cross_grip_swing(POSTER['phi'], GRIPS)
    # Reported 1.25–1.27× across N = 20/40/100; the rounded N=100 table gives 1.28
    assert 1.2 < ratio < 1.35


def test_probe_recovers_linear_signal_and_grouped_cv():
    rng = np.random.default_rng(0)
    groups = np.repeat(np.arange(50), 20)
    grip = rng.uniform(0.2, 1.0, 50)[groups]
    X = np.column_stack([3 * grip + 0.01 * rng.normal(size=grip.size), rng.normal(size=grip.size)])
    assert cv_r2(X, grip, groups=groups) > 0.99
    noise = rng.normal(size=(grip.size, 3))
    assert cv_r2(noise, grip, groups=groups) < 0.1
    probe = fit_ridge(X, grip)
    assert r2_score(grip, probe.predict(X)) > 0.99
