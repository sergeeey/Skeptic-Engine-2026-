"""Tests for integrity module.

Created 2026-05-10 after ARCHCODE version mismatch incident.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from skeptic_toolkit.integrity import (
    compute_hash,
    fetch_zenodo_checksums,
    verify_against_zenodo,
    verify_file_integrity,
)


def test_compute_hash_md5(tmp_path: Path) -> None:
    """Test MD5 hash computation."""
    test_file = tmp_path / "test.txt"
    # Use write_bytes to avoid platform newline issues
    test_file.write_bytes(b"hello world\n")

    hash_result = compute_hash(test_file, "md5")

    import hashlib

    expected = hashlib.md5(b"hello world\n").hexdigest()
    assert hash_result == expected


def test_compute_hash_sha256(tmp_path: Path) -> None:
    """Test SHA256 hash computation."""
    test_file = tmp_path / "test.txt"
    # Use write_bytes to avoid platform newline issues
    test_file.write_bytes(b"hello world\n")

    hash_result = compute_hash(test_file, "sha256")

    import hashlib

    expected = hashlib.sha256(b"hello world\n").hexdigest()
    assert hash_result == expected


def test_verify_file_integrity_correct_md5(tmp_path: Path) -> None:
    """Test verification with correct MD5."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"test content\n")

    import hashlib

    expected_md5 = hashlib.md5(b"test content\n").hexdigest()

    result = verify_file_integrity(test_file, expected_md5=expected_md5)

    assert result["verified"] is True
    assert len(result["mismatches"]) == 0


def test_verify_file_integrity_wrong_md5(tmp_path: Path) -> None:
    """Test verification with wrong MD5."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content\n")

    result = verify_file_integrity(test_file, expected_md5="wrong_hash")

    assert result["verified"] is False
    assert len(result["mismatches"]) == 1
    assert "MD5 mismatch" in result["mismatches"][0]


def test_verify_file_integrity_case_insensitive(tmp_path: Path) -> None:
    """Test that hash comparison is case-insensitive."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"test content\n")

    import hashlib

    expected_md5_lower = hashlib.md5(b"test content\n").hexdigest()
    expected_md5_upper = expected_md5_lower.upper()

    # Both should pass
    result_lower = verify_file_integrity(test_file, expected_md5=expected_md5_lower)
    result_upper = verify_file_integrity(test_file, expected_md5=expected_md5_upper)

    assert result_lower["verified"] is True
    assert result_upper["verified"] is True


def test_verify_file_not_found() -> None:
    """Test verification of non-existent file."""
    result = verify_file_integrity(Path("/nonexistent/file.txt"), expected_md5="abc123")

    assert result["verified"] is False
    assert "File not found" in result["mismatches"][0]


def test_fetch_zenodo_checksums_success() -> None:
    """Test fetching checksums from Zenodo API."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "files": [
            {"key": "file1.txt", "checksum": "md5:abc123"},
            {"key": "file2.csv", "checksum": "md5:def456"},
        ]
    }

    with patch("requests.get", return_value=mock_response) as mock_get:
        checksums = fetch_zenodo_checksums("10.5281/zenodo.12345")

    mock_get.assert_called_once()
    assert checksums == {"file1.txt": "abc123", "file2.csv": "def456"}


def test_fetch_zenodo_checksums_invalid_doi() -> None:
    """Test fetching with invalid DOI format."""
    with pytest.raises(ValueError, match="Invalid Zenodo DOI format"):
        fetch_zenodo_checksums("10.1234/invalid")


def test_fetch_zenodo_checksums_http_error() -> None:
    """Test fetching when Zenodo returns HTTP error."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        with pytest.raises(requests.HTTPError):
            fetch_zenodo_checksums("10.5281/zenodo.99999999")


def test_verify_against_zenodo_file_not_in_record(tmp_path: Path) -> None:
    """Test verification when file is not in Zenodo record."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    with patch("skeptic_toolkit.integrity.fetch_zenodo_checksums") as mock_fetch:
        mock_fetch.return_value = {"other_file.txt": "abc123"}

        result = verify_against_zenodo(test_file, "10.5281/zenodo.12345", filename="test.txt")

    assert result["verified"] is False
    assert "not found in Zenodo record" in result["mismatches"][0]


def test_verify_against_zenodo_success(tmp_path: Path) -> None:
    """Test successful verification against Zenodo."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"test content\n")

    import hashlib

    expected_md5 = hashlib.md5(b"test content\n").hexdigest()

    with patch("skeptic_toolkit.integrity.fetch_zenodo_checksums") as mock_fetch:
        mock_fetch.return_value = {"test.txt": expected_md5}

        result = verify_against_zenodo(test_file, "10.5281/zenodo.12345")

    assert result["verified"] is True
    assert len(result["mismatches"]) == 0
