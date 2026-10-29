# Maps

`aut`, `esp`, `gbr`, `mco` (+ `*_centerline.csv`: x, y, w_right, w_left, no header) come from
[BDEvan5/f1tenth_benchmarks](https://github.com/BDEvan5/f1tenth_benchmarks) (Apache-2.0).

The final policy trained on 14 × `<name>_tight` tracks (35% scale). Build them with:

    python tools/prepare_tracks.py

That rescales these four maps and downloads ten more circuits from
[f1tenth/f1tenth_racetracks](https://github.com/f1tenth/f1tenth_racetracks) (GPL-3.0, Betz et al. 2022).
Generated files are git-ignored rather than redistributed.
