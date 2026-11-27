"""The table types of a TimeToShare package: the registry, the Extraction
table, the pre-parsed tables and the MatchClaim tables.

A package's registry holds one row per resolvable ID: an event row for each
event (its timeline, its position on the root's axis, its extraction and
the pre-parsed table holding its content), an index row for each element of
the manifests, each MatchClaim and each extraction. The Extraction table
records each run of a parser over a source file; a pre-parsed table holds
the content of events of one type by their IDs, the Projection table the
event each Projection stands for; a manifest names its MatchClaims in a
MatchClaim table. This module declares their columns, read from the
schema's ``tables.json``, reads a table, a file or a folder of files,
keeping the rows of some timelines or IDs (``read_table``), checks a table
(alone, or against a manifest, every row then the manifest's: a shared file
is read filtered first), checks a package whole (``package_problems``), resolves an ID
(``resolve``) and builds, writes and checks the registry's index rows
(``index_rows``, ``write_index``, ``stale_index``),
checks the succession rule
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
    check_extractions,
    check_match_claims,
    check_projections,
    check_registry,
    check_succession,
    extraction_problems,
    match_claim_problems,
    projection_problems,
    registry_problems,
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
    ELEMENT_KINDS,
    EXTRACTION_COLUMNS,
    EXTRACTION_REQUIRED,
    EXTRACTION_SCHEMA,
    INDEX_KINDS,
    INTEGRITY_TYPE,
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
    REGISTRY_COLUMNS,
    REGISTRY_EVENT_REQUIRED,
    REGISTRY_REQUIRED,
    REGISTRY_SCHEMA,
    TABLES_DOCUMENT,
    coordinate_value,
    fixture_path,
    number_cell,
    tables_path,
)
from .package import (
    INDEX_PART,
    PACKAGE_FILE,
    TYPE_METADATA_KEY,
    VERSION_METADATA_KEY,
    PackageCode,
    PackageProblem,
    is_table_resource,
    package_fixture_path,
    package_problems,
    read_table,
    table_files,
)
from .registry import Resolution, index_rows, resolve, stale_index, write_index

__all__ = [
    "INDEX_PART",
    "PACKAGE_FILE",
    "TYPE_METADATA_KEY",
    "VERSION_METADATA_KEY",
    "PackageCode",
    "PackageProblem",
    "package_fixture_path",
    "package_problems",
    "is_table_resource",
    "read_table",
    "table_files",
    "ANCHOR_TYPE",
    "BELIEF_KEYS",
    "BELIEF_TYPE",
    "CHUNK_SENTINEL",
    "COORDINATE_KEYS",
    "COORDINATE_TYPE",
    "ELEMENT_KINDS",
    "EXTRACTION_COLUMNS",
    "EXTRACTION_REQUIRED",
    "EXTRACTION_SCHEMA",
    "INDEX_KINDS",
    "INTEGRITY_TYPE",
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
    "REGISTRY_COLUMNS",
    "REGISTRY_EVENT_REQUIRED",
    "REGISTRY_REQUIRED",
    "REGISTRY_SCHEMA",
    "TABLES_DOCUMENT",
    "AlignmentAnchor",
    "PotentialMatchStamp",
    "Resolution",
    "TableCode",
    "TableError",
    "TableProblem",
    "TimelineCoordinate",
    "alignment_anchors",
    "believed_rows",
    "check_extractions",
    "check_match_claims",
    "check_projections",
    "check_registry",
    "check_succession",
    "coordinate_value",
    "extraction_problems",
    "fixture_path",
    "index_rows",
    "match_claim_problems",
    "number_cell",
    "potential_matchstamps",
    "projection_problems",
    "registry_problems",
    "resolve",
    "row_provenance",
    "stale_index",
    "succession_problems",
    "tables_path",
    "write_index",
]
