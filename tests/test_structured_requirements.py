"""
Structured data quality tests for dash-synthetic (no Spark required).

Covers the seven formal data quality requirements:
  R1 — Preservation of Correlation Structure
  R2 — Marginal Distribution Preservation
  R3 — Joint Distribution Fidelity
  R4 — Missing Value Patterns (MCAR, MAR, MNAR)
  R5 — Static or Constant Value Preservation
  R6 — Data Type Integrity
  R7 — Outlier Representation
"""
import pytest
import numpy as np
from dashsynthetic.stats import (
    null_rates,
    column_mean_std,
    categorical_distribution,
    pearson_correlation,
    is_static_column,
    z_scores,
    outlier_indices,
    outlier_rate,
    sample_categorical,
    sample_correlated_normals,
)

RNG = np.random.default_rng(0)


# ── R1: Preservation of Correlation Structure ────────────────────────────────

class TestR1CorrelationPreservation:
    """Synthetic data must maintain pairwise linear relationships from source."""

    def test_strong_positive_correlation_preserved(self):
        n = 2000
        x = list(range(n))
        y = [xi * 0.9 + RNG.normal(0, 10) for xi in x]
        r_source = pearson_correlation(x, y)

        cov = np.cov([x, y])
        means = [np.mean(x), np.mean(y)]
        samples = sample_correlated_normals(means, cov.tolist(), n, seed=1)

        r_synth = pearson_correlation(samples[:, 0].tolist(), samples[:, 1].tolist())
        assert abs(r_synth - r_source) < 0.05, (
            f"Correlation drift too large: source={r_source:.3f}, synth={r_synth:.3f}"
        )

    def test_negative_correlation_preserved(self):
        n = 2000
        x = list(range(n))
        y = [-xi * 0.8 + RNG.normal(0, 5) for xi in x]
        r_source = pearson_correlation(x, y)
        assert r_source < -0.7

        cov = np.cov([x, y])
        means = [np.mean(x), np.mean(y)]
        samples = sample_correlated_normals(means, cov.tolist(), n, seed=2)

        r_synth = pearson_correlation(samples[:, 0].tolist(), samples[:, 1].tolist())
        assert r_synth < -0.7, "Negative correlation not preserved"
        assert abs(r_synth - r_source) < 0.05

    def test_near_zero_correlation_preserved(self):
        n = 2000
        x = RNG.normal(0, 1, n).tolist()
        y = RNG.normal(0, 1, n).tolist()
        r_source = pearson_correlation(x, y)

        cov = np.cov([x, y])
        means = [0.0, 0.0]
        samples = sample_correlated_normals(means, cov.tolist(), n, seed=3)

        r_synth = pearson_correlation(samples[:, 0].tolist(), samples[:, 1].tolist())
        assert abs(r_synth) < 0.1, "Near-zero correlation should remain near zero"

    def test_pearson_correlation_degenerate_inputs_return_zero(self):
        assert pearson_correlation([], []) == 0.0
        assert pearson_correlation([1.0], [2.0]) == 0.0

    def test_pearson_correlation_constant_column_returns_zero(self):
        assert pearson_correlation([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]) == 0.0

    def test_pearson_correlation_none_pairs_ignored(self):
        x = [1.0, None, 3.0, 4.0]
        y = [2.0, 4.0, None, 8.0]
        r = pearson_correlation(x, y)
        assert abs(r - 1.0) < 0.01


# ── R2: Marginal Distribution Preservation ──────────────────────────────────

