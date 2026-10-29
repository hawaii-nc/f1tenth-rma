"""Shared CLI plumbing for experiments/e*.py."""
import argparse
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src' / 'f1tenth_research'))

import os  # noqa: E402

import yaml  # noqa: E402

if os.environ.get('F1TENTH_FAKE_SIM') == '1':
    # CI smoke tests only: swap f110_gym for tests/fake_sim.py
    sys.path.insert(0, str(REPO / 'tests'))
    from fake_sim import FakeSim  # noqa: E402
    from f1tenth_research.envs import F1TenthRMAEnv  # noqa: E402
    FakeSim.half_width = float(os.environ.get('F1TENTH_FAKE_HALF_WIDTH', 0.4))
    F1TenthRMAEnv.wrapper_factory = staticmethod(FakeSim)

DEFAULT_PHASE1 = REPO / 'checkpoints' / 'final' / 'phase1_v42.pt'
DEFAULT_PHASE2 = REPO / 'checkpoints' / 'final' / 'phase2_crashtol_clean.pt'
DEFAULT_CONFIG = REPO / 'configs' / 'final_phase2_crashtol.yaml'


def base_parser(description: str, n_default: int = 100) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument('--phase1', default=str(DEFAULT_PHASE1), help='actor-critic checkpoint')
    ap.add_argument('--phase2', default=str(DEFAULT_PHASE2), help='adaptation (φ) checkpoint')
    ap.add_argument('--config', default=str(DEFAULT_CONFIG), help='YAML with an environment: block')
    ap.add_argument('-n', '--episodes', type=int, default=n_default, help='episodes per condition')
    ap.add_argument('--tracks', nargs='*', help='evaluation tracks (default: config environment.tracks)')
    ap.add_argument('--max-steps', type=int, default=2500, help='episode step cap (50 Hz → 50 s)')
    ap.add_argument('--seed', type=int, default=0, help='base seed; episode i uses seed+i for every controller')
    ap.add_argument('--out', default=None, help='output directory (default results/<exp>/<timestamp>)')
    ap.add_argument('--device', default='cpu')
    return ap


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def out_dir(args, exp: str) -> Path:
    if args.out:
        return Path(args.out)
    return REPO / 'results' / exp / time.strftime('%Y%m%d-%H%M%S')


def eval_tracks(args, cfg) -> list:
    return args.tracks or cfg['environment'].get('tracks') or [cfg['environment'].get('track', 'aut')]


def track_for(i: int, tracks: list) -> str:
    """Round-robin so every condition sees the same track sequence."""
    return tracks[i % len(tracks)]
