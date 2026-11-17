"""The canonical order of a TimeToShare manifest and its standard writer.

The standard writer sorts the keys of every object by Unicode code point, so
equal objects are equal text whatever order their keys were given in. Every
array of a manifest whose order carries no meaning has one canonical order:

* ``timelines`` by id;
* in every timeline, ``children`` by offset, then id; ``conversion_maps`` by
  id; ``regions`` by start, then end, then id; ``flow_control`` by
  coordinate, then id;
* ``groups`` by id and every group's ``members`` by code point;
* ``measure_maps`` by id;
* ``schemes`` by id;
* ``graphical.timestamps`` by timeline, then coordinate, then id, and every
  timestamp's ``display`` in the order of :data:`TIMESTAMP_DISPLAY`.

Own-axis values compare by their exact numeric value, never by their JSON
spelling; strings compare by Unicode code point. Nothing else is reordered;
in particular a ``graphical.order`` array is a display order and stays as it
is, as do the ``links`` of the manifest, a timeline or a region (a display
order), a link's ``uri`` (the first preferred) and ``parts`` (the order of
its reading), and every other array of a link. Readers accept any order;
writers emit the canonical one.

The declared number type decides how a value is read, never its spelling, and
writers spell every value canonically: an own-axis value on an int axis as a
JSON integer, on a float axis as a float, and every member of a Fraction pair
as a JSON integer. A number whose place declares no number type keeps its
spelling.

The standard writer emits UTF-8 text with every character unescaped except
``"``, ``\\`` and the control characters, two-space indentation and a final
newline. A float is always written as a float (``2.0``, ``1e-07``), spelled as
Python's ``repr``; an integer never carries a decimal point or an exponent.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from fractions import Fraction
from typing import Any

__all__ = ["TIMESTAMP_DISPLAY", "canonical_json", "canonical_order", "dumps"]

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

_MAP_NUMBER_MEMBERS = {
    "ConstantMap": {"values": ("value",)},
    "LinearMap": {"values": ("scalar", "offset")},
    "PiecewiseMap": {"arrays": ("breaks",)},
    "TableMap": {"arrays": ("x_values", "y_values")},
}
"""The members of each conversion map type that hold a Number."""

_MAP_NESTED_MEMBERS = {
    "ChainMap": {"arrays": ("maps",)},
    "CombinationMap": {"records": ("maps",)},
    "PiecewiseMap": {"arrays": ("maps",)},
}
"""The members of each conversion map type that hold nested conversion maps."""

TIMESTAMP_DISPLAY = ("wedge", "name", "id", "coordinate", "cross_section")
"""The words of a named timestamp's ``display``, in canonical order."""

_ROW_NUMBER_MEMBERS = (
    "qstamp",
    "nominal_length",
    "actual_length",
    "offset_within_measure",
)


def _display_key(word: Any) -> tuple[int, int, str]:
    """Order the words of ``display``: the known ones canonically, then others.

    A string the schema does not know follows them by code point, and any
    other value follows last in its given order, so ordering never fails.
    """
    if word in TIMESTAMP_DISPLAY:
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


def canonical_json(value: Any) -> str:
    """Return the canonical JSON text of a value: keys sorted, no whitespace.

    Raises:
        ValueError: If the value holds a NaN or an infinity, or a string with a
            lone surrogate (which UTF-8 cannot encode).
    """
    return _utf8(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    )


def _utf8(text: str) -> str:
    """Return ``text``, refused if it holds a lone surrogate."""
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError(f"a string holds a lone surrogate: {error}") from error
    return text


def _exact(value: Any) -> Fraction:
    """Return the exact value of a bare Number: a JSON number or a pair.

    An integral float in a Fraction pair counts as the integer it equals, as a
    JavaScript reader cannot tell ``1.0`` from ``1``.
    """
    if isinstance(value, list) and len(value) == 2:
        numerator, denominator = (_integer(item) for item in value)
        if denominator > 0:
            return Fraction(numerator, denominator)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"not a Number: {value!r}")
    return Fraction(value)


