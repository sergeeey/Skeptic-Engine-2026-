"""Count matrix format detection and loading for H26 GEO screening.

Handles MTX, H5, CSV/TSV formats commonly found in GEO supplementary files.
"""

from __future__ import annotations

import csv
import gzip
from pathlib import Path

import numpy as np
from scipy.io import mmread


def detect_format(path: Path) -> str:
    """Detect the format of a count matrix file."""
    name = path.name.lower()
    if ".mtx" in name:
        return "mtx"
    if name.endswith(".h5") or name.endswith(".hdf5"):
        return "h5"
    if ".csv" in name:
        return "csv"
    if ".tsv" in name or ".txt" in name:
        return "tsv"
    return "unknown"


def load_count_matrix(path: Path, max_cells: int = 5000) -> np.ndarray | None:
    """Load a count matrix from any supported format.

    Returns (cells x genes) int64 matrix, or None on failure.
    Subsamples to max_cells if larger.
    """
    fmt = detect_format(path)

    try:
        if fmt == "mtx":
            matrix = _load_mtx(path)
        elif fmt == "h5":
            matrix = _load_h5(path)
        elif fmt in ("csv", "tsv"):
            matrix = _load_delimited(path, fmt)
        else:
            return None

        if matrix is None or matrix.size == 0:
            return None

        # Subsample if too large
        if matrix.shape[0] > max_cells:
            rng = np.random.default_rng(42)
            idx = rng.choice(matrix.shape[0], size=max_cells, replace=False)
            matrix = matrix[idx]

        return matrix.astype(np.int64)

    except Exception as e:
        print(f"    Load error ({path.name}): {e}")
        return None


def _load_mtx(path: Path) -> np.ndarray | None:
    """Load Matrix Market format (.mtx or .mtx.gz)."""
    try:
        if path.suffix == ".gz" or ".mtx.gz" in path.name:
            import tempfile
            import shutil

            # WHY: NamedTemporaryFile (not mktemp) avoids TOCTOU race condition
            with tempfile.NamedTemporaryFile(suffix=".mtx", delete=False) as tmp_f:
                tmp = Path(tmp_f.name)
                with gzip.open(path, "rb") as gz_in:
                    shutil.copyfileobj(gz_in, tmp_f)
            sparse = mmread(str(tmp))
            tmp.unlink(missing_ok=True)
        else:
            sparse = mmread(str(path))

        dense = sparse.toarray()
        # 10x format is genes x cells — transpose if more genes than cells
        if dense.shape[0] > dense.shape[1]:
            dense = dense.T
        return dense
    except Exception:
        return None


def _load_h5(path: Path) -> np.ndarray | None:
    """Load HDF5 count matrix (10x Genomics or AnnData format)."""
    try:
        import h5py
    except ImportError:
        print("    h5py not installed — skipping H5 file")
        return None

    try:
        with h5py.File(path, "r") as f:
            # Try 10x Genomics v3 format
            if "matrix" in f:
                group = f["matrix"]
                from scipy.sparse import csc_matrix

                data = np.array(group["data"])
                indices = np.array(group["indices"])
                indptr = np.array(group["indptr"])
                shape = tuple(group["shape"])
                sparse = csc_matrix((data, indices, indptr), shape=shape)
                return sparse.toarray().T

            # Try AnnData format (X dataset)
            if "X" in f:
                X = f["X"]
                if hasattr(X, "toarray"):
                    return np.array(X.toarray())
                return np.array(X)

            # Try generic "counts" or "raw" groups
            for key in ["counts", "raw", "data"]:
                if key in f:
                    return np.array(f[key])

        return None
    except Exception:
        return None


def _load_delimited(path: Path, fmt: str) -> np.ndarray | None:
    """Load CSV or TSV count matrix."""
    preview = _read_preview_lines(path)
    if not preview:
        return None

    delimiter = _sniff_delimiter(preview[0], fmt)
    header_tokens = _parse_delimited_line(preview[0], delimiter)
    data_tokens = _parse_delimited_line(preview[1], delimiter) if len(preview) > 1 else []

    has_header = bool(header_tokens) and (
        header_tokens[0] == "" or not _is_numeric_token(header_tokens[0])
    )
    first_data_tokens = data_tokens if has_header else header_tokens
    has_row_labels = bool(first_data_tokens) and not _is_numeric_token(first_data_tokens[0])

    n_cols = len(first_data_tokens)
    if n_cols <= (1 if has_row_labels else 0):
        return None

    usecols = tuple(range(1 if has_row_labels else 0, n_cols))

    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", newline="") as f:
                data = np.loadtxt(
                    f,
                    delimiter=delimiter,
                    skiprows=1 if has_header else 0,
                    usecols=usecols,
                    ndmin=2,
                )
        else:
            data = np.loadtxt(
                path,
                delimiter=delimiter,
                skiprows=1 if has_header else 0,
                usecols=usecols,
                ndmin=2,
            )

        if has_row_labels:
            data = data.T
        return data
    except Exception:
        return None


def _read_preview_lines(path: Path, n_lines: int = 2) -> list[str]:
    opener = gzip.open if path.suffix == ".gz" else open
    lines: list[str] = []
    with opener(path, "rt", newline="") as f:
        for _ in range(n_lines):
            line = f.readline()
            if not line:
                break
            lines.append(line.rstrip("\r\n"))
    return lines


def _sniff_delimiter(line: str, fmt: str) -> str:
    candidates = [",", ";", "\t"]
    if fmt == "tsv":
        candidates = ["\t", ";", ","]
    counts = {delimiter: line.count(delimiter) for delimiter in candidates}
    best = max(candidates, key=lambda delimiter: counts[delimiter])
    if counts[best] == 0:
        return "\t" if fmt == "tsv" else ","
    return best


def _parse_delimited_line(line: str, delimiter: str) -> list[str]:
    return next(csv.reader([line], delimiter=delimiter))


def _is_numeric_token(token: str) -> bool:
    stripped = token.strip().strip('"')
    if stripped == "":
        return False
    try:
        float(stripped)
        return True
    except ValueError:
        return False
