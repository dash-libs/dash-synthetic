## DashSynthetic — Synthetic Data v0.1.1

**Released:** 2026-06-30
**Previous:** v0.1.0

### Notes
Initial public release — multi-table relationship configuration (PK/FK, master data columns) on top of single-table synthetic data generation

### What's included
- All tests passing across Python 3.9, 3.10, 3.11, 3.12
- API documentation regenerated (see `docs/api/`)
- Published to PyPI and Databricks Marketplace

### Install
```bash
pip install dash-synthetic==0.1.1
```

### Quick Start (Databricks notebook)
```python
%pip install dash-synthetic==0.1.1
import dashsynthetic
dashsynthetic.launch()
```
