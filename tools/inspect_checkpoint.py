#!/usr/bin/env python3
"""
Print a checkpoint's tensor shapes, training step and embedded config, or
export the config to YAML.

    python tools/inspect_checkpoint.py checkpoints/final/phase1_v42.pt
    python tools/inspect_checkpoint.py checkpoints/final/phase1_v42.pt --export-config out.yaml

Loads with weights_only=True (no arbitrary unpickling).
"""
import argparse
import sys

import torch
import yaml


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('checkpoint')
    ap.add_argument('--export-config', metavar='YAML')
    args = ap.parse_args()

    ck = torch.load(args.checkpoint, map_location='cpu', weights_only=True)
    if args.export_config:
        with open(args.export_config, 'w') as f:
            f.write(f"# Exported from {args.checkpoint} (global_step={ck.get('global_step')})\n")
            yaml.safe_dump(ck.get('config', {}), f, sort_keys=False)
        print(f"wrote {args.export_config}")
        return

    print(f"{args.checkpoint}: global_step={ck.get('global_step')}")
    for key in ('actor_critic', 'adaptation', 'aux_head'):
        if key in ck:
            print(f"[{key}]")
            for name, t in ck[key].items():
                print(f"  {name:32s} {tuple(t.shape)}")
    yaml.safe_dump({'config': ck.get('config', {})}, sys.stdout, sort_keys=False)


if __name__ == '__main__':
    main()
