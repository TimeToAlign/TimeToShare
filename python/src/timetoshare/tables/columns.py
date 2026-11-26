"""The columns of the two table types and the cells they hold.

A number is three members, filled by its number type and never mirrored:
an ``int`` is its ``numerator`` alone, a ``fraction`` its ``numerator`` and
its ``denominator`` (at least 1), a ``float`` its finite ``value`` alone;
every other member is null. A coordinate cell of the MatchClaim table adds
the ``unit`` and the ``number_type`` of its coordinate; a row of the
Projections table states them once, in its own ``unit`` and ``number_type``
columns, for its ``start`` and its ``duration``. :func:`number_cell` writes
a number's members and :func:`coordinate_value` reads them back.

Both tables' columns and the structs of their cells are read from one file,
``tables.json`` beside the manifest schema (:func:`tables_path`), never
declared a second time here.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from fractions import Fraction
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pyarrow as pa

from ..ids import CHUNK_SENTINEL, NOMATCH_SENTINEL
from ..validate import (
    PROVENANCE_DEFINITION,
    PROVENANCE_DOCUMENT,
    SCHEMA_VERSION,
    data_root,
    load_schema,
)

__all__ = [
    "ANCHOR_TYPE",
    "BELIEF_KEYS",
    "BELIEF_TYPE",
    "CHUNK_SENTINEL",
    "COORDINATE_KEYS",
    "COORDINATE_TYPE",
    "MATCH_CLAIM_COLUMNS",
    "MATCH_CLAIM_REQUIRED",
    "MATCH_CLAIM_SCHEMA",
    "NOMATCH_SENTINEL",
    "NUMBER_KEYS",
    "NUMBER_MEMBERS",
    "NUMBER_TYPE",
    "PROJECTION_COLUMNS",
    "PROJECTION_REQUIRED",
    "PROJECTION_OF_TYPE",
    "PROJECTION_SCHEMA",
    "PROVENANCE_KEYS",
    "PROVENANCE_METADATA_KEY",
    "PROVENANCE_TYPE",
    "TABLES_DOCUMENT",
    "coordinate_value",
    "fixture_path",
    "number_cell",
    "tables_path",
]

TABLES_DOCUMENT = "tables.json"
"""The file name of the column types beside the manifest schema."""


def tables_path() -> Path:
    """Return the path of the column types of the two tables, ``tables.json``.

    The one source of :data:`MATCH_CLAIM_SCHEMA` and
    :data:`PROJECTION_SCHEMA`: its ``types`` declare the structs a cell
    holds, its ``tables`` each table's status and its columns, in order.
    """
    return data_root() / "schema" / SCHEMA_VERSION / TABLES_DOCUMENT


def _read_tables() -> dict[str, Any]:
    with tables_path().open(encoding="utf-8") as handle:
        return json.load(handle)


_TABLES = _read_tables()
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


def _provenance_type() -> pa.DataType:
    return pa.struct(
        [
            pa.field(key, _member_type(_RECORD["properties"][key]))
            for key in PROVENANCE_KEYS
        ]
    )


def _arrow_type(name: str) -> pa.DataType:
    """The Arrow type a column or a struct member names: a type of the
    file's ``types``, else one of the type names ``string``, ``bool``,
    ``int64`` and ``float64``."""
    declared = _TABLES["types"].get(name)
    if declared is None:
        return pa.type_for_alias(name)
    if "schema" in declared:
        if declared["schema"] != PROVENANCE_DOCUMENT:
            raise ValueError(f"the type '{name}' names an unknown schema")
        return _provenance_type()
    return pa.struct(
        [
            pa.field(member["name"], _arrow_type(member["type"]))
            for member in declared["struct"]
        ]
    )


def _table_schema(table: str) -> pa.Schema:
    return pa.schema(
        [
            pa.field(column["name"], _arrow_type(column["type"]))
            for column in _TABLES["tables"][table]["columns"]
        ]
    )


def _required(table: str) -> tuple[str, ...]:
    """The columns of ``table`` that hold no null, in the table's order."""
    return tuple(
        column["name"]
        for column in _TABLES["tables"][table]["columns"]
        if not column["nullable"]
    )


NUMBER_KEYS = tuple(member["name"] for member in _TABLES["types"]["number"]["struct"])
"""The members of a number."""

NUMBER_MEMBERS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "int": ("numerator",),
        "fraction": ("numerator", "denominator"),
        "float": ("value",),
    }
)
"""The members a number of each number type fills; the others are null."""

NUMBER_TYPE = _arrow_type("number")
"""A number: a Projection's ``start`` or ``duration``, whose row states the unit
and the number type."""

COORDINATE_KEYS = tuple(
    member["name"] for member in _TABLES["types"]["coordinate"]["struct"]
)
"""The members of a coordinate cell."""

COORDINATE_TYPE = _arrow_type("coordinate")
"""A coordinate on one timeline's axis: a number with its unit and number type."""

ANCHOR_TYPE = _arrow_type("anchor")
"""An AlignmentAnchor: one coordinate of each of the row's two timelines,
``coordinate_a`` on its ``timeline_a_id``, ``coordinate_b`` on its
``timeline_b_id``."""

PROVENANCE_TYPE = _arrow_type("provenance")
"""A row's provenance, the members of :data:`PROVENANCE_KEYS` with their types."""

PROVENANCE_METADATA_KEY = "timetoshare:provenance"
"""The schema-metadata key holding, as JSON, a provenance shared by every row."""

PROJECTION_OF_TYPE = _arrow_type("projection_of")
"""The event a Projection stands for, by its timeline and its ID."""

MATCH_CLAIM_SCHEMA = _table_schema("MatchClaim")
"""The MatchClaim table: one row per MatchClaim, one column per property,
each MatchClaim addressed by its ID alone."""

PROJECTION_SCHEMA = _table_schema("Projection")
"""The Projections table: one row per Projection, its ``unit`` and
``number_type`` stated once for its ``start`` and its ``duration``;
``duration`` null for an instant."""

MATCH_CLAIM_COLUMNS = tuple(MATCH_CLAIM_SCHEMA.names)
PROJECTION_COLUMNS = tuple(PROJECTION_SCHEMA.names)

MATCH_CLAIM_REQUIRED = _required("MatchClaim")
"""The columns of the MatchClaim table that hold no null, in its order."""

PROJECTION_REQUIRED = _required("Projection")
"""The columns of the Projections table that hold no null, in its order."""


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
    ``fraction`` an integer or a Fraction, written as its numerator and
    denominator, a ``float`` a finite float or an integer a double holds
    exactly; a float is never written as a Fraction, nor a Fraction as a
    float, and an exact number's members are 64-bit integers.

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

    A fraction is read in whatever terms it is written: ``(2, 4, null)``
    is the value ``1/2``.

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
    return data_root() / "fixtures" / "tables" / SCHEMA_VERSION / name
