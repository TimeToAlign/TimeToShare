"""The canonical order of a TimeToShare manifest and the respelling of its values.

Readers accept a manifest's arrays in any order; writers emit one canonical
order (the README's "Canonical order"):

* ``timelines``, ``groups`` and ``measure_maps`` by ID, and
  every group's ``members`` by code point;
* in every timeline, ``children`` by offset, then ID; ``conversion_maps`` by
  ID; ``regions`` by start, then end, then ID; ``flow_control`` by
  coordinate, then ID, and the ``targets`` of every jump by place: the
  destination without a place first, then those with ``by``, by value, then
  those with ``to``, by ID;
* ``resources``, ``flow_maps`` and ``virtual_timelines`` by ID; a FlowMap's
  ``chunks`` keep their order, which is the order they are played in;
* ``graphical.timestamps`` by timeline, then coordinate, then ID, and every
  timestamp's ``display`` in the order of :data:`TIMESTAMP_DISPLAY`, other
  strings after them by code point and other values last in their given
  order;
* ``graphical.matchstamps`` by ID, the ``alignment_anchors`` of each by ID,
  and every anchor's ``display`` in the order of :data:`ANCHOR_DISPLAY`, as
  a timestamp's;
* ``graphical.elisions`` by timeline, then start, then ID, and every
  elision's ``display`` in the order of :data:`ELISION_DISPLAY`, as a
  timestamp's.

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
from types import MappingProxyType
from typing import Any, NamedTuple

__all__ = [
    "ANCHOR_DISPLAY",
    "ELISION_DISPLAY",
    "TIMESTAMP_DISPLAY",
    "UNITS",
    "UnitEntry",
    "canonical_order",
]


class UnitEntry(NamedTuple):
    """One row of the unit table: a unit's domain, modality and number types.

    ``number_type`` is the default number type of an axis declaring none, and
    ``number_types`` the number types the unit admits, in the order ``int``,
    ``float``, ``fraction``.
    """

    domain: str
    modality: str
    number_type: str
    number_types: tuple[str, ...]


_DISCRETE = ("int",)
_CONTINUOUS = ("float", "fraction")

UNITS: Mapping[str, UnitEntry] = MappingProxyType(
    {
        "number": UnitEntry("logical", "continuous", "float", ("int", *_CONTINUOUS)),
        "floating_measures": UnitEntry("logical", "continuous", "float", _CONTINUOUS),
        "whole_notes": UnitEntry("logical", "continuous", "fraction", _CONTINUOUS),
        "quarters": UnitEntry("logical", "continuous", "fraction", _CONTINUOUS),
        "ticks": UnitEntry("logical", "discrete", "int", _DISCRETE),
        "milliseconds": UnitEntry("physical", "continuous", "float", _CONTINUOUS),
        "seconds": UnitEntry("physical", "continuous", "float", _CONTINUOUS),
        "minutes": UnitEntry("physical", "continuous", "float", _CONTINUOUS),
        "samples": UnitEntry("physical", "discrete", "int", _DISCRETE),
        "frames": UnitEntry("physical", "discrete", "int", _DISCRETE),
        "pixels": UnitEntry("graphical", "discrete", "int", _DISCRETE),
        "meters": UnitEntry("graphical", "continuous", "float", _CONTINUOUS),
        "centimeters": UnitEntry("graphical", "continuous", "float", _CONTINUOUS),
        "millimeters": UnitEntry("graphical", "continuous", "float", _CONTINUOUS),
        "inches": UnitEntry("graphical", "continuous", "float", _CONTINUOUS),
        "points": UnitEntry("graphical", "continuous", "float", _CONTINUOUS),
        "css_pixels": UnitEntry("graphical", "continuous", "float", _CONTINUOUS),
        "user_units": UnitEntry("graphical", "continuous", "float", _CONTINUOUS),
    }
)
"""The unit table, in the schema's order of ``TimeUnit``: every unit's domain,
modality, default number type and admitted number types. A discrete unit
admits ``int`` only, a continuous unit ``float`` or ``fraction``, and
``number`` all three."""

_NUMBER_TYPES = ("int", "float", "fraction")

TIMESTAMP_DISPLAY = ("wedge", "name", "id", "coordinate", "cross_section")
"""The words of a named timestamp's ``display``, in canonical order."""

