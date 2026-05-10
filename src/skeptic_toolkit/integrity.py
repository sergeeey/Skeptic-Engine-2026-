"""File integrity verification for Skeptic Engine.

Prevents analysis of untrusted files by verifying checksums against
canonical sources (Zenodo, arXiv, etc.).

Created 2026-05-10 in response to ARCHCODE version mismatch incident.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Literal, Optional

import requests


def compute_hash(file_path: Path, algorithm: Literal["md5", "sha256"] = "sha256") -> str:
    """Compute file hash with given algorithm.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm ("md5" or "sha256")

    Returns:
        Hexadecimal hash string

    Example:
        >>> compute_hash(Path("data.csv"), "md5")
        '5478a2662af82dbf6b8473391e18d12d'
    """
    if algorithm == "md5":
        hasher = hashlib.md5()
    elif algorithm == "sha256":
        hasher = hashlib.sha256()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def verify_file_integrity(
    file_path: Path,
    expected_md5: Optional[str] = None,
    expected_sha256: Optional[str] = None,
) -> dict[str, str | bool | list[str]]:
    """Verify file integrity against expected checksums.

    Args:
        file_path: Path to file to verify
        expected_md5: Expected MD5 hash (optional)
        expected_sha256: Expected SHA256 hash (optional)

    Returns:
        Dictionary with keys:
            - verified (bool): True if all provided checksums match
            - md5 (str): Computed MD5 hash
            - sha256 (str): Computed SHA256 hash
            - mismatches (list[str]): Human-readable mismatch descriptions

    Example:
        >>> result = verify_file_integrity(
        ...     Path("paper.pdf"),
        ...     expected_md5="5478a2662af82dbf6b8473391e18d12d"
        ... )
        >>> result["verified"]
        True
    """
    if not file_path.exists():
        return {
            "verified": False,
            "md5": "",
            "sha256": "",
            "mismatches": [f"File not found: {file_path}"],
        }

    actual_md5 = compute_hash(file_path, "md5")
    actual_sha256 = compute_hash(file_path, "sha256")

    mismatches: list[str] = []

    if expected_md5 and actual_md5 != expected_md5.lower():
        mismatches.append(f"MD5 mismatch:\n  Expected: {expected_md5}\n  Actual:   {actual_md5}")

    if expected_sha256 and actual_sha256 != expected_sha256.lower():
        mismatches.append(
            f"SHA256 mismatch:\n  Expected: {expected_sha256}\n  Actual:   {actual_sha256}"
        )

    return {
        "verified": len(mismatches) == 0,
        "md5": actual_md5,
        "sha256": actual_sha256,
        "mismatches": mismatches,
    }


def fetch_zenodo_checksums(doi: str) -> dict[str, str]:
    """Fetch MD5 checksums from Zenodo record.

    Args:
        doi: Zenodo DOI (e.g., "10.5281/zenodo.19238786")

    Returns:
        Dictionary mapping filenames to MD5 hashes

    Raises:
        requests.HTTPError: If Zenodo API request fails
        ValueError: If DOI format is invalid

    Example:
        >>> checksums = fetch_zenodo_checksums("10.5281/zenodo.19238786")
        >>> checksums["skeptic_engine_v0.1.0.tar.gz"]
        '5478a2662af82dbf6b8473391e18d12d'
    """
    # Extract record ID from DOI
    if not doi.startswith("10.5281/zenodo."):
        raise ValueError(f"Invalid Zenodo DOI format: {doi}")

    record_id = doi.split("zenodo.")[1]

    # Fetch record metadata from Zenodo API
    url = f"https://zenodo.org/api/records/{record_id}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()

    # Extract checksums from files
    checksums = {}
    for file_info in data.get("files", []):
        filename = file_info["key"]
        md5_hash = file_info["checksum"].replace("md5:", "")
        checksums[filename] = md5_hash

    return checksums


def verify_against_zenodo(file_path: Path, doi: str, filename: Optional[str] = None) -> dict:
    """Verify file against Zenodo canonical version.

    Args:
        file_path: Local file to verify
        doi: Zenodo DOI (e.g., "10.5281/zenodo.19238786")
        filename: Filename in Zenodo record (defaults to file_path.name)

    Returns:
        Dictionary with verification results (same as verify_file_integrity)

    Example:
        >>> result = verify_against_zenodo(
        ...     Path("local_paper.pdf"),
        ...     "10.5281/zenodo.19238786",
        ...     filename="paper.pdf"
        ... )
        >>> if not result["verified"]:
        ...     print("WARNING: File does not match Zenodo canonical version")
    """
    if filename is None:
        filename = file_path.name

    try:
        checksums = fetch_zenodo_checksums(doi)
    except (requests.HTTPError, ValueError) as e:
        return {
            "verified": False,
            "md5": "",
            "sha256": "",
            "mismatches": [f"Failed to fetch Zenodo checksums: {e}"],
        }

    if filename not in checksums:
        available = ", ".join(checksums.keys())
        return {
            "verified": False,
            "md5": "",
            "sha256": "",
            "mismatches": [
                f"File '{filename}' not found in Zenodo record.\n" f"Available files: {available}"
            ],
        }

    expected_md5 = checksums[filename]
    return verify_file_integrity(file_path, expected_md5=expected_md5)


def cli_verify() -> None:
    """CLI entry point for file integrity verification.

    Usage:
        skeptic-toolkit verify file.pdf --md5 5478a2662af82dbf6b8473391e18d12d
        skeptic-toolkit verify file.pdf --zenodo-doi 10.5281/zenodo.19238786
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify file integrity against expected checksums or Zenodo records."
    )
    parser.add_argument("file", type=Path, help="File to verify")
    parser.add_argument("--md5", help="Expected MD5 hash")
    parser.add_argument("--sha256", help="Expected SHA256 hash")
    parser.add_argument("--zenodo-doi", help="Zenodo DOI to verify against")
    parser.add_argument(
        "--zenodo-filename",
        help="Filename in Zenodo record (defaults to basename of file)",
    )

    args = parser.parse_args()

    if args.zenodo_doi:
        result = verify_against_zenodo(args.file, args.zenodo_doi, args.zenodo_filename)
    else:
        if not args.md5 and not args.sha256:
            parser.error("Provide at least one of: --md5, --sha256, --zenodo-doi")
        result = verify_file_integrity(args.file, args.md5, args.sha256)

    print(f"File: {args.file}")
    print(f"MD5:    {result['md5']}")
    print(f"SHA256: {result['sha256']}")

    if result["verified"]:
        print("\n✅ VERIFIED: Checksums match")
        sys.exit(0)
    else:
        print("\n❌ VERIFICATION FAILED")
        for mismatch in result["mismatches"]:
            print(f"  {mismatch}")
        sys.exit(1)


if __name__ == "__main__":
    cli_verify()
