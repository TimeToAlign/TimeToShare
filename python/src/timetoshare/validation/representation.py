"""Finite-number and own-axis representation rules."""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping
from fractions import Fraction
from typing import Any

from ..manifest import exact
from ..serialization import spell
from .diagnostics import (
    InstancePath,
    SchemaValidationError,
    axes_by_id,
    elisions_of,
    entries_of,
    json_pointer,
    number_type_of,
    timelines_by_id,
    timestamps_of,
)

_ARTICLES = {"int": "an int", "float": "a float", "fraction": "a fraction"}


def _written_as(value: Any) -> str:
    if isinstance(value, list):
        return "fraction"
    return "int" if isinstance(value, int) else "float"


def _represents(value: Any, number_type: str) -> bool:
    if number_type == "fraction":
        return isinstance(value, list)
    if isinstance(value, list):
        return False
    if number_type == "float":
        return not isinstance(value, int) or rewritten(value, "float") is not None
    return isinstance(value, int) or value.is_integer()


def rewritten(value: Any, number_type: str) -> str | None:
    """Return an exact rewriting in ``number_type``, or ``None``."""
    read = exact(value)
    if number_type == "fraction":
        return spell([read.numerator, read.denominator])
    if number_type == "int":
        return spell(read.numerator) if read.denominator == 1 else None
    try:
        double = read.numerator / read.denominator
    except OverflowError:
        return None
    return spell(double) if Fraction(double) == read else None


def _representation_problem(
    key: str,
    owner: Mapping[str, Any],
    path: InstancePath,
    number_type: str,
    of: str | None = None,
) -> Iterator[SchemaValidationError]:
    """Yield the representation problem of ``owner[key]``, if any.

    The message names the element ``of``, by default the owner's ``id``.
    """
    value = owner.get(key)
    if value is None or _represents(value, number_type):
        return
    fix = rewritten(value, number_type) or _ARTICLES[number_type]
    yield SchemaValidationError(
        "representation",
        (*path, key),
        f"{key} {spell(value)} of '{owner['id'] if of is None else of}' is "
        f"{_ARTICLES[_written_as(value)]} "
        f"on {_ARTICLES[number_type]} axis: write {fix}",
    )


def _timeline_representation(
    timeline: Mapping[str, Any], path: InstancePath, offset_type: str | None
) -> Iterator[SchemaValidationError]:
    own = number_type_of(timeline)
    yield from _representation_problem("offset", timeline, path, offset_type or own)
    yield from _representation_problem("length", timeline, path, own)
    for index, region in enumerate(entries_of(timeline, "regions")):
        for key in ("start", "end"):
            yield from _representation_problem(
                key, region, (*path, "regions", index), own
            )
    for index, entry in enumerate(entries_of(timeline, "flow_control")):
        at = (*path, "flow_control", index)
        yield from _representation_problem("coordinate", entry, at, own)
        after = entry.get("ends", {}).get("after")
        if after is not None:
            yield from _representation_problem(
                "by", after, (*at, "ends", "after"), own, entry["id"]
            )
        for number, destination in enumerate(entries_of(entry, "targets")):
            here = (*at, "targets", number)
            yield from _representation_problem(
                "by", destination, here, own, entry["id"]
            )
            if "after" in destination:
                yield from _representation_problem(
                    "by", destination["after"], (*here, "after"), own, entry["id"]
                )
    for index, child in enumerate(entries_of(timeline, "children")):
        yield from _timeline_representation(child, (*path, "children", index), own)


def representation_problems(
    manifest: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """Yield own-axis representation violations in manifest order.

    The timelines first (a flow-control element's coordinate, then the
    ``by`` of its ``ends`` and of each destination and its ``after``), then
    the coordinate of every named timestamp on a timeline of the manifest
    or a virtual timeline, then the ``start``, ``end`` and width ``span`` of
    every elision on one, then the gaps of every FlowMap of a timeline of
    the manifest, each read as that timeline's number type, then the
    ``length`` of every virtual timeline, read as its own.
    """
    for index, root in enumerate(entries_of(manifest, "timelines")):
        yield from _timeline_representation(root, ("timelines", index), None)
    timelines = timelines_by_id(manifest)
    axes = axes_by_id(manifest)
    for index, timestamp in enumerate(timestamps_of(manifest)):
        timeline = axes.get(timestamp["timeline"])
        if timeline is not None:
            yield from _representation_problem(
                "coordinate",
                timestamp,
                ("graphical", "timestamps", index),
                number_type_of(timeline),
            )
    for index, elision in enumerate(elisions_of(manifest)):
        timeline = axes.get(elision["timeline"])
        if timeline is None:
            continue
        path = ("graphical", "elisions", index)
        number_type = number_type_of(timeline)
        for key in ("start", "end"):
            yield from _representation_problem(key, elision, path, number_type)
        if "width" in elision:
            yield from _representation_problem(
                "span", elision["width"], (*path, "width"), number_type, elision["id"]
            )
    for index, flow_map in enumerate(entries_of(manifest, "flow_maps")):
        timeline = timelines.get(flow_map["timeline"])
        if timeline is None:
            continue
        for number, chunk in enumerate(flow_map["chunks"]):
            if isinstance(chunk, Mapping):
                yield from _representation_problem(
                    "gap",
                    chunk,
                    ("flow_maps", index, "chunks", number),
                    number_type_of(timeline),
                    flow_map["id"],
                )
    for index, virtual in enumerate(entries_of(manifest, "virtual_timelines")):
        yield from _representation_problem(
            "length", virtual, ("virtual_timelines", index), virtual["number_type"]
        )


_PLAIN = frozenset({str, int, bool, type(None)})


def plainly_finite(value: Any) -> bool:
    """Whether ``value`` is plain JSON data whose every float is finite.

    Plain JSON data is made of ``dict``, ``list``, ``str``, ``int``,
    ``float``, ``bool`` and ``None`` alone. Where this answers ``True``,
    :func:`finite_number_problems` yields nothing for ``value`` and for any
    copy of it that only rewrites its strings; ``False`` means only that the
    rule must run.
    """
    kind = type(value)
    if kind is float:
        return math.isfinite(value)
    if kind is list:
        items: Any = value
    elif kind is dict:
        items = value.values()
    else:
        return kind in _PLAIN
    for item in items:
        if type(item) in _PLAIN:
            continue
        if not plainly_finite(item):
            return False
    return True


def finite_number_problems(
    value: Any,
    path: InstancePath = (),
    owner_id: str | None = None,
    owner_key: str | None = None,
) -> Iterator[SchemaValidationError]:
    """Yield non-finite float leaves before schema validation."""
    if isinstance(value, float) and not math.isfinite(value):
        detail = (
            f"{owner_key} of '{owner_id}' is not a finite number"
            if owner_id is not None and owner_key is not None
            else f"{json_pointer(path)} is not a finite number"
        )
        yield SchemaValidationError("finite_number", path, detail)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from finite_number_problems(item, (*path, index), owner_id, owner_key)
        return
    if not isinstance(value, Mapping):
        return
    identifier = value.get("id")
    current_id = identifier if isinstance(identifier, str) else owner_id
    for key, item in value.items():
        yield from finite_number_problems(item, (*path, key), current_id, key)
