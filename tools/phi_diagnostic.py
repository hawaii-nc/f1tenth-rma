#!/usr/bin/env python3
"""
Why can't φ read grip? Separates "the information is not in the history"
from "φ fails to learn it".

collect: roll out the base policy at a random true grip (uniform 0.2-1.0;
other physics from the training range, no mid-episode drop) with one of
three grip beliefs:
  oracle  - the true grip (training data of the oracle round; actions leak grip)
  phi     - φ's own estimate (deployment; φ given by --phase2)
  belief  - a random grip, independent of the true one (no action leakage)
Saves every episode's (obs, action) sequence plus true and believed grip.

train: fit a grip regressor (AdaptationModule CNN, scalar output) on one
dataset and report held-out R² (split by episode) on each dataset, for
several input variants: all 115 channels or proprioception only (v, δ,
v_des, δ_des, yaw rate, 2 actions), window k, stride.

    python tools/phi_diagnostic.py collect --mode belief --episodes 240 --out diag/belief.npz
    python tools/phi_diagnostic.py train diag/belief.npz diag/phi.npz --train-on 0
"""
import argparse
import multiprocessing as mp
import os
import sys
from pathlib import Path

import numpy as np

PROPRIO = [0, 1, 2, 3, 4]  # v, steering, v_des, steering_des, yaw_rate (actions appended last)


def _collect_worker(args, wid, n, q):
    os.environ.setdefault('OMP_NUM_THREADS', '1')
    import torch
    torch.set_num_threads(1)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
    from _common import load_config
    from f1tenth_research.eval import harness
    from f1tenth_research.eval.harness import physics_for, load_policy_pair, make_env
    from f1tenth_research.envs.randomization import PhysicsRandomizer, PARAM_KEYS, NOMINAL_PARAMS

    cfg = load_config(args.config, args.tire_model)
    if args.car_sensors:
        cfg['environment']['sensors'] = {'model': 'car'}
    if args.probe:
        cfg['environment']['probe'] = {'period_steps': args.probe[0], 'duration_steps': args.probe[1],
                                       'amplitude': args.probe[2], 'max_steer': args.probe[3]}
    ac, phi, _ = load_policy_pair(args.phase1, args.phase2)
    env = make_env(cfg, args.max_steps)
    tracks = cfg['environment']['tracks']
    randomizer = PhysicsRandomizer(cfg['environment'].get('randomization', {}))
    k = phi.history_window if phi is not None else 0
    out = []
    with torch.no_grad():
        for j in range(n):
            ep = wid + j * args.workers
            rng = np.random.default_rng([args.seed, ep])
            grip = float(rng.uniform(0.2, 1.0))
            belief = float(rng.uniform(0.2, 1.0))
            np.random.seed(args.seed * 1000 + ep)
            s = randomizer.sample_training()
            others = {key: s[key] for key in PARAM_KEYS if key != 'grip_factor'}
            opts = {'training': False, 'obs_noise': True, 'disturbance_step': -1,
                    'physics_params': physics_for(grip, others), 'track': tracks[ep % len(tracks)],
                    'spawn_frac': harness.spawn_frac_for(args.seed + ep)}
            obs, info = env.reset(seed=args.seed + ep, options=opts)
            e_true = torch.as_tensor(info['physics_vector'], dtype=torch.float32)
            e_bel = e_true.clone(); e_bel[0] = belief
            z_nom = ac.get_intrinsics(torch.tensor(NOMINAL_PARAMS, dtype=torch.float32))
            seq = []
            for t in range(args.max_steps):
                if args.mode == 'oracle':
                    z = ac.get_intrinsics(e_true)
                elif args.mode == 'belief':
                    z = ac.get_intrinsics(e_bel)
                else:
                    z = phi(torch.as_tensor(np.asarray(seq[-k:], np.float32)).unsqueeze(0)).squeeze(0) \
                        if len(seq) >= k else z_nom
                mean, _ = ac.policy(torch.as_tensor(obs, dtype=torch.float32), z)
                a = mean.numpy()
                seq.append(np.concatenate([obs, a]).astype(np.float32))
                obs, _, term, trunc, info = env.step(a)
                if term or trunc or info.get('collision'):
                    break
            out.append((np.asarray(seq, np.float16), grip, belief, bool(info.get('collision'))))
    q.put(out)


def collect(args):
    per = [len(range(w, args.episodes, args.workers)) for w in range(args.workers)]
    q = mp.get_context('spawn').Queue()
    procs = [mp.get_context('spawn').Process(target=_collect_worker, args=(args, w, per[w], q))
             for w in range(args.workers)]
    for p in procs:
        p.start()
    eps = [e for _ in procs for e in q.get()]
    crash = np.array([c for *_, c in eps]); eps = [e[:3] for e in eps]
    for p in procs:
        p.join()
    lens = np.array([len(s) for s, _, _ in eps])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out, sa=np.concatenate([s for s, _, _ in eps]), lens=lens,
                        grip=np.array([g for _, g, _ in eps]), belief=np.array([b for _, _, b in eps]), crash=crash)
    v = np.concatenate([s[:, 0] for s, _, _ in eps]).astype(np.float32)
    print(f'{args.mode}: {len(eps)} episodes, {lens.sum()} steps (median {int(np.median(lens))}), '
          f'mean v {v.mean():.3f}, crash rate {crash.mean():.3f} -> {args.out}')


