"""Unit tests for multi_engine (no Spark required — only the pre-Spark validation path)."""
import pytest

from dashsynthetic.multi_engine import TableGenSpec, generate_multi
from dashsynthetic.relationships import RelationshipGraph


def test_table_gen_spec_defaults():
    spec = TableGenSpec()
    assert spec.n_rows == 0
    assert spec.preserve_corr is True
    assert spec.output_table is None


def test_generate_multi_raises_on_invalid_graph_before_touching_spark():
    graph = RelationshipGraph()
    graph.add_table("Customer", table="cat.sch.dim_customer", primary_key="customer_id")
    graph.add_foreign_key("Account", "customer_id", "Customer", "customer_id")  # Account undefined

    with pytest.raises(ValueError, match="Invalid relationship graph"):
        generate_multi(graph)
