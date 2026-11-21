"""The columns of the two table types and the cells they hold.

A coordinate cell stores its number twice, as a float64 ``value`` and as an
integer ``numerator``/``denominator`` pair, beside the ``unit`` and the
``number_type`` of the coordinate; the number type says which side is
authoritative: ``float`` the double, ``int`` and ``fraction`` the pair. Both
sides are present on every non-null cell.
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from pathlib import Path
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
    "PROJECTION_COLUMNS",
    "PROJECTION_OF_TYPE",
    "PROJECTION_SCHEMA",
    "PROVENANCE_KEYS",
    "PROVENANCE_METADATA_KEY",
    "PROVENANCE_TYPE",
    "SCOPE_FIELD",
    "coordinate_value",
    "fixture_path",
]

COORDINATE_KEYS = ("value", "numerator", "denominator", "unit", "number_type")
"""The members of a coordinate cell."""

COORDINATE_TYPE = pa.struct(
    [
        pa.field("value", pa.float64()),
        pa.field("numerator", pa.int64()),
        pa.field("denominator", pa.int64()),
        pa.field("unit", pa.string()),
        pa.field("number_type", pa.string()),
    ]
)
"""A coordinate (or a duration) on one timeline's axis."""

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
        pa.field("start", COORDINATE_TYPE),
        pa.field("duration", COORDINATE_TYPE),
        pa.field("projection_of", PROJECTION_OF_TYPE),
    ]
)
"""The Projections table: one row per Projection; ``duration`` null for an instant."""

MATCH_CLAIM_COLUMNS = tuple(MATCH_CLAIM_SCHEMA.names)
PROJECTION_COLUMNS = tuple(PROJECTION_SCHEMA.names)


def coordinate_value(cell: Mapping[str, Any]) -> Fraction:
    """The exact value of a well-formed coordinate cell, read from its number type."""
    if cell["number_type"] == "float":
        return Fraction(cell["value"])
    return Fraction(cell["numerator"], cell["denominator"])


def fixture_path(name: str) -> Path:
    """The path of one file of the table fixture, by its name.

    The fixture is a manifest (``manifest.yaml``), its two tables
    (``match_claims.parquet``, ``projections.parquet``) and the anchors and
    potential MatchStamps expected of the MatchClaim table
    (``expected.yaml``).
    """
    return _data_root() / "fixtures" / "tables" / SCHEMA_VERSION / name
