"""DashSynthetic interactive UI for Databricks notebooks."""
from __future__ import annotations

_LIBRARY = "dashsynthetic"


def env_setup() -> None:
    """Open the environment setup panel — where should dashsynthetic
    read/write its configs? Defaults to the notebook's current working
    directory if never called."""
    try:
        import dashui
        from IPython.display import display
    except ImportError:
        raise RuntimeError("ipywidgets required. Run: %pip install ipywidgets") from None

    display(dashui.card([
        dashui.header("DashSynthetic — Environment Setup", library=_LIBRARY),
        dashui.env_setup_panel(_LIBRARY).widget,
    ]))


def launch():
    try:
        import ipywidgets as w
        from IPython.display import display
    except ImportError:
        raise RuntimeError("ipywidgets required. Run: %pip install ipywidgets")

    import dashui

    tab = w.Tab(children=[_build_single_table_tab(w), _build_relationships_tab(w)])
    tab.set_title(0, "Single Table")
    tab.set_title(1, "Multi-Table Relationships")

    env_accordion = w.Accordion(children=[dashui.env_setup_panel(_LIBRARY).widget])
    env_accordion.set_title(0, "Environment setup")
    env_accordion.selected_index = None

    ui = dashui.card([
        dashui.header("DashSynthetic — Synthetic Data Generation",
                      library="dashsynthetic"),
        env_accordion,
        tab,
    ])
    display(ui)


def _build_single_table_tab(w):
    import dashui

    saved = dashui.load_config(_LIBRARY, name="single_table", defaults={
        "n_rows": 10000, "preserve_corr": True, "preserve_nulls": True, "preserve_dist": True,
    })

    src = dashui.source_selector()

    n_rows = w.IntText(value=saved["n_rows"], description="Rows to generate:", min=1)
    preserve_corr = w.Checkbox(value=saved["preserve_corr"], description="Preserve correlation structure")
    preserve_nulls = w.Checkbox(value=saved["preserve_nulls"], description="Preserve missing value patterns")
    preserve_dist = w.Checkbox(value=saved["preserve_dist"], description="Preserve marginal distributions")

    save_toggle = w.Checkbox(value=False, description="Save to Delta table")
    save_input = w.Text(placeholder="catalog.schema.synthetic_output", description="Output table:", disabled=True)
    save_toggle.observe(lambda c: setattr(save_input, "disabled", not c["new"]), names="value")

    profile_btn = dashui.action_button("Profile source", style="info")
    run_btn = dashui.action_button("Generate Synthetic Data", style="success")
    output = dashui.output_panel()

    def _save_state() -> None:
        try:
            dashui.save_config(_LIBRARY, {
                "n_rows": n_rows.value, "preserve_corr": preserve_corr.value,
                "preserve_nulls": preserve_nulls.value, "preserve_dist": preserve_dist.value,
            }, name="single_table")
        except Exception:
            pass  # persistence is a convenience, never block the actual operation on it

    def on_profile(b):
        with output:
            output.clear_output()
            try:
                gen = _build_generator(src)
                import json
                profile = gen.profile()
                print(json.dumps({k: v for k, v in list(profile["columns"].items())[:5]}, indent=2, default=str))
                print(f"\n... {len(profile['columns'])} columns total, {profile['total_rows']:,} rows")
            except Exception as e:
                print(f"Error: {e}")

    def on_run(b):
        with output:
            output.clear_output()
            _save_state()
            try:
                gen = _build_generator(src)
                gen.set_volume(n_rows.value) \
                   .preserve_correlations(preserve_corr.value) \
                   .preserve_null_patterns(preserve_nulls.value) \
                   .preserve_distributions(preserve_dist.value)
                if save_toggle.value and save_input.value.strip():
                    gen.output_to(save_input.value.strip())
                syn_df = gen.run()
                print(f"Generated {syn_df.count():,} synthetic rows")
                syn_df.show(5, truncate=True)
            except Exception as e:
                print(f"Error: {e}")

    profile_btn.on_click(on_profile)
    run_btn.on_click(on_run)

    return dashui.card([
        dashui.section("Step 1: Source data"),
        src.toggle, src.box,
        dashui.section("Step 2: Generation settings"),
        n_rows, preserve_corr, preserve_nulls, preserve_dist,
        dashui.section("Step 3: Output"),
        save_toggle, save_input,
        w.HTML("<hr>"),
        w.HBox([profile_btn, run_btn]),
        output,
    ])


