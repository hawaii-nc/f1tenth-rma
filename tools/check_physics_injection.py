#!/usr/bin/env python3
"""
Pre-flight check on the REAL f110_gym (run it on the lab machine / Docker
image before any retraining). Verifies, in the simulator itself rather than
in our Python dicts, that:

  1. the forced mid-episode grip drop reaches the simulated car's μ (bug C1),
  2. the drop changes the car's motion (yaw rate diverges from a no-drop run),
  3. the requested tire model is the one f110_gym is integrating.

    python tools/check_physics_injection.py --track aut_tight
    python tools/check_physics_injection.py --track aut_tight --tire-model friction_circle

Exits non-zero on any failure.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src' / 'f1tenth_research'))

from f1tenth_research.envs import F1TenthRMAEnv  # noqa: E402

MU_NOMINAL = 1.0489


def run(cfg, track, drop_step, drop_grip, steps, steer, speed, drop=True):
    env = F1TenthRMAEnv(config=cfg, track=track)
    if env.base_env is None:
        sys.exit(f'FAIL: no simulator for {track!r}: f110_gym is missing (run inside the Docker image) '
                 f'or the map is not prepared (python tools/prepare_tracks.py).')
    throttle = 2.0 * speed / env.max_velocity - 1.0
    opts = {'training': False, 'physics_params': {'grip_factor': 1.0},
            'disturbance_step': drop_step if drop else -1, 'disturbance_grip': drop_grip,
            'obs_noise': False}
    env.reset(seed=0, options=opts)
    agent = env.base_env.env.sim.agents[0]
    yaw, mus = [], []
    for _ in range(steps):
        _, _, term, trunc, info = env.step(np.array([steer, throttle], dtype=np.float32))
        yaw.append(info['yaw_rate'])
        mus.append(float(agent.params['mu']))
        if term or trunc:
            break
    import f110_gym.envs.base_classes as bc
    dyn = bc.vehicle_dynamics_st
    env.close()
    return np.array(yaw), np.array(mus), dyn


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', default=str(REPO / 'configs' / 'final_phase2_crashtol.yaml'))
    ap.add_argument('--track', default='aut_tight')
    ap.add_argument('--tire-model', default='linear', choices=['linear', 'friction_circle'])
    ap.add_argument('--drop-step', type=int, default=30)
    ap.add_argument('--drop-grip', type=float, default=0.4)
    ap.add_argument('--steps', type=int, default=45)
    ap.add_argument('--steer', type=float, default=0.05)
    ap.add_argument('--speed', type=float, default=2.0)
    a = ap.parse_args()

    with open(a.config) as f:
        cfg = yaml.safe_load(f)
    cfg['environment']['tire_model'] = a.tire_model

    yaw_d, mu_d, dyn = run(cfg, a.track, a.drop_step, a.drop_grip, a.steps, a.steer, a.speed, drop=True)
    yaw_c, mu_c, _ = run(cfg, a.track, a.drop_step, a.drop_grip, a.steps, a.steer, a.speed, drop=False)
    ok = True

    n = min(len(yaw_d), len(yaw_c))
    if n <= a.drop_step + 5:
        print(f'FAIL: episode ended after {n} steps, before the drop could be checked. '
              f'Try a smaller --steer/--speed or another --track.')
        sys.exit(1)

    before, after = mu_d[a.drop_step - 2], mu_d[-1]
    expect = MU_NOMINAL * a.drop_grip
    print(f'[1] simulator mu: before drop {before:.4f}, after {after:.4f} (expected {expect:.4f}); '
          f'control run stays at {mu_c[-1]:.4f}')
    if not (abs(before - MU_NOMINAL) < 1e-6 and abs(after - expect) < 1e-6 and abs(mu_c[-1] - MU_NOMINAL) < 1e-6):
        print('    FAIL: the grip drop did not reach f110_gym (bug C1 is back)')
        ok = False

    pre = np.max(np.abs(yaw_d[:a.drop_step - 1] - yaw_c[:a.drop_step - 1]))
    post = np.max(np.abs(yaw_d[a.drop_step:n] - yaw_c[a.drop_step:n]))
    print(f'[2] |yaw-rate difference| vs no-drop run: before {pre:.2e} rad/s, after {post:.3f} rad/s')
    if pre > 1e-6 or post < 1e-3:
        print('    FAIL: runs should match before the drop and diverge after it')
        ok = False

    from f1tenth_research.envs import tire_models
    import f110_gym.envs.dynamic_models as dm
    want = dm.vehicle_dynamics_st if a.tire_model == 'linear' else tire_models.vehicle_dynamics_st_friction_circle
    print(f'[3] f110_gym integrates: {getattr(dyn, "__name__", dyn)} (requested {a.tire_model})')
    if dyn is not want:
        print('    FAIL: wrong tire model installed')
        ok = False

    print('PASS' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
