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


def test_bootstrap_calibration_brackets_point_estimate_and_keeps_pairing():
    from f1tenth_research.metrics import bootstrap_calibration
    rng = np.random.default_rng(0)
    grips = [1.0, 0.8, 0.6, 0.4]
    n = 100
    # Shared per-episode offset (same seed for every controller) + small noise
    shared = rng.normal(0, 0.03, n)
    eps = {c: {g: POSTER[c][g] + shared + rng.normal(0, 0.003, n) for g in grips} for c in POSTER}
    # At μ = 1.0 Blind's nominal belief is the truth, so it runs the same episodes as Oracle
    eps['blind'][1.0] = eps['oracle'][1.0].copy()
    point = calibration_gaps({c: {g: float(np.mean(eps[c][g])) for g in grips} for c in POSTER})
    boot = bootstrap_calibration(eps, grips, n_boot=500, seed=1)
    lo, hi = boot['gap_closed'][0.4]
    assert lo < point['gap_closed'][0.4] < hi
    # Pairing cancels the large shared offset, so the interval stays narrow
    assert hi - lo < 0.15
    # μ = 1.0: Blind equals Oracle in the poster table, so the gap is undefined
    assert all(np.isnan(boot['gap_closed'][1.0]))


def test_bootstrap_calibration_rejects_unpaired_cells():
    from f1tenth_research.metrics import bootstrap_calibration
    eps = {c: {0.4: np.ones(10), 1.0: np.ones(10)} for c in ('oracle', 'phi', 'blind')}
    eps['phi'][0.4] = np.ones(9)
    with pytest.raises(ValueError):
        bootstrap_calibration(eps, [1.0, 0.4], n_boot=10)
