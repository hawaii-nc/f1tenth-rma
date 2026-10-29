"""Env plumbing + E-series harness, against the fake simulator."""
from pathlib import Path

import numpy as np
import pytest
import yaml

from f1tenth_research.envs import F1TenthRMAEnv
from f1tenth_research.eval.harness import (
    Belief, Blind, Oracle, Phi, load_policy_pair, run_episode, summarize,
)
from fake_sim import FakeSim

REPO = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((REPO / 'configs/final_phase2_crashtol.yaml').read_text())


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(F1TenthRMAEnv, 'wrapper_factory', staticmethod(FakeSim))
    return F1TenthRMAEnv(config=CFG, max_episode_steps=300)


@pytest.fixture(scope='module')
def policy():
    return load_policy_pair(str(REPO / 'checkpoints/final/phase1_v42.pt'),
                            str(REPO / 'checkpoints/final/phase2_crashtol_clean.pt'))


def test_observation_matches_final_checkpoint(env):
    obs, info = env.reset(seed=0)
    assert obs.shape == (113,)
    assert info['track'] in CFG['environment']['tracks']
    assert info['physics_vector'].shape == (7,)
    assert env.max_velocity == 3.0
    obs, *_ = env.step(np.array([0.0, 1.0]))
    assert obs[2] == pytest.approx(3.0)            # v_des uses max_velocity, not 8.0
    assert ((obs[5:] >= 0) & (obs[5:] <= 1)).all()


def test_forced_disturbance_reaches_simulator(env):
    env.reset(seed=0, options={'physics_params': {'grip_factor': 1.0}, 'disturbance_step': 10,
                               'disturbance_grip': 0.3, 'track': 'aut_tight'})
    for t in range(1, 15):
        _, _, _, _, info = env.step(np.array([0.0, 0.0]))
        if t < 10:
            assert info['physics_params']['grip_factor'] == 1.0
    assert info['physics_params']['grip_factor'] == pytest.approx(0.3)
    assert env.base_env.mu == pytest.approx(1.0489 * 0.3)    # the sim's μ really changed


def test_sampled_disturbance_fires_at_most_once(env):
    hits = 0
    for seed in range(30):
        _, info = env.reset(seed=seed)
        fired = 0
        for _ in range(env.max_episode_steps):
            *_, term, trunc, step_info = env.step(np.array([0.0, -0.5]))
            fired += step_info['disturbance_fired']
            if term or trunc:
                break
        assert fired <= 1
        hits += fired
    assert hits > 0


def test_forced_physics_override(env):
    _, info = env.reset(options={'physics_params': {'grip_factor': 0.4}, 'track': 'aut_tight'})
    p = info['physics_params']
    assert p['grip_factor'] == 0.4 and p['mass_scale'] == 1.0 and p['delay_drive'] == 0.0
    assert info['disturbance_step'] is None


def test_harness_controllers_run(env, policy):
    ac, phi, _ = policy
    results = []
    for ctrl in (Oracle(ac), Blind(ac), Phi(ac, phi), Belief(ac, 0.2)):
        for grip in (1.0, 0.4):
            results.append(run_episode(env, ac, ctrl, grip, seed=0, track='aut_tight', max_steps=120))
    rows = summarize(results)
    assert {r['controller'] for r in rows} == {'oracle', 'blind', 'phi', 'belief_0.2'}
    assert all(0.0 <= r['crash_rate'] <= 1.0 for r in rows)


def test_paired_episodes_are_deterministic(env, policy):
    ac, _, _ = policy
    a = run_episode(env, ac, Blind(ac), 0.6, seed=3, track='aut_tight', max_steps=100, keep_trace=True)
    b = run_episode(env, ac, Blind(ac), 0.6, seed=3, track='aut_tight', max_steps=100, keep_trace=True)
    assert a.trace['steer'] == b.trace['steer']
