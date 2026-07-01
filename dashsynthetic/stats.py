"""
Pure-Python statistical primitives for synthetic data generation.

No Spark dependency — all functions work with plain Python lists so they are
unit-testable without a live cluster. engine.py uses these under the hood.
"""
from __future__ import annotations
import numpy as np


# ── Descriptive ─────────────────────────────────────────────────────────────

def null_rates(col_data: dict) -> dict:
    """Return {col: fraction_null} for each column in col_data ({col: [values]})."""
    rates = {}
    for col, vals in col_data.items():
        n = len(vals)
        rates[col] = sum(1 for v in vals if v is None) / n if n else 0.0
    return rates


def column_mean_std(values: list) -> tuple[float, float]:
    """Mean and sample std of non-None numeric values. Returns (0.0, 1.0) when empty."""
    clean = [v for v in values if v is not None]
    if not clean:
        return 0.0, 1.0
    n = len(clean)
    mean = sum(clean) / n
    variance = sum((x - mean) ** 2 for x in clean) / max(n - 1, 1)
    return mean, variance ** 0.5


def categorical_distribution(values: list) -> tuple[list, list]:
    """
    Compute value probabilities from a list, ignoring None.
    Returns (sorted_unique_values, probabilities).
    """
    clean = [v for v in values if v is not None]
    if not clean:
        return [], []
    counts: dict = {}
    for v in clean:
        counts[v] = counts.get(v, 0) + 1
    total = len(clean)
    sorted_items = sorted(counts.items(), key=lambda x: str(x[0]))
    return [k for k, _ in sorted_items], [c / total for _, c in sorted_items]


def pearson_correlation(x: list, y: list) -> float:
    """Pearson r between two numeric lists (None-pairs excluded). Returns 0.0 if degenerate."""
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pairs) < 2:
        return 0.0
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    _, sx = column_mean_std(xs)
    _, sy = column_mean_std(ys)
    if sx < 1e-10 or sy < 1e-10:
        return 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    n = len(xs)
    cov = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / max(n - 1, 1)
    return cov / (sx * sy)


# ── Static / outlier detection ───────────────────────────────────────────────

def is_static_column(values: list, threshold: float = 0.95) -> bool:
    """
    True if one value accounts for >= threshold of non-null values.
    Use to detect constant or near-constant columns (e.g. single-currency tables).
    """
    clean = [v for v in values if v is not None]
    if not clean:
        return True
    counts: dict = {}
    for v in clean:
        counts[v] = counts.get(v, 0) + 1
    return max(counts.values()) / len(clean) >= threshold


def z_scores(values: list) -> list[float]:
    """Z-score for each non-None value. Returns [] when fewer than 2 values."""
    clean = [v for v in values if v is not None]
    if len(clean) < 2:
        return []
    mean, std = column_mean_std(clean)
    if std < 1e-10:
        return [0.0] * len(clean)
    return [(v - mean) / std for v in clean]


def outlier_indices(values: list, z_threshold: float = 3.0) -> list[int]:
    """
    Indices (into the non-None values) where |z-score| > z_threshold.
    Outlier proportion ≈ len(result) / len(non-None values).
    """
    zs = z_scores(values)
    return [i for i, z in enumerate(zs) if abs(z) > z_threshold]


def outlier_rate(values: list, z_threshold: float = 3.0) -> float:
    """Fraction of non-None values that are outliers."""
    clean = [v for v in values if v is not None]
    if not clean:
        return 0.0
    return len(outlier_indices(values, z_threshold)) / len(clean)


# ── Sampling ─────────────────────────────────────────────────────────────────

def sample_categorical(values: list, probs: list, n: int, seed: int = None) -> list:
    """
    Sample n values from a categorical distribution.
    Only values present in the source can appear in the output (Data Type Integrity).
    """
    rng = np.random.default_rng(seed)
    arr = np.array(probs, dtype=float)
    arr = arr / arr.sum()
    return list(rng.choice(values, size=n, p=arr))


def sample_correlated_normals(
    means: list, cov_matrix: list, n: int, seed: int = None
) -> np.ndarray:
    """
    Sample n rows of correlated normal data.
    Returns ndarray of shape (n, len(means)).
    Falls back to independent normals if the covariance matrix is not positive-definite.
    """
    rng = np.random.default_rng(seed)
    cov = np.array(cov_matrix, dtype=float)
    try:
        return rng.multivariate_normal(means, cov, n)
    except (np.linalg.LinAlgError, ValueError):
        stds = [max(cov[i, i] ** 0.5, 1e-6) for i in range(len(means))]
        return np.column_stack([rng.normal(m, s, n) for m, s in zip(means, stds)])
