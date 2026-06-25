"""DashSynthetic interactive UI for Databricks notebooks."""
from __future__ import annotations


def launch():
    try:
        import ipywidgets as w
        from IPython.display import display
    except ImportError:
        raise RuntimeError("ipywidgets required. Run: %pip install ipywidgets")

    source_toggle = w.ToggleButtons(
        options=["UC Table", "DataFrame variable", "SQL Query"],
        description="Source:",
    )
    table_input = w.Text(placeholder="catalog.schema.table", description="Table:")
    df_input = w.Text(placeholder="df", description="Variable:")
    sql_input = w.Textarea(placeholder="SELECT * FROM ...", description="SQL:", rows=3)
    source_box = w.VBox([table_input])

    def on_source(change):
        if change["new"] == "UC Table":
            source_box.children = [table_input]
        elif change["new"] == "DataFrame variable":
            source_box.children = [df_input]
        else:
            source_box.children = [sql_input]

    source_toggle.observe(on_source, names="value")

    n_rows = w.IntText(value=10000, description="Rows to generate:", min=1)
    preserve_corr = w.Checkbox(value=True, description="Preserve correlation structure")
    preserve_nulls = w.Checkbox(value=True, description="Preserve missing value patterns")
    preserve_dist = w.Checkbox(value=True, description="Preserve marginal distributions")

    save_toggle = w.Checkbox(value=False, description="Save to Delta table")
    save_input = w.Text(placeholder="catalog.schema.synthetic_output", description="Output table:", disabled=True)
    save_toggle.observe(lambda c: setattr(save_input, "disabled", not c["new"]), names="value")

    profile_btn = w.Button(description="🔍 Profile source", button_style="info")
    run_btn = w.Button(description="▶ Generate Synthetic Data", button_style="success",
                       layout=w.Layout(height="40px"))
    output = w.Output()

    def on_profile(b):
        with output:
            output.clear_output()
            try:
                gen = _build_generator(source_toggle.value, table_input.value,
                                       df_input.value, sql_input.value)
                import json
                profile = gen.profile()
                print(json.dumps({k: v for k, v in list(profile["columns"].items())[:5]}, indent=2, default=str))
                print(f"\n... {len(profile['columns'])} columns total, {profile['total_rows']:,} rows")
            except Exception as e:
                print(f"❌ {e}")

    def on_run(b):
        with output:
            output.clear_output()
            try:
                gen = _build_generator(source_toggle.value, table_input.value,
                                       df_input.value, sql_input.value)
                gen.set_volume(n_rows.value) \
                   .preserve_correlations(preserve_corr.value) \
                   .preserve_null_patterns(preserve_nulls.value) \
                   .preserve_distributions(preserve_dist.value)
                if save_toggle.value and save_input.value.strip():
                    gen.output_to(save_input.value.strip())
                syn_df = gen.run()
                print(f"✅ Generated {syn_df.count():,} synthetic rows")
                syn_df.show(5, truncate=True)
            except Exception as e:
                print(f"❌ {e}")

    profile_btn.on_click(on_profile)
    run_btn.on_click(on_run)

    ui = w.VBox([
        w.HTML("<h2 style='color:#7B1FA2'>🧬 DashSynthetic — Synthetic Data Generation</h2>"),
        w.HTML("<b>Step 1: Source data</b>"),
        source_toggle, source_box,
        w.HTML("<hr><b>Step 2: Generation settings</b>"),
        n_rows, preserve_corr, preserve_nulls, preserve_dist,
        w.HTML("<hr><b>Step 3: Output</b>"),
        save_toggle, save_input,
        w.HTML("<hr>"),
        w.HBox([profile_btn, run_btn]),
        output,
    ], layout=w.Layout(padding="16px", border="1px solid #ddd", border_radius="8px"))

    display(ui)


def _build_generator(source, table, df_var, sql):
    from dashsynthetic.generator import SyntheticGenerator
    import IPython
    shell = IPython.get_ipython()
    if source == "UC Table":
        return SyntheticGenerator(table=table.strip())
    elif source == "DataFrame variable":
        df = shell.user_ns.get(df_var.strip()) if shell else None
        if df is None:
            raise ValueError(f"Variable '{df_var}' not found")
        return SyntheticGenerator(df=df)
    else:
        return SyntheticGenerator(query=sql.strip())
