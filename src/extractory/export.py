"""Export helpers for records and normalized data."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any, TextIO, cast

from pydantic import BaseModel


def to_jsonable(value: Any) -> Any:
    """Convert Pydantic models and datetimes into JSON-compatible values."""
    if isinstance(value, BaseModel):
        return to_jsonable(value.model_dump(mode="python"))
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(child) for key, child in value.items()}
    if isinstance(value, list | tuple | set):
        return [to_jsonable(child) for child in value]
    return value


def _open_output(path_or_file: str | Path | TextIO) -> tuple[TextIO, bool]:
    if isinstance(path_or_file, str | Path):
        return Path(path_or_file).open("w", encoding="utf-8", newline=""), True
    return cast("TextIO", path_or_file), False


def export_jsonl(records: Iterable[Any], path_or_file: str | Path | TextIO) -> None:
    """Write records as JSON Lines, preserving lists and dictionaries."""
    handle, should_close = _open_output(path_or_file)
    try:
        for record in records:
            handle.write(json.dumps(to_jsonable(record), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    finally:
        if should_close:
            handle.close()


def export_csv(records: Iterable[Any], path_or_file: str | Path | TextIO) -> None:
    """Write records as CSV, JSON-encoding nested values."""
    rows = [to_jsonable(record) for record in records]
    keys = sorted({key for row in rows if isinstance(row, Mapping) for key in row})
    handle, should_close = _open_output(path_or_file)
    try:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False, sort_keys=True)
                    if isinstance(value, (dict, list))
                    else value
                    for key, value in row.items()
                }
            )
    finally:
        if should_close:
            handle.close()
