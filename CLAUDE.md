# CLAUDE.md — dash-synthetic

Part of the **Dashlibs** suite. See ~/dashlibs for the full context.

## Purpose
Synthetic data generation from real Databricks tables. generator.py=generation API, profiler.py=source profiling, engine.py=numpy-based correlated sampling

## Structure
- `/ui.py`       — ipywidgets UI, `launch()` entrypoint
- `/*.py`        — core logic
- `tests/`           — pytest, no Spark dependency for unit tests

## Key Design Rules
- Never import Spark at module level — always inside functions
- UI calls core classes; never contains business logic
- `launch()` is always the public entrypoint for business users

## CI
- `ci.yml`    — PR gate: lint → test → build
- `daily.yml` — 06:00 UTC: tests + .health/log.txt commit
- `release.yml`— Monday 09:00 UTC: patch bump + GitHub release
