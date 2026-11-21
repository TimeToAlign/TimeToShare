"""From MatchClaims to AlignmentAnchors and potential MatchStamps.

The reference derivation of the format: small and exact, for conformance,
not for speed. It reads a MatchClaim table the checks accept.

- The belief filter selects the rows. Without an actor nothing is filtered;
  for an actor, every row the actor does not believe ``false`` (the default)
  or, with ``only_true``, only the rows the actor believes ``true``.
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
from typing import Any

import pyarrow as pa

from .checks import row_provenance
from .columns import coordinate_value

__all__ = [
    "AlignmentAnchor",
    "PotentialMatchStamp",
    "TimelineCoordinate",
    "alignment_anchors",
    "believed_rows",
    "potential_matchstamps",
]


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
    table: pa.Table, actor: str | None = None, *, only_true: bool = False
) -> list[int]:
    """The rows the belief filter keeps, by index."""
    provenance = row_provenance(table)
    if actor is None:
        return list(range(len(provenance)))
    kept = []
    for index, entry in enumerate(provenance):
        beliefs = (entry or {}).get("beliefs") or ()
        belief = next((b["belief"] for b in beliefs if b["actor"] == actor), None)
        if (belief == "true") if only_true else (belief != "false"):
            kept.append(index)
    return kept


def _anchor(cell: dict[str, Any]) -> AlignmentAnchor:
    first, second = sorted(
        TimelineCoordinate(
            cell[f"timeline_{side}_id"], coordinate_value(cell[f"coordinate_{side}"])
        )
        for side in ("a", "b")
    )
    return AlignmentAnchor((first, second))


def alignment_anchors(
    table: pa.Table, actor: str | None = None, *, only_true: bool = False
) -> dict[AlignmentAnchor, tuple[str, ...]]:
    """The unique anchors of the rows the filter keeps, sorted, each with the
    sorted IDs of the MatchClaims stating it."""
    rows = table.select(["id", "start_anchor", "end_anchor"]).to_pylist()
    stated: dict[AlignmentAnchor, set[str]] = {}
    for index in believed_rows(table, actor, only_true=only_true):
        row = rows[index]
        for key in ("start_anchor", "end_anchor"):
            if row[key] is not None:
                stated.setdefault(_anchor(row[key]), set()).add(row["id"])
    return {anchor: tuple(sorted(stated[anchor])) for anchor in sorted(stated)}


def potential_matchstamps(
    table: pa.Table, actor: str | None = None, *, only_true: bool = False
) -> list[PotentialMatchStamp]:
    """The potential MatchStamps of the rows the filter keeps, sorted by
    their first coordinate."""
    anchors = alignment_anchors(table, actor, only_true=only_true)
    parent: dict[TimelineCoordinate, TimelineCoordinate] = {}

    def root(coordinate: TimelineCoordinate) -> TimelineCoordinate:
        parent.setdefault(coordinate, coordinate)
        while parent[coordinate] != coordinate:
            parent[coordinate] = parent[parent[coordinate]]
            coordinate = parent[coordinate]
        return coordinate

    for first, second in (anchor.coordinates for anchor in anchors):
        parent[root(first)] = root(second)
    sets: dict[TimelineCoordinate, list[AlignmentAnchor]] = {}
    for anchor in anchors:
        sets.setdefault(root(anchor.coordinates[0]), []).append(anchor)
    stamps = [
        PotentialMatchStamp(
            coordinates=tuple(
                sorted({c for anchor in members for c in anchor.coordinates})
            ),
            alignment_anchors=tuple(members),
            match_claims=tuple(
                sorted({claim for anchor in members for claim in anchors[anchor]})
            ),
        )
        for members in sets.values()
    ]
    return sorted(stamps, key=lambda stamp: stamp.coordinates[0])
