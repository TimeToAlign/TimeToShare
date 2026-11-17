"""The canonical order of a TimeToShare manifest and the respelling of its values.

Readers accept a manifest's arrays in any order; writers emit one canonical
order (the README's "Canonical order"):

* ``timelines``, ``groups``, ``measure_maps`` and ``schemes`` by ID, and
  every group's ``members`` by code point;
* in every timeline, ``children`` by offset, then ID; ``conversion_maps`` by
  ID; ``regions`` by start, then end, then ID; ``flow_control`` by
  coordinate, then ID;
* ``graphical.timestamps`` by timeline, then coordinate, then ID, and every
  timestamp's ``display`` in the order of :data:`TIMESTAMP_DISPLAY`, other
  strings after them by code point and other values last in their given
  order.

Coordinates compare by their exact numeric value, never by their spelling;
strings compare by Unicode code point; entries that tie keep their given
order. Every other array keeps its order.

The declared number type decides how an own-axis value is read, never its
spelling, and writers respell every own-axis value as its axis's number type
selects (the README's "Values on a timeline's own axis"): an integral float on
an ``int`` axis as the integer it equals, an integer on a ``float`` axis as the
float that equals it exactly, and a Fraction pair on a ``fraction`` axis
reduced to lowest terms, its members integers. A value its number type cannot
take, and every value on an axis whose ``unit`` or ``number_type`` is unknown,
is written as given.
"""

from __future__ import annotations

import copy
import math
from collections import Counter
from collections.abc import Callable, Mapping
from fractions import Fraction
from typing import Any

__all__ = ["TIMESTAMP_DISPLAY", "UNIT_NUMBER_TYPES", "canonical_order"]

UNIT_NUMBER_TYPES = {
    "number": "float",
    "floating_measures": "float",
    "whole_notes": "fraction",
    "quarters": "fraction",
    "ticks": "int",
    "milliseconds": "float",
    "seconds": "float",
    "minutes": "float",
    "samples": "int",
    "frames": "int",
    "pixels": "int",
    "meters": "float",
    "centimeters": "float",
    "millimeters": "float",
    "inches": "float",
    "points": "float",
}
"""The default number type of each unit."""

_NUMBER_TYPES = ("int", "float", "fraction")

TIMESTAMP_DISPLAY = ("wedge", "name", "id", "coordinate", "cross_section")
"""The words of a named timestamp's ``display``, in canonical order."""


def _integral(value: Any) -> int | None:
    """The integer a JSON integer or an integral float equals, else ``None``."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def fraction_pair(value: Any) -> Fraction | None:
    """The value of a Fraction pair, or ``None`` when ``value`` is none.

    A pair is two integers, an integral float counting as the integer it
    equals, whose denominator is at least 1.
    """
    if not isinstance(value, list) or len(value) != 2:
        return None
    numerator, denominator = (_integral(member) for member in value)
    if numerator is None or denominator is None or denominator < 1:
        return None
    return Fraction(numerator, denominator)


def _exact(value: Any) -> Fraction:
    """Return the exact value of a coordinate: a JSON number or a Fraction pair.

    Raises:
        TypeError: If the value is neither.
        ValueError: If it is a NaN.
        OverflowError: If it is an infinity.
    """
    pair = fraction_pair(value)
    if pair is not None:
        return pair
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"not a number or a Fraction pair: {value!r}")
    return Fraction(value)


def _display_key(word: Any) -> tuple[int, int, str]:
    """Order the words of ``display``: the known ones canonically, then others.

    A string the schema does not know follows them by code point, and any
    other value follows last in its given order, so ordering never fails.
    """
    if isinstance(word, str) and word in TIMESTAMP_DISPLAY:
        return (0, TIMESTAMP_DISPLAY.index(word), "")
    if isinstance(word, str):
        return (1, 0, word)
    return (2, 0, "")


def _order_displays(manifest: Any) -> None:
    """Put the ``display`` of every named timestamp in canonical order, in place."""
    for timestamp in _dicts(_timestamps(manifest)):
        display = timestamp.get("display")
        if isinstance(display, list):
            timestamp["display"] = sorted(display, key=_display_key)


def _sorted(entries: list[Any], key: Callable[[Any], Any], where: str) -> list[Any]:
    try:
        return sorted(entries, key=key)
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"cannot put {where} in canonical order: {error!r}") from error


def _identifier(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"not a string: {value!r}")
    return value


def _by_id(entry: Any) -> str:
    return _identifier(entry["id"])


def _order_timeline(timeline: dict[str, Any]) -> None:
    """Put the arrays of one timeline and its descendants in order, in place."""
    children = timeline.get("children")
    if isinstance(children, list):
        for child in _dicts(children):
            _order_timeline(child)
        timeline["children"] = _sorted(
            children,
            lambda entry: (_exact(entry["offset"]), _by_id(entry)),
            "children",
        )
    if isinstance(timeline.get("conversion_maps"), list):
        timeline["conversion_maps"] = _sorted(
            timeline["conversion_maps"], _by_id, "conversion_maps"
        )
    if isinstance(timeline.get("regions"), list):
        timeline["regions"] = _sorted(
            timeline["regions"],
            lambda entry: (_exact(entry["start"]), _exact(entry["end"]), _by_id(entry)),
            "regions",
        )
    if isinstance(timeline.get("flow_control"), list):
        timeline["flow_control"] = _sorted(
            timeline["flow_control"],
            lambda entry: (_exact(entry["coordinate"]), _by_id(entry)),
            "flow_control",
        )


def _on_axis(value: Any, number_type: str | None) -> Any:
    """Return an own-axis value respelled as its axis's number type selects."""
    if number_type == "fraction":
        pair = fraction_pair(value)
        return value if pair is None else [pair.numerator, pair.denominator]
    if number_type == "int":
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value
    if (
        number_type == "float"
        and isinstance(value, int)
        and not isinstance(value, bool)
    ):
        try:
            double = float(value)
        except OverflowError:
            return value
        return double if math.isfinite(double) and double == value else value
    return value


