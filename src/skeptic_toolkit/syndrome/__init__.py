"""Syndrome-style anomaly decomposition for scientific data integrity."""

from .constraints import (
    ConstraintModel,
    Module,
    build_pairwise_constraints,
    build_residual_constraints,
)
from .scoring import SyndromeResult, compute_syndrome_pairwise
from .reporting import syndrome_to_json, syndrome_to_markdown, syndrome_to_csv

__all__ = [
    "ConstraintModel",
    "Module",
    "build_pairwise_constraints",
    "build_residual_constraints",
    "SyndromeResult",
    "compute_syndrome_pairwise",
    "syndrome_to_json",
    "syndrome_to_markdown",
    "syndrome_to_csv",
]