ANCHOR_DISPLAY = ("line", "name")
"""The words of an alignment anchor's ``display``, in canonical order."""

ELISION_DISPLAY = ("ellipsis", "name", "id", "coordinate", "continuation")
"""The words of an elision's ``display``, in canonical order."""


def _integral(value: Any) -> int | None:
    """The integer a JSON integer or an integral float equals, else ``None``."""
    if type(value) is int:
        return value
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
    numerator, denominator = _integral(value[0]), _integral(value[1])
    if numerator is None or denominator is None or denominator < 1:
        return None
    return Fraction(numerator, denominator)


def exact(value: Any) -> Fraction:
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


def _display_key(words: tuple[str, ...]) -> Callable[[Any], tuple[int, int, str]]:
    """Order the words of a ``display``: the known ``words`` canonically, then others.

    A string the schema does not know follows them by code point, and any
    other value follows last in its given order, so ordering never fails.
    """

    def key(word: Any) -> tuple[int, int, str]:
        if isinstance(word, str) and word in words:
            return (0, words.index(word), "")
        if isinstance(word, str):
            return (1, 0, word)
        return (2, 0, "")

    return key


def _order_display(owner: dict[str, Any], words: tuple[str, ...]) -> None:
    display = owner.get("display")
    if isinstance(display, list):
        owner["display"] = sorted(display, key=_display_key(words))


def order_displays(manifest: Any) -> None:
    """Put the ``display`` of every timestamp, anchor and elision in canonical order."""
    for timestamp in _dicts(_timestamps(manifest)):
        _order_display(timestamp, TIMESTAMP_DISPLAY)
    for matchstamp in _dicts(_matchstamps(manifest)):
        for anchor in _dicts(matchstamp.get("alignment_anchors")):
            _order_display(anchor, ANCHOR_DISPLAY)
    for elision in _dicts(_elisions(manifest)):
        _order_display(elision, ELISION_DISPLAY)


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


def _by_place(destination: Any) -> tuple[int, Fraction, str]:
    """Order a jump's destinations: without a place, then by ``by``, then by ``to``."""
    if "by" in destination:
        return (1, exact(destination["by"]), "")
    if "to" in destination:
        return (2, Fraction(0), _identifier(destination["to"]))
    return (0, Fraction(0), "")