class TestR2MarginalDistribution:
    """Each column's individual distribution (mean, std, proportions) must match source."""

    def test_numeric_mean_preserved(self):
        source = RNG.normal(100, 15, 500).tolist()
        mean_src, std_src = column_mean_std(source)
        synth = RNG.normal(mean_src, std_src, 2000).tolist()
        mean_syn, _ = column_mean_std(synth)
        assert abs(mean_syn - 100) < 3

    def test_numeric_std_preserved(self):
        source = RNG.normal(50, 8, 500).tolist()
        _, std_src = column_mean_std(source)
        synth = RNG.normal(50, std_src, 2000).tolist()
        _, std_syn = column_mean_std(synth)
        assert abs(std_syn - 8) < 2

    def test_categorical_proportions_preserved_three_classes(self):
        values = ["A"] * 70 + ["B"] * 20 + ["C"] * 10
        vals, probs = categorical_distribution(values)
        synth = sample_categorical(vals, probs, 2000, seed=10)
        synth_vals, synth_probs = categorical_distribution(synth)
        expected = {"A": 0.70, "B": 0.20, "C": 0.10}
        actual = dict(zip(synth_vals, synth_probs))
        for k, p in expected.items():
            assert abs(actual.get(k, 0) - p) < 0.04, (
                f"Proportion mismatch for '{k}': expected {p}, got {actual.get(k, 0):.3f}"
            )

    def test_categorical_proportions_preserved_binary(self):
        values = ["yes"] * 80 + ["no"] * 20
        vals, probs = categorical_distribution(values)
        synth = sample_categorical(vals, probs, 2000, seed=11)
        synth_vals, synth_probs = categorical_distribution(synth)
        actual = dict(zip(synth_vals, synth_probs))
        assert abs(actual.get("yes", 0) - 0.80) < 0.04

    def test_column_mean_std_ignores_none(self):
        values = [10.0, None, 20.0, None, 30.0]
        mean, std = column_mean_std(values)
        assert abs(mean - 20.0) < 1e-6
        assert std > 0

    def test_column_mean_std_empty_returns_defaults(self):
        mean, std = column_mean_std([])
        assert mean == 0.0
        assert std == 1.0

    def test_column_mean_std_all_none_returns_defaults(self):
        mean, std = column_mean_std([None, None])
        assert mean == 0.0
        assert std == 1.0

    def test_categorical_distribution_ignores_none(self):
        values = ["A", None, "B", None, "A"]
        vals, probs = categorical_distribution(values)
        assert None not in vals
        assert abs(sum(probs) - 1.0) < 1e-9


# ── R3: Joint Distribution Fidelity ─────────────────────────────────────────

class TestR3JointDistributionFidelity:
    """Full multivariate structure (all pairwise correlations) must be preserved."""

    def test_three_column_covariance_preserved(self):
        cov_src = np.array([
            [4.0, 2.4, 0.6],
            [2.4, 9.0, 1.8],
            [0.6, 1.8, 1.0],
        ])
        data = RNG.multivariate_normal([10.0, 20.0, 5.0], cov_src, 2000)
        cov_emp = np.cov(data.T)
        synth = sample_correlated_normals(
            [10.0, 20.0, 5.0], cov_emp.tolist(), 2000, seed=20
        )
        for i in range(3):
            for j in range(3):
                if i != j:
                    r_src = pearson_correlation(data[:, i].tolist(), data[:, j].tolist())
                    r_syn = pearson_correlation(synth[:, i].tolist(), synth[:, j].tolist())
                    assert abs(r_syn - r_src) < 0.08, (
                        f"Joint fidelity failure at ({i},{j}): "
                        f"source r={r_src:.3f}, synth r={r_syn:.3f}"
                    )

    def test_marginals_preserved_within_joint_sample(self):
        cov = np.diag([1.0, 4.0, 9.0])
        means = [0.0, 10.0, -5.0]
        data = RNG.multivariate_normal(means, cov, 1000)
        synth = sample_correlated_normals(means, cov.tolist(), 1000, seed=21)

        for i, (expected_mean, expected_std) in enumerate(zip(means, [1.0, 2.0, 3.0])):
            m, s = column_mean_std(synth[:, i].tolist())
            assert abs(m - expected_mean) < 0.3, f"Mean drift in col {i}"
            assert abs(s - expected_std) < 0.3, f"Std drift in col {i}"

    def test_singular_covariance_falls_back_gracefully(self):
        # Perfectly correlated columns → singular covariance matrix
        x = list(range(100))
        y = x  # identical → zero variance in the combined direction
        cov = np.cov([x, y]).tolist()
        # Should not raise; falls back to independent sampling
        samples = sample_correlated_normals([50.0, 50.0], cov, 100, seed=22)
        assert samples.shape == (100, 2)


# ── R4: Missing Value Patterns ───────────────────────────────────────────────

