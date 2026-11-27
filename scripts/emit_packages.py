#!/usr/bin/env python
"""Write the package fixtures: a package of two manifests sharing their
registry and tables, the packages that change it and pass the package check,
and one package per rule of the package check that breaks it, to
``fixtures/packages/<version>/``.

Every value is written here by hand: the rows, the manifests, the rows
``read_table`` returns for each resource, the resolutions of some IDs and
the problems expected of each broken package are literal data, never
computed by the code they test; the script checks that the package check
agrees before it writes anything. The one value read from bytes is the
digest of the source file of the first extraction. A Parquet file is
rewritten only when its table changes, and the files of a released
version, whose tag ``v<version>`` exists, are never overwritten.

Run it from ``python/`` with ``uv run python ../scripts/emit_packages.py``;
pyarrow is a development dependency of the package.

The package ``shared/``: two manifests, ``bach/manifest.yaml`` (a score
``clt_1`` in quarters and a performance ``dpt_1`` in samples) and
``handel/manifest.yaml`` (a score ``clt_2`` with a child ``clt_3`` starting
at the quarter 4, and a performance ``dpt_2``), share the registry
``registry/``, a folder of parts: ``index.parquet``, the index rows of both
manifests' elements, the MatchClaims and the extractions, sorted by
location and ID, and one part per extraction holding its event rows, sorted
by timeline, start and ID: ``extraction_1.parquet``, Bach's Projections,
made from ``bach/alignment.csv``, each with its locator, and
``extraction_2.parquet``, Handel's, made by a tool without a source file,
the two on ``clt_3`` at their positions on the root ``clt_2``. The
Extraction table ``tables/extractions.parquet`` records both runs. The
pre-parsed Projection table ``tables/Projection/`` holds each Projection's
``projection_of`` in two files whose rows interleave the two manifests',
and the folder of MatchClaims ``tables/MatchClaim/`` one file, which states
one provenance for all its rows in its metadata. Each manifest's resources
name the registry, with the timelines whose event rows it keeps, and the
MatchClaims, with the timelines whose MatchClaims it reads.

Each acceptance under ``acceptances/<case>/`` is ``shared/`` with one
change the package check accepts, beside an ``expected.yaml`` listing no
problem and, where the case concerns them, the resolutions of some IDs.
Each rejection under ``rejections/<case>/`` is ``shared/`` with one change,
beside an ``expected.yaml`` listing exactly the problems the package check
reports, in order. A change that adds or alters an element of a manifest
changes its index row too, so that the index is stale only where a case
says so.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from fractions import Fraction
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from timetoshare import SCHEMA_VERSION, dumps, validate, validate_package, with_file_ids
from timetoshare.tables import (
    EXTRACTION_SCHEMA,
    MATCH_CLAIM_SCHEMA,
    PROJECTION_SCHEMA,
    PROVENANCE_METADATA_KEY,
    REGISTRY_SCHEMA,
    TYPE_METADATA_KEY,
    VERSION_METADATA_KEY,
    package_problems,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = REPOSITORY_ROOT / "fixtures" / "packages" / SCHEMA_VERSION

PARQUET = "application/vnd.apache.parquet"
REGISTRY = "registry/"
EXTRACTIONS = "tables/extractions.parquet"
PROJECTIONS = "tables/Projection/"
MATCH_CLAIMS = "tables/MatchClaim/"
INDEX_FILE = f"{REGISTRY}index.parquet"
BACH_PART = f"{REGISTRY}extraction_1.parquet"
HANDEL_PART = f"{REGISTRY}extraction_2.parquet"
PART_A_FILE = f"{PROJECTIONS}part_a.parquet"
PART_B_FILE = f"{PROJECTIONS}part_b.parquet"
CLAIM_FILE = f"{MATCH_CLAIMS}part_a.parquet"
BACH_FILE = "bach/manifest.yaml"
HANDEL_FILE = "handel/manifest.yaml"
SOURCE = "bach/alignment.csv"
SOURCE_TEXT = "onset,sample\n0,0\n1,44100\n2,88200\n3,132300\n"
"""The source file of the first extraction, Bach's alignment."""

BACH: dict[str, Any] = {
    "timetoshare": SCHEMA_VERSION,
    "name": "Bach",
    "timelines": [
        {"id": "clt_1", "unit": "quarters", "length": [8, 1]},
        {"id": "dpt_1", "unit": "samples", "length": 352800},
    ],
    "resources": [
        {
            "id": "resource_1",
            "type": "MatchClaim",
            "timelines": ["clt_1", "dpt_1"],
            "url": f"../{MATCH_CLAIMS}",
            "media_type": PARQUET,
        },
        {
            "id": "resource_2",
            "type": "Registry",
            "timelines": ["dpt_1"],
            "url": f"../{REGISTRY}",
            "media_type": PARQUET,
        },
    ],
}
"""The first manifest, IDs bare as in memory."""

HANDEL: dict[str, Any] = {
    "timetoshare": SCHEMA_VERSION,
    "name": "Handel",
    "timelines": [
        {
            "id": "clt_2",
            "unit": "quarters",
            "length": [8, 1],
            "children": [
                {"id": "clt_3", "unit": "quarters", "offset": [4, 1], "length": [4, 1]}
            ],
        },
        {"id": "dpt_2", "unit": "samples", "length": 352800},
    ],
    "resources": [
        {
            "id": "resource_1",
            "type": "MatchClaim",
            "timelines": ["clt_2", "dpt_2"],
            "url": f"../{MATCH_CLAIMS}",
            "media_type": PARQUET,
        },
        {
            "id": "resource_2",
            "type": "Registry",
            "timelines": ["clt_3", "dpt_2"],
            "url": f"../{REGISTRY}",
            "media_type": PARQUET,
        },
    ],
}
"""The second manifest, IDs bare; its child ``clt_3`` holds event rows of
its own."""

