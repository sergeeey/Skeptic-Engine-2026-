"""Benford digit frequency extraction for count matrices."""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray


# Benford expected frequencies for first digit (1-9).
BENFORD_FIRST: NDArray[np.float64] = np.array([math.log10(1 + 1 / d) for d in range(1, 10)])

# Benford expected frequencies for second digit (0-9).
BENFORD_SECOND: NDArray[np.float64] = np.array(
    [sum(math.log10(1 + 1 / (10 * d1 + d2)) for d1 in range(1, 10)) for d2 in range(10)]
)


def _first_digit(x: int) -> int:
    """Return leading digit (1-9) of a positive integer."""
    while x >= 10:
        x //= 10
    return x


def _second_digit(x: int) -> int:
    """Return second digit (0-9) of an integer >= 10. Returns -1 for single-digit."""
    if x < 10:
        return -1
    while x >= 100:
        x //= 10
    return x % 10


def first_digit_frequencies(values: NDArray[np.int64]) -> NDArray[np.float64]:
    """Compute first-digit frequency distribution (9 bins: digits 1-9).

    Only nonzero values are considered. Vectorized for performance on large arrays.
    """
    nonzero = values[values > 0].astype(np.float64)
    if len(nonzero) == 0:
        return np.zeros(9, dtype=np.float64)

    # WHY: vectorized first-digit extraction — ~100x faster than pure Python loop on PBMC3k scale
    digits = np.floor(nonzero / (10.0 ** np.floor(np.log10(nonzero)))).astype(int)
    digits = np.clip(digits, 1, 9)
    counts = np.bincount(digits, minlength=10)[1:].astype(np.float64)

    total = counts.sum()
    if total > 0:
        counts /= total
    return counts


def second_digit_frequencies(values: NDArray[np.int64]) -> NDArray[np.float64]:
    """Compute second-digit frequency distribution (10 bins: digits 0-9).

    Only values >= 10 are considered (single-digit numbers have no second digit).
    Vectorized for performance on large arrays.
    """
    eligible = values[values >= 10].astype(np.float64)
    if len(eligible) == 0:
        return np.zeros(10, dtype=np.float64)

    # WHY: vectorized second-digit extraction — remove first digit, take leading digit of remainder
    magnitude = 10.0 ** np.floor(np.log10(eligible))
    first = np.floor(eligible / magnitude)
    remainder = eligible - first * magnitude
    # For 2-digit numbers (magnitude=10), second digit = remainder itself
    # For 3+ digit numbers, extract leading digit of remainder
    sub_magnitude = np.maximum(magnitude / 10.0, 1.0)
    digits = np.floor(remainder / sub_magnitude).astype(int)
    digits = np.clip(digits, 0, 9)
    counts = np.bincount(digits, minlength=10).astype(np.float64)

    total = counts.sum()
    if total > 0:
        counts /= total
    return counts


def chi2_vs_benford(
    observed_freq: NDArray[np.float64], expected_freq: NDArray[np.float64]
) -> float:
    """Chi-squared statistic of observed digit frequencies vs Benford expected."""
    mask = expected_freq > 0
    if mask.sum() == 0:
        return 0.0
    diff = observed_freq[mask] - expected_freq[mask]
    return float(np.sum(diff**2 / expected_freq[mask]))


def benford_feature_vector(values: NDArray[np.int64]) -> NDArray[np.float64]:
    """Extract full Benford feature vector from a 1D array of count values.

    Returns 21 features:
      [0:9]   — first-digit frequencies (digits 1-9)
      [9:19]  — second-digit frequencies (digits 0-9)
      [19]    — chi2 first-digit vs Benford
      [20]    — chi2 second-digit vs Benford
    """
    fd = first_digit_frequencies(values)
    sd = second_digit_frequencies(values)
    chi2_fd = chi2_vs_benford(fd, BENFORD_FIRST)
    chi2_sd = chi2_vs_benford(sd, BENFORD_SECOND)
    return np.concatenate([fd, sd, [chi2_fd, chi2_sd]])


def extract_features_per_sample(
    count_matrix: NDArray[np.int64],
) -> NDArray[np.float64]:
    """Extract Benford features for each row (sample/cell) in a count matrix.

    Args:
        count_matrix: shape (n_samples, n_genes), integer counts.

    Returns:
        Feature matrix shape (n_samples, 21).
    """
    n_samples = count_matrix.shape[0]
    features = np.zeros((n_samples, 21), dtype=np.float64)
    for i in range(n_samples):
        features[i] = benford_feature_vector(count_matrix[i])
    return features


def extract_features_per_gene(
    count_matrix: NDArray[np.int64],
) -> NDArray[np.float64]:
    """Extract Benford features for each column (gene) in a count matrix.

    Args:
        count_matrix: shape (n_samples, n_genes), integer counts.

    Returns:
        Feature matrix shape (n_genes, 21).
    """
    n_genes = count_matrix.shape[1]
    features = np.zeros((n_genes, 21), dtype=np.float64)
    for j in range(n_genes):
        features[j] = benford_feature_vector(count_matrix[:, j])
    return features
