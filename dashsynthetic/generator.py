from __future__ import annotations
from typing import Optional

from dashsynthetic.relationships import RelationshipGraph


class SyntheticGenerator:
    """
    Generate synthetic data from a source Databricks table or DataFrame.

    Usage::
        gen = SyntheticGenerator(table="catalog.schema.customers")
        gen.set_volume(50000)
        gen.preserve_correlations(True)
        syn_df = gen.run()
    """

    def __init__(self, df=None, table: str = None, query: str = None):
        self._source_df = self._resolve(df, table, query)
        self._volume: int = 0
        self._preserve_corr: bool = True
        self._preserve_nulls: bool = True
        self._preserve_distributions: bool = True
        self._output_table: Optional[str] = None

    def _resolve(self, df, table, query):
        if df is not None:
            return df
        try:
            from pyspark.sql import SparkSession
            spark = SparkSession.getActiveSession()
            if table:
                return spark.table(table)
            if query:
                return spark.sql(query)
        except Exception as e:
            raise ValueError(f"Could not load source: {e}")
        raise ValueError("Provide df, table, or query")

    def set_volume(self, n_rows: int):
        self._volume = n_rows
        return self

    def preserve_correlations(self, enabled: bool = True):
        self._preserve_corr = enabled
        return self

    def preserve_null_patterns(self, enabled: bool = True):
        self._preserve_nulls = enabled
        return self

    def preserve_distributions(self, enabled: bool = True):
        self._preserve_distributions = enabled
        return self

    def output_to(self, table: str):
        self._output_table = table
        return self

    def profile(self) -> dict:
        """Profile the source dataframe — distributions, null rates, correlations."""
        from dashsynthetic.profiler import profile_df
        return profile_df(self._source_df)

    def run(self):
        """Generate and return a synthetic DataFrame."""
        from dashsynthetic.engine import generate
        syn_df = generate(
            source_df=self._source_df,
            n_rows=self._volume or self._source_df.count(),
            preserve_corr=self._preserve_corr,
            preserve_nulls=self._preserve_nulls,
            preserve_distributions=self._preserve_distributions,
        )
        if self._output_table:
            syn_df.write.format("delta").mode("overwrite") \
                .option("overwriteSchema", "true") \
                .saveAsTable(self._output_table)
            print(f"Synthetic data written to {self._output_table}")
        return syn_df


class MultiTableGenerator:
    """
    Generate synthetic data for several related tables at once, preserving
    primary/foreign key referential integrity and master-data columns.

    Usage::
        graph = RelationshipGraph()
        graph.add_table("Customer", table="catalog.schema.dim_customer", primary_key="customer_id")
        graph.add_table("Account", table="catalog.schema.fact_account", primary_key="account_id")
        graph.add_foreign_key("Account", "customer_id", "Customer", "customer_id")

        gen = MultiTableGenerator(graph)
        gen.configure_table("Customer", n_rows=5000)
        gen.configure_table("Account", n_rows=20000, output_table="catalog.schema.syn_account")
        results = gen.run()   # {"Customer": df, "Account": df}
    """

    def __init__(self, graph: RelationshipGraph):
        self._graph = graph
        self._specs: dict = {}

    def configure_table(self, name: str, n_rows: int = 0, preserve_corr: bool = True,
                        preserve_nulls: bool = True, preserve_distributions: bool = True,
                        output_table: Optional[str] = None):
        from dashsynthetic.multi_engine import TableGenSpec
        self._specs[name] = TableGenSpec(
            n_rows=n_rows, preserve_corr=preserve_corr, preserve_nulls=preserve_nulls,
            preserve_distributions=preserve_distributions, output_table=output_table,
        )
        return self

    def validate(self) -> list:
        return self._graph.validate()

    def generation_order(self) -> list:
        return self._graph.generation_order()

    def run(self) -> dict:
        """Generate and return {table_name: synthetic DataFrame} in dependency order."""
        from dashsynthetic.multi_engine import generate_multi
        return generate_multi(self._graph, self._specs)