def _order_timeline(timeline: dict[str, Any]) -> None:
    """Put the arrays of one timeline and its descendants in order, in place."""
    children = timeline.get("children")
    if isinstance(children, list):
        for child in _dicts(children):
            _order_timeline(child)
        timeline["children"] = _sorted(
            children,
            lambda entry: (exact(entry["offset"]), _by_id(entry)),
            "children",
        )
    if isinstance(timeline.get("conversion_maps"), list):
        timeline["conversion_maps"] = _sorted(
            timeline["conversion_maps"], _by_id, "conversion_maps"
        )
    if isinstance(timeline.get("regions"), list):
        timeline["regions"] = _sorted(
            timeline["regions"],
            lambda entry: (exact(entry["start"]), exact(entry["end"]), _by_id(entry)),
            "regions",
        )
    if isinstance(timeline.get("flow_control"), list):
        for entry in _dicts(timeline["flow_control"]):
            if isinstance(entry.get("targets"), list):
                entry["targets"] = _sorted(entry["targets"], _by_place, "targets")
        timeline["flow_control"] = _sorted(
            timeline["flow_control"],
            lambda entry: (exact(entry["coordinate"]), _by_id(entry)),
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
    if not isinstance(unit, str) or unit not in UNITS:
        return None
    if "number_type" not in timeline:
        return UNITS[unit].number_type
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


def _respell_condition(holder: Any, number_type: str | None) -> None:
    """Respell the ``by`` of the ``after`` a destination or an ``ends`` holds."""
    after = holder.get("after") if isinstance(holder, dict) else None
    if isinstance(after, dict):
        _respell_axis(after, ("by",), number_type)


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
        _respell_condition(entry.get("ends"), own)
        for destination in _dicts(entry.get("targets")):
            _respell_axis(destination, ("by",), own)
            _respell_condition(destination, own)
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


def _matchstamps(manifest: Any) -> Any:
    graphical = manifest.get("graphical") if isinstance(manifest, Mapping) else None
    return graphical.get("matchstamps") if isinstance(graphical, dict) else None


def _elisions(manifest: Any) -> Any:
    graphical = manifest.get("graphical") if isinstance(manifest, Mapping) else None
    return graphical.get("elisions") if isinstance(graphical, dict) else None


def respell(manifest: Any) -> None:
    """Respell every own-axis value of a manifest as its number type selects, in place.

    The own-axis values are a timeline's ``length`` and ``offset``, its
    regions' ``start`` and ``end``, its flow-control coordinates and the
    ``by`` of every destination and of every ``after`` on it, the
    coordinate of every named timestamp on it, the ``start``, ``end`` and
    width ``span`` of every elision on it, the gaps of every FlowMap of it,
    and a virtual timeline's ``length`` on the virtual timeline's own axis.
    A timestamp, an elision or a FlowMap whose ``timeline`` names no
    timeline, or more than one, keeps its values.
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
    for elision in _dicts(_elisions(manifest)):
        timeline = elision.get("timeline")
        if isinstance(timeline, str):
            number_type = axis_types.get(timeline)
            _respell_axis(elision, ("start", "end"), number_type)
            width = elision.get("width")
            if isinstance(width, dict):
                _respell_axis(width, ("span",), number_type)
    for flow_map in _dicts(manifest.get("flow_maps")):
        timeline = flow_map.get("timeline")
        if isinstance(timeline, str):
            for chunk in _dicts(flow_map.get("chunks")):
                _respell_axis(chunk, ("gap",), axis_types.get(timeline))
    for virtual in _dicts(manifest.get("virtual_timelines")):
        _respell_axis(virtual, ("length",), _axis_type(virtual))


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
    respell(result)
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
    if isinstance(result.get("measure_maps"), list):
        result["measure_maps"] = _sorted(result["measure_maps"], _by_id, "measure_maps")
    timestamps = _timestamps(result)
    if isinstance(timestamps, list):
        result["graphical"]["timestamps"] = _sorted(
            timestamps,
            lambda entry: (
                _identifier(entry["timeline"]),
                exact(entry["coordinate"]),
                _by_id(entry),
            ),
            "timestamps",
        )
    for key in ("resources", "flow_maps", "virtual_timelines"):
        if isinstance(result.get(key), list):
            result[key] = _sorted(result[key], _by_id, key)
    matchstamps = _matchstamps(result)
    if isinstance(matchstamps, list):
        for matchstamp in _dicts(matchstamps):
            if isinstance(matchstamp.get("alignment_anchors"), list):
                matchstamp["alignment_anchors"] = _sorted(
                    matchstamp["alignment_anchors"], _by_id, "alignment_anchors"
                )
        result["graphical"]["matchstamps"] = _sorted(matchstamps, _by_id, "matchstamps")
    elisions = _elisions(result)
    if isinstance(elisions, list):
        result["graphical"]["elisions"] = _sorted(
            elisions,
            lambda entry: (
                _identifier(entry["timeline"]),
                exact(entry["start"]),
                _by_id(entry),
            ),
            "elisions",
        )
    order_displays(result)
    return result
