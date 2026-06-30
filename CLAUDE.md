# CLAUDE.md — dash-synthetic

Part of the **Dashlibs** suite. Full suite-wide context (release process
gotchas, PR/review norms, repo list, rationale for past decisions):
see `~/dashlibs/CLAUDE.md`.

## Purpose
Synthetic data generation from real Databricks tables. generator.py=generation API
(`SyntheticGenerator` single-table, `MultiTableGenerator` multi-table), profiler.py=source
profiling, engine.py=numpy-based correlated sampling, relationships.py=`RelationshipGraph`
(tables, primary/foreign keys, master data columns, dependency order), multi_engine.py=
FK-aware multi-table orchestration. UI widgets come from the shared `dashui` package
(PyPI distribution name `dash-uis` — `dash-ui` was already taken).

## Structure
- `/ui.py`            — ipywidgets UI (Single Table + Multi-Table Relationships tabs), `launch()` entrypoint
- `/relationships.py` — `RelationshipGraph`: define tables, PK/FK, master data columns, topo-sort generation order
- `/multi_engine.py`  — `generate_multi()` / `TableGenSpec`: runs tables in dependency order, samples FKs from parent PKs
- `/*.py`             — core logic
- `tests/`            — pytest, no Spark dependency for unit tests

## Key Design Rules
- Never import Spark at module level — always inside functions
- UI calls core classes; never contains business logic
- `launch()` is always the public entrypoint for business users
- Reusable widgets (header, source picker, output panel, schema lookups) come from `dashui`
  — don't reimplement them locally; add new generic widgets to the `dash-ui` repo (PyPI: `dash-uis`) instead
- Foreign-key columns are sampled from the parent table's *already-generated* primary key
  values (`pk_pools` in `multi_engine.py`), so generation order matters — always go through
  `RelationshipGraph.generation_order()` rather than an arbitrary table order
- "Master data" columns (e.g. currency/country codes) are forced into categorical sampling
  from real distinct source values regardless of dtype, via `force_categorical` in `engine.generate()`

## CI
- `ci.yml`    — PR gate: lint → test → build
- `daily.yml` — 06:00 UTC: tests + .health/log.txt commit
- `release.yml`— Monday 09:00 UTC: patch bump (via a release PR) + GitHub release + PyPI

This repo has branch protection requiring **1 approving review** — release
PRs sit open until a human approves; the wheel build / GitHub Release / PyPI
publish steps don't block on that PR merging, so the release itself still
completes.

## Working norms
- **Every change goes through a PR with real human review before merging —
  no exceptions**, including the release workflow's own version-bump commit.
  Don't self-merge, don't lower the required-review count to make automation
  easier — that defeats the point of requiring review.
- Prefer small, targeted commits/PRs over large batched ones.
- README badges previously pointed at `darshan-innovation/dash-synthetic`
  instead of the actual `dash-libs/dash-synthetic` repo — a leftover from
  an earlier rename. Check badge URLs match the real remote when scaffolding
  a new repo from this one.
