"""
Filesystem locations shared by training, evaluation and experiments.

The original lab setup hard-coded ``/research_ws/maps``. Everything now goes
through these helpers so the code runs from any checkout:

  F1TENTH_MAPS_DIR   directory holding <track>.png/.yaml/_centerline.csv
                     (default: <repo>/maps, falling back to /research_ws/maps)
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def maps_dir() -> Path:
    env = os.environ.get('F1TENTH_MAPS_DIR')
    if env:
        return Path(env)
    repo_maps = REPO_ROOT / 'maps'
    if repo_maps.is_dir():
        return repo_maps
    return Path('/research_ws/maps')


def map_base(track: str) -> str:
    """Map path without extension, as F110Env expects."""
    return str(maps_dir() / track)


def centerline_path(track: str) -> Path:
    return maps_dir() / f'{track}_centerline.csv'


def raceline_path(track: str) -> Path:
    return maps_dir() / 'racelines' / f'{track}_raceline.csv'
