"""Skeptic Engine — Statistical artifact detection for scientific data integrity."""

__version__ = "0.2.0"

from .cli import main, compute_scores, load_count_matrix  # noqa: F401
from .integrity import (  # noqa: F401
    compute_hash,
    verify_file_integrity,
    verify_against_zenodo,
    fetch_zenodo_checksums,
)
from .verdict import Verdict, VerdictLevel, make_verdict  # noqa: F401
from .verified_result import VerifiedResult  # noqa: F401
