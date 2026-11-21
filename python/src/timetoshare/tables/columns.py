"""The columns of the two table types and the cells they hold.

A number is three members, filled by its number type and never mirrored:
an ``int`` is its ``numerator`` alone, a ``fraction`` its ``numerator`` and
its ``denominator`` (at least 1), a ``float`` its finite ``value`` alone;
every other member is null. A coordinate cell of the MatchClaim table adds
the ``unit`` and the ``number_type`` of its coordinate; a row of the
Projections table states them once, in its own ``unit`` and ``number_type``
columns, for its ``start`` and its ``duration``. :func:`number_cell` writes
a number's members and :func:`coordinate_value` reads them back.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from fractions import Fraction
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pyarrow as pa

from ..validate import PROVENANCE_DEFINITION, SCHEMA_VERSION, _data_root, load_schema

__all__ = [
    "ANCHOR_TYPE",
    "BELIEF_KEYS",
    "BELIEF_TYPE",
    "COORDINATE_KEYS",
    "COORDINATE_TYPE",
    "MATCH_CLAIM_COLUMNS",
    "MATCH_CLAIM_SCHEMA",
    "NUMBER_KEYS",
    "NUMBER_MEMBERS",
    "NUMBER_TYPE",
    "PROJECTION_COLUMNS",
    "PROJECTION_OF_TYPE",
    "PROJECTION_SCHEMA",
    "PROVENANCE_KEYS",
    "PROVENANCE_METADATA_KEY",
    "PROVENANCE_TYPE",
    "SCOPE_FIELD",
    "coordinate_value",
    "fixture_path",
    "number_cell",
]

NUMBER_KEYS = ("numerator", "denominator", "value")
"""The members of a number."""

NUMBER_MEMBERS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "int": ("numerator",),
        "fraction": ("numerator", "denominator"),
        "float": ("value",),
    }
)
"""The members a number of each number type fills; the others are null."""

NUMBER_TYPE = pa.struct(
    [
        pa.field("numerator", pa.int64()),
        pa.field("denominator", pa.int64()),
        pa.field("value", pa.float64()),
    ]
)
"""A number: a Projection's ``start`` or ``duration``, whose row states the unit
and the number type."""

COORDINATE_KEYS = (*NUMBER_KEYS, "unit", "number_type")
"""The members of a coordinate cell."""

COORDINATE_TYPE = pa.struct(
    [*NUMBER_TYPE, pa.field("unit", pa.string()), pa.field("number_type", pa.string())]
)
"""A coordinate on one timeline's axis: a number with its unit and number type."""

ANCHOR_TYPE = pa.struct(
    [
        pa.field("coordinate_a", COORDINATE_TYPE),
        pa.field("coordinate_b", COORDINATE_TYPE),
    ]
)
"""An AlignmentAnchor: one coordinate of each of the row's two timelines,
``coordinate_a`` on its ``timeline_a_id``, ``coordinate_b`` on its
``timeline_b_id``."""

_DEFINITIONS = load_schema()["$defs"]
_RECORD = _DEFINITIONS[PROVENANCE_DEFINITION]
_BELIEF_REFERENCE = "#/$defs/Belief"

BELIEF_KEYS = tuple(_DEFINITIONS["Belief"]["properties"])
"""The members of a belief: the keys of the provenance schema's ``Belief``."""

BELIEF_TYPE = pa.struct([pa.field(key, pa.string()) for key in BELIEF_KEYS])
"""A belief, each member a string (``belief`` one of :data:`timetoshare.BELIEFS`)."""

PROVENANCE_KEYS = tuple(_RECORD["properties"])
"""The members of a row's provenance: the keys of the provenance schema.

How it was made, then who believes it, in the schema's order. The
manifest's entries add ``property`` and ``value``, which a row needs no
more than it needs a subject: the row is what the entry is about.
"""


def _member_type(member: Mapping[str, Any]) -> pa.DataType:
    """The Arrow type of a provenance member: a list for an array, else a string."""
    if member.get("type") != "array":
        return pa.string()
    if member["items"].get("$ref") == _BELIEF_REFERENCE:
        return pa.list_(BELIEF_TYPE)
    return pa.list_(pa.string())


PROVENANCE_TYPE = pa.struct(
    [pa.field(key, _member_type(_RECORD["properties"][key])) for key in PROVENANCE_KEYS]
)
"""A row's provenance, the members of :data:`PROVENANCE_KEYS` with their types."""

PROVENANCE_METADATA_KEY = "timetoshare:provenance"
"""The schema-metadata key holding, as JSON, a provenance shared by every row."""

PROJECTION_OF_TYPE = pa.struct(
    [pa.field("timeline_id", pa.string()), pa.field("event_id", pa.string())]
)
"""The event a Projection stands for, by its timeline and its ID."""

