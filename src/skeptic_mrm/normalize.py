"""SE-MRM normalize module — validation, dedup, fingerprinting."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from skeptic_mrm.schemas.material_candidate import MaterialCandidate


@dataclass(frozen=True)
class NormalizationReport:
    """Report on normalization results."""

    total_input: int
    kept: int
    rejected: int
    deduplicated: int
    rejections: list[dict[str, str]] = field(default_factory=list)  # {candidate_id, reason}

    def to_dict(self) -> dict:
        return {
            "total_input": self.total_input,
            "kept": self.kept,
            "rejected": self.rejected,
            "deduplicated": self.deduplicated,
            "rejections": self.rejections,
        }


# ── Composition validator ──────────────────────────────────────────

_COMPOSITION_RE = re.compile(r"^([A-Z][a-z]?\d*\s*)+$")


def _validate_composition(comp: str) -> tuple[bool, str]:
    """Check if composition string looks like a valid chemical formula."""
    if not comp or comp == "unknown" or comp == "pending_fetch":
        return True, "skipped"
    if not _COMPOSITION_RE.match(comp.strip()):
        return False, f"invalid composition format: {comp!r}"
    return True, "ok"


# ── Structure fingerprint ──────────────────────────────────────────


def compute_fingerprint(candidate: MaterialCandidate) -> str:
    """Compute a structural fingerprint for deduplication.

    For v0.1 this is a hash of composition + normalized structure_blob.
    A proper structural fingerprint (e.g. RDF-based) is deferred.
    """
    payload = f"{candidate.composition}|{candidate.structure_blob.strip()}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ── Geometry sanity checks ─────────────────────────────────────────


def _check_structure_sanity(candidate: MaterialCandidate) -> tuple[bool, str]:
    """Basic sanity checks on structure data.

    v0.1 checks:
    - CIF must have at least one _cell_length or lattice line
    - POSCAR must have at least 4 lines
    - JSON/MP-ID always pass (deferred to backend)
    """
    fmt = candidate.structure_format
    blob = candidate.structure_blob

    if fmt in ("json", "mp_id"):
        return True, "deferred"

    if fmt == "cif":
        # Look for cell parameters or at least _cell_length
        has_cell = any(
            line.strip().startswith(("_cell_length", "lattice_", "_symmetry"))
            for line in blob.splitlines()
        )
        if not has_cell:
            return False, "cif missing cell parameters"
        return True, "ok"

    if fmt == "poscar":
        lines = [l for l in blob.splitlines() if l.strip()]
        if len(lines) < 4:
            return False, "poscar too few lines"
        return True, "ok"

    return True, "unknown format, deferred"


# ── Main normalization ─────────────────────────────────────────────


def normalize_candidates(
    candidates: list[MaterialCandidate],
) -> tuple[list[MaterialCandidate], NormalizationReport]:
    """Validate, deduplicate, and fingerprint candidates.

    Returns (kept_candidates, report).
    """
    kept: list[MaterialCandidate] = []
    rejections: list[dict[str, str]] = []
    seen_fps: set[str] = set()
    dedup_count = 0

    for c in candidates:
        # 1. Composition check
        comp_valid, comp_msg = _validate_composition(c.composition)
        if not comp_valid:
            rejections.append({"candidate_id": c.candidate_id, "reason": comp_msg})
            continue

        # 2. Structure sanity
        struct_ok, struct_msg = _check_structure_sanity(c)
        if not struct_ok:
            rejections.append({"candidate_id": c.candidate_id, "reason": struct_msg})
            continue

        # 3. Dedup via fingerprint
        fp = compute_fingerprint(c)
        if fp in seen_fps:
            dedup_count += 1
            continue
        seen_fps.add(fp)

        kept.append(c)

    report = NormalizationReport(
        total_input=len(candidates),
        kept=len(kept),
        rejected=len(rejections),
        deduplicated=dedup_count,
        rejections=rejections,
    )
    return kept, report
