"""The bundled cases of the current version: fixtures, rejections and warnings.

The emitted manifests under ``fixtures/<version>/`` (drawings excluded), the
hand-authored rejection cases under ``fixtures/rejections/<version>/`` and the
hand-authored warning cases under ``fixtures/warnings/<version>/``, found
beside the schema. Every case is read with :func:`~timetoshare.validate.loads`,
as the JavaScript package reads it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .validate import SCHEMA_VERSION, _data_root, loads
from .validation.diagnostics import _Path


def fixture_paths() -> list[Path]:
    """Return every bundled manifest fixture, excluding drawings."""
    directory = _data_root() / "fixtures" / SCHEMA_VERSION
    return sorted(
        path
        for path in directory.rglob("*.json")
        if "drawings" not in path.relative_to(directory).parts
    )


def rejection_paths() -> list[Path]:
    """Return the shared rejection cases, sorted by name."""
    directory = _data_root() / "fixtures" / "rejections" / SCHEMA_VERSION
    return sorted(directory.glob("*.json"))


@dataclass(frozen=True)
class RejectionCase:
    """One shared rejection case, read for validation.

    Attributes:
        manifest: The value to validate, with any non-finite number in place.
        path: Where the validator reports the problem.
        code: The rule's code, or ``None`` where the case raises an error
            without one.
        error: The name of the error class where it is not
            ``SchemaValidationError``, else ``None``.
        reason: The rule the case breaks, in words.
    """

    manifest: Any
    path: _Path
    code: str | None
    error: str | None
    reason: str


_NON_FINITE = {"NaN": math.nan, "Infinity": math.inf, "-Infinity": -math.inf}


def rejection_case(path: Path) -> RejectionCase:
    """Read one shared rejection case from ``path``.

    JSON holds no NaN and no infinity, so a case about the finite rule stores
    a finite placeholder at its path and names the value to put there under
    ``non_finite``; the reader puts it in place.

    Raises:
        ValueError: If the file is not JSON or names an unknown non-finite value.
    """
    case = loads(path.read_text(encoding="utf-8"))
    location = tuple(case["path"])
    manifest = case["manifest"]
    if "non_finite" in case:
        name = case["non_finite"]
        if name not in _NON_FINITE:
            raise ValueError(f"{path.name}: {name!r} names no non-finite number")
        owner = manifest
        for segment in location[:-1]:
            owner = owner[segment]
        owner[location[-1]] = _NON_FINITE[name]
    return RejectionCase(
        manifest=manifest,
        path=location,
        code=case["code"],
        error=case.get("error"),
        reason=case["reason"],
    )


def warning_paths() -> list[Path]:
    """Return the shared warning cases, sorted by name."""
    directory = _data_root() / "fixtures" / "warnings" / SCHEMA_VERSION
    return sorted(directory.glob("*.json"))