PACKAGE: dict[str, Any] = {
    "timetoshare": SCHEMA_VERSION,
    "name": "Two manifests sharing their registry and tables",
    "manifests": [
        {"url": BACH_FILE, "media_type": "application/yaml"},
        {"url": HANDEL_FILE, "media_type": "application/yaml"},
    ],
    "tables": [
        {"type": "Registry", "url": REGISTRY, "media_type": PARQUET},
        {"type": "Extraction", "url": EXTRACTIONS, "media_type": PARQUET},
        {"type": "MatchClaim", "url": MATCH_CLAIMS, "media_type": PARQUET},
        {"type": "Projection", "url": PROJECTIONS, "media_type": PARQUET},
    ],
}
"""The package's ``package.yaml``."""

SHARED_PROVENANCE = {
    "method": "imported",
    "service": "https://example.org/aligner",
    "date": "2026-11-20",
}
"""The provenance the MatchClaim file states for every row."""


def number(value: int | Fraction | float, number_type: str) -> dict[str, Any]:
    """A number's members, filled by its number type alone."""
    if number_type == "int":
        return {"numerator": value, "denominator": None, "value": None}
    if number_type == "float":
        return {"numerator": None, "denominator": None, "value": value}
    fraction = Fraction(value)
    return {
        "numerator": fraction.numerator,
        "denominator": fraction.denominator,
        "value": None,
    }


SAMPLES = ("samples", "int")
QUARTERS = ("quarters", "fraction")
_NULLS = dict.fromkeys(REGISTRY_SCHEMA.names)


def event(
    identifier: str,
    timeline: str,
    axis: tuple[str, str],
    start: Any,
    extraction: str,
    duration: Any = None,
    locator: str | None = None,
    kind: str = "Projection",
    location: str | None = PROJECTIONS,
) -> dict[str, Any]:
    """An event row, its position on its root's axis."""
    unit, number_type = axis
    return {
        **_NULLS,
        "id": identifier,
        "kind": kind,
        "location": location,
        "timeline_id": timeline,
        "unit": unit,
        "number_type": number_type,
        "start": number(start, number_type),
        "duration": None if duration is None else number(duration, number_type),
        "extraction_id": extraction,
        "locator": locator,
    }


def index(identifier: str, kind: str, location: str, **members: Any) -> dict[str, Any]:
    """An index row."""
    return {**_NULLS, "id": identifier, "kind": kind, "location": location, **members}


BACH_EVENTS: list[dict[str, Any]] = [
    event("projection_1", "dpt_1", SAMPLES, 0, "extraction_1", locator="row 1"),
    event("projection_2", "dpt_1", SAMPLES, 44100, "extraction_1", locator="row 2"),
    event("projection_9", "dpt_1", SAMPLES, 88200, "extraction_1", locator="row 3"),
    event("projection_7", "dpt_1", SAMPLES, 132300, "extraction_1", locator="row 4"),
]
"""Bach's event rows, sorted by timeline, start and ID."""

HANDEL_EVENTS: list[dict[str, Any]] = [
    event(
        "projection_5",
        "clt_3",
        QUARTERS,
        Fraction(9, 2),
        "extraction_2",
        Fraction(1, 2),
    ),
    event("projection_8", "clt_3", QUARTERS, Fraction(11, 2), "extraction_2"),
    event("projection_3", "dpt_2", SAMPLES, 0, "extraction_2"),
    event("projection_4", "dpt_2", SAMPLES, 88200, "extraction_2", 44100),
    event("projection_6", "dpt_2", SAMPLES, 132300, "extraction_2"),
]
"""Handel's event rows, sorted by timeline, start and ID; the two on the
child ``clt_3`` lie at 1/2 and 3/2 on it, 9/2 and 11/2 on its root."""

INDEX: list[dict[str, Any]] = [
    index("clt_1", "Timeline", BACH_FILE),
    index("dpt_1", "Timeline", BACH_FILE),
    index("resource_1", "Resource", BACH_FILE),
    index("resource_2", "Resource", BACH_FILE),
    index("clt_2", "Timeline", HANDEL_FILE),
    index("clt_3", "Timeline", HANDEL_FILE),
    index("dpt_2", "Timeline", HANDEL_FILE),
    index("resource_1", "Resource", HANDEL_FILE),
    index("resource_2", "Resource", HANDEL_FILE),
    *(
        index(f"claim_{number}", "MatchClaim", MATCH_CLAIMS)
        for number in (1, 2, 3, 4, 5)
    ),
    index("extraction_1", "Extraction", EXTRACTIONS),
    index("extraction_2", "Extraction", EXTRACTIONS),
]
"""The index rows, sorted by location and ID: each element of the two
manifests, each MatchClaim and each extraction."""


def projection(identifier: str, of: tuple[str, str] | None) -> dict[str, Any]:
    """A pre-parsed Projection: its ID and the event it stands for."""
    return {
        "id": identifier,
        "projection_of": None
        if of is None
        else {"timeline_id": of[0], "event_id": of[1]},
    }


PART_A: list[dict[str, Any]] = [
    projection("projection_5", ("dpt_2", "onset_1")),
    projection("projection_1", ("clt_1", "note_1")),
    projection("projection_2", ("clt_1", "note_2")),
    projection("projection_3", ("clt_2", "note_5")),
    projection("projection_4", ("clt_2", "note_6")),
]
"""The first file of pre-parsed Projections."""

PART_B: list[dict[str, Any]] = [
    projection("projection_6", ("clt_2", "note_7")),
    projection("projection_7", ("clt_1", "note_3")),
    projection("projection_8", ("dpt_2", "onset_2")),
    projection("projection_9", ("clt_1", "note_4")),
]
"""The second file of pre-parsed Projections."""


