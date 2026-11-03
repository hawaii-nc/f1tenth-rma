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


def test_eval_episodes_differ_by_seed_but_pair_across_controllers(monkeypatch):
    """Pseudo-replication fix: seeds must give distinct starts; controllers share them."""
    from f1tenth_research.eval import harness
    seen = []
    monkeypatch.setattr(harness, 'EVAL_SPAWN', 'random')
    fracs = [harness.spawn_frac_for(s) for s in range(50)]
    assert len(set(fracs)) == 50 and all(0 <= f < 1 for f in fracs)
    assert harness.spawn_frac_for(7) == harness.spawn_frac_for(7)

    class Stop(Exception):
        pass

    class Env:
        max_episode_steps = 1
        def reset(self, seed=None, options=None):
            seen.append(options.get('spawn_frac'))
            raise Stop
    for s in (0, 0, 1):
        with pytest.raises(Stop):
            harness.run_episode(Env(), None, harness.Controller(), 1.0, seed=s)
    assert seen[0] == seen[1] != seen[2]
    monkeypatch.setattr(harness, 'EVAL_SPAWN', 'start')
    with pytest.raises(Stop):
        harness.run_episode(Env(), None, harness.Controller(), 1.0, seed=0)
    assert seen[-1] is None


def test_speed_cap_clips_command():
    from f1tenth_research.envs import F1TenthRMAEnv
    from fake_sim import FakeSim
    F1TenthRMAEnv.wrapper_factory = staticmethod(FakeSim)
    try:
        env = F1TenthRMAEnv(config={'environment': {'speed_cap': 1.2, 'max_velocity': 3.0, 'tracks': ['aut']}})
        env.reset(options={'training': False, 'track': 'aut'})
        _, _, _, _, info = env.step(np.array([0.0, 1.0], dtype=np.float32))
        assert info['velocity_cmd'] == pytest.approx(1.2)
    finally:
        F1TenthRMAEnv.wrapper_factory = None


def test_probe_pulses_on_straights_only():
    """Amendment 6: the active grip probe adds `amplitude` to the command for
    duration_steps every period_steps, only while |steer| < max_steer."""
    from f1tenth_research.envs import F1TenthRMAEnv
    from fake_sim import FakeSim
    F1TenthRMAEnv.wrapper_factory = staticmethod(FakeSim)
    try:
        env = F1TenthRMAEnv(config={'environment': {
            'max_velocity': 3.0, 'tracks': ['aut'], 'speed_cap': 1.0,
            'probe': {'period_steps': 10, 'duration_steps': 3, 'amplitude': 2.0, 'max_steer': 0.15}}})
        env.reset(options={'training': False, 'track': 'aut'})
        cmds, flags = [], []
        for t in range(20):
            steer = 0.3 if t >= 10 else 0.0
            _, _, _, _, info = env.step(np.array([steer, 1.0], dtype=np.float32))
            cmds.append(info['velocity_cmd']); flags.append(info['probing'])
        # episode_step = t + 1. Pulse when step % 10 < 3: steps 1, 2 (t = 0, 1) and
        # 10 (t = 9, still straight); steps 11, 12 and 20 come with steer 0.3
        assert flags[:3] == [True, True, False] and flags[9]
        assert cmds[0] == pytest.approx(3.0)      # cap 1.0, plus the 2.0 pulse
        assert not any(flags[10:])
        assert all(c == pytest.approx(1.0) for c, f in zip(cmds, flags) if not f)
    finally:
        F1TenthRMAEnv.wrapper_factory = None
