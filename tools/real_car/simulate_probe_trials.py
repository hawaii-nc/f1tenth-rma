#!/usr/bin/env python3
"""
Simulated Stage 1: the same maneuver as probe_maneuver_node.py, in f1tenth_gym with
the friction-circle tire and the car sensor model (sensors.model = car), written
in the same CSV format. Two uses:
  1. validate analyze_probe_trials.py (the surfaces here have known grip), and
  2. a prediction to compare the real car's numbers against.
The car is held on a straight of the IMS oval by Pure Pursuit steering; the
speed command follows the maneuver. Other physics (mass, motor gains, delays) are
drawn from the training range per trial, as are the odometry gain errors.

    python tools/real_car/simulate_probe_trials.py --grips 1.0 0.7 0.4 --trials 20 --out sim_probe_trials.csv
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'experiments'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--grips', type=float, nargs='+', default=[1.0, 0.7, 0.4])
    ap.add_argument('--trials', type=int, default=20)
    ap.add_argument('--cruise', type=float, default=1.5)
    ap.add_argument('--amplitude', type=float, default=-1.0)
    ap.add_argument('--cruise_s', type=float, default=1.5)
    ap.add_argument('--pulse_s', type=float, default=0.1)
    ap.add_argument('--recover_s', type=float, default=1.0)
    ap.add_argument('--imu_noise', type=float, default=0.3, help='m/s^2 noise on the simulated IMU')
    ap.add_argument('--config', default=str(REPO / 'configs/real_phase2_probe.yaml'))
    ap.add_argument('--track', default='ims_tight')
    ap.add_argument('--spawn_frac', type=float, default=None, help='default: search for a straight')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    from _common import load_config
    from f1tenth_research.envs import F1TenthRMAEnv
    from f1tenth_research.envs.randomization import PhysicsRandomizer, PARAM_KEYS
    from f1tenth_research.eval.harness import physics_for
    from f1tenth_research.training.env_pool import create_experts, expert_action
    cfg = load_config(a.config, 'friction_circle')
    cfg['environment'].pop('probe', None)            # the maneuver is the probe here
    cfg['environment']['tracks'] = [a.track]
    cfg['phase1_training'] = {'il': {'use_expert_actions': True}}
    experts = create_experts(cfg)
    env = F1TenthRMAEnv(config=cfg, max_episode_steps=1000)
    dt = 0.01
    rng = np.random.default_rng(0)
    randomizer = PhysicsRandomizer(cfg['environment'].get('randomization', {}))

    def run(grip, others, seed, sf, log=None, surface='', trial=0):
        obs, info = env.reset(seed=seed, options={'training': False, 'obs_noise': False, 'disturbance_step': -1,
                                                  'physics_params': physics_for(grip, others), 'track': a.track,
                                                  'spawn_frac': sf})
        T = a.cruise_s + a.pulse_s + a.recover_s
        max_steer = 0.0
        prev_v = info.get('velocity', 0.0) if isinstance(info, dict) else 0.0
        for k in range(int(round(T / dt))):
            t = k * dt
            if t < a.cruise_s:
                phase, v = 'cruise', a.cruise
            elif t < a.cruise_s + a.pulse_s:
                phase, v = 'pulse', max(0.0, a.cruise + a.amplitude)
            else:
                phase, v = 'recover', a.cruise
            steer = float(expert_action(experts, info)[0]) if 'poses_x' in info else 0.0
            max_steer = max(max_steer, abs(steer))
            throttle = 2.0 * v / env.max_velocity - 1.0
            if log is not None:
                scan = env._scan_hold
                front = float(np.median(scan[540 - 20:540 + 21])) if scan is not None else float('nan')
                true_v = info.get('velocity', obs[0])
                ax = (true_v - prev_v) / dt + rng.normal(0, a.imu_noise)
                prev_v = true_v
                log.writerow([f'{t:.4f}', surface, trial, phase, v, float(obs[0]), float(obs[4]), front, ax, float('nan')])
            obs, _, term, trunc, info = env.step(np.array([steer, throttle], np.float32))
            if term:
                return None
        return max_steer

    # Find a spawn point on a straight: Pure Pursuit steering stays small for the whole maneuver
    sf = a.spawn_frac
    if sf is None:
        best = min((run(1.0, None, 0, s) or 9.0, s) for s in np.linspace(0, 0.95, 20))
        sf = best[1]
        print(f'spawn_frac {sf:.2f} (max |steer| {best[0]:.3f} rad)')
    with open(a.out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['t', 'surface', 'trial', 'phase', 'cmd_speed', 'odom_speed', 'odom_yaw_rate',
                    'front_range', 'imu_ax', 'motor_current'])
        for grip in a.grips:
            for i in range(a.trials):
                np.random.seed(1000 * i + int(grip * 100))
                s = randomizer.sample_training()
                others = {k: s[k] for k in PARAM_KEYS if k != 'grip_factor'}
                if run(grip, others, 100 + i, sf, log=w, surface=f'grip_{grip:.1f}', trial=i) is None:
                    print(f'  grip {grip} trial {i}: crashed')
    print(f'-> {a.out}')


if __name__ == '__main__':
    main()
