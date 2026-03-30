"""Count matrix format detection and loading for H26 GEO screening.

Handles MTX, H5, CSV/TSV formats commonly found in GEO supplementary files.
"""

from __future__ import annotations

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

            # Decompress to temp file for mmread
            with gzip.open(path, "rb") as gz_in:
                tmp = Path(tempfile.mktemp(suffix=".mtx"))
                with open(tmp, "wb") as f_out:
                    shutil.copyfileobj(gz_in, f_out)
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
    delimiter = "," if fmt == "csv" else "\t"

    try:
        if path.suffix == ".gz":
            import io

            with gzip.open(path, "rt") as f:
                # Read first line to check for header
                first_line = f.readline()
                f.seek(0)
                has_header = (
                    not first_line.strip()
                    .replace(delimiter, "")
                    .replace(".", "")
                    .replace("-", "")
                    .isdigit()
                )
                skiprows = 1 if has_header else 0
                data = np.loadtxt(f, delimiter=delimiter, skiprows=skiprows)
        else:
            with open(path, "r") as f:
                first_line = f.readline()
            has_header = (
                not first_line.strip()
                .replace(delimiter, "")
                .replace(".", "")
                .replace("-", "")
                .isdigit()
            )
            skiprows = 1 if has_header else 0
            data = np.loadtxt(path, delimiter=delimiter, skiprows=skiprows)

        if data.ndim == 1:
            return None
        return data
    except Exception:
        return None
