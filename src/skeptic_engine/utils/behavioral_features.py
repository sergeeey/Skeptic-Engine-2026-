"""Behavioral feature extraction from p-value sequences.

This module provides functions to extract fraud-style behavioral features
from sequences of p-values, originally developed for H23 p-hacking detection
and reused across H27 (clinical trials) and H28 (paper mills).

The 18 features capture the "behavioral fingerprint" of the research process,
detecting patterns consistent with p-hacking or selective reporting.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import numpy as np

__all__ = [
    "extract_behavioral_features",
    "pcurve_test_stat",
    "extract_pvalues_regex",
    "FEATURE_NAMES",
]

FEATURE_NAMES = [
    "mean_p",
    "std_p",
    "min_p",
    "frac_sig",
    "frac_gray_zone",
    "frac_just_below_05",
    "mean_delta",
    "volatility",
    "frac_decreasing",
    "final_p",
    "success_flag",
    "total_drift",
    "entropy",
    "seq_length",
    "log_seq_length",
    "direction_change_rate",
    "max_jump",
    "trend_corr",
]


def extract_behavioral_features(p_values: Sequence[float] | np.ndarray) -> np.ndarray:
    """Extract fraud-style behavioral features from a p-value sequence.

    Parameters
    ----------
    p_values : Sequence[float] | np.ndarray
        Sequence of p-values from a study or paper.

    Returns
    -------
    np.ndarray
        18-dimensional feature vector capturing behavioral fingerprint.

    Notes
    -----
    Features include:
    - Basic p-value statistics (mean, std, min)
    - Distribution shape (fraction significant, gray zone, just below 0.05)
    - Sequence dynamics (velocity, direction changes)
    - Terminal behavior (final p-value, success flag)
    - Entropy and regularity
    - Suspicious patterns (direction change rate, max jump, trend)
    """
    p_sequence = np.asarray(p_values, dtype=np.float64)
    n = len(p_sequence)
    if n == 0:
        return np.zeros(18)

    p = np.clip(p_sequence, 1e-15, 1.0)

    features: list[float] = []

    # 1-3: Basic p-value statistics
    features.append(float(np.mean(p)))  # mean p-value
    features.append(float(np.std(p)) if n > 1 else 0.0)  # std of p-values
    features.append(float(np.min(p)))  # minimum p-value

    # 4-6: Distribution shape
    features.append(float((p < 0.05).sum() / n))  # fraction significant
    features.append(
        float((p < 0.10).sum() / n - (p < 0.05).sum() / n)
    )  # fraction in "gray zone" 0.05-0.10
    features.append(float(((p > 0.04) & (p < 0.05)).sum() / max(n, 1)))  # fraction just below 0.05

    # 7-9: Sequence dynamics (fraud-style: velocity, direction changes)
    if n > 1:
        diffs = np.diff(p)
        features.append(float(np.mean(diffs)))  # mean delta (trend)
        features.append(float(np.std(diffs)))  # volatility of deltas
        features.append(float((diffs < 0).sum() / len(diffs)))  # fraction of decreasing steps
    else:
        features.extend([0.0, 0.0, 0.0])

    # 10-12: Terminal behavior (fraud: what happens at the end?)
    features.append(float(p[-1]))  # final p-value
    features.append(1.0 if p[-1] < 0.05 else 0.0)  # did they "succeed"?
    features.append(float(p[-1] - p[0]) if n > 1 else 0.0)  # total drift

    # 13-15: Entropy and regularity
    hist, _ = np.histogram(p, bins=10, range=(0, 1))
    hist_norm = hist / max(hist.sum(), 1)
    entropy = -np.sum(hist_norm[hist_norm > 0] * np.log2(hist_norm[hist_norm > 0]))
    features.append(float(entropy))  # Shannon entropy of p-distribution
    features.append(float(n))  # sequence length
    features.append(float(np.log1p(n)))  # log sequence length

    # 16-18: Suspicious patterns
    features.append(
        float(np.sum(np.abs(np.diff(np.sign(np.diff(p)))) > 0) / max(n - 2, 1)) if n > 2 else 0.0
    )  # direction change rate
    features.append(float(np.max(np.abs(np.diff(p)))) if n > 1 else 0.0)  # max single-step jump
    features.append(
        float(np.corrcoef(np.arange(n), p)[0, 1]) if n > 2 else 0.0
    )  # trend correlation

    return np.array(features[:18])


def pcurve_test_stat(p_sequence: Sequence[float] | np.ndarray) -> float:
    """Simple p-curve right-skew test: fraction of significant p-values < 0.025.

    Under real effect: most sig p-values cluster near 0.
    Under p-hacking: p-values cluster just below 0.05.

    Parameters
    ----------
    p_sequence : Sequence[float] | np.ndarray
        Sequence of p-values.

    Returns
    -------
    float
        Fraction of significant p-values that are < 0.025.
        Returns 0.5 if no significant p-values exist.
    """
    p = np.asarray(p_sequence, dtype=np.float64)
    sig = p[p < 0.05]
    if len(sig) == 0:
        return 0.5
    return float((sig < 0.025).mean())


def extract_pvalues_regex(text: str) -> list[float]:
    """Extract p-values from text using regex patterns for APA-style reporting.

    Matches patterns like:
    - p = 0.023, p=.023, p < .001, p < 0.001
    - (p = 0.05), p = 0.001

    Parameters
    ----------
    text : str
        Text content (e.g., paper fulltext) to extract p-values from.

    Returns
    -------
    list[float]
        Extracted p-values.
    """
    # Pattern matches: p = 0.023, p=.023, p < .001, p < 0.001
    pattern = r"p\s*[<>=]\s*\.?(\d+(?:\.\d+)?)"

    p_values = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        try:
            p_str = match.group(1)
            # Handle cases like ".023" → "0.023"
            if p_str.startswith("."):
                p_str = "0" + p_str
            p_val = float(p_str)
            if 0 <= p_val <= 1:
                p_values.append(p_val)
        except (ValueError, IndexError):
            continue

    return p_values
