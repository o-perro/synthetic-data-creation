"""Unit tests for JSON and CSV exporters."""

import json
from pathlib import Path

import pytest

from src.generators.customer import generate_customers
from src.utils.exporters import write_csv, write_json


@pytest.fixture()
def tmp_customers(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Small customer batch for exporter tests."""
    return generate_customers(count=5, seed=42)


class TestWriteJson:
    def test_creates_file(self, tmp_path: Path, tmp_customers: list) -> None:
        out = tmp_path / "customers.json"
        write_json(tmp_customers, out)
        assert out.exists()

    def test_output_is_valid_json(self, tmp_path: Path, tmp_customers: list) -> None:
        out = tmp_path / "customers.json"
        write_json(tmp_customers, out)
        data = json.loads(out.read_text())
        assert isinstance(data, list)

    def test_record_count_matches(self, tmp_path: Path, tmp_customers: list) -> None:
        out = tmp_path / "customers.json"
        write_json(tmp_customers, out)
        data = json.loads(out.read_text())
        assert len(data) == len(tmp_customers)

    def test_creates_parent_dirs(self, tmp_path: Path, tmp_customers: list) -> None:
        out = tmp_path / "nested" / "deep" / "customers.json"
        write_json(tmp_customers, out)
        assert out.exists()


class TestWriteCsv:
    def test_creates_file(self, tmp_path: Path, tmp_customers: list) -> None:
        out = tmp_path / "customers.csv"
        write_csv(tmp_customers, out)
        assert out.exists()

    def test_has_header_row(self, tmp_path: Path, tmp_customers: list) -> None:
        out = tmp_path / "customers.csv"
        write_csv(tmp_customers, out)
        lines = out.read_text().splitlines()
        assert len(lines) > 1  # header + at least one data row

    def test_row_count_matches(self, tmp_path: Path, tmp_customers: list) -> None:
        out = tmp_path / "customers.csv"
        write_csv(tmp_customers, out)
        lines = out.read_text().splitlines()
        # Lines = 1 header + N data rows
        assert len(lines) == len(tmp_customers) + 1

    def test_nested_address_is_flattened(self, tmp_path: Path, tmp_customers: list) -> None:
        out = tmp_path / "customers.csv"
        write_csv(tmp_customers, out)
        header = out.read_text().splitlines()[0]
        # Address sub-model should be flattened with __ separator
        assert "address__city" in header
        assert "address__state" in header