def _build_relationships_tab(w):
    """
    Configuration UI for defining multi-table relationships: which tables
    participate, their primary key + master data columns, the foreign keys
    linking them, and the resulting generation ("ontology") order.
    """
    import dashui

    saved = dashui.load_config(_LIBRARY, name="relationships", defaults={
        "tables": [], "foreign_keys": [], "n_rows": 10000,
        "preserve_corr": True, "preserve_nulls": True, "preserve_dist": True,
        "output_prefix": "",
    })

    tables: list[dict] = list(saved["tables"])
    foreign_keys: list[dict] = list(saved["foreign_keys"])

    # ── Tables ────────────────────────────────────────────────────────────
    t_name = w.Text(description="Logical name:", placeholder="Customer")
    t_table = w.Text(description="UC Table:", placeholder="catalog.schema.dim_customer")
    t_pk = w.Text(description="Primary key:", placeholder="customer_id")
    t_master = w.Text(description="Master data cols:", placeholder="country_code, currency_code (comma separated)")
    add_table_btn = dashui.action_button("Add Table", style="info")
    tables_output, render_tables = dashui.running_list(
        lambda i, t: f"  {i}. {t['name']} → {t['table']}  (PK: {t['pk'] or '—'}, master data: {', '.join(t['master']) or '—'})"
    )

    from_table_dd = w.Dropdown(options=[t["name"] for t in tables], description="From table:")
    to_table_dd = w.Dropdown(options=[t["name"] for t in tables], description="To table:")

    def _save_state() -> None:
        try:
            dashui.save_config(_LIBRARY, {
                "tables": tables, "foreign_keys": foreign_keys,
                "n_rows": n_rows.value, "preserve_corr": preserve_corr.value,
                "preserve_nulls": preserve_nulls.value, "preserve_dist": preserve_dist.value,
                "output_prefix": output_prefix.value,
            }, name="relationships")
        except Exception:
            pass  # persistence is a convenience, never block the actual operation on it

    def on_add_table(b):
        name = t_name.value.strip()
        if not name or not t_table.value.strip():
            return
        tables.append({
            "name": name, "table": t_table.value.strip(), "pk": t_pk.value.strip(),
            "master": [c.strip() for c in t_master.value.split(",") if c.strip()],
        })
        render_tables(tables)
        names = [t["name"] for t in tables]
        from_table_dd.options = names
        to_table_dd.options = names
        t_name.value = t_table.value = t_pk.value = t_master.value = ""
        _save_state()

    add_table_btn.on_click(on_add_table)

    # ── Foreign keys ─────────────────────────────────────────────────────
    from_col = w.Text(description="From column:", placeholder="customer_id")
    to_col = w.Text(description="To column:", placeholder="customer_id")
    add_fk_btn = dashui.action_button("Add Foreign Key", style="info")
    fks_output, render_fks = dashui.running_list(
        lambda i, fk: f"  {i}. {fk['from_table']}.{fk['from_column']} → {fk['to_table']}.{fk['to_column']}"
    )

    def on_add_fk(b):
        if not from_table_dd.value or not to_table_dd.value:
            return
        foreign_keys.append({
            "from_table": from_table_dd.value, "from_column": from_col.value.strip(),
            "to_table": to_table_dd.value, "to_column": to_col.value.strip(),
        })
        render_fks(foreign_keys)
        from_col.value = to_col.value = ""
        _save_state()

    add_fk_btn.on_click(on_add_fk)

    # ── Generation settings (applied to every table) ────────────────────
    n_rows = w.IntText(value=saved["n_rows"], description="Rows per table:", min=1)
    preserve_corr = w.Checkbox(value=saved["preserve_corr"], description="Preserve correlation structure")
    preserve_nulls = w.Checkbox(value=saved["preserve_nulls"], description="Preserve missing value patterns")
    preserve_dist = w.Checkbox(value=saved["preserve_dist"], description="Preserve marginal distributions")
    output_prefix = w.Text(
        value=saved["output_prefix"], description="Output schema:",
        placeholder="catalog.schema (optional — leave blank to skip saving)",
    )

    validate_btn = dashui.action_button("Validate / Show Order", style="warning")
    run_btn = dashui.action_button("Generate All Tables", style="success")
    output = dashui.output_panel()

    render_tables(tables)
    render_fks(foreign_keys)

    def _build_graph():
        from dashsynthetic.relationships import RelationshipGraph
        graph = RelationshipGraph()
        for t in tables:
            graph.add_table(t["name"], t["table"], t["pk"] or None, t["master"])
        for fk in foreign_keys:
            graph.add_foreign_key(fk["from_table"], fk["from_column"], fk["to_table"], fk["to_column"])
        return graph

    def on_validate(b):
        with output:
            output.clear_output()
            _save_state()
            try:
                _build_graph().summary()
            except Exception as e:
                print(f"Error: {e}")

    def on_run(b):
        with output:
            output.clear_output()
            _save_state()
            try:
                from dashsynthetic.generator import MultiTableGenerator
                graph = _build_graph()
                issues = graph.validate()
                if issues:
                    for i in issues:
                        print(f"{i}")
                    return
                gen = MultiTableGenerator(graph)
                prefix = output_prefix.value.strip()
                for t in tables:
                    output_table = f"{prefix}.{t['name'].lower()}_synthetic" if prefix else None
                    gen.configure_table(
                        t["name"], n_rows=n_rows.value, preserve_corr=preserve_corr.value,
                        preserve_nulls=preserve_nulls.value, preserve_distributions=preserve_dist.value,
                        output_table=output_table,
                    )
                results = gen.run()
                print(f"Generated {len(results)} table(s) in order: {' → '.join(graph.generation_order())}")
                for name, df in results.items():
                    print(f"  - {name}: {df.count():,} rows")
            except Exception as e:
                print(f"Error: {e}")

    validate_btn.on_click(on_validate)
    run_btn.on_click(on_run)

    return dashui.card([
        dashui.section("Step 1: Tables"),
        w.HBox([t_name, t_table]), w.HBox([t_pk, t_master]),
        add_table_btn, tables_output,
        dashui.section("Step 2: Foreign keys"),
        w.HBox([from_table_dd, to_table_dd]), w.HBox([from_col, to_col]),
        add_fk_btn, fks_output,
        dashui.section("Step 3: Generation settings"),
        n_rows, preserve_corr, preserve_nulls, preserve_dist, output_prefix,
        w.HTML("<hr>"),
        w.HBox([validate_btn, run_btn]),
        output,
    ])


def _build_generator(src):
    from dashsynthetic.generator import SyntheticGenerator
    kind, value = src.value()
    if kind == "table":
        return SyntheticGenerator(table=value)
    elif kind == "dataframe":
        return SyntheticGenerator(df=src.resolve_df())
    else:
        return SyntheticGenerator(query=value)
