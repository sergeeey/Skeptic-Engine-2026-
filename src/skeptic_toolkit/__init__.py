"""Skeptic Engine — Statistical artifact detection for scientific data integrity."""

__version__ = "0.1.1"

from .cli import main, compute_scores, load_count_matrix  # noqa: F401
from .verdict import Verdict, VerdictLevel, make_verdict  # noqa: F401
from .verified_result import VerifiedResult  # noqa: F401
