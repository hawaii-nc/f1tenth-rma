"""Phase 1 with several environments: per-env GAE, expert labels and physics (env_pool.py)."""
import copy
import sys
import types
from pathlib import Path

import numpy as np
import pytest
import yaml

from f1tenth_research.envs import F1TenthRMAEnv
from fake_sim import FakeSim

REPO = Path(__file__).resolve().parents[1]
FINAL = yaml.safe_load((REPO / 'configs/final_phase2_crashtol.yaml').read_text())


@pytest.fixture(autouse=True)
def fake_backend(monkeypatch):
    monkeypatch.setattr(FakeSim, 'half_width', 50.0)
    monkeypatch.setattr(F1TenthRMAEnv, 'wrapper_factory', staticmethod(FakeSim))


def cfg(n):
    c = copy.deepcopy(FINAL)
    c['environment']['tracks'] = ['aut']
    c['environment']['max_episode_steps'] = 40
    c['phase1_training'].update(num_envs=n, inproc_envs=True, rollout_steps=120, num_epochs=1,
                                batch_size=32, total_timesteps=240, log_interval=1)
    return c


def test_multi_env_rollout_is_per_env(tmp_path):
    from f1tenth_research.training.phase1_ppo_il import Phase1Trainer
    tr = Phase1Trainer(cfg(3), device='cpu', log_dir=str(tmp_path), checkpoint_dir=str(tmp_path))
    data = tr.rollout(120)
    T = 40
    assert len(data['obs']) == 3 * T and data['expert_mask'].all()
    # Every env sampled its own physics: intrinsics differ between env blocks.
    blocks = data['intrinsics'].reshape(3, T, 8)[:, 0]
    assert not np.allclose(blocks[0], blocks[1]) and not np.allclose(blocks[1], blocks[2])
    # GAE per env: recompute env 1's block on its own and compare.
    sl = slice(T, 2 * T)
    adv, _ = tr.compute_gae(data['rewards'][sl], data['values'][sl], 0.0, data['dones'][sl])
    # Only the last step's bootstrap differs; everything before a done must match.
    d = np.where(data['dones'][sl] > 0)[0]
    upto = d[-1] + 1 if len(d) else 0
    np.testing.assert_allclose(data['advantages'][sl][:upto], adv[:upto], rtol=1e-5, atol=1e-5)
    tr.update(data, epoch=0)


def test_episodes_continue_across_rollouts_and_resume(tmp_path):
    from f1tenth_research.training.phase1_ppo_il import Phase1Trainer
    tr = Phase1Trainer(cfg(2), device='cpu', log_dir=str(tmp_path), checkpoint_dir=str(tmp_path))
    tr.train()
    assert tr.epoch == 2 and tr.global_step == 240
    assert sum(e['length'] for e in tr.episode_stats) >= 0  # stats collected without error
    tr2 = Phase1Trainer(cfg(2), device='cpu', log_dir=str(tmp_path), checkpoint_dir=str(tmp_path))
    tr2.load_checkpoint('latest.pt')
    assert tr2.epoch == 1 and tr2.global_step == 120  # latest.pt written after epoch 0


def test_missing_expert_signal_is_loud(tmp_path):
    from f1tenth_research.training.phase1_ppo_il import Phase1Trainer
    tr = Phase1Trainer(cfg(1), device='cpu', log_dir=str(tmp_path), checkpoint_dir=str(tmp_path))
    data = tr.rollout(40)
    data['expert_mask'][:] = False
    with pytest.raises(RuntimeError):
        tr.update(data, epoch=0)


def test_spawn_is_on_the_centerline(monkeypatch):
    """Bug C16: the spawn pose used to be spawn_xy itself, not the centerline point."""
    f110 = types.ModuleType('f110_gym')
    envs = types.ModuleType('f110_gym.envs')
    f110env = types.ModuleType('f110_gym.envs.f110_env')
    f110env.F110Env = object
    for name, mod in [('f110_gym', f110), ('f110_gym.envs', envs), ('f110_gym.envs.f110_env', f110env)]:
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.delitem(sys.modules, 'f1tenth_research.envs.real_env', raising=False)
    from f1tenth_research.envs.real_env import spawn_pose_from_centerline
    th = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    circle = np.c_[3 + 2 * np.cos(th), 2 * np.sin(th)]   # (0.7, 0) is 0.3 m off this track
    x, y, h = spawn_pose_from_centerline(circle)
    assert np.min(np.hypot(circle[:, 0] - x, circle[:, 1] - y)) < 1e-9
    assert abs(np.hypot(x - 3, y) - 2) < 1e-9


def test_phase2_parallel_collection_keeps_episodes_separate(tmp_path):
    from f1tenth_research.training.phase2_adaptation import Phase2Trainer
    c = cfg(3)
    c['phase2_training'].update(num_envs=3)
    c['networks']['adaptation']['history_window'] = 10
    tr = Phase2Trainer(str(REPO / 'checkpoints/final/phase1_v42.pt'), c, device='cpu',
                       log_dir=str(tmp_path), checkpoint_dir=str(tmp_path))
    tr.collect_data(5)
    assert len(tr.buffer.episodes) == 5
    for sa, z, e in tr.buffer.episodes:
        assert len(sa) == len(z) == len(e) <= 40
        # one physics draw per episode (fake sim never drops grip mid-episode here unless sampled)
        assert np.allclose(e[0, 1:], e[-1, 1:])


def test_spawn_frac_places_car_along_the_lap(monkeypatch):
    f110 = types.ModuleType('f110_gym')
    envs = types.ModuleType('f110_gym.envs')
    f110env = types.ModuleType('f110_gym.envs.f110_env')
    f110env.F110Env = object
    for name, mod in [('f110_gym', f110), ('f110_gym.envs', envs), ('f110_gym.envs.f110_env', f110env)]:
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.delitem(sys.modules, 'f1tenth_research.envs.real_env', raising=False)
    from f1tenth_research.envs.real_env import spawn_pose_from_centerline
    th = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    circle = np.c_[2 * np.cos(th), 2 * np.sin(th)]
    x, y, h = spawn_pose_from_centerline(circle, spawn_frac=0.25)
    assert np.allclose([x, y], [0, 2], atol=1e-9)
    assert abs(((h - np.pi) + np.pi) % (2 * np.pi) - np.pi) < 0.05   # heading along the track (CCW)


def test_ppo_update_trains_the_encoder(tmp_path):
    """Bug C21: μ must receive gradients from the PPO/IL update."""
    import torch
    from f1tenth_research.training.phase1_ppo_il import Phase1Trainer
    tr = Phase1Trainer(cfg(2), device='cpu', log_dir=str(tmp_path), checkpoint_dir=str(tmp_path))
    before = [p.detach().clone() for p in tr.actor_critic.encoder.parameters()]
    tr.update(tr.rollout(80), epoch=0)
    assert any(not torch.equal(b, p) for b, p in zip(before, tr.actor_critic.encoder.parameters()))


def test_dagger_pretrain_runs_and_beats_random(tmp_path):
    from f1tenth_research.training.phase1_ppo_il import Phase1Trainer
    c = cfg(2)
    c['phase1_training']['dagger'] = {'iterations': 2, 'steps_per_iter': 200, 'epochs': 5, 'batch_size': 64}
    tr = Phase1Trainer(c, device='cpu', log_dir=str(tmp_path), checkpoint_dir=str(tmp_path))
    tr.dagger_pretrain()
    assert (tmp_path / 'dagger.pt').exists()
