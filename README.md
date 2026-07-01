# DashSynthetic — Databricks Library

[![CI](https://github.com/dash-libs/dash-synthetic/actions/workflows/ci.yml/badge.svg)](https://github.com/dash-libs/dash-synthetic/actions)
[![PyPI](https://img.shields.io/pypi/v/dash-synthetic)](https://pypi.org/project/dash-synthetic/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

Part of the **[Dashlibs](https://github.com/dash-libs)** suite — Databricks libraries built for business users.

## Installation

```bash
%pip install dash-synthetic
```

## Quick Start

```python
import dashsynthetic
dashsynthetic.launch()   # Opens interactive UI in your Databricks notebook
```

The UI has two tabs:
- **Single Table** — profile a source table/DataFrame/SQL query and generate synthetic data from it.
- **Multi-Table Relationships** — define multiple tables, their primary keys, foreign keys, and
  master data columns (e.g. currency/country codes); the tool figures out the dependency order and
  generates every table with referentially valid foreign keys.

## What it looks like

**Single Table** — profile a source and generate synthetic data from it:

![DashSynthetic single-table tab](https://raw.githubusercontent.com/dash-libs/dash-synthetic/main/docs/screenshots/single_table.png)

**Multi-Table Relationships** — define tables, primary/foreign keys, and master data columns:

![DashSynthetic multi-table relationships tab](https://raw.githubusercontent.com/dash-libs/dash-synthetic/main/docs/screenshots/multi_table_relationships.png)

## Python API

```python
from dashsynthetic import RelationshipGraph, MultiTableGenerator

graph = RelationshipGraph()
graph.add_table("Customer", table="catalog.schema.dim_customer", primary_key="customer_id")
graph.add_table("Account", table="catalog.schema.fact_account", primary_key="account_id",
                master_data_columns=["currency_code"])
graph.add_foreign_key("Account", "customer_id", "Customer", "customer_id")

gen = MultiTableGenerator(graph)
gen.configure_table("Customer", n_rows=5000)
gen.configure_table("Account", n_rows=20000, output_table="catalog.schema.syn_account")
results = gen.run()   # {"Customer": df, "Account": df}, generated in dependency order
```

## Part of Dashlibs

| Library | Purpose |
|---|---|
| dash-dq | Data Quality |
| dash-synthetic | Synthetic Data Generation |
| dash-observe | Data Observability (freshness, volume, schema) |
| dash-ml | ML Model Monitoring |
| dash-ingest | Data Ingestion |
| dash-gov | Data Governance |
| dash-relate | Ontology & Lineage for AI |
| dash-ui | Shared UI components (PyPI: `dash-uis`) |

## Quality & Contributing

- 16 unit tests, zero Spark dependency to run them — `pytest tests/ -v`
  (the relationship graph, generation ordering, and multi-table
  orchestration logic are all pure Python and fully covered)
- Lint-clean (`ruff check dashsynthetic/`), PEP 561 typed (`py.typed`)
- Every change ships through a reviewed pull request; CI (lint → test on
  Python 3.9–3.12 → build) gates every PR and every release
- See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup,
  [CHANGELOG.md](CHANGELOG.md) for release history,
  [SECURITY.md](SECURITY.md) to report a vulnerability, and
  [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## License

Apache 2.0