class TestR4MissingValuePatterns:
    """Null rates from source must be faithfully reproduced in synthetic data."""

    def test_mcar_twenty_percent_nulls(self):
        values = [None if i % 5 == 0 else float(i) for i in range(100)]
        rates = null_rates({"col": values})
        assert abs(rates["col"] - 0.20) < 0.01

    def test_no_nulls_in_source_yields_zero_rate(self):
        values = [1.0, 2.0, 3.0, 4.0]
        rates = null_rates({"col": values})
        assert rates["col"] == 0.0

    def test_all_null_yields_rate_one(self):
        values = [None, None, None]
        rates = null_rates({"col": values})
        assert rates["col"] == 1.0

    def test_multiple_columns_tracked_independently(self):
        col_a = [None if i % 4 == 0 else float(i) for i in range(40)]  # 25% null
        col_b = [None if i % 10 == 0 else float(i) for i in range(40)]  # 10% null
        rates = null_rates({"a": col_a, "b": col_b})
        assert abs(rates["a"] - 0.25) < 0.01
        assert abs(rates["b"] - 0.10) < 0.01

    def test_empty_column_yields_zero_rate(self):
        rates = null_rates({"col": []})
        assert rates["col"] == 0.0

    def test_mar_pattern_preserved_per_column(self):
        # MAR: nulls in column B are conditional on column A being low
        col_a = [float(i) for i in range(100)]
        col_b = [None if i < 30 else float(i) for i in range(100)]  # null when A < 30 → 30%
        rates = null_rates({"a": col_a, "b": col_b})
        assert rates["a"] == 0.0
        assert abs(rates["b"] - 0.30) < 0.01

    def test_mnar_high_null_rate_preserved(self):
        # MNAR: 60% of high-value rows are missing
        values = [None] * 60 + [float(i) for i in range(40)]
        rates = null_rates({"col": values})
        assert abs(rates["col"] - 0.60) < 0.01


# ── R5: Static or Constant Value Preservation ───────────────────────────────

class TestR5StaticValuePreservation:
    """Columns where one value dominates must remain constant in synthetic data."""

    def test_constant_column_detected(self):
        values = [42] * 100
        assert is_static_column(values) is True

    def test_near_constant_above_threshold_detected(self):
        values = ["USD"] * 98 + ["EUR"] + ["GBP"]
        assert is_static_column(values, threshold=0.95) is True

    def test_near_constant_below_threshold_not_flagged(self):
        values = ["USD"] * 90 + ["EUR"] * 10
        assert is_static_column(values, threshold=0.95) is False

    def test_even_split_is_not_static(self):
        values = ["A"] * 50 + ["B"] * 50
        assert is_static_column(values, threshold=0.95) is False

    def test_static_detection_ignores_nulls(self):
        # 96 "USD" and 4 None — after ignoring nulls, 100% USD → static
        values = ["USD"] * 96 + [None] * 4
        assert is_static_column(values, threshold=0.95) is True

    def test_all_null_treated_as_static(self):
        assert is_static_column([None, None, None]) is True

    def test_empty_list_treated_as_static(self):
        assert is_static_column([]) is True

    def test_static_column_categorical_sampling_produces_dominant_value(self):
        values = ["USD"] * 99 + ["EUR"]
        vals, probs = categorical_distribution(values)
        synth = sample_categorical(vals, probs, 1000, seed=30)
        usd_rate = synth.count("USD") / len(synth)
        assert usd_rate > 0.95, f"Dominant value not preserved: USD rate = {usd_rate:.3f}"

    def test_custom_threshold_applied_correctly(self):
        values = ["A"] * 85 + ["B"] * 15
        assert is_static_column(values, threshold=0.80) is True
        assert is_static_column(values, threshold=0.90) is False


# ── R6: Data Type Integrity ──────────────────────────────────────────────────

