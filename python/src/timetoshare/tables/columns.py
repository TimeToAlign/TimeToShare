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

from ..validate import SCHEMA_VERSION, _data_root

__all__ = [
    "ANCHOR_TYPE",
    "BELIEFS",
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
        pa.field("timeline_a_id", pa.string()),
        pa.field("coordinate_a", COORDINATE_TYPE),
        pa.field("timeline_b_id", pa.string()),
        pa.field("coordinate_b", COORDINATE_TYPE),
    ]
)
"""An AlignmentAnchor: one coordinate of each of two timelines."""

BELIEFS = ("true", "false", "unlikely")
"""The words of a belief."""

BELIEF_KEYS = ("actor", "belief", "date", "note")
"""The members of a belief."""

BELIEF_TYPE = pa.struct([pa.field(key, pa.string()) for key in BELIEF_KEYS])

PROVENANCE_KEYS = (
    "stated_by",
    "date",
    "method",
    "service",
    "basis",
    "match",
    "note",
    "beliefs",
)
"""The members of a row's provenance: how it was made, then who believes it.

These are the keys of the format's provenance entry without ``property`` and
``value``, which a row needs no more than it needs a subject: the row is
what the entry is about.
"""

PROVENANCE_TYPE = pa.struct(
    [
        pa.field("stated_by", pa.list_(pa.string())),
        pa.field("date", pa.string()),
        pa.field("method", pa.string()),
        pa.field("service", pa.string()),
        pa.field("basis", pa.list_(pa.string())),
        pa.field("match", pa.string()),
        pa.field("note", pa.string()),
        pa.field("beliefs", pa.list_(BELIEF_TYPE)),
    ]
)

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
        pa.field("is_explicit", pa.bool_()),
        pa.field("provenance", PROVENANCE_TYPE),
        pa.field("certainty", pa.float64()),
        pa.field("source_claim_id", pa.string()),
        pa.field("event_a_id", pa.string()),
        pa.field("event_a_name", pa.string()),
        pa.field("event_b_id", pa.string()),
        pa.field("event_b_name", pa.string()),
        pa.field("source_coordinate", COORDINATE_TYPE),
        pa.field("id", pa.string()),
        pa.field("id_minted", pa.bool_()),
    ]
)
"""The MatchClaim table: one row per MatchClaim, one column per property."""

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
