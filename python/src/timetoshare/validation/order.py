"""Graphical display-order and band-order rules."""

from __future__ import annotations

from collections.abc import Collection, Iterator, Mapping, Sequence
from typing import Any

from .diagnostics import SchemaValidationError, ValidationCode, _entries, _Path

_DEFAULT_BAND_ORDER = (
    "children",
    "conversion_maps",
    "line",
    "markers",
    "regions",
    "flow_control",
)


def _permutation_problems(
    code: ValidationCode,
    owner: str,
    order: list[str],
    expected: Sequence[str],
    path: _Path,
    messages: tuple[str, str],
) -> Iterator[SchemaValidationError]:
    stranger, missing = messages
    allowed = set(expected)
    listed = set(order)
    for index, entry in enumerate(order):
        if entry not in allowed:
            yield SchemaValidationError(
                code,
                (*path, index),
                stranger.format(entry=f"'{entry}'", owner=f"'{owner}'"),
            )
    for entry in expected:
        if entry not in listed:
            yield SchemaValidationError(
                code,
                path,
                missing.format(entry=f"'{entry}'", owner=f"'{owner}'"),
            )


def order_problems(
    manifest: Mapping[str, Any],
    timelines: Collection[str],
    first_group: Mapping[str, int],
) -> Iterator[SchemaValidationError]:
    """Yield unknown order keys and invalid display and band orders.

    ``timelines`` holds every timeline ID and ``first_group`` the index of the
    first group of each group ID, as the identity rules collected them.
    """
    groups = _entries(manifest, "groups")
    orders = (manifest.get("graphical") or {}).get("order") or {}
    for key in sorted(orders):
        path = ("graphical", "order", key)
        if key in first_group:
            group = groups[first_group[key]]
            yield from _permutation_problems(
                "display_order",
                key,
                orders[key],
                group["members"],
                path,
                (
                    "{entry} is not a member of group {owner}",
                    "member {entry} of group {owner} is missing",
                ),
            )
        elif key in timelines:
            yield from _permutation_problems(
                "band_order",
                key,
                orders[key],
                _DEFAULT_BAND_ORDER,
                path,
                (
                    "{entry} is not 'line' or a facet, in the band order of {owner}",
                    "{entry} is missing from the band order of {owner}",
                ),
            )
        else:
            yield SchemaValidationError(
                "order_key",
                path,
                f"'{key}' names no group or timeline of this manifest",
            )