class TestR6DataTypeIntegrity:
    """Synthetic columns must match their source data type and value domain."""

    def test_categorical_sample_only_contains_source_values(self):
        source_values = ["apple", "banana", "cherry"]
        probs = [0.5, 0.3, 0.2]
        synth = sample_categorical(source_values, probs, 2000, seed=40)
        unseen = set(synth) - set(source_values)
        assert not unseen, f"Unseen values in synthetic: {unseen}"

    def test_categorical_all_source_values_can_appear(self):
        source_values = ["X", "Y", "Z"]
        probs = [0.34, 0.33, 0.33]
        synth = sample_categorical(source_values, probs, 3000, seed=41)
        assert set(synth) == set(source_values)

    def test_integer_rounding_preserves_int_type(self):
        samples = RNG.normal(100, 15, 200)
        int_samples = [int(round(float(v))) for v in samples]
        assert all(isinstance(v, int) for v in int_samples)

    def test_float_column_mean_std_returns_floats(self):
        mean, std = column_mean_std([1.5, 2.5, 3.5])
        assert isinstance(mean, float)
        assert isinstance(std, float)

    def test_sampling_with_single_category(self):
        synth = sample_categorical(["ONLY"], [1.0], 100, seed=42)
        assert all(v == "ONLY" for v in synth)

    def test_correlated_sampling_returns_numeric_array(self):
        means = [0.0, 0.0]
        cov = [[1.0, 0.5], [0.5, 1.0]]
        samples = sample_correlated_normals(means, cov, 100, seed=43)
        assert samples.dtype.kind == "f"  # floating-point
        assert samples.shape == (100, 2)

    def test_categorical_distribution_preserves_string_type(self):
        values = ["alpha", "beta", "gamma"]
        vals, probs = categorical_distribution(values)
        assert all(isinstance(v, str) for v in vals)

    def test_large_integer_column_preserves_scale(self):
        source = [50_000.0, 52_000.0, 48_000.0, 51_000.0, 49_000.0]
        mean, std = column_mean_std(source)
        assert 45_000 < mean < 55_000
        assert std < 5_000

    def test_z_score_returns_floats(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        zs = z_scores(values)
        assert all(isinstance(z, float) for z in zs)

    def test_categorical_probability_sum_is_one(self):
        values = ["A"] * 30 + ["B"] * 50 + ["C"] * 20
        _, probs = categorical_distribution(values)
        assert abs(sum(probs) - 1.0) < 1e-9


# ── R7: Outlier Representation ───────────────────────────────────────────────

class TestR7OutlierRepresentation:
    """Extreme values must appear in synthetic data at a proportional rate."""

    def test_single_extreme_outlier_detected(self):
        normal = [100.0] * 97
        outliers = [1000.0, -800.0, 950.0]
        values = normal + outliers
        idx = outlier_indices(values, z_threshold=2.5)
        assert len(idx) >= 1, "At least one outlier should be detected"

    def test_tight_distribution_has_no_outliers(self):
        values = [float(i) for i in range(100)]  # uniform [0, 99], no extreme values
        idx = outlier_indices(values, z_threshold=3.0)
        assert len(idx) == 0

    def test_outlier_rate_low_for_normal_distribution(self):
        data = RNG.normal(0, 1, 10_000).tolist()
        rate = outlier_rate(data, z_threshold=3.0)
        # Theoretical rate at ±3σ is ~0.27 %; allow up to 1 %
        assert rate < 0.01, f"Outlier rate too high for normal data: {rate:.4f}"

    def test_outlier_rate_reflects_injected_proportion(self):
        normal = RNG.normal(100, 5, 98).tolist()
        extreme = [200.0, -50.0]
        values = normal + extreme
        rate = outlier_rate(values, z_threshold=3.0)
        # 2 out of 100 → expect ~2 % with some tolerance
        assert 0.01 <= rate <= 0.05, f"Outlier rate unexpected: {rate:.4f}"

    def test_z_scores_length_matches_non_none_count(self):
        values = [1.0, None, 3.0, None, 5.0]
        zs = z_scores(values)
        non_none = [v for v in values if v is not None]
        assert len(zs) == len(non_none)

    def test_z_scores_empty_for_single_value(self):
        assert z_scores([42.0]) == []

    def test_z_scores_all_zeros_for_constant_column(self):
        values = [7.0] * 10
        zs = z_scores(values)
        assert all(z == 0.0 for z in zs)

    def test_outlier_indices_empty_list(self):
        assert outlier_indices([]) == []

    def test_outlier_indices_all_none(self):
        assert outlier_indices([None, None, None]) == []

    def test_outlier_rate_empty_list_returns_zero(self):
        assert outlier_rate([]) == 0.0

    def test_custom_z_threshold_changes_detection(self):
        values = RNG.normal(0, 1, 500).tolist()
        strict = outlier_indices(values, z_threshold=2.0)
        lenient = outlier_indices(values, z_threshold=4.0)
        assert len(strict) >= len(lenient), (
            "Stricter threshold should flag at least as many outliers"
        )

    def test_outlier_proportion_matches_within_tolerance(self):
        """Synthetic outlier rate should be within 3× of source rate (sampling noise)."""
        source = RNG.normal(0, 1, 1000).tolist()
        source_rate = outlier_rate(source, z_threshold=2.5)

        # Simulate synthetic by re-sampling from the same distribution
        synth = RNG.normal(0, 1, 1000).tolist()
        synth_rate = outlier_rate(synth, z_threshold=2.5)

        # Both should be small; neither should be wildly different from the other
        assert abs(synth_rate - source_rate) < 0.03, (
            f"Outlier rate drift: source={source_rate:.4f}, synth={synth_rate:.4f}"
        )
