#!/usr/bin/env python3
"""
Build the 14 "<name>_tight" training tracks used by the final (v42) policy.

The final policy trained on 35%-scale copies of 14 circuits, sized to match
the physical cardboard test track (~2–3 ft wide; the car is ~8–9 in wide):

    aut esp gbr mco                      <- BDEvan5/f1tenth_benchmarks (Apache-2.0, in maps/)
    spielberg silverstone monza sochi
    ims zandvoort sepang yasmarina
    budapest melbourne                   <- f1tenth/f1tenth_racetracks (GPL-3.0, downloaded)

A tight variant keeps the occupancy PNG and rescales everything metric:
map resolution, map origin, centerline x/y and track half-widths, and the
raceline x/y: all × scale (default 0.35).

Scale (November 2026). A uniform 35% makes several corners tighter than the
car can physically turn (min turning radius 0.33 m / tan(0.4189) = 0.74 m):
aut_tight has a 0.24 m-radius hairpin, and the Pure Pursuit expert crashes on
13 of 14 tracks. By default each track now uses the smallest scale from
{0.35, 0.40, ..., 0.70} at which the expert completes a full lap (TIGHT_SCALE,
found with the search in docs/RETRAINING.md). Zandvoort crashes the expert at
the same point at every scale up to 0.70 (a map defect), so it is excluded
from the retraining configs.

Usage:
    python tools/prepare_tracks.py                  # download racetracks + build all *_tight (per-track scale)
    python tools/prepare_tracks.py --scale 0.35     # the July reconstruction: uniform 35%
    python tools/prepare_tracks.py --racetracks /path/to/f1tenth_racetracks

Output goes to maps/ (or $F1TENTH_MAPS_DIR). Racelines go to maps/racelines/.
"""
import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[1]
RACETRACKS_URL = 'https://github.com/f1tenth/f1tenth_racetracks.git'

BENCHMARK_TRACKS = ['aut', 'esp', 'gbr', 'mco']
RACETRACK_DB = {
    'spielberg': 'Spielberg', 'silverstone': 'Silverstone', 'monza': 'Monza',
    'sochi': 'Sochi', 'ims': 'IMS', 'zandvoort': 'Zandvoort', 'sepang': 'Sepang',
    'yasmarina': 'YasMarina', 'budapest': 'Budapest', 'melbourne': 'Melbourne',
}

# Smallest scale at which the Pure Pursuit expert laps the track (see above).
TIGHT_SCALE = {
    'aut': 0.70, 'esp': 0.60, 'gbr': 0.60, 'mco': 0.65,
    'spielberg': 0.55, 'silverstone': 0.45, 'monza': 0.60, 'sochi': 0.45,
    'ims': 0.35, 'zandvoort': 0.35, 'sepang': 0.40, 'yasmarina': 0.55,
    'budapest': 0.35, 'melbourne': 0.40,
}


def maps_dir() -> Path:
    return Path(os.environ.get('F1TENTH_MAPS_DIR', REPO / 'maps'))


def write_map(src_yaml: Path, src_png: Path, out_dir: Path, name: str, scale: float):
    meta = yaml.safe_load(src_yaml.read_text())
    meta['image'] = f'{name}.png'
    meta['resolution'] = float(meta['resolution']) * scale
    meta['origin'] = [float(meta['origin'][0]) * scale, float(meta['origin'][1]) * scale,
                      float(meta['origin'][2]) if len(meta['origin']) > 2 else 0.0]
    meta.setdefault('negate', 0)
    meta.setdefault('occupied_thresh', 0.65)
    meta.setdefault('free_thresh', 0.196)
    (out_dir / f'{name}.yaml').write_text(yaml.safe_dump(meta, sort_keys=False))
    shutil.copyfile(src_png, out_dir / f'{name}.png')


def write_centerline(src_csv: Path, out_csv: Path, scale: float):
    """Output format: x, y, w_right, w_left: comma separated, no header."""
    cl = np.loadtxt(src_csv, delimiter=',', comments='#')
    cl[:, 0:4] *= scale
    np.savetxt(out_csv, cl[:, 0:4], delimiter=',', fmt='%.6f')


def write_raceline(src_csv: Path, out_csv: Path, scale: float):
    """
    Input: TUMFTM format "s_m; x_m; y_m; psi_rad; kappa_radpm; vx_mps; ax_mps2".
    Output: s, x, y, psi, kappa, vx: comma separated, '#' header. Distances
    scale by `scale`, curvature by 1/scale; vx is kept (it is clipped to
    max_velocity downstream). psi is kept for reference only: it is 90° off
    from the f110_gym heading convention; compute headings with arctan2.
    """
    rl = np.loadtxt(src_csv, delimiter=';', comments='#')
    out = np.column_stack([rl[:, 0] * scale, rl[:, 1] * scale, rl[:, 2] * scale,
                           rl[:, 3], rl[:, 4] / scale, rl[:, 5]])
    np.savetxt(out_csv, out, delimiter=',', fmt='%.6f', header='s_m,x_m,y_m,psi_rad,kappa_radpm,vx_mps')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--scale', type=float, default=None,
                    help='uniform scale for every *_tight track (default: per-track TIGHT_SCALE)')
    ap.add_argument('--racetracks', type=Path, help='existing f1tenth_racetracks checkout (else cloned)')
    args = ap.parse_args()

    out = maps_dir()
    (out / 'racelines').mkdir(parents=True, exist_ok=True)

    for name in BENCHMARK_TRACKS:
        tight = f'{name}_tight'
        scale = args.scale or TIGHT_SCALE[name]
        write_map(out / f'{name}.yaml', out / f'{name}.png', out, tight, scale)
        write_centerline(out / f'{name}_centerline.csv', out / f'{tight}_centerline.csv', scale)
        print(f'built {tight} (scale {scale:.2f})')

    tmp = None
    db = args.racetracks
    if db is None:
        tmp = tempfile.mkdtemp()
        db = Path(tmp) / 'f1tenth_racetracks'
        subprocess.run(['git', 'clone', '--depth', '1', RACETRACKS_URL, str(db)], check=True)
    try:
        for name, folder in RACETRACK_DB.items():
            src = db / folder
            for variant, scale in ((name, 1.0), (f'{name}_tight', args.scale or TIGHT_SCALE[name])):
                write_map(src / f'{folder}_map.yaml', src / f'{folder}_map.png', out, variant, scale)
                write_centerline(src / f'{folder}_centerline.csv', out / f'{variant}_centerline.csv', scale)
                if variant == name:
                    # Not for *_tight: a scaled raceline keeps its full-scale
                    # distance to the walls ×scale, but the car does not shrink,
                    # so it ends up inside the car's half-width (0.155 m) of a
                    # wall and the expert crashes within ~50 steps. The Phase 1
                    # expert falls back to the centerline, which laps every track.
                    write_raceline(src / f'{folder}_raceline.csv', out / 'racelines' / f'{variant}_raceline.csv', scale)
            print(f'built {name} and {name}_tight (scale {args.scale or TIGHT_SCALE[name]:.2f})')
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
