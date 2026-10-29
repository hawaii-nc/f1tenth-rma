"""Every shipped checkpoint loads with weights_only=True and runs a forward pass."""
from pathlib import Path

import pytest
import torch
import yaml

from f1tenth_research.models import load_actor_critic, load_adaptation

REPO = Path(__file__).resolve().parents[1]
CKPTS = sorted((REPO / 'checkpoints').glob('*/*.pt'))


def _kind(path):
    return 'adaptation' if 'adaptation' in torch.load(path, map_location='cpu', weights_only=True) else 'actor_critic'


@pytest.mark.parametrize('path', CKPTS, ids=lambda p: p.name)
def test_loads_and_runs(path):
    if _kind(path) == 'actor_critic':
        model, cfg = load_actor_critic(str(path))
        obs = torch.zeros(1, model.policy.obs_dim)
        z = model.get_intrinsics(torch.tensor([[1.0, 1, 1, 1, 1, 0, 0]]))
        mean, log_std = model.policy(obs, z)
        assert mean.shape == (1, 2) and log_std.shape[-1] == 2
    else:
        phi, cfg = load_adaptation(str(path))
        z = phi(torch.zeros(1, phi.history_window, phi.state_action_dim))
        assert z.shape == (1, 8)


def test_final_pair_is_compatible():
    ac, cfg1 = load_actor_critic(str(REPO / 'checkpoints/final/phase1_v42.pt'))
    phi, cfg2 = load_adaptation(str(REPO / 'checkpoints/final/phase2_crashtol_clean.pt'))
    assert ac.policy.obs_dim == 113
    assert phi.state_action_dim == 113 + 2
    assert phi.history_window == 50 == cfg2['networks']['adaptation']['history_window']
    assert cfg1['environment']['observation']['lidar_beams'] == 108
    assert cfg1['environment']['max_velocity'] == 3.0


def test_exported_configs_match_checkpoints():
    for ck, yml in (('final/phase1_v42.pt', 'final_phase1_v42.yaml'),
                    ('final/phase2_crashtol_clean.pt', 'final_phase2_crashtol.yaml')):
        cfg = torch.load(REPO / 'checkpoints' / ck, map_location='cpu', weights_only=True)['config']
        assert yaml.safe_load((REPO / 'configs' / yml).read_text()) == cfg
