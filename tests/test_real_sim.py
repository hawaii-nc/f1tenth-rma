"""Tests that need the real f110_gym (Docker image / lab machine); skipped otherwise."""
import copy
from pathlib import Path

import numpy as np
import pytest
import yaml

pytest.importorskip('f110_gym')
REPO = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((REPO / 'configs/retrain_phase2.yaml').read_text())


def _maps_ready(*tracks):
    from f1tenth_research.paths import maps_dir
    return all((maps_dir() / f'{t}.yaml').exists() for t in tracks)


@pytest.mark.skipif(not _maps_ready('aut_tight', 'esp_tight'), reason='run tools/prepare_tracks.py')
def test_each_track_raycasts_against_its_own_map():
    """Bug C22: f110_gym's scan simulator is process-wide; a cached env for
    track A must not see track B's map after B was loaded."""
    from f1tenth_research.envs import F1TenthRMAEnv
    opts = {'training': False, 'physics_params': {'grip_factor': 1.0}, 'obs_noise': False, 'disturbance_step': -1}
    fresh = F1TenthRMAEnv(config=copy.deepcopy(CFG), track='aut_tight')
    ref, _ = fresh.reset(seed=0, options=dict(opts, track='aut_tight'))
    env = F1TenthRMAEnv(config=copy.deepcopy(CFG))
    a1, _ = env.reset(seed=0, options=dict(opts, track='aut_tight'))
    env.reset(seed=0, options=dict(opts, track='esp_tight'))       # loads esp's map
    a2, _ = env.reset(seed=0, options=dict(opts, track='aut_tight'))
    np.testing.assert_allclose(a1, ref, atol=0.02)
    np.testing.assert_allclose(a2, ref, atol=0.02)                   # was esp's scan before the fix
    for _ in range(20):                                              # and stepping keeps the right map
        o, _, term, _, _ = env.step(np.array([0.0, 0.0], dtype=np.float32))
        assert not term
