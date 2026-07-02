"""
Multi-table relationship configuration — primary keys, foreign keys, master
data columns, and the dependency ("ontology") order tables must be generated in.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class TableNode:
    name: str
    table: str
    primary_key: str | None = None
    master_data_columns: list[str] = field(default_factory=list)


@dataclass
class ForeignKey:
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class RelationshipGraph:
    """
    Defines which tables exist, their primary/master-data columns, and the
    foreign keys linking them — so synthetic generation can run tables in
    dependency order and keep FK values referentially valid.

    Usage::
        graph = RelationshipGraph()
        graph.add_table("Customer", table="catalog.schema.dim_customer", primary_key="customer_id")
        graph.add_table("Account", table="catalog.schema.fact_account", primary_key="account_id",
                         master_data_columns=["currency_code"])
        graph.add_foreign_key("Account", "customer_id", "Customer", "customer_id")
        graph.generation_order()   # -> ["Customer", "Account"]
    """

    def __init__(self):
        self._tables: dict[str, TableNode] = {}
        self._foreign_keys: list[ForeignKey] = []

    def add_table(self, name: str, table: str, primary_key: str | None = None,
                  master_data_columns: list[str] | None = None):
        self._tables[name] = TableNode(name, table, primary_key, master_data_columns or [])
        return self

    def add_foreign_key(self, from_table: str, from_column: str,
                        to_table: str, to_column: str):
        self._foreign_keys.append(ForeignKey(from_table, from_column, to_table, to_column))
        return self

    @property
    def tables(self) -> dict[str, TableNode]:
        return self._tables

    @property
    def foreign_keys(self) -> list[ForeignKey]:
        return self._foreign_keys

    def foreign_keys_for(self, table_name: str) -> list[ForeignKey]:
        """Foreign keys defined on `table_name` (i.e. it depends on their `to_table`)."""
        return [fk for fk in self._foreign_keys if fk.from_table == table_name]

    def validate(self) -> list[str]:
        """Check referential integrity of tables/foreign keys; cycle detection."""
        issues = []
        for fk in self._foreign_keys:
            if fk.from_table not in self._tables:
                issues.append(f"Unknown table '{fk.from_table}' in foreign key")
            if fk.to_table not in self._tables:
                issues.append(f"Unknown table '{fk.to_table}' in foreign key")
        try:
            self.generation_order()
        except ValueError as e:
            issues.append(str(e))
        return issues

    def generation_order(self) -> list[str]:
        """
        Topologically sort tables so every table is generated after the
        tables its foreign keys point to. Raises ValueError on a dependency cycle.
        """
        deps: dict[str, set[str]] = {name: set() for name in self._tables}
        for fk in self._foreign_keys:
            if fk.from_table in deps and fk.to_table in deps:
                deps[fk.from_table].add(fk.to_table)

        ordered: list[str] = []
        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(name: str):
            if name in visited:
                return
            if name in visiting:
                raise ValueError(f"Dependency cycle detected involving table '{name}'")
            visiting.add(name)
            for dep in sorted(deps[name]):
                visit(dep)
            visiting.discard(name)
            visited.add(name)
            ordered.append(name)

        for name in sorted(self._tables):
            visit(name)
        return ordered

    def to_dict(self) -> dict:
        return {
            "tables": {
                name: {
                    "table": n.table,
                    "primary_key": n.primary_key,
                    "master_data_columns": n.master_data_columns,
                }
                for name, n in self._tables.items()
            },
            "foreign_keys": [
                {
                    "from_table": fk.from_table, "from_column": fk.from_column,
                    "to_table": fk.to_table, "to_column": fk.to_column,
                }
                for fk in self._foreign_keys
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        import json
        return json.dumps(self.to_dict(), indent=indent)

    def summary(self):
        print(f"Tables:       {len(self._tables)}")
        print(f"Foreign keys: {len(self._foreign_keys)}")
        issues = self.validate()
        if issues:
            print(f"{len(issues)} validation issue(s):")
            for i in issues:
                print(f"   - {i}")
        else:
            print(f"Validation passed — generation order: {' → '.join(self.generation_order())}")
