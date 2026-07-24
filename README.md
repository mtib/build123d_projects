# build123d_projects

Parametric CAD models built with [build123d](https://github.com/gumyr/build123d),
each emitting **STL files for 3D printing**. Every model is a small, self-contained
Python project under `projects/`.

## Quick start

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # runtime (build123d)
pip install -r requirements-dev.txt    # + matplotlib, for slice rendering

python build_all.py                    # build every project → projects/*/exports/*.stl
python build_all.py flowerpot          # build a single project
python build_all.py --views            # + render inspection PNGs next to the STLs
python build_all.py --dist dist        # + collect release assets into dist/
python build_all.py --list             # list projects
```

> build123d pulls in `cadquery-ocp` (OpenCascade), which currently has no wheels
> for Python 3.14 — hence the pin to **Python 3.12**.

## Layout

```
build_all.py          entrypoint: discover + build projects → STL
pipeline.py           shared STL export helper
viz.py                render slice/section PNGs to verify a model
projects/<name>/
  build.py            defines build() -> dict[str, Shape]
  exports/            generated STLs (gitignored)
```

Each project's `build.py` exposes `build() -> dict[str, Shape]`; the dict keys are
variant names, exported locally to `projects/<name>/exports/<key>.stl`. The
globally-unique release name `<project>_<key>.stl` is applied only when collecting
with `--dist` (path-derived prefix, hard error on any collision).

Run `build_all.py --views` to also render cross-section/plan PNGs next to each STL
(local verification aid; requires `requirements-dev.txt`, never uploaded to a release).

## Projects

- **flowerpot** — draining outer pots ("Übertopf") that a standard tapered nursery
  pot of **9 / 10 / 11 cm** top diameter drops into. The nursery pot rests on internal
  bosses above a drainage plenum; water leaves through a floor hole ring and round side
  vents. Designed to print support-free (flush base, gentle outward taper, arched vents).

## Continuous integration

On every push to `main`, [`.github/workflows/build.yml`](.github/workflows/build.yml)
runs `build_all.py --dist dist` and publishes a GitHub release containing every
`<project>_<name>.stl`. The project prefix is derived from the folder at collection
time and collisions are a hard error, so assets can't silently clash.

## Conventions

Models are designed to be **easy to print with minimal support** (flat base,
self-supporting overhangs). See `CLAUDE.md` for the full design guide, the
build123d primer, and the mandatory slice-verification loop.
