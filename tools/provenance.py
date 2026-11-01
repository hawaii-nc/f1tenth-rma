#!/usr/bin/env python3
"""
Write provenance.json next to every summary.json under the given results
roots: git commit (+ dirty flag), library versions, f110_gym commit, SHA-256
of the checkpoints and config named in summary.json's args, and the track
scales. Lets anyone check which code and weights produced a number.

    python tools/provenance.py results/retrain_nov2026
"""
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def sha256(p):
    p = Path(p)
    if not p.is_absolute():
        p = REPO / p
    if not p.exists():
        return None
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def git(*args, cwd=REPO):
    try:
        return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def environment():
    env = {'python': platform.python_version(), 'platform': platform.platform(),
           'repo_commit': git('rev-parse', 'HEAD'), 'repo_dirty': bool(git('status', '--porcelain', '--untracked-files=no'))}
    for mod in ('numpy', 'torch', 'scipy', 'numba'):
        try:
            env[mod] = __import__(mod).__version__
        except Exception:
            env[mod] = None
    try:
        import f110_gym
        root = Path(f110_gym.__file__).resolve().parents[2]
        env['f110_gym_path'] = str(root)
        env['f110_gym_commit'] = git('rev-parse', 'HEAD', cwd=root)
    except Exception:
        env['f110_gym_commit'] = None
    sys.path.insert(0, str(REPO / 'tools'))
    try:
        import prepare_tracks
        env['tight_scale'] = prepare_tracks.TIGHT_SCALE
    except Exception:
        pass
    return env


def main():
    env = environment()
    n = 0
    for root in sys.argv[1:]:
        for summ in Path(root).rglob('summary.json'):
            args = json.loads(summ.read_text()).get('args', {})
            prov = {'written': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'environment': env,
                    'files': {k: {'path': args[k], 'sha256': sha256(args[k])}
                              for k in ('phase1', 'phase2', 'config') if args.get(k)}}
            (summ.parent / 'provenance.json').write_text(json.dumps(prov, indent=2))
            n += 1
    print(f'wrote provenance.json in {n} result dirs (repo {env["repo_commit"][:8] if env["repo_commit"] else "?"}, '
          f'dirty={env["repo_dirty"]}, f110_gym {str(env.get("f110_gym_commit"))[:8]})')


if __name__ == '__main__':
    main()
