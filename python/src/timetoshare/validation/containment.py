"""Timeline containment rules."""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping
from fractions import Fraction
from itertools import pairwise
from typing import Any

from ..manifest import _exact
from ..serialization import spell
from .diagnostics import SchemaValidationError, _entries, _Path, number_type_of
from .representation import rewritten


def offset_order(children: list[Any]) -> list[int]:
    """Return child indices in exact offset order, ties by id."""
    return sorted(
        range(len(children)),
        key=lambda index: (_exact(children[index]["offset"]), children[index]["id"]),
    )


def _double(value: Any) -> float | None:
    """Return a JSON number as the double a reader reads, or ``None`` for none.

    A Fraction pair and an integer beyond the range of doubles have none.
    """
    if isinstance(value, list):
        return None
    try:
        return float(value)
    except OverflowError:
        return None


def _child_end(timeline: Mapping[str, Any], child: Mapping[str, Any]) -> Fraction:
    """Return where a child of known length ends on its parent's axis.

    The offset lies on the parent's axis and the length on the child's. Where
    both axes are ``float``, a reader adds the two JSON numbers as doubles, so
    the end is their double sum, which may differ from the exact sum by a
    rounding; wherever either axis is ``int`` or ``fraction``, the end is the
    exact sum.
    """
    if number_type_of(timeline) == number_type_of(child) == "float":
        offset, length = _double(child["offset"]), _double(child["length"])
        if offset is not None and length is not None and math.isfinite(offset + length):
            return Fraction(offset + length)
    return _exact(child["offset"]) + _exact(child["length"])


def child_ends(timeline: Mapping[str, Any]) -> list[Fraction | None]:
    """Return each child's end on its parent's axis, as an exact Fraction.

    A child's end is its ``offset`` plus its ``length``. Where the timeline and
    the child both have number type ``float``, the two JSON numbers are summed
    in IEEE double arithmetic, as a reader adds them, so the end may differ from
    the exact sum by a rounding. In every other case (``int``, ``fraction``,
    mixed number types, a value with no double such as a Fraction pair or an
    integer beyond the range of doubles, or a double sum that overflows) the
    sum is exact. A child with no length, or on another unit than its parent, has
    end ``None``, except a child of a segment line without a length, whose
    end is the offset of the next child in offset order.
    """
    children = _entries(timeline, "children")
    ends: list[Fraction | None] = [
        _child_end(timeline, child)
        if child.get("length") is not None and child["unit"] == timeline["unit"]
        else None
        for child in children
    ]
    if timeline.get("is_segment_line") is True:
        order = offset_order(children)
        for index, successor in pairwise(order):
            if children[index].get("length") is None:
                ends[index] = _exact(children[successor]["offset"])
    return ends


def timeline_containment_problems(
    timeline: Mapping[str, Any], path: _Path
) -> Iterator[SchemaValidationError]:
    """Yield children off their parent's axis or beyond its known end."""
    length = timeline.get("length")
    ends = child_ends(timeline)
    for index, child in enumerate(_entries(timeline, "children")):
        at = (*path, "children", index)
        offset = _exact(child["offset"])
        if child["unit"] != timeline["unit"]:
            yield SchemaValidationError(
                "child_unit",
                (*at, "unit"),
                f"child '{child['id']}' has unit '{child['unit']}', its parent "
                f"'{timeline['id']}' has '{timeline['unit']}'",
            )
        end = ends[index]
        if length is not None and offset > _exact(length):
            yield SchemaValidationError(
                "child_offset",
                (*at, "offset"),
                f"offset {spell(child['offset'])} of '{child['id']}' is beyond the "
                f"length {spell(length)} of its parent '{timeline['id']}'",
            )
        elif length is not None and end is not None and end > _exact(length):
            pair = [end.numerator, end.denominator]
            yield SchemaValidationError(
                "child_end",
                (*at, "length"),
                f"child '{child['id']}' ends at "
                f"{rewritten(pair, number_type_of(timeline)) or spell(pair)}, beyond "
                f"the length {spell(length)} of its parent '{timeline['id']}'",
            )
        yield from timeline_containment_problems(child, at)