def extractions() -> list[dict[str, Any]]:
    """The two runs: a parser over Bach's alignment, a tool without a source."""
    digest = hashlib.sha256(SOURCE_TEXT.encode("utf-8")).hexdigest()
    return [
        {
            "id": "extraction_1",
            "source": SOURCE,
            "source_integrity": {"algorithm": "SHA-256", "digest": digest},
            "parser": "https://example.org/alignment-reader",
            "parser_version": "1.2.0",
            "parameters": '{"delimiter":","}',
            "minter": "1",
            "id_length": 8,
            "seed": None,
            "date": "2026-11-27T21:30:00Z",
        },
        {
            "id": "extraction_2",
            "source": None,
            "source_integrity": None,
            "parser": "https://example.org/aligner",
            "parser_version": "0.4",
            "parameters": None,
            "minter": "1",
            "id_length": 8,
            "seed": "handel",
            "date": "2026-11-27T21:31:00Z",
        },
    ]


def coordinate(value: Any, axis: tuple[str, str]) -> dict[str, Any]:
    unit, number_type = axis
    return {**number(value, number_type), "unit": unit, "number_type": number_type}


def claim(
    identifier: str,
    a: tuple[str, str],
    b: tuple[str, str],
    start: tuple[dict[str, Any], dict[str, Any]],
    end: tuple[dict[str, Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """A synchronous MatchClaim between two events, provenance left to the file."""

    def anchor(pair: tuple[dict[str, Any], dict[str, Any]] | None) -> Any:
        return (
            None if pair is None else {"coordinate_a": pair[0], "coordinate_b": pair[1]}
        )

    return {
        "timeline_a_id": a[0],
        "timeline_b_id": b[0],
        "start_anchor": anchor(start),
        "end_anchor": anchor(end),
        "is_synchronous": True,
        "provenance": None,
        "certainty": 1.0,
        "event_a_id": a[1],
        "event_a_name": None,
        "event_b_id": b[1],
        "event_b_name": None,
        "id": identifier,
    }


CLAIMS: list[dict[str, Any]] = [
    claim(
        "claim_1",
        ("clt_1", "note_1"),
        ("dpt_1", "projection_1"),
        (coordinate(0, QUARTERS), coordinate(0, SAMPLES)),
    ),
    claim(
        "claim_2",
        ("clt_1", "note_2"),
        ("dpt_1", "projection_2"),
        (coordinate(1, QUARTERS), coordinate(44100, SAMPLES)),
    ),
    claim(
        "claim_3",
        ("clt_2", "note_5"),
        ("dpt_2", "projection_3"),
        (coordinate(0, QUARTERS), coordinate(0, SAMPLES)),
    ),
    claim(
        "claim_4",
        ("clt_2", "note_6"),
        ("dpt_2", "projection_4"),
        (coordinate(2, QUARTERS), coordinate(88200, SAMPLES)),
        (coordinate(3, QUARTERS), coordinate(132300, SAMPLES)),
    ),
    claim(
        "claim_5",
        ("dpt_1", "projection_7"),
        ("clt_1", "note_3"),
        (coordinate(132300, SAMPLES), coordinate(3, QUARTERS)),
    ),
]
"""The MatchClaim file, sorted by its two timelines and ID: Bach's, Handel's,
then Bach's again, written in the other orientation."""

READ: dict[str, dict[str, list[str]]] = {
    BACH_FILE: {
        "resource_1": ["claim_1", "claim_2", "claim_5"],
        "resource_2": ["projection_1", "projection_2", "projection_7", "projection_9"],
    },
    HANDEL_FILE: {
        "resource_1": ["claim_3", "claim_4"],
        "resource_2": [
            "projection_3",
            "projection_4",
            "projection_5",
            "projection_6",
            "projection_8",
        ],
    },
}
"""For each manifest and resource, the IDs of the rows ``read_table`` returns
for the resource's timelines, sorted: a reader never relies on their order."""


def resolution(
    kind: str, location: str, manifest: str | None, row: dict[str, Any] | None
) -> dict[str, Any]:
    return {"kind": kind, "location": location, "manifest": manifest, "row": row}


RESOLUTIONS: list[dict[str, Any]] = [
    {
        "path": BACH_FILE,
        "id": "dpt_1",
        "found": [
            resolution(
                "Timeline", BACH_FILE, BACH_FILE, index("dpt_1", "Timeline", BACH_FILE)
            )
        ],
    },
    {
        "path": BACH_FILE,
        "id": "projection_1",
        "found": [resolution("Projection", PROJECTIONS, BACH_FILE, BACH_EVENTS[0])],
    },
    {"path": BACH_FILE, "id": "projection_3", "found": []},
    {
        "path": BACH_FILE,
        "id": "claim_1",
        "found": [
            resolution(
                "MatchClaim",
                MATCH_CLAIMS,
                BACH_FILE,
                index("claim_1", "MatchClaim", MATCH_CLAIMS),
            )
        ],
    },
    {
        "path": BACH_FILE,
        "id": "extraction_1",
        "found": [
            resolution(
                "Extraction",
                EXTRACTIONS,
                BACH_FILE,
                index("extraction_1", "Extraction", EXTRACTIONS),
            )
        ],
    },
    {"path": BACH_FILE, "id": "extraction_2", "found": []},
    {
        "path": HANDEL_FILE,
        "id": "projection_5",
        "found": [resolution("Projection", PROJECTIONS, HANDEL_FILE, HANDEL_EVENTS[0])],
    },
    {
        "path": ".",
        "id": "resource_1",
        "found": [
            resolution(
                "Resource",
                BACH_FILE,
                BACH_FILE,
                index("resource_1", "Resource", BACH_FILE),
            ),
            resolution(
                "Resource",
                HANDEL_FILE,
                HANDEL_FILE,
                index("resource_1", "Resource", HANDEL_FILE),
            ),
        ],
    },
    {
        "path": ".",
        "id": "projection_5",
        "found": [resolution("Projection", PROJECTIONS, None, HANDEL_EVENTS[0])],
    },
    {"path": ".", "id": "ghost", "found": []},
]
"""For each path (a manifest, or ``.``, the package's root) and ID, every
resolution, sorted by location: through a manifest, its element, then the
registry rows belonging to it; through the package, every registry row."""


class Package:
    """A package's files as data: its ``package.yaml``, its manifests, its
    Parquet files with their metadata and its other files."""

    def __init__(self) -> None:
        self.package = copy.deepcopy(PACKAGE)
        self.manifests = {
            BACH_FILE: copy.deepcopy(BACH),
            HANDEL_FILE: copy.deepcopy(HANDEL),
        }
        self.tables: dict[str, tuple[list[dict[str, Any]], pa.Schema]] = {
            INDEX_FILE: (copy.deepcopy(INDEX), REGISTRY_SCHEMA),
            BACH_PART: (copy.deepcopy(BACH_EVENTS), REGISTRY_SCHEMA),
            HANDEL_PART: (copy.deepcopy(HANDEL_EVENTS), REGISTRY_SCHEMA),
            EXTRACTIONS: (extractions(), EXTRACTION_SCHEMA),
            PART_A_FILE: (copy.deepcopy(PART_A), PROJECTION_SCHEMA),
            PART_B_FILE: (copy.deepcopy(PART_B), PROJECTION_SCHEMA),
            CLAIM_FILE: (copy.deepcopy(CLAIMS), MATCH_CLAIM_SCHEMA),
        }
        self.metadata = {
            INDEX_FILE: _metadata("Registry"),
            BACH_PART: _metadata("Registry"),
            HANDEL_PART: _metadata("Registry"),
            EXTRACTIONS: _metadata("Extraction"),
            PART_A_FILE: _metadata("Projection"),
            PART_B_FILE: _metadata("Projection"),
            CLAIM_FILE: {
                **_metadata("MatchClaim"),
                PROVENANCE_METADATA_KEY: json.dumps(SHARED_PROVENANCE, sort_keys=True),
            },
        }
        self.texts = {SOURCE: SOURCE_TEXT}

    def table(self, name: str) -> pa.Table:
        rows, schema = self.tables[name]
        table = pa.Table.from_pylist(rows, schema=schema)
        return table.replace_schema_metadata(self.metadata[name])

    def write(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        _write_text(directory / "package.yaml", dumps(self.package))
        for name, manifest in self.manifests.items():
            _write_text(directory / name, dumps(with_file_ids(manifest)))
        for name, text in self.texts.items():
            _write_text(directory / name, text)
        for name in self.tables:
            _write_table(directory / name, self.table(name))


def _metadata(kind: str) -> dict[str, str]:
    return {TYPE_METADATA_KEY: kind, VERSION_METADATA_KEY: SCHEMA_VERSION}


def problem(
    code: str, file: str, row: int | None, path: list[Any], message: str
) -> dict[str, Any]:
    return {"code": code, "file": file, "row": row, "path": path, "message": message}


# The acceptances: each a change to the shared package that the package
# check accepts, with its reason.


EXTERNAL = "https://example.org/events/projection_1"
"""An absolute URI naming the content of an event outside the package."""


def _external_location(package: Package) -> None:
    package.tables[BACH_PART][0][0]["location"] = EXTERNAL
    rows = package.tables[PART_A_FILE][0]
    rows[:] = [row for row in rows if row["id"] != "projection_1"]


def _recording_resource(package: Package) -> None:
    package.manifests[BACH_FILE]["resources"].append(
        {
            "id": "resource_3",
            "type": "Audio",
            "timelines": ["dpt_1"],
            "url": "recording.flac",
            "media_type": "audio/flac",
        }
    )
    package.tables[INDEX_FILE][0].insert(4, index("resource_3", "Resource", BACH_FILE))


def _timeline_in_two_manifests(package: Package) -> None:
    handel = package.manifests[HANDEL_FILE]
    handel["timelines"].insert(1, {"id": "dpt_1", "unit": "samples", "length": 352800})
    handel["resources"][1]["timelines"].append("dpt_1")
    package.tables[INDEX_FILE][0].insert(6, index("dpt_1", "Timeline", HANDEL_FILE))


def _single_file_registry(package: Package) -> None:
    rows = [
        *package.tables.pop(INDEX_FILE)[0],
        *package.tables.pop(BACH_PART)[0],
        *package.tables.pop(HANDEL_PART)[0],
    ]
    for name in (INDEX_FILE, BACH_PART, HANDEL_PART):
        del package.metadata[name]
    package.tables["registry.parquet"] = (rows, REGISTRY_SCHEMA)
    package.metadata["registry.parquet"] = _metadata("Registry")
    package.package["tables"][0]["url"] = "registry.parquet"
    for manifest in package.manifests.values():
        manifest["resources"][1]["url"] = "../registry.parquet"


def _re_parsable_event(package: Package) -> None:
    package.tables[BACH_PART][0].append(
        event(
            "onset_9",
            "dpt_1",
            SAMPLES,
            176400,
            "extraction_1",
            locator="row 5",
            kind="Onset",
            location=None,
        )
    )


ACCEPTANCES: dict[
    str, tuple[Callable[[Package], None], str, list[dict[str, Any]] | None]
] = {
    "external_location": (
        _external_location,
        "The content of Bach's first Projection lies outside the package: its "
        "location is an absolute URI, which the package check does not follow, "
        "and the pre-parsed tables hold no row of it.",
        [
            {
                "path": BACH_FILE,
                "id": "projection_1",
                "found": [
                    resolution(
                        "Projection",
                        EXTERNAL,
                        BACH_FILE,
                        {**BACH_EVENTS[0], "location": EXTERNAL},
                    )
                ],
            }
        ],
    ),
    "recording_resource": (
        _recording_resource,
        "Bach's manifest names a recording beside it, a resource naming no "
        "table, which package.yaml does not list and the package check "
        "passes over; the index holds the resource.",
        None,
    ),
    "timeline_in_two_manifests": (
        _timeline_in_two_manifests,
        "Handel's manifest holds a timeline dpt_1, as Bach's does, and keeps its "
        "event rows too: manifests sharing a timeline ID share its event rows, "
        "and the ID resolves through each.",
        [
            {
                "path": BACH_FILE,
                "id": "dpt_1",
                "found": [
                    resolution(
                        "Timeline",
                        BACH_FILE,
                        BACH_FILE,
                        index("dpt_1", "Timeline", BACH_FILE),
                    )
                ],
            },
            {
                "path": HANDEL_FILE,
                "id": "dpt_1",
                "found": [
                    resolution(
                        "Timeline",
                        HANDEL_FILE,
                        HANDEL_FILE,
                        index("dpt_1", "Timeline", HANDEL_FILE),
                    )
                ],
            },
            {
                "path": HANDEL_FILE,
                "id": "projection_1",
                "found": [
                    resolution("Projection", PROJECTIONS, HANDEL_FILE, BACH_EVENTS[0])
                ],
            },
            {
                "path": ".",
                "id": "dpt_1",
                "found": [
                    resolution(
                        "Timeline",
                        BACH_FILE,
                        BACH_FILE,
                        index("dpt_1", "Timeline", BACH_FILE),
                    ),
                    resolution(
                        "Timeline",
                        HANDEL_FILE,
                        HANDEL_FILE,
                        index("dpt_1", "Timeline", HANDEL_FILE),
                    ),
                ],
            },
        ],
    ),
    "single_file_registry": (
        _single_file_registry,
        "The registry is one file, registry.parquet, holding the index rows and "
        "the event rows of both extractions.",
        None,
    ),
    "re_parsable_event": (
        _re_parsable_event,
        "An onset of Bach's extraction has no pre-parsed content: its location "
        "is null, its content re-parsable from the extraction's source file.",
        [
            {
                "path": BACH_FILE,
                "id": "onset_9",
                "found": [
                    resolution(
                        "Onset",
                        None,
                        BACH_FILE,
                        event(
                            "onset_9",
                            "dpt_1",
                            SAMPLES,
                            176400,
                            "extraction_1",
                            locator="row 5",
                            kind="Onset",
                            location=None,
                        ),
                    )
                ],
            }
        ],
    ),
}
"""Each acceptance: the change, its reason, and the resolutions it lists (or
none); the package check finds no problem."""


# The rejections: each a change to the shared package, with its reason and
# the problems expected, written by hand.


def _row_of_no_manifest(package: Package) -> None:
    package.tables[BACH_PART][0].append(
        event(
            "onset_9",
            "dpt_9",
            SAMPLES,
            0,
            "extraction_1",
            locator="row 5",
            kind="Onset",
            location=None,
        )
    )


def _projection_id_in_two_files(package: Package) -> None:
    package.tables[PART_B_FILE][0][3]["id"] = "projection_3"


def _claim_across_manifests(package: Package) -> None:
    package.tables[CLAIM_FILE][0].insert(
        2,
        claim(
            "claim_6",
            ("clt_1", "note_4"),
            ("dpt_2", "projection_6"),
            (coordinate(3, QUARTERS), coordinate(132300, SAMPLES)),
        ),
    )
    package.tables[INDEX_FILE][0].insert(
        14, index("claim_6", "MatchClaim", MATCH_CLAIMS)
    )


def _column_in_two_types(package: Package) -> None:
    for name, kind in ((PART_A_FILE, pa.int64()), (PART_B_FILE, pa.string())):
        rows, schema = package.tables[name]
        for number_, row in enumerate(rows):
            row["velocity"] = 64 + number_ if kind == pa.int64() else "mf"
        package.tables[name] = (rows, schema.append(pa.field("velocity", kind)))


def _version_mismatch(package: Package) -> None:
    package.metadata[PART_B_FILE][VERSION_METADATA_KEY] = "0.1.0"


def _resource_naming_no_table(package: Package) -> None:
    package.manifests[BACH_FILE]["resources"].append(
        {
            "id": "resource_3",
            "type": "Box",
            "timelines": ["clt_1"],
            "url": "../tables/Box/",
        }
    )
    package.tables[INDEX_FILE][0].insert(4, index("resource_3", "Resource", BACH_FILE))


def _folder_with_size(package: Package) -> None:
    package.package["tables"][3]["size"] = 1024


def _timeline_unlisted(package: Package) -> None:
    package.manifests[HANDEL_FILE]["resources"][1]["timelines"] = ["dpt_2"]


def _axis_mismatch(package: Package) -> None:
    rows = package.tables[BACH_PART][0]
    rows[3] = event(
        "projection_7",
        "dpt_1",
        ("seconds", "float"),
        3.0,
        "extraction_1",
        locator="row 4",
    )


def _file_of_another_type(package: Package) -> None:
    package.metadata[PART_B_FILE][TYPE_METADATA_KEY] = "MatchClaim"


def _table_listed_twice(package: Package) -> None:
    package.package["tables"].append(
        {"type": "Projection", "url": PROJECTIONS, "media_type": PARQUET}
    )


def _file_in_a_listed_folder(package: Package) -> None:
    package.package["tables"].append(
        {"type": "Projection", "url": PART_B_FILE, "media_type": PARQUET}
    )


def _registry_missing(package: Package) -> None:
    del package.package["tables"][0]
    for name in (INDEX_FILE, BACH_PART, HANDEL_PART):
        del package.tables[name]
    for manifest in package.manifests.values():
        del manifest["resources"][1]


def _registry_listed_twice(package: Package) -> None:
    package.package["tables"].append(
        {"type": "Registry", "url": "old/registry.parquet", "media_type": PARQUET}
    )
    package.tables["old/registry.parquet"] = ([], REGISTRY_SCHEMA)
    package.metadata["old/registry.parquet"] = _metadata("Registry")


def _extraction_table_listed_twice(package: Package) -> None:
    package.package["tables"].append(
        {"type": "Extraction", "url": "old/extractions.parquet", "media_type": PARQUET}
    )
    package.tables["old/extractions.parquet"] = ([], EXTRACTION_SCHEMA)
    package.metadata["old/extractions.parquet"] = _metadata("Extraction")


def _unknown_extraction(package: Package) -> None:
    package.tables[HANDEL_PART][0][2]["extraction_id"] = "extraction_9"


def _vanished_in_an_unknown_extraction(package: Package) -> None:
    package.tables[HANDEL_PART][0][2]["vanished_in"] = "extraction_3"


def _unknown_location(package: Package) -> None:
    package.tables[BACH_PART][0][1]["location"] = "tables/Note/"


def _missing_content(package: Package) -> None:
    package.tables[BACH_PART][0].append(
        event(
            "projection_10", "dpt_1", SAMPLES, 176400, "extraction_1", locator="row 5"
        )
    )


def _unregistered_id(package: Package) -> None:
    package.tables[PART_B_FILE][0].append(projection("projection_10", None))


def _locator_twice(package: Package) -> None:
    package.tables[BACH_PART][0][3]["locator"] = "row 1"


def _registry_id_twice(package: Package) -> None:
    package.tables[HANDEL_PART][0].append(
        event(
            "claim_1",
            "dpt_2",
            SAMPLES,
            176400,
            "extraction_2",
            kind="Onset",
            location=None,
        )
    )


def _index_row_with_a_position(package: Package) -> None:
    row = package.tables[INDEX_FILE][0][0]
    row.update(unit="quarters", number_type="fraction", start=number(0, "fraction"))


def _stale_index(package: Package) -> None:
    rows = package.tables[INDEX_FILE][0]
    rows[0]["name"] = "Score"
    rows.insert(4, index("region_9", "Region", BACH_FILE, timeline_id="clt_1"))
    package.manifests[HANDEL_FILE]["groups"] = [
        {"id": "group_1", "members": ["clt_2", "dpt_2"]}
    ]


def _projection_of_its_own_timeline(package: Package) -> None:
    package.tables[PART_A_FILE][0][1]["projection_of"] = {
        "timeline_id": "dpt_1",
        "event_id": "note_1",
    }


def _projection_of_no_timeline(package: Package) -> None:
    package.tables[PART_B_FILE][0][1]["projection_of"] = {
        "timeline_id": "clt_9",
        "event_id": "note_3",
    }


REJECTIONS: dict[str, tuple[Callable[[Package], None], str, list[dict[str, Any]]]] = {
    "row_of_no_manifest": (
        _row_of_no_manifest,
        "An event row lies on dpt_9, a timeline no manifest of the package holds.",
        [
            problem(
                "unknown_timeline",
                BACH_PART,
                4,
                ["timeline_id"],
                "no manifest of the package has the timeline 'dpt_9'",
            ),
        ],
    ),
    "projection_id_in_two_files": (
        _projection_id_in_two_files,
        "The ID projection_3 names a pre-parsed Projection of Handel's in part_a "
        "and, in part_b, the one of Bach's projection_9, whose content is then "
        "missing.",
        [
            problem(
                "duplicate_id",
                PART_B_FILE,
                3,
                ["id"],
                "the event ID 'projection_3' is given twice, first in "
                "'tables/Projection/part_a.parquet' at row 3",
            ),
            problem(
                "missing_content",
                BACH_PART,
                2,
                ["location"],
                "the table 'tables/Projection/' holds no row of the ID 'projection_9'",
            ),
        ],
    ),
    "claim_across_manifests": (
        _claim_across_manifests,
        "A MatchClaim joins Bach's score and Handel's performance; a MatchClaim "
        "lies within one manifest.",
        [
            problem(
                "claim_across_manifests",
                CLAIM_FILE,
                2,
                ["timeline_b_id"],
                "no manifest of the package holds both the timeline 'clt_1' and the "
                "timeline 'dpt_2'",
            ),
        ],
    ),
    "column_in_two_types": (
        _column_in_two_types,
        "The further column velocity is an integer in part_a and a string in "
        "part_b; one column name has one Arrow type in the files of a folder.",
        [
            problem(
                "column_type_mismatch",
                PROJECTIONS,
                None,
                ["velocity"],
                "the column 'velocity' is int64 in 'part_a.parquet' and string in "
                "'part_b.parquet'",
            ),
        ],
    ),
    "version_mismatch": (
        _version_mismatch,
        "part_b declares the format version 0.1.0 in its metadata, the package 0.2.0.",
        [
            problem(
                "version_mismatch",
                PART_B_FILE,
                None,
                [],
                "the file declares the version '0.1.0', the package '0.2.0'",
            ),
        ],
    ),
    "resource_naming_no_table": (
        _resource_naming_no_table,
        "Bach's manifest names a folder of Box events that package.yaml does not list.",
        [
            problem(
                "unknown_table",
                BACH_FILE,
                None,
                ["resources", 2, "url"],
                "the resource 'resource_3' names '../tables/Box/', which is no table "
                "of the type Box in the package",
            ),
        ],
    ),
    "folder_with_size": (
        _folder_with_size,
        "package.yaml states a size for the folder of Projections; a folder has none.",
        [
            problem(
                "folder_descriptor",
                "package.yaml",
                None,
                ["tables", 3, "size"],
                "'tables/Projection/' names a folder, which has no size",
            ),
        ],
    ),
    "timeline_unlisted": (
        _timeline_unlisted,
        "Handel's Registry resource no longer lists its child clt_3, whose event "
        "rows the registry holds; a reader of the manifest would not find them.",
        [
            problem(
                "unlisted_timeline",
                HANDEL_PART,
                0,
                ["timeline_id"],
                "the timeline 'clt_3' of 'handel/manifest.yaml' is listed by no "
                "resource of the type Registry naming this table",
            ),
            problem(
                "unlisted_timeline",
                HANDEL_PART,
                1,
                ["timeline_id"],
                "the timeline 'clt_3' of 'handel/manifest.yaml' is listed by no "
                "resource of the type Registry naming this table",
            ),
        ],
    ),
    "axis_mismatch": (
        _axis_mismatch,
        "An event row on the samples timeline dpt_1 is written in seconds.",
        [
            problem(
                "axis_mismatch",
                BACH_PART,
                3,
                ["unit"],
                "a coordinate in seconds (float) on the timeline 'dpt_1' in samples "
                "(int)",
            ),
        ],
    ),
    "file_of_another_type": (
        _file_of_another_type,
        "part_b, in the folder of Projections, states the type MatchClaim.",
        [
            problem(
                "table_type",
                PART_B_FILE,
                None,
                [],
                "the file holds the type MatchClaim, its table the type Projection",
            ),
        ],
    ),
    "table_listed_twice": (
        _table_listed_twice,
        "package.yaml lists the folder of Projections twice; a table is listed "
        "once under its URL and type.",
        [
            problem(
                "duplicate_url",
                "package.yaml",
                None,
                ["tables", 4, "url"],
                "the table 'tables/Projection/' of the type Projection is listed "
                "twice, first at #/tables/3/url",
            ),
        ],
    ),
    "file_in_a_listed_folder": (
        _file_in_a_listed_folder,
        "package.yaml lists part_b, a file of the listed folder of Projections, "
        "as a table of its own; its rows would be read twice.",
        [
            problem(
                "duplicate_url",
                "package.yaml",
                None,
                ["tables", 4, "url"],
                "the file 'tables/Projection/part_b.parquet' is read by the table "
                "'tables/Projection/' already",
            ),
        ],
    ),
    "registry_missing": (
        _registry_missing,
        "package.yaml lists no registry; the manifests name none and no event "
        "has content.",
        [
            problem(
                "missing_registry",
                "package.yaml",
                None,
                ["tables"],
                "the package lists no table of the type Registry",
            ),
        ],
    ),
    "registry_listed_twice": (
        _registry_listed_twice,
        "package.yaml lists a second registry; a package has one.",
        [
            problem(
                "duplicate_registry",
                "package.yaml",
                None,
                ["tables", 4, "type"],
                "the package lists a second table of the type Registry, first at "
                "#/tables/0/type",
            ),
        ],
    ),
    "extraction_table_listed_twice": (
        _extraction_table_listed_twice,
        "package.yaml lists a second Extraction table; a package has at most one.",
        [
            problem(
                "duplicate_extraction",
                "package.yaml",
                None,
                ["tables", 4, "type"],
                "the package lists a second table of the type Extraction, first at "
                "#/tables/1/type",
            ),
        ],
    ),
    "unknown_extraction": (
        _unknown_extraction,
        "An event row of Handel's names extraction_9, which the Extraction table "
        "does not hold.",
        [
            problem(
                "unknown_extraction",
                HANDEL_PART,
                2,
                ["extraction_id"],
                "no extraction of the package has the ID 'extraction_9'",
            ),
        ],
    ),
    "vanished_in_an_unknown_extraction": (
        _vanished_in_an_unknown_extraction,
        "An event row of Handel's vanished in extraction_3, which the Extraction "
        "table does not hold.",
        [
            problem(
                "unknown_extraction",
                HANDEL_PART,
                2,
                ["vanished_in"],
                "no extraction of the package has the ID 'extraction_3'",
            ),
        ],
    ),
    "unknown_location": (
        _unknown_location,
        "An event row names tables/Note/ as its content's table, which "
        "package.yaml does not list.",
        [
            problem(
                "unknown_location",
                BACH_PART,
                1,
                ["location"],
                "the location 'tables/Note/' names no table of the type Projection in "
                "the package",
            ),
        ],
    ),
    "missing_content": (
        _missing_content,
        "An event row names the pre-parsed Projections, which hold no row of its ID.",
        [
            problem(
                "missing_content",
                BACH_PART,
                4,
                ["location"],
                "the table 'tables/Projection/' holds no row of the ID 'projection_10'",
            ),
        ],
    ),
    "unregistered_id": (
        _unregistered_id,
        "A pre-parsed Projection has an ID no event row of the registry has.",
        [
            problem(
                "unregistered_id",
                PART_B_FILE,
                4,
                ["id"],
                "no event row of the type Projection in the registry has the ID "
                "'projection_10'",
            ),
        ],
    ),
    "locator_twice": (
        _locator_twice,
        "Two event rows of Bach's extraction give the locator 'row 1'.",
        [
            problem(
                "duplicate_locator",
                BACH_PART,
                3,
                ["locator"],
                "the locator 'row 1' is given twice in the extraction 'extraction_1'",
            ),
        ],
    ),
    "registry_id_twice": (
        _registry_id_twice,
        "An onset of Handel's has the ID claim_1, a MatchClaim's; an event ID and "
        "a MatchClaim ID are held once among the registry's rows.",
        [
            problem(
                "duplicate_id",
                INDEX_FILE,
                9,
                ["id"],
                "the ID 'claim_1' is given twice, first in "
                "'registry/extraction_2.parquet' at row 5",
            ),
        ],
    ),
    "index_row_with_a_position": (
        _index_row_with_a_position,
        "An index row states a position; an element's position lies in its manifest.",
        [
            problem(
                "schema_violation",
                INDEX_FILE,
                0,
                ["unit"],
                "an index row has no 'unit'",
            ),
            problem(
                "schema_violation",
                INDEX_FILE,
                0,
                ["number_type"],
                "an index row has no 'number_type'",
            ),
            problem(
                "schema_violation",
                INDEX_FILE,
                0,
                ["start"],
                "an index row has no 'start'",
            ),
        ],
    ),
    "stale_index": (
        _stale_index,
        "The index gives Bach's score a name it does not have and a region it "
        "does not hold, and lacks the group Handel's manifest gained.",
        [
            problem(
                "stale_index",
                INDEX_FILE,
                0,
                ["name"],
                "the index row of the ID 'clt_1' at 'bach/manifest.yaml' has the name "
                "'Score', not None",
            ),
            problem(
                "stale_index",
                INDEX_FILE,
                4,
                ["id"],
                "the index holds the ID 'region_9' at 'bach/manifest.yaml', which no "
                "manifest or table holds there",
            ),
            problem(
                "stale_index",
                INDEX_FILE,
                None,
                ["id"],
                "the index lacks the ID 'group_1' at 'handel/manifest.yaml'",
            ),
        ],
    ),
    "projection_of_its_own_timeline": (
        _projection_of_its_own_timeline,
        "A pre-parsed Projection of Bach's on dpt_1 stands for an event of dpt_1.",
        [
            problem(
                "invalid_projection_of",
                PART_A_FILE,
                1,
                ["projection_of", "timeline_id"],
                "a Projection stands for an event of another timeline than 'dpt_1'",
            ),
        ],
    ),
    "projection_of_no_timeline": (
        _projection_of_no_timeline,
        "A pre-parsed Projection stands for an event of clt_9, a timeline no "
        "manifest holds.",
        [
            problem(
                "unknown_timeline",
                PART_B_FILE,
                1,
                ["projection_of", "timeline_id"],
                "no manifest of the package has the timeline 'clt_9'",
            ),
        ],
    ),
}
"""Each rejection: the change, its reason, and every problem expected, in order."""


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.write_bytes(text.encode("utf-8"))


def _write_table(path: Path, table: pa.Table) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file() or not pq.read_table(path).equals(table, check_metadata=True):
        pq.write_table(table, path)


def _prune(directory: Path, package: Package) -> None:
    """Remove the files of a case's folder that its package no longer has."""
    kept = {
        "package.yaml",
        "expected.yaml",
        *package.manifests,
        *package.tables,
        *package.texts,
    }
    for path in sorted(directory.rglob("*"), reverse=True):
        name = path.relative_to(directory).as_posix()
        if path.is_file() and name not in kept:
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def _found(directory: Path) -> list[dict[str, Any]]:
    return [
        problem(found.code, found.file, found.row, list(found.path), found.message)
        for found in package_problems(directory / "package.yaml")
    ]


def main() -> int:
    """Check every package and write every file that changed."""
    tag = f"v{SCHEMA_VERSION}"
    tagged = subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "tag", "--list", tag],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    if tag in tagged:
        raise SystemExit(
            f"{tag} is released; its packages in {PACKAGE_DIR} are frozen."
        )
    shared = Package()
    validate_package(shared.package)
    for manifest in shared.manifests.values():
        validate(with_file_ids(manifest))
    shared.write(PACKAGE_DIR / "shared")
    _prune(PACKAGE_DIR / "shared", shared)
    _write_text(
        PACKAGE_DIR / "shared" / "expected.yaml",
        dumps({"read": READ, "resolutions": RESOLUTIONS}),
    )
    found = _found(PACKAGE_DIR / "shared")
    if found:
        raise SystemExit(f"the shared package has problems: {found}")
    accepted = PACKAGE_DIR / "acceptances"
    for stale in accepted.iterdir() if accepted.is_dir() else ():
        if stale.name not in ACCEPTANCES:
            shutil.rmtree(stale)
    for name, (change, reason, resolutions) in ACCEPTANCES.items():
        package = Package()
        change(package)
        directory = accepted / name
        package.write(directory)
        _prune(directory, package)
        expected = {"problems": [], "reason": reason}
        if resolutions is not None:
            expected["resolutions"] = resolutions
        _write_text(directory / "expected.yaml", dumps(expected))
        found = _found(directory)
        if found:
            raise SystemExit(f"{name}: expected no problem, found {found}")
    failed: list[str] = []
    cases = PACKAGE_DIR / "rejections"
    for stale in cases.iterdir() if cases.is_dir() else ():
        if stale.name not in REJECTIONS:
            shutil.rmtree(stale)
    for name, (change, reason, expected) in REJECTIONS.items():
        package = Package()
        change(package)
        directory = cases / name
        package.write(directory)
        _prune(directory, package)
        _write_text(
            directory / "expected.yaml", dumps({"problems": expected, "reason": reason})
        )
        found = _found(directory)
        if found != expected:
            failed.append(f"{name}: expected {expected},\n found {found}")
    if failed:
        raise SystemExit("\n".join(failed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