def spell(value: Any) -> str:
    """Spell a value as a message quotes it.

    A number is spelled as the standard writer spells it, an array as its
    items separated by ``, `` within brackets (``[32, 1]``), anything else as
    compact JSON. The JavaScript package spells numbers and arrays the same way.
    """
    if isinstance(value, list):
        return "[" + ", ".join(spell(item) for item in value) + "]"
    if isinstance(value, bool) or not isinstance(value, int | float):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return repr(value)


def _integer(value: Any) -> int:
    if type(value) is int:
        return value
    if type(value) is float and value.is_integer():
        return int(value)
    raise TypeError(f"not an integer: {value!r}")


def _sorted(entries: list[Any], key: Callable[[Any], Any], where: str) -> list[Any]:
    try:
        return sorted(entries, key=key)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        raise ValueError(f"cannot put {where} in canonical order: {error!r}") from error


def _identifier(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"not an id: {value!r}")
    return value


def _by_id(entry: Any) -> str:
    return _identifier(entry["id"])


def _order_timeline(timeline: dict[str, Any]) -> None:
    """Put the arrays of one timeline and its descendants in order, in place."""
    children = timeline.get("children")
    if isinstance(children, list):
        for child in children:
            if isinstance(child, dict):
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


def _integral(value: Any) -> Any:
    """Return an integral float as the integer it equals, anything else as it is."""
    if type(value) is float and value.is_integer():
        return int(value)
    return value


def _fraction(value: Any) -> Any:
    """Return a pair with its members spelled as integers, anything else as it is."""
    if isinstance(value, list) and len(value) == 2:
        return [_integral(member) for member in value]
    return value


def _on_axis(value: Any, number_type: str | None) -> Any:
    """Return an own-axis value spelled as its axis's number type selects."""
    if number_type == "fraction":
        return _fraction(value)
    if number_type == "int":
        return _integral(value)
    if number_type == "float" and type(value) is int:
        try:
            double = float(value)
        except OverflowError:
            return value
        return double if double == value else value
    return value


def _axis_type(timeline: Mapping[str, Any]) -> str | None:
    """The number type of a timeline's axis, or ``None`` where it states none."""
    number_type = timeline.get("number_type")
    if number_type in ("int", "float", "fraction"):
        return number_type
    unit = timeline.get("unit")
    return UNIT_NUMBER_TYPES.get(unit) if isinstance(unit, str) else None


def _dicts(value: Any) -> list[dict[str, Any]]:
    return (
        [entry for entry in value if isinstance(entry, dict)]
        if isinstance(value, list)
        else []
    )


def _respell_map(conversion_map: dict[str, Any]) -> None:
    map_type = conversion_map.get("type")
    if not isinstance(map_type, str):
        return
    members = _MAP_NUMBER_MEMBERS.get(map_type, {})
    for key in members.get("values", ()):
        if key in conversion_map:
            conversion_map[key] = _fraction(conversion_map[key])
    for key in members.get("arrays", ()):
        if isinstance(conversion_map.get(key), list):
            conversion_map[key] = [_fraction(value) for value in conversion_map[key]]
    nested = _MAP_NESTED_MEMBERS.get(map_type, {})
    for key in nested.get("values", ()):
        if isinstance(conversion_map.get(key), dict):
            _respell_map(conversion_map[key])
    for key in nested.get("arrays", ()):
        for entry in _dicts(conversion_map.get(key)):
            _respell_map(entry)
    for key in nested.get("records", ()):
        record = conversion_map.get(key)
        if isinstance(record, dict):
            for entry in _dicts(list(record.values())):
                _respell_map(entry)


def _respell_axis(
    owner: dict[str, Any], keys: tuple[str, ...], number_type: str | None
) -> None:
    for key in keys:
        if key in owner:
            owner[key] = _on_axis(owner[key], number_type)


def _respell_timeline(timeline: dict[str, Any], offset_type: str | None) -> None:
    own = _axis_type(timeline)
    _respell_axis(timeline, ("offset",), offset_type or own)
    _respell_axis(timeline, ("length",), own)
    for region in _dicts(timeline.get("regions")):
        _respell_axis(region, ("start", "end"), own)
    for entry in _dicts(timeline.get("flow_control")):
        _respell_axis(entry, ("coordinate",), own)
    for conversion_map in _dicts(timeline.get("conversion_maps")):
        _respell_map(conversion_map)
    for child in _dicts(timeline.get("children")):
        _respell_timeline(child, own)