def _axis_type(timeline: Mapping[str, Any]) -> str | None:
    """The number type of a timeline's axis, or ``None`` where it is unknown.

    A ``unit`` that is missing, not a string or not a unit is unknown, and so
    is a ``number_type`` that is present but not one of the three types
    (``null`` included); a missing ``number_type`` is the unit's default.
    """
    unit = timeline.get("unit")
    if not isinstance(unit, str) or unit not in UNIT_NUMBER_TYPES:
        return None
    if "number_type" not in timeline:
        return UNIT_NUMBER_TYPES[unit]
    number_type = timeline["number_type"]
    return number_type if number_type in _NUMBER_TYPES else None


def _dicts(value: Any) -> list[dict[str, Any]]:
    return (
        [entry for entry in value if isinstance(entry, dict)]
        if isinstance(value, list)
        else []
    )


def _respell_axis(
    owner: dict[str, Any], keys: tuple[str, ...], number_type: str | None
) -> None:
    for key in keys:
        if key in owner:
            owner[key] = _on_axis(owner[key], number_type)


def _respell_timeline(timeline: dict[str, Any], offset_type: str | None) -> None:
    """Respell a timeline's own-axis values and its descendants', in place.

    ``offset_type`` is the number type of the axis its ``offset`` lies on:
    its own for a root, its parent's for a child.
    """
    own = _axis_type(timeline)
    _respell_axis(timeline, ("offset",), offset_type)
    _respell_axis(timeline, ("length",), own)
    for region in _dicts(timeline.get("regions")):
        _respell_axis(region, ("start", "end"), own)
    for entry in _dicts(timeline.get("flow_control")):
        _respell_axis(entry, ("coordinate",), own)
    for child in _dicts(timeline.get("children")):
        _respell_timeline(child, own)


def _axis_types(manifest: dict[str, Any]) -> dict[str, str | None]:
    """The number type of every timeline's axis by ID.

    An ID that names more than one timeline names no axis (``None``).
    """
    found: dict[str, str | None] = {}
    counts: Counter[str] = Counter()

    def visit(timeline: dict[str, Any]) -> None:
        identifier = timeline.get("id")
        if isinstance(identifier, str):
            counts[identifier] += 1
            found[identifier] = _axis_type(timeline)
        for child in _dicts(timeline.get("children")):
            visit(child)

    for timeline in _dicts(manifest.get("timelines")):
        visit(timeline)
    return {key: value if counts[key] == 1 else None for key, value in found.items()}


def _timestamps(manifest: Any) -> Any:
    graphical = manifest.get("graphical") if isinstance(manifest, Mapping) else None
    return graphical.get("timestamps") if isinstance(graphical, dict) else None


def _respell(manifest: Any) -> None:
    """Respell every own-axis value of a manifest as its number type selects, in place.

    The own-axis values are a timeline's ``length`` and ``offset``, its
    regions' ``start`` and ``end``, its flow-control coordinates and the
    coordinate of every named timestamp on it. A timestamp whose
    ``timeline`` names no timeline, or more than one, keeps its coordinate.
    """
    if not isinstance(manifest, dict):
        return
    for timeline in _dicts(manifest.get("timelines")):
        _respell_timeline(timeline, _axis_type(timeline))
    axis_types = _axis_types(manifest)
    for timestamp in _dicts(_timestamps(manifest)):
        timeline = timestamp.get("timeline")
        if isinstance(timeline, str):
            _respell_axis(timestamp, ("coordinate",), axis_types.get(timeline))


def is_manifest(value: Any) -> bool:
    """Whether a value is a manifest: an object whose ``timelines`` is an array."""
    return isinstance(value, dict) and isinstance(value.get("timelines"), list)


def canonical_order(value: Any) -> Any:
    """Return a deep copy of ``value``, a manifest put in canonical order and spelling.

    A value is a manifest when it is an object whose ``timelines`` member is
    an array: its arrays are put in canonical order (module docstring) and
    its own-axis values respelled. Object keys are left as they are (the
    writers sort them), and every other value is copied unchanged.

    Raises:
        ValueError: If the manifest cannot be put in canonical order: an
            entry of an ordered array of objects is not an object, lacks a
            member it is ordered by or holds that member in a wrong type, or
            a group's ``members`` holds a value that is not a string.
    """
    result = copy.deepcopy(value)
    if not is_manifest(result):
        return result
    _respell(result)
    timelines = result["timelines"]
    for timeline in _dicts(timelines):
        _order_timeline(timeline)
    result["timelines"] = _sorted(timelines, _by_id, "timelines")
    groups = result.get("groups")
    if isinstance(groups, list):
        for group in _dicts(groups):
            if isinstance(group.get("members"), list):
                group["members"] = _sorted(group["members"], _identifier, "members")
        result["groups"] = _sorted(groups, _by_id, "groups")
    for key in ("measure_maps", "schemes"):
        if isinstance(result.get(key), list):
            result[key] = _sorted(result[key], _by_id, key)
    timestamps = _timestamps(result)
    if isinstance(timestamps, list):
        result["graphical"]["timestamps"] = _sorted(
            timestamps,
            lambda entry: (
                _identifier(entry["timeline"]),
                _exact(entry["coordinate"]),
                _by_id(entry),
            ),
            "timestamps",
        )
    _order_displays(result)
    return result
