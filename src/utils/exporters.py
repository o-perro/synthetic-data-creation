"""
Export utilities for JSON and CSV output.

Both formats are Snowflake-compatible:
  JSON  → COPY INTO ... FILE_FORMAT = (TYPE = 'JSON')
  CSV   → COPY INTO ... FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1)
"""

import csv
import json
import logging
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def write_json(records: list[BaseModel], output_path: Path) -> None:
    """
    Write a list of Pydantic models to a JSON file as an array.

    Dates are serialized as ISO-8601 strings (YYYY-MM-DD), which Snowflake
    parses automatically with DATE column types.

    Args:
        records: Pydantic model instances to serialize.
        output_path: Destination file path (parent dirs must exist).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [r.model_dump(mode="json") for r in records]
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info("Wrote %d records → %s", len(records), output_path)


def write_csv(records: list[BaseModel], output_path: Path) -> None:
    """
    Write a list of Pydantic models to a CSV file with a header row.

    Nested Pydantic models (e.g. Customer.address) are flattened with
    double-underscore notation: address__street, address__city, etc.
    This avoids nested structures that CSV cannot represent naturally.

    Args:
        records: Pydantic model instances to serialize.
        output_path: Destination file path (parent dirs must exist).
    """
    if not records:
        logger.warning("No records to write to %s", output_path)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [_flatten(r.model_dump(mode="json")) for r in records]
    headers = list(rows[0].keys())

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Wrote %d records → %s", len(records), output_path)


def _flatten(data: dict[str, object], prefix: str = "") -> dict[str, object]:
    """
    Recursively flatten a nested dict using double-underscore separators.

    Example:
        {"address": {"city": "Austin"}} → {"address__city": "Austin"}
    """
    result: dict[str, object] = {}
    for key, value in data.items():
        full_key = f"{prefix}__{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten(value, prefix=full_key))
        else:
            result[full_key] = value
    return result
