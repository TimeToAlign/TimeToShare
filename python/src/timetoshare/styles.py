"""Helpers for reading the styles of a manifest's ``graphical`` object."""

from __future__ import annotations

import copy
import warnings


class MissingStyleWarning(UserWarning):
    """Warn that statements name styles absent from their ``graphical`` object."""


def complete_styles(graphical: dict) -> tuple[dict, list[str]]:
    """Return a copy of ``graphical`` with empty declarations for missing styles."""
    completed = copy.deepcopy(graphical)
    styles = completed.get("styles", {})
    missing = sorted(
        {
            statement["set"]
            for statement in completed.get("statements", [])
            if isinstance(statement["set"], str) and statement["set"] not in styles
        }
    )
    if missing:
        completed["styles"] = styles
        for name in missing:
            styles[name] = {}
        names = ", ".join(repr(name) for name in missing)
        warnings.warn(
            f"Missing graphical styles: {names}",
            MissingStyleWarning,
            stacklevel=2,
        )
    return completed, missing
