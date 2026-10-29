import numpy as np

from f1tenth_research.envs.randomization import PhysicsRandomizer, SampleMode, PARAM_KEYS, params_to_vector


def test_training_samples_are_physical():
    np.random.seed(0)
    r = PhysicsRandomizer({'apply_post_scale_noise': True, 'noise_fraction': 0.2})
    for _ in range(2000):
        p = r.sample(SampleMode.TRAIN)
        assert 0.05 <= p['grip_factor'] <= 1.0
        assert p['delay_steering'] >= 0 and p['delay_drive'] >= 0
        assert params_to_vector(p).shape == (len(PARAM_KEYS),)


def test_disturbance_is_one_shot_and_non_mutating():
    np.random.seed(1)
    r = PhysicsRandomizer({'mid_episode_disturbance': True, 'disturbance_timing': (0.3, 0.9),
                           'disturbance_friction_scale': 0.7})
    times = [r.sample_disturbance_time() for _ in range(5000)]
    fired = [t for t in times if t is not None]
    assert 0.25 < len(fired) / len(times) < 0.35          # 30% of episodes
    assert all(0.3 <= t <= 0.9 for t in fired)
    p = {'grip_factor': 0.8}
    q = r.apply_disturbance(p)
    assert q['grip_factor'] == 0.8 * 0.7 and p['grip_factor'] == 0.8


def test_disturbance_disabled():
    r = PhysicsRandomizer({'mid_episode_disturbance': False})
    assert all(r.sample_disturbance_time() is None for _ in range(100))
