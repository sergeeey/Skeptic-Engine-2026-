"""Syndrome-style anomaly decomposition for scientific data integrity."""

from .constraints import ConstraintModel, build_pairwise_constraints
from .scoring import SyndromeResult, compute_syndrome_pairwise
from .reporting import syndrome_to_json, syndrome_to_markdown

__all__ = [
    "ConstraintModel",
    "build_pairwise_constraints",
    "SyndromeResult",
    "compute_syndrome_pairwise",
    "syndrome_to_json",
    "syndrome_to_markdown",
]
