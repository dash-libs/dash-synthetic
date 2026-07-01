# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses patch-only [semantic versioning](https://semver.org/)
bumps via the automated release workflow.

## [Unreleased]

### Added
- Repo hygiene: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, this CHANGELOG,
  issue/PR templates, `py.typed`

## [0.1.1] - 2026-06-30

### Added
- Multi-table relationship configuration: `RelationshipGraph` (tables,
  primary/foreign keys, master-data columns, dependency ordering),
  `MultiTableGenerator`, FK-aware multi-table generation that samples
  foreign keys from the parent table's already-generated primary keys
- "Multi-Table Relationships" tab in the notebook UI
- UI rebuilt on the shared `dash-ui` (`dashui`) component library

### Fixed
- `hatch version patch` now works (dynamic versioning)
- Hatchling can now find the wheel's package directory
- `generate_multi()` no longer imports pyspark before validating the
  input graph (was crashing in any environment without pyspark installed,
  even for invalid input that should fail with a clean error)
- README badges now point at the correct `dash-libs/dash-synthetic` repo

## [0.1.0] - 2026-06-29

### Added
- Initial release: `SyntheticGenerator` (single-table generation),
  source profiling, numpy-based correlated sampling
