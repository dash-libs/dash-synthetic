"""Unit tests for RelationshipGraph (no Spark required)."""
from dashsynthetic.relationships import RelationshipGraph


def _three_table_graph():
    graph = RelationshipGraph()
    graph.add_table("Customer", table="cat.sch.dim_customer", primary_key="customer_id")
    graph.add_table("Account", table="cat.sch.fact_account", primary_key="account_id",
                     master_data_columns=["currency_code"])
    graph.add_table("Transaction", table="cat.sch.fact_txn", primary_key="txn_id")
    graph.add_foreign_key("Account", "customer_id", "Customer", "customer_id")
    graph.add_foreign_key("Transaction", "account_id", "Account", "account_id")
    return graph


def test_add_table_and_foreign_key():
    graph = _three_table_graph()
    assert set(graph.tables) == {"Customer", "Account", "Transaction"}
    assert len(graph.foreign_keys) == 2
    assert graph.tables["Account"].master_data_columns == ["currency_code"]


def test_generation_order_respects_dependencies():
    graph = _three_table_graph()
    order = graph.generation_order()
    assert order.index("Customer") < order.index("Account")
    assert order.index("Account") < order.index("Transaction")


def test_foreign_keys_for_table():
    graph = _three_table_graph()
    fks = graph.foreign_keys_for("Account")
    assert len(fks) == 1
    assert fks[0].to_table == "Customer"
    assert graph.foreign_keys_for("Customer") == []


def test_validate_passes_for_valid_graph():
    graph = _three_table_graph()
    assert graph.validate() == []


def test_validate_flags_unknown_table_in_foreign_key():
    graph = RelationshipGraph()
    graph.add_table("Customer", table="cat.sch.dim_customer", primary_key="customer_id")
    graph.add_foreign_key("Account", "customer_id", "Customer", "customer_id")
    issues = graph.validate()
    assert any("Account" in issue for issue in issues)


def test_validate_detects_cycle():
    graph = RelationshipGraph()
    graph.add_table("A", table="cat.sch.a", primary_key="id")
    graph.add_table("B", table="cat.sch.b", primary_key="id")
    graph.add_foreign_key("A", "b_id", "B", "id")
    graph.add_foreign_key("B", "a_id", "A", "id")
    issues = graph.validate()
    assert any("cycle" in issue.lower() for issue in issues)


def test_generation_order_raises_on_cycle():
    graph = RelationshipGraph()
    graph.add_table("A", table="cat.sch.a", primary_key="id")
    graph.add_table("B", table="cat.sch.b", primary_key="id")
    graph.add_foreign_key("A", "b_id", "B", "id")
    graph.add_foreign_key("B", "a_id", "A", "id")
    try:
        graph.generation_order()
        assert False, "expected ValueError"
    except ValueError as e:
        assert "cycle" in str(e).lower()


def test_to_dict_round_trips_structure():
    graph = _three_table_graph()
    d = graph.to_dict()
    assert set(d["tables"]) == {"Customer", "Account", "Transaction"}
    assert len(d["foreign_keys"]) == 2
    assert d["tables"]["Account"]["master_data_columns"] == ["currency_code"]


def test_to_json_is_valid_json():
    import json
    graph = _three_table_graph()
    parsed = json.loads(graph.to_json())
    assert "tables" in parsed and "foreign_keys" in parsed


def test_independent_tables_have_no_forced_order_between_them():
    graph = RelationshipGraph()
    graph.add_table("X", table="cat.sch.x", primary_key="id")
    graph.add_table("Y", table="cat.sch.y", primary_key="id")
    order = graph.generation_order()
    assert set(order) == {"X", "Y"}
