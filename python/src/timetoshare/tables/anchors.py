"""From MatchClaims to AlignmentAnchors and potential MatchStamps.

The reference derivation of the format: small and exact, for conformance,
not for speed. It reads a MatchClaim table the checks accept.

- The belief filter selects the rows. Without a believer nothing is
  filtered; for a believer, a row is kept when its state for the believer
  is one of the states ``beliefs`` names
  (:data:`timetoshare.BELIEF_STATES`): the believer's belief in it
  (``"true"``, ``"unlikely"``, ``"false"``), or ``"undecided"`` where the
  believer holds none. The default keeps every state but ``"false"``.
  Actors compare as the IRIs they stand for under a JSON-LD context
  (:func:`timetoshare.expand_iri`), so a compact and an absolute IRI of one
  actor name the same actor; an actor that expands to nothing compares as
  written. Where a row holds beliefs of one believer under two spellings
  (which the table check refuses only under the manifest's context), its
  state is the most critical of them: ``"false"``, then ``"unlikely"``, then
  ``"true"``.
- A synchronous MatchClaim gives the anchor of its ``start_anchor`` and, if
  it has one, of its ``end_anchor``; NOMATCH and conceptual MatchClaims give
  none. Two anchors are the same when both coordinates are equal, compared
  exactly on the two timelines' axes, whichever side each stands on.
- A potential MatchStamp is one connected set of coordinates under the
  unique anchors.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

import pyarrow as pa

from ..statements import DEFAULT_BELIEFS, BeliefState, check_belief_filter, expand_iri
from ..validation.diagnostics import connected_sets
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


_CRITICAL_FIRST: tuple[BeliefState, ...] = ("false", "unlikely", "true")
"""The beliefs from the most critical: the state of a row whose believer holds
several under different spellings is the first of them it holds."""


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


def _actor(actor: str, context: Mapping[str, Any] | None) -> str:
    """The IRI an actor stands for under ``context``, else the actor as written."""
    return expand_iri(context, actor) or actor


def believed_rows(
    table: pa.Table,
    believer: str | None = None,
    beliefs: Collection[BeliefState] = DEFAULT_BELIEFS,
    *,
    context: Mapping[str, Any] | None = None,
) -> list[int]:
    """The rows the belief filter keeps, by index.

    Args:
        table: A MatchClaim table the checks accept.
        believer: The actor whose beliefs filter, an IRI (compact or
            absolute); ``None`` keeps every row.
        beliefs: The states kept (:data:`timetoshare.BELIEF_STATES`), a collection;
            empty keeps no row for a believer.
        context: The JSON-LD context (the manifest's ``@context``) whose
            prefixes expand compact IRIs, the believer's and the actors'
            alike; ``None`` declares no prefix.

    Raises:
        ValueError: If ``beliefs`` is a single string or names a word that
            is none of :data:`timetoshare.BELIEF_STATES`
            (:func:`timetoshare.check_belief_filter`).
    """
    states = check_belief_filter(beliefs)
    provenance = row_provenance(table)
    if believer is None:
        return list(range(len(provenance)))
    iri = _actor(believer, context)
    kept = []
    for index, entry in enumerate(provenance):
        held = {
            belief["belief"]
            for belief in (entry or {}).get("beliefs") or ()
            if _actor(belief["actor"], context) == iri
        }
        state = next((word for word in _CRITICAL_FIRST if word in held), "undecided")
        if state in states:
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
    table: pa.Table,
    believer: str | None = None,
    beliefs: Collection[BeliefState] = DEFAULT_BELIEFS,
    *,
    context: Mapping[str, Any] | None = None,
) -> dict[AlignmentAnchor, tuple[str, ...]]:
    """The unique anchors of the rows the filter keeps, sorted, each with the
    sorted IDs of the MatchClaims stating it."""
    columns = ["id", "timeline_a_id", "timeline_b_id", "start_anchor", "end_anchor"]
    rows = table.select(columns).to_pylist()
    stated: dict[AlignmentAnchor, set[str]] = {}
    for index in believed_rows(table, believer, beliefs, context=context):
        row = rows[index]
        for key in ("start_anchor", "end_anchor"):
            if row[key] is not None:
                stated.setdefault(_anchor(row, key), set()).add(row["id"])
    return {anchor: tuple(sorted(stated[anchor])) for anchor in sorted(stated)}


def potential_matchstamps(
    table: pa.Table,
    believer: str | None = None,
    beliefs: Collection[BeliefState] = DEFAULT_BELIEFS,
    *,
    context: Mapping[str, Any] | None = None,
) -> list[PotentialMatchStamp]:
    """The potential MatchStamps of the rows the filter keeps, sorted by
    their first coordinate."""
    anchors = alignment_anchors(table, believer, beliefs, context=context)
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