def load(path):
    d = np.load(path)
    sa = d['sa'].astype(np.float32)
    starts = np.concatenate([[0], np.cumsum(d['lens'])[:-1]])
    return [sa[s:s + n] for s, n in zip(starts, d['lens'])], d['grip'].astype(np.float32)


def windows(eps, grips, ids, k, stride, chans, n, rng):
    """n random windows (k steps spaced by stride) from episodes ids."""
    span = (k - 1) * stride + 1
    ok = [i for i in ids if len(eps[i]) >= span]
    w = np.array([len(eps[i]) - span + 1 for i in ok], float)
    pick = rng.choice(len(ok), size=n, p=w / w.sum())
    X = np.empty((n, k, len(chans)), np.float32); y = np.empty(n, np.float32)
    for j, p in enumerate(pick):
        i = ok[p]
        s = rng.integers(0, len(eps[i]) - span + 1)
        X[j] = eps[i][s:s + span:stride][:, chans]
        y[j] = grips[i]
    return X, y


def train(args):
    import torch
    from torch import nn
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'f1tenth_research'))
    from f1tenth_research.models import AdaptationModule
    torch.set_num_threads(args.threads)
    data = [load(p) for p in args.data]
    names = [Path(p).stem for p in args.data]
    D = data[0][0][0].shape[1]
    variants = {'full_k50': (list(range(D)), 50, 1), 'proprio_k50': (PROPRIO + [D - 2, D - 1], 50, 1),
                'proprio_k200s4': (PROPRIO + [D - 2, D - 1], 50, 4), 'full_k200': (list(range(D)), 200, 1),
                'proprio_k200': (PROPRIO + [D - 2, D - 1], 200, 1),
                'proprio_front_k50': (PROPRIO + list(range(5 + 49, 5 + 59)) + [D - 2, D - 1], 50, 1)}
    if args.variants:
        variants = {k: variants[k] for k in args.variants}
    rng = np.random.default_rng(0)
    splits = []
    for eps, g in data:
        perm = rng.permutation(len(eps)); cut = int(0.8 * len(eps))
        splits.append((perm[:cut], perm[cut:]))
    print(f"train on {[names[i] for i in args.train_on]}; R² on held-out episodes of each dataset")
    print('variant'.ljust(16) + ''.join(n.rjust(10) for n in names))
    for vname, (chans, k, stride) in variants.items():
        torch.manual_seed(0)
        net = AdaptationModule(state_action_dim=len(chans), history_window=k, intrinsics_dim=1)
        opt = torch.optim.Adam(net.parameters(), lr=5e-4)
        trng = np.random.default_rng(1)
        for step in range(args.steps):
            i = args.train_on[step % len(args.train_on)]
            X, y = windows(*data[i], splits[i][0], k, stride, chans, args.batch, trng)
            loss = nn.functional.mse_loss(net(torch.from_numpy(X)).squeeze(1), torch.from_numpy(y))
            opt.zero_grad(); loss.backward(); opt.step()
        r2s = []
        with torch.no_grad():
            for (eps, g), (_, te) in zip(data, splits):
                X, y = windows(eps, g, te, k, stride, chans, 4000, np.random.default_rng(2))
                p = net(torch.from_numpy(X)).squeeze(1).numpy()
                r2s.append(1 - np.mean((p - y) ** 2) / np.var(y))
        print(vname.ljust(16) + ''.join(f'{r:10.3f}' for r in r2s), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('collect')
    c.add_argument('--mode', choices=['oracle', 'phi', 'belief'], required=True)
    c.add_argument('--episodes', type=int, default=240)
    c.add_argument('--max-steps', type=int, default=1500)
    c.add_argument('--workers', type=int, default=4)
    c.add_argument('--seed', type=int, default=50_000)
    c.add_argument('--phase1', default='runs/phase1_fc/final.pt')
    c.add_argument('--phase2', default='runs/phase2_fc/final.pt')
    c.add_argument('--config', default='configs/retrain_phase2_fc_onpolicy.yaml')
    c.add_argument('--tire-model', default='friction_circle', choices=['linear', 'friction_circle', 'brush'])
    c.add_argument('--probe', type=float, nargs=4, metavar=('PERIOD', 'DURATION', 'AMP', 'MAX_STEER'),
                   help='active grip probe (environment.probe), e.g. 50 10 2.0 0.15')
    c.add_argument('--car-sensors', action='store_true', help="environment.sensors.model = 'car' (amendment 8)")
    c.add_argument('--out', required=True)
    t = sub.add_parser('train')
    t.add_argument('data', nargs='+')
    t.add_argument('--train-on', type=int, nargs='+', default=[0])
    t.add_argument('--variants', nargs='*')
    t.add_argument('--steps', type=int, default=3000)
    t.add_argument('--batch', type=int, default=256)
    t.add_argument('--threads', type=int, default=4)
    a = ap.parse_args()
    collect(a) if a.cmd == 'collect' else train(a)


if __name__ == '__main__':
    main()
