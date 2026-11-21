"""From MatchClaims to AlignmentAnchors and potential MatchStamps.

The reference derivation of the format: small and exact, for conformance,
not for speed. It reads a MatchClaim table the checks accept.

- The belief filter selects the rows. Without a believer nothing is
  filtered; for a believer, every row the believer does not believe
  ``"false"`` (``belief="not_false"``, the default) or only the rows the
  believer believes ``"true"`` (``belief="true"``).
- A synchronous MatchClaim gives the anchor of its ``start_anchor`` and, if
  it has one, of its ``end_anchor``; NOMATCH and conceptual MatchClaims give
  none. Two anchors are the same when both coordinates are equal, compared
  exactly on the two timelines' axes, whichever side each stands on.
- A potential MatchStamp is one connected set of coordinates under the
  unique anchors.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Literal

import pyarrow as pa

from ..validation.diagnostics import connected_sets
from .checks import row_provenance
from .columns import coordinate_value

__all__ = [
    "BELIEF_FILTERS",
    "AlignmentAnchor",
    "PotentialMatchStamp",
    "TimelineCoordinate",
    "alignment_anchors",
    "believed_rows",
    "potential_matchstamps",
]


BeliefFilter = Literal["not_false", "true"]

BELIEF_FILTERS: tuple[BeliefFilter, ...] = ("not_false", "true")
"""What a filter asks of its believer: any belief but ``"false"``, or ``"true"``."""


@dataclass(frozen=True, order=True)
class TimelineCoordinate:
    """A coordinate of a timeline: its ID and the exact value on its axis.

    A timeline's coordinates share one unit and one number type (the checks
    hold it), so the value alone tells two of them apart.
    """

    timeline_id: str
    value: Fraction


@dataclass(frozen=True, order=True)
class AlignmentAnchor:
    """Two coordinates of two timelines, in sorted order: no metadata."""

    coordinates: tuple[TimelineCoordinate, TimelineCoordinate]


@dataclass(frozen=True)
class PotentialMatchStamp:
    """The coordinates one chain of anchors joins, sorted, with the anchors
    joining them and the MatchClaims stating those, each sorted."""

    coordinates: tuple[TimelineCoordinate, ...]
    alignment_anchors: tuple[AlignmentAnchor, ...]
    match_claims: tuple[str, ...]


def believed_rows(
    table: pa.Table, believer: str | None = None, belief: BeliefFilter = "not_false"
) -> list[int]:
    """The rows the belief filter keeps, by index.

    Raises:
        ValueError: If ``belief`` is none of :data:`BELIEF_FILTERS`.
    """
    if belief not in BELIEF_FILTERS:
        raise ValueError(f"'{belief}' is no belief filter: write 'not_false' or 'true'")
    provenance = row_provenance(table)
    if believer is None:
        return list(range(len(provenance)))
    kept = []
    for index, entry in enumerate(provenance):
        beliefs = (entry or {}).get("beliefs") or ()
        held = next((b["belief"] for b in beliefs if b["actor"] == believer), None)
        if (held == "true") if belief == "true" else (held != "false"):
            kept.append(index)
    return kept


def _anchor(row: dict[str, Any], key: str) -> AlignmentAnchor:
    """The anchor of a row's anchor cell, its coordinates on the row's timelines."""
    cell = row[key]
    first, second = sorted(
        TimelineCoordinate(
            row[f"timeline_{side}_id"], coordinate_value(cell[f"coordinate_{side}"])
        )
        for side in ("a", "b")
    )
    return AlignmentAnchor((first, second))


def alignment_anchors(
    table: pa.Table, believer: str | None = None, belief: BeliefFilter = "not_false"
) -> dict[AlignmentAnchor, tuple[str, ...]]:
    """The unique anchors of the rows the filter keeps, sorted, each with the
    sorted IDs of the MatchClaims stating it."""
    columns = ["id", "timeline_a_id", "timeline_b_id", "start_anchor", "end_anchor"]
    rows = table.select(columns).to_pylist()
    stated: dict[AlignmentAnchor, set[str]] = {}
    for index in believed_rows(table, believer, belief):
        row = rows[index]
        for key in ("start_anchor", "end_anchor"):
            if row[key] is not None:
                stated.setdefault(_anchor(row, key), set()).add(row["id"])
    return {anchor: tuple(sorted(stated[anchor])) for anchor in sorted(stated)}


def potential_matchstamps(
    table: pa.Table, believer: str | None = None, belief: BeliefFilter = "not_false"
) -> list[PotentialMatchStamp]:
    """The potential MatchStamps of the rows the filter keeps, sorted by
    their first coordinate."""
    anchors = alignment_anchors(table, believer, belief)
    sets = connected_sets(anchor.coordinates for anchor in anchors)
    members: dict[TimelineCoordinate, list[AlignmentAnchor]] = {}
    for anchor in anchors:
        members.setdefault(sets[anchor.coordinates[0]], []).append(anchor)
    stamps = [
        PotentialMatchStamp(
            coordinates=tuple(
                sorted({c for anchor in held for c in anchor.coordinates})
            ),
            alignment_anchors=tuple(held),
            match_claims=tuple(
                sorted({claim for anchor in held for claim in anchors[anchor]})
            ),
        )
        for held in members.values()
    ]
    return sorted(stamps, key=lambda stamp: stamp.coordinates[0])
