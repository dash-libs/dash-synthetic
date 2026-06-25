from __future__ import annotations


def profile_df(df) -> dict:
    """Return a statistical profile of the DataFrame — distributions, nulls, correlations."""
    from pyspark.sql import functions as F

    schema = {f.name: str(f.dataType) for f in df.schema.fields}
    total = df.count()
    profile = {"total_rows": total, "columns": {}}

    for col_name, dtype in schema.items():
        col_profile = {"dtype": dtype}

        # Null rate
        null_count = df.filter(F.col(col_name).isNull()).count()
        col_profile["null_rate"] = round(null_count / total, 4) if total > 0 else 0.0
        col_profile["null_count"] = null_count

        # Numeric stats
        if any(t in dtype for t in ("Int", "Long", "Double", "Float", "Decimal")):
            stats = df.agg(
                F.mean(col_name).alias("mean"),
                F.stddev(col_name).alias("std"),
                F.min(col_name).alias("min"),
                F.max(col_name).alias("max"),
                F.expr(f"percentile_approx({col_name}, 0.25)").alias("p25"),
                F.expr(f"percentile_approx({col_name}, 0.50)").alias("p50"),
                F.expr(f"percentile_approx({col_name}, 0.75)").alias("p75"),
            ).collect()[0].asDict()
            col_profile.update(stats)

        # Categorical stats
        elif "String" in dtype:
            distinct = df.select(col_name).distinct().count()
            col_profile["distinct_count"] = distinct
            col_profile["cardinality_ratio"] = round(distinct / total, 4) if total > 0 else 0.0
            if distinct <= 50:
                top_vals = (
                    df.groupBy(col_name).count()
                      .orderBy(F.desc("count"))
                      .limit(10)
                      .collect()
                )
                col_profile["top_values"] = {r[col_name]: r["count"] for r in top_vals}

        profile["columns"][col_name] = col_profile

    return profile