MATCH_CLAIM_SCHEMA = pa.schema(
    [
        pa.field("timeline_a_id", pa.string()),
        pa.field("timeline_b_id", pa.string()),
        pa.field("start_anchor", ANCHOR_TYPE),
        pa.field("end_anchor", ANCHOR_TYPE),
        pa.field("is_synchronous", pa.bool_()),
        pa.field("provenance", PROVENANCE_TYPE),
        pa.field("certainty", pa.float64()),
        pa.field("event_a_id", pa.string()),
        pa.field("event_a_name", pa.string()),
        pa.field("event_b_id", pa.string()),
        pa.field("event_b_name", pa.string()),
        pa.field("id", pa.string()),
    ]
)
"""The MatchClaim table: one row per MatchClaim, one column per property."""

SCOPE_FIELD = pa.field("scope", pa.string())
"""The MatchClaim table's optional key column: the scope of each row's ID.

Null for the package's own MatchClaims, else the name of the scope the row
comes from; a table of the package's own MatchClaims alone has no such
column. A MatchClaim is its scope and its ID, never a string joining them.
"""

PROJECTION_SCHEMA = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("timeline_id", pa.string()),
        pa.field("unit", pa.string()),
        pa.field("number_type", pa.string()),
        pa.field("start", NUMBER_TYPE),
        pa.field("duration", NUMBER_TYPE),
        pa.field("projection_of", PROJECTION_OF_TYPE),
    ]
)
"""The Projections table: one row per Projection, its ``unit`` and
``number_type`` stated once for its ``start`` and its ``duration``;
``duration`` null for an instant."""

MATCH_CLAIM_COLUMNS = tuple(MATCH_CLAIM_SCHEMA.names)
PROJECTION_COLUMNS = tuple(PROJECTION_SCHEMA.names)


_INT64 = (-(2**63), 2**63 - 1)


def _double(value: int) -> bool:
    """Whether a double holds the integer ``value`` exactly."""
    try:
        return float(value) == value
    except OverflowError:
        return False


def number_cell(value: int | Fraction | float, number_type: str) -> dict[str, Any]:
    """The members of a number of the number type ``number_type``.

    An ``int`` takes an integer (or a Fraction whose denominator is 1), a
    ``fraction`` an integer or a Fraction, written in lowest terms, a
    ``float`` a finite float or an integer a double holds exactly; a float
    is never written as a Fraction, nor a Fraction as a float, and an exact
    number's members are 64-bit integers.

    Raises:
        ValueError: If ``number_type`` is no number type or ``value`` is no
            number of it.
    """
    if number_type not in NUMBER_MEMBERS:
        raise ValueError(f"'{number_type}' is no number type")
    exact = isinstance(value, (int, Fraction)) and not isinstance(value, bool)
    if number_type == "float":
        if isinstance(value, float) and math.isfinite(value):
            return {"numerator": None, "denominator": None, "value": value}
        if isinstance(value, int) and not isinstance(value, bool) and _double(value):
            return {"numerator": None, "denominator": None, "value": float(value)}
        raise ValueError(f"a float number is a finite float, not {value!r}")
    article = "an" if number_type == "int" else "a"
    if not exact:
        raise ValueError(f"{article} {number_type} number is exact, not {value!r}")
    fraction = Fraction(value)
    if number_type == "int" and fraction.denominator != 1:
        raise ValueError(f"an int number is an integer, not {value!r}")
    if (
        not _INT64[0] <= fraction.numerator <= _INT64[1]
        or fraction.denominator > _INT64[1]
    ):
        raise ValueError(
            f"{article} {number_type} number is written in 64-bit integers, "
            f"not {value!r}"
        )
    if number_type == "int":
        return {"numerator": fraction.numerator, "denominator": None, "value": None}
    return {
        "numerator": fraction.numerator,
        "denominator": fraction.denominator,
        "value": None,
    }


def coordinate_value(
    cell: Mapping[str, Any], number_type: str | None = None
) -> Fraction:
    """The exact value of a well-formed number, read from its number type.

    Args:
        cell: A coordinate cell, or a Projection's ``start`` or ``duration``.
        number_type: The number type the row states, for a Projection's
            number; ``None`` reads the cell's own ``number_type``.
    """
    kind = cell["number_type"] if number_type is None else number_type
    if kind == "float":
        return Fraction(cell["value"])
    if kind == "int":
        return Fraction(cell["numerator"])
    return Fraction(cell["numerator"], cell["denominator"])


def fixture_path(name: str) -> Path:
    """The path of one file of the table fixture, by its name.

    The fixture is a manifest (``manifest.yaml``), its two tables
    (``match_claims.parquet``, ``projections.parquet``) and the anchors and
    potential MatchStamps expected of the MatchClaim table
    (``expected.yaml``).
    """
    return _data_root() / "fixtures" / "tables" / SCHEMA_VERSION / name
