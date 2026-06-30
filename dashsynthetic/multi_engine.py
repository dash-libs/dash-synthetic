"""
Multi-table synthetic generation — runs a RelationshipGraph's tables in
dependency order, sampling foreign keys from the already-generated parent
table's primary key values so referential integrity is preserved.
"""
from __future__ import annotations
from dataclasses import dataclass

from dashsynthetic.relationships import RelationshipGraph


@dataclass
class TableGenSpec:
    n_rows: int = 0
    preserve_corr: bool = True
    preserve_nulls: bool = True
    preserve_distributions: bool = True
    output_table: str | None = None


def generate_multi(graph: RelationshipGraph, table_specs: dict = None) -> dict:
    """
    Generate synthetic DataFrames for every table in `graph`, in dependency
    (foreign-key-safe) order. Returns {table_name: synthetic_df}.
    """
    issues = graph.validate()
    if issues:
        raise ValueError("Invalid relationship graph: " + "; ".join(issues))

    from dashsynthetic.engine import generate
    from pyspark.sql import SparkSession
    spark = SparkSession.getActiveSession()

    table_specs = table_specs or {}
    order = graph.generation_order()
    results: dict = {}
    pk_pools: dict[str, list] = {}

    for name in order:
        node = graph.tables[name]
        spec = table_specs.get(name, TableGenSpec())
        source_df = spark.table(node.table)

        column_value_pools = {}
        for fk in graph.foreign_keys_for(name):
            parent_values = pk_pools.get(fk.to_table)
            if parent_values is None:
                raise ValueError(
                    f"Foreign key '{name}.{fk.from_column}' references "
                    f"'{fk.to_table}' which has no generated primary key values "
                    f"(check that '{fk.to_table}' declares a primary_key)"
                )
            column_value_pools[fk.from_column] = parent_values

        syn_df = generate(
            source_df=source_df,
            n_rows=spec.n_rows or source_df.count(),
            preserve_corr=spec.preserve_corr,
            preserve_nulls=spec.preserve_nulls,
            preserve_distributions=spec.preserve_distributions,
            force_categorical=node.master_data_columns,
            column_value_pools=column_value_pools,
        )

        if node.primary_key:
            pk_pools[name] = [r[node.primary_key] for r in syn_df.select(node.primary_key).collect()]

        if spec.output_table:
            syn_df.write.format("delta").mode("overwrite") \
                .option("overwriteSchema", "true") \
                .saveAsTable(spec.output_table)

        results[name] = syn_df

    return results
