"""
Synthetic data generation engine.
Uses numpy multivariate normal sampling for correlated columns
and per-column distribution fitting for marginals.
"""
from __future__ import annotations
import numpy as np
from pyspark.sql import functions as F
from pyspark.sql.types import *


def generate(source_df, n_rows: int, preserve_corr: bool,
             preserve_nulls: bool, preserve_distributions: bool):
    from pyspark.sql import SparkSession
    spark = SparkSession.getActiveSession()

    schema = source_df.schema
    numeric_cols = [f.name for f in schema.fields
                    if any(t in str(f.dataType)
                           for t in ("Int", "Long", "Double", "Float", "Decimal"))]
    string_cols = [f.name for f in schema.fields if "String" in str(f.dataType)]
    bool_cols = [f.name for f in schema.fields if "Boolean" in str(f.dataType)]
    date_cols = [f.name for f in schema.fields
                 if any(t in str(f.dataType) for t in ("Date", "Timestamp"))]

    np.random.seed(42)
    rows = []

    # Collect stats for numeric columns
    numeric_stats = {}
    if numeric_cols:
        agg_exprs = []
        for c in numeric_cols:
            agg_exprs += [F.mean(c).alias(f"{c}__mean"), F.stddev(c).alias(f"{c}__std")]
        stats_row = source_df.agg(*agg_exprs).collect()[0].asDict()
        for c in numeric_cols:
            mean = stats_row.get(f"{c}__mean") or 0.0
            std = stats_row.get(f"{c}__std") or 1.0
            numeric_stats[c] = (float(mean), float(std))

    # Collect categorical distributions
    cat_dists = {}
    for c in string_cols:
        total = source_df.count()
        dist = (
            source_df.groupBy(c).count()
                     .withColumn("prob", F.col("count") / total)
                     .select(c, "prob")
                     .collect()
        )
        cat_dists[c] = (
            [r[c] for r in dist],
            [float(r["prob"]) for r in dist],
        )

    # Null rates
    null_rates = {}
    if preserve_nulls:
        total = source_df.count()
        for f in schema.fields:
            nc = source_df.filter(F.col(f.name).isNull()).count()
            null_rates[f.name] = nc / total if total > 0 else 0.0

    # Generate numeric data (correlated if requested)
    if numeric_cols and preserve_corr:
        pandas_df = source_df.select(numeric_cols).dropna().toPandas()
        cov = pandas_df.cov().values
        means = pandas_df.mean().values
        try:
            samples = np.random.multivariate_normal(means, cov, n_rows)
        except np.linalg.LinAlgError:
            samples = np.column_stack([
                np.random.normal(numeric_stats[c][0], numeric_stats[c][1], n_rows)
                for c in numeric_cols
            ])
        numeric_samples = {c: samples[:, i] for i, c in enumerate(numeric_cols)}
    elif numeric_cols:
        numeric_samples = {
            c: np.random.normal(numeric_stats[c][0], max(numeric_stats[c][1], 1e-6), n_rows)
            for c in numeric_cols
        }
    else:
        numeric_samples = {}

    # Build rows
    for i in range(n_rows):
        row = {}
        for f in schema.fields:
            c = f.name
            dtype = str(f.dataType)
            null_roll = np.random.random() < null_rates.get(c, 0.0)

            if null_roll and preserve_nulls:
                row[c] = None
            elif c in numeric_samples:
                val = float(numeric_samples[c][i])
                if "Int" in dtype or "Long" in dtype:
                    row[c] = int(round(val))
                else:
                    row[c] = round(val, 4)
            elif c in cat_dists:
                values, probs = cat_dists[c]
                probs_arr = np.array(probs)
                probs_arr = probs_arr / probs_arr.sum()
                row[c] = np.random.choice(values, p=probs_arr)
            elif c in bool_cols:
                row[c] = bool(np.random.random() > 0.5)
            elif c in date_cols:
                row[c] = None  # dates handled separately in practice
            else:
                row[c] = None
        rows.append(row)

    return spark.createDataFrame(rows, schema)
