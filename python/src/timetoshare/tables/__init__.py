"""The table types of a TimeToShare package: MatchClaims and Projections.

A manifest names its MatchClaims in a MatchClaim table (``match_claims.parquet``
beside it, or a file or folder its package's manifests share) and the events
standing on a timeline for events held elsewhere in a Projections table. This
module declares their columns, read from the schema's ``tables.json``,
reads a table, a file or a folder of files, keeping the rows of some
timelines (``read_table``), checks a table (alone, or against a manifest,
every row then the manifest's: a shared file is read filtered first),
checks a package whole (``package_problems``), checks the succession rule
between a table and the one written over it, and derives the
AlignmentAnchors and potential MatchStamps of a MatchClaim table under the
belief filter.

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
    CHUNK_SENTINEL,
    COORDINATE_KEYS,
    COORDINATE_TYPE,
    MATCH_CLAIM_COLUMNS,
    MATCH_CLAIM_REQUIRED,
    MATCH_CLAIM_SCHEMA,
    NOMATCH_SENTINEL,
    NUMBER_KEYS,
    NUMBER_MEMBERS,
    NUMBER_TYPE,
    PROJECTION_COLUMNS,
    PROJECTION_OF_TYPE,
    PROJECTION_REQUIRED,
    PROJECTION_SCHEMA,
    PROVENANCE_KEYS,
    PROVENANCE_METADATA_KEY,
    PROVENANCE_TYPE,
    TABLES_DOCUMENT,
    coordinate_value,
    fixture_path,
    number_cell,
    tables_path,
)
from .package import (
    PACKAGE_FILE,
    TYPE_METADATA_KEY,
    VERSION_METADATA_KEY,
    PackageCode,
    PackageProblem,
    package_fixture_path,
    package_problems,
    read_table,
    table_files,
)

__all__ = [
    "PACKAGE_FILE",
    "TYPE_METADATA_KEY",
    "VERSION_METADATA_KEY",
    "PackageCode",
    "PackageProblem",
    "package_fixture_path",
    "package_problems",
    "read_table",
    "table_files",
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
    "PROJECTION_OF_TYPE",
    "PROJECTION_REQUIRED",
    "PROJECTION_SCHEMA",
    "PROVENANCE_KEYS",
    "PROVENANCE_METADATA_KEY",
    "PROVENANCE_TYPE",
    "TABLES_DOCUMENT",
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
    "number_cell",
    "potential_matchstamps",
    "projection_problems",
    "row_provenance",
    "succession_problems",
    "tables_path",
]
