"""The table types of a TimeToShare package: MatchClaims and Projections.

A package keeps its MatchClaims beside the manifest in one MatchClaim table
(``match_claims.parquet``) and the events standing on a timeline for events
held elsewhere in one Projections table (``projections.parquet``). This
module declares their columns, checks a table (alone, or against the
manifest's timelines), checks the succession rule between a table and the
one written over it, and derives the AlignmentAnchors and potential
MatchStamps of a MatchClaim table under the belief filter.

It needs pyarrow: install the extra, ``pip install "timetoshare[tables]"``.
"""

from __future__ import annotations

try:
    import pyarrow  # noqa: F401
except ImportError as error:  # pragma: no cover - depends on the environment
    raise ImportError(
        'timetoshare.tables needs pyarrow: pip install "timetoshare[tables]"'
    ) from error

from .anchors import (
    AlignmentAnchor,
    PotentialMatchStamp,
    TimelineCoordinate,
    alignment_anchors,
    believed_rows,
    potential_matchstamps,
)
from .checks import (
    TableCode,
    TableError,
    TableProblem,
    check_match_claims,
    check_projections,
    check_succession,
    match_claim_problems,
    projection_problems,
    row_provenance,
    succession_problems,
)
from .columns import (
    ANCHOR_TYPE,
    BELIEF_KEYS,
    BELIEF_TYPE,
    BELIEFS,
    COORDINATE_KEYS,
    COORDINATE_TYPE,
    MATCH_CLAIM_COLUMNS,
    MATCH_CLAIM_SCHEMA,
    PROJECTION_COLUMNS,
    PROJECTION_OF_TYPE,
    PROJECTION_SCHEMA,
    PROVENANCE_KEYS,
    PROVENANCE_METADATA_KEY,
    PROVENANCE_TYPE,
    coordinate_value,
    fixture_path,
)

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
    "AlignmentAnchor",
    "PotentialMatchStamp",
    "TableCode",
    "TableError",
    "TableProblem",
    "TimelineCoordinate",
    "alignment_anchors",
    "believed_rows",
    "check_match_claims",
    "check_projections",
    "check_succession",
    "coordinate_value",
    "fixture_path",
    "match_claim_problems",
    "potential_matchstamps",
    "projection_problems",
    "row_provenance",
    "succession_problems",
]
