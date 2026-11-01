"""tools/stats.py helpers against known values."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import stats  # noqa: E402


def test_wilson_matches_reference():
    lo, hi = stats.wilson(5, 10)          # textbook: 0.237, 0.763
    assert lo == pytest.approx(0.2366, abs=1e-3) and hi == pytest.approx(0.7634, abs=1e-3)
    assert stats.wilson(0, 20)[0] == 0.0


def test_mcnemar_exact():
    a = np.array([True] * 10 + [False] * 10)
    b = np.array([False] * 10 + [False] * 10)
    assert stats.mcnemar(a, b) == pytest.approx(2 * 0.5 ** 10)   # 10 discordant, all one way
    assert stats.mcnemar(a, a) == 1.0


def test_holm():
    assert stats.holm(np.array([0.01, 0.04, 0.03])) == pytest.approx([0.03, 0.06, 0.06])


def test_gap_closed():
    assert stats.gap(np.array([0.1]), np.array([0.15]), np.array([0.2])) == pytest.approx(0.5)