def _axis_types(manifest: dict[str, Any]) -> dict[str, str | None]:
    """The number type of every timeline's axis by ID, the first of a repeated ID."""
    found: dict[str, str | None] = {}

    def visit(timeline: dict[str, Any]) -> None:
        identifier = timeline.get("id")
        if isinstance(identifier, str):
            found.setdefault(identifier, _axis_type(timeline))
        for child in _dicts(timeline.get("children")):
            visit(child)

    for timeline in _dicts(manifest.get("timelines")):
        visit(timeline)
    return found


def _timestamps(manifest: Any) -> Any:
    graphical = manifest.get("graphical") if isinstance(manifest, Mapping) else None
    return graphical.get("timestamps") if isinstance(graphical, dict) else None


def _respell(manifest: Any) -> None:
    """Spell every value of a manifest as its number type selects, in place.

    An own-axis value on an int axis becomes a JSON integer, on a float axis
    a float where one equals it exactly, and every member of a Fraction pair
    (own-axis, conversion-map Numbers at any depth, MeasureMap rows) a JSON
    integer where it is integral; a named timestamp's coordinate is read on
    the axis of the timeline it names. Anything else is left as it is, so any
    value may be given.
    """
    if not isinstance(manifest, dict):
        return
    for timeline in _dicts(manifest.get("timelines")):
        _respell_timeline(timeline, None)
    for measure_map in _dicts(manifest.get("measure_maps")):
        for row in _dicts(measure_map.get("rows")):
            for key in _ROW_NUMBER_MEMBERS:
                if key in row:
                    row[key] = _fraction(row[key])
    axis_types = _axis_types(manifest)
    for timestamp in _dicts(_timestamps(manifest)):
        timeline = timestamp.get("timeline")
        if isinstance(timeline, str):
            _respell_axis(timestamp, ("coordinate",), axis_types.get(timeline))


def canonical_order(value: Any) -> Any:
    """Return a deep copy of ``value``, its manifest in canonical order and spelling.

    A value with a top-level ``timelines`` array is a manifest: every timeline
    in it is ordered at every depth and the array itself by id, its ``groups``
    are ordered by id, each with its ``members`` by code point, its
    ``measure_maps`` and its ``schemes`` by id and its ``graphical.timestamps``
    by timeline, then coordinate, then id, each with its ``display`` in
    canonical order.
    Every value it reads by a number type is spelled as that type selects
    (module docstring). Only the arrays listed in the module docstring move;
    object keys are left as they are (``dumps`` sorts them), and any other
    JSON value is copied unchanged.

    Raises:
        ValueError: If a collection holds an entry whose ordering members are
            missing or of the wrong type.
    """
    result = copy.deepcopy(value)
    if not isinstance(result, Mapping) or not isinstance(result.get("timelines"), list):
        return result
    _respell(result)
    timelines = result["timelines"]
    for timeline in timelines:
        if isinstance(timeline, dict):
            _order_timeline(timeline)
    result["timelines"] = _sorted(timelines, _by_id, "timelines")
    groups = result.get("groups")
    if isinstance(groups, list):
        for group in groups:
            if isinstance(group, dict) and isinstance(group.get("members"), list):
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


def dumps(value: Any) -> str:
    """Return the standard text of a TimeToShare manifest, or of any JSON value.

    The value is put in :func:`canonical_order`, then written as UTF-8 text
    with the keys of every object sorted by code point, two-space indentation
    and a final newline, characters unescaped
    (``ensure_ascii=False``) and every float spelled as ``repr`` spells it.

    Raises:
        ValueError: If the value holds a NaN or an infinity, a string with a
            lone surrogate (which UTF-8 cannot encode), or a collection that
            cannot be put in canonical order.
    """
    ordered = canonical_order(value)
    return _utf8(
        json.dumps(
            ordered, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
        )
        + "\n"
    )
