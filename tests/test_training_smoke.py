"""A few hundred steps of Phase 1 and Phase 2 on the fake simulator: does the loop run end to end?"""
import copy
from pathlib import Path

import pytest
import torch
import yaml

from f1tenth_research.envs import F1TenthRMAEnv
from f1tenth_research.models import load_adaptation
from fake_sim import FakeSim

REPO = Path(__file__).resolve().parents[1]
FINAL = yaml.safe_load((REPO / 'configs/final_phase2_crashtol.yaml').read_text())


@pytest.fixture(autouse=True)
def fake_backend(monkeypatch):
    monkeypatch.setattr(FakeSim, 'half_width', 50.0)
    monkeypatch.setattr(F1TenthRMAEnv, 'wrapper_factory', staticmethod(FakeSim))


def small_config():
    cfg = copy.deepcopy(FINAL)
    cfg['environment']['tracks'] = ['aut']            # ships with a centerline -> expert can be built
    cfg['environment']['max_episode_steps'] = 120
    t = cfg['phase1_training']
    t.update(total_timesteps=600, rollout_steps=300, num_epochs=1, batch_size=64, num_envs=1,
             log_interval=1, track_reweight_interval=10_000)
    cfg['phase2_training'].update(num_eval_episodes=3, num_epochs=1, batch_size=16, buffer_size=10_000)
    cfg['networks']['adaptation']['history_window'] = 20
    return cfg


def test_phase1_runs_and_expert_is_active(tmp_path):
    from f1tenth_research.training.phase1_ppo_il import Phase1Trainer
    trainer = Phase1Trainer(small_config(), device='cpu', log_dir=str(tmp_path / 'logs'),
                            checkpoint_dir=str(tmp_path / 'ckpt'))
    assert trainer.obs_dim == 113
    data = trainer.rollout(200)
    # One expert action per transition: the IL signal actually exists now
    assert len(data['expert_actions']) == len(data['obs']) > 0
    trainer.update(data, epoch=0)
    trainer.save_checkpoint('smoke.pt')
    ck = torch.load(tmp_path / 'ckpt' / 'smoke.pt', map_location='cpu', weights_only=True)
    assert ck['actor_critic']['policy.network.0.weight'].shape == (256, 121)


def test_phase2_runs_from_final_phase1(tmp_path):
    from f1tenth_research.training.phase2_adaptation import Phase2Trainer
    cfg = small_config()
    trainer = Phase2Trainer(str(REPO / 'checkpoints/final/phase1_v42.pt'), cfg, device='cpu',
                            log_dir=str(tmp_path / 'logs'), checkpoint_dir=str(tmp_path / 'ckpt'))
    trainer.collect_data(3)
    assert len(trainer.buffer) > 0
    trainer.train_epoch(num_epochs=1, batch_size=16)
    trainer.save_checkpoint('phi.pt')
    phi, _ = load_adaptation(str(tmp_path / 'ckpt' / 'phi.pt'))
    assert phi.history_window == 20 and phi.state_action_dim == 115
