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
digest of the source file of the first parse. A Parquet file is
rewritten only when its table changes, and the files of a released
version, whose tag ``v<version>`` exists, are never overwritten.

Run it from ``python/`` with ``uv run python ../scripts/emit_packages.py``;
pyarrow is a development dependency of the package.

The package ``shared/``: two manifests, ``bach/manifest.yaml`` (a score
``clt_1`` in quarters and a performance ``dpt_1`` in samples) and
``handel/manifest.yaml`` (a score ``clt_2`` with a child ``clt_3`` starting
at the quarter 4, and a performance ``dpt_2``), share the registry
``registry.parquet``, one file holding every row: first the non-event rows of
both manifests' elements, the MatchClaims and the parses, sorted by
location and ID, then the event rows, sorted by timeline, start and ID:
the notes of Bach's score, made by a score editor without a source file
(``parse_3``), and of Handel's, made by an aligner without a source file
(``parse_2``), Bach's Projections, made from ``bach/alignment.csv``
(``parse_1``), each with its locator, and Handel's, made by the aligner
(``parse_2``), the two on ``clt_3`` at their positions on the root
``clt_2``. A Projection's row names the event it stands for in its
``projection_of`` and its ``location`` is null: a Projection holds nothing
but its ID and that event, so it has no pre-parsed table. The
Parse table ``tables/parses.parquet`` records the three runs. The
pre-parsed Note table ``tables/Note/`` holds each note's MIDI pitch in two
files whose rows interleave the two manifests', and the folder of
MatchClaims ``tables/MatchClaim/`` one file, which states one provenance for
all its rows in its metadata. Each manifest's resources name the registry,
with the timelines whose event rows it keeps, and the MatchClaims, with the
timelines whose MatchClaims it reads.

Each acceptance under ``acceptances/<case>/`` is ``shared/`` with one
change the package check accepts, beside an ``expected.yaml`` listing no
problem and, where the case concerns them, the resolutions of some IDs.
Each rejection under ``rejections/<case>/`` is ``shared/`` with one change,
beside an ``expected.yaml`` listing exactly the problems the package check
reports, in order. A change that adds or alters an element of a manifest
changes its non-event row too, so that the non-event rows are stale only
where a case says so.
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
    MATCH_CLAIM_SCHEMA,
    PARSE_SCHEMA,
    PROVENANCE_METADATA_KEY,
    REGISTRY_SCHEMA,
    TYPE_METADATA_KEY,
    VERSION_METADATA_KEY,
    package_problems,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = REPOSITORY_ROOT / "fixtures" / "packages" / SCHEMA_VERSION

PARQUET = "application/vnd.apache.parquet"
REGISTRY = "registry.parquet"
PARSES = "tables/parses.parquet"
NOTES = "tables/Note/"
MATCH_CLAIMS = "tables/MatchClaim/"
PART_A_FILE = f"{NOTES}part_a.parquet"
PART_B_FILE = f"{NOTES}part_b.parquet"
CLAIM_FILE = f"{MATCH_CLAIMS}part_a.parquet"
BACH_FILE = "bach/manifest.yaml"
HANDEL_FILE = "handel/manifest.yaml"
SOURCE = "bach/alignment.csv"
SOURCE_TEXT = "onset,sample\n0,0\n1,44100\n2,88200\n3,132300\n"
"""The source file of the first parse, Bach's alignment."""

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
            "timelines": ["clt_1", "dpt_1"],
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
            "timelines": ["clt_2", "clt_3", "dpt_2"],
            "url": f"../{REGISTRY}",
            "media_type": PARQUET,
        },
    ],
}
"""The second manifest, IDs bare; its child ``clt_3`` holds event rows of
its own beside its parent's."""

PACKAGE: dict[str, Any] = {
    "timetoshare": SCHEMA_VERSION,
    "name": "Two manifests sharing their registry and tables",
    "manifests": [
        {"url": BACH_FILE, "media_type": "application/yaml"},
        {"url": HANDEL_FILE, "media_type": "application/yaml"},
    ],
    "tables": [
        {"type": "Registry", "url": REGISTRY, "media_type": PARQUET},
        {"type": "Parse", "url": PARSES, "media_type": PARQUET},
        {"type": "MatchClaim", "url": MATCH_CLAIMS, "media_type": PARQUET},
        {"type": "Note", "url": NOTES, "media_type": PARQUET},
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
    parse: str,
    duration: Any = None,
    locator: str | None = None,
    kind: str = "Projection",
    location: str | None = None,
    of: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """An event row, its position on its root's axis; a Projection's names the
    event it stands for (``of``)."""
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
        "parse_id": parse,
        "locator": locator,
        "projection_of": None
        if of is None
        else {"timeline_id": of[0], "event_id": of[1]},
    }


def note(identifier: str, timeline: str, start: Any) -> dict[str, Any]:
    """A note's event row, a quarter long, its content in the pre-parsed Note
    table: Bach's (on ``clt_1``) of the score editor's parse, Handel's of the
    aligner's."""
    return event(
        identifier,
        timeline,
        QUARTERS,
        start,
        "parse_3" if timeline == "clt_1" else "parse_2",
        Fraction(1),
        kind="Note",
        location=NOTES,
    )


def non_event(
    identifier: str, kind: str, location: str, **members: Any
) -> dict[str, Any]:
    """A non-event row."""
    return {**_NULLS, "id": identifier, "kind": kind, "location": location, **members}


BACH_NOTES: list[dict[str, Any]] = [
    note("note_1", "clt_1", 0),
    note("note_2", "clt_1", 1),
    note("note_4", "clt_1", 2),
    note("note_3", "clt_1", 3),
]
"""Bach's notes, sorted by start."""

HANDEL_NOTES: list[dict[str, Any]] = [
    note("note_5", "clt_2", 0),
    note("note_6", "clt_2", 2),
    note("note_7", "clt_2", 3),
]
"""Handel's notes, sorted by start."""


def _bach(identifier: str, start: int, row: int, of: str) -> dict[str, Any]:
    return event(
        identifier,
        "dpt_1",
        SAMPLES,
        start,
        "parse_1",
        locator=f"row {row}",
        of=("clt_1", of),
    )


BACH_EVENTS: list[dict[str, Any]] = [
    _bach("projection_1", 0, 1, "note_1"),
    _bach("projection_2", 44100, 2, "note_2"),
    _bach("projection_9", 88200, 3, "note_4"),
    _bach("projection_7", 132300, 4, "note_3"),
]
"""Bach's Projections, sorted by timeline, start and ID, each of a note."""

HANDEL_EVENTS: list[dict[str, Any]] = [
    event(
        "projection_5",
        "clt_3",
        QUARTERS,
        Fraction(9, 2),
        "parse_2",
        Fraction(1, 2),
        of=("dpt_2", "onset_1"),
    ),
    event(
        "projection_8",
        "clt_3",
        QUARTERS,
        Fraction(11, 2),
        "parse_2",
        of=("dpt_2", "onset_2"),
    ),
    event("projection_3", "dpt_2", SAMPLES, 0, "parse_2", of=("clt_2", "note_5")),
    event(
        "projection_4",
        "dpt_2",
        SAMPLES,
        88200,
        "parse_2",
        44100,
        of=("clt_2", "note_6"),
    ),
    event("projection_6", "dpt_2", SAMPLES, 132300, "parse_2", of=("clt_2", "note_7")),
]
"""Handel's Projections, sorted by timeline, start and ID; the two on the
child ``clt_3`` lie at 1/2 and 3/2 on it, 9/2 and 11/2 on its root, and
stand for onsets of the performance the package does not hold."""

EVENTS: list[dict[str, Any]] = [
    *BACH_NOTES,
    *HANDEL_NOTES,
    *HANDEL_EVENTS[:2],
    *BACH_EVENTS,
    *HANDEL_EVENTS[2:],
]
"""Every event row, sorted by timeline, start and ID: Bach's four notes on
``clt_1``, Handel's three on ``clt_2``, Handel's two Projections on
``clt_3``, Bach's four on ``dpt_1``, Handel's three on ``dpt_2``."""

NON_EVENTS: list[dict[str, Any]] = [
    non_event("clt_1", "Timeline", BACH_FILE),
    non_event("dpt_1", "Timeline", BACH_FILE),
    non_event("resource_1", "Resource", BACH_FILE),
    non_event("resource_2", "Resource", BACH_FILE),
    non_event("clt_2", "Timeline", HANDEL_FILE),
    non_event("clt_3", "Timeline", HANDEL_FILE),
    non_event("dpt_2", "Timeline", HANDEL_FILE),
    non_event("resource_1", "Resource", HANDEL_FILE),
    non_event("resource_2", "Resource", HANDEL_FILE),
    *(
        non_event(f"claim_{number}", "MatchClaim", MATCH_CLAIMS)
        for number in (1, 2, 3, 4, 5)
    ),
    non_event("parse_1", "Parse", PARSES),
    non_event("parse_2", "Parse", PARSES),
    non_event("parse_3", "Parse", PARSES),
]
"""The non-event rows, sorted by location and ID: each element of the two
manifests, each MatchClaim and each parse."""


NOTE_SCHEMA = pa.schema(
    [pa.field("id", pa.string()), pa.field("midi_pitch", pa.int64())]
)
"""The columns of the pre-parsed Note table: a note's ID and its MIDI pitch."""


def pitched(identifier: str, midi_pitch: int) -> dict[str, Any]:
    """A pre-parsed note: its ID and its MIDI pitch."""
    return {"id": identifier, "midi_pitch": midi_pitch}


PART_A: list[dict[str, Any]] = [
    pitched("note_5", 67),
    pitched("note_1", 60),
    pitched("note_2", 62),
    pitched("note_6", 69),
]
"""The first file of pre-parsed notes."""

PART_B: list[dict[str, Any]] = [
    pitched("note_7", 71),
    pitched("note_3", 65),
    pitched("note_4", 64),
]
"""The second file of pre-parsed notes."""


def parses() -> list[dict[str, Any]]:
    """The three runs: a parser over Bach's alignment, an aligner without a
    source, a score editor without a source."""
    digest = hashlib.sha256(SOURCE_TEXT.encode("utf-8")).hexdigest()
    return [
        {
            "id": "parse_1",
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
            "id": "parse_2",
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
        {
            "id": "parse_3",
            "source": None,
            "source_integrity": None,
            "parser": "https://example.org/score-editor",
            "parser_version": "2.0",
            "parameters": None,
            "minter": "1",
            "id_length": 8,
            "seed": None,
            "date": "2026-11-27T21:29:00Z",
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
        "resource_2": [
            "note_1",
            "note_2",
            "note_3",
            "note_4",
            "projection_1",
            "projection_2",
            "projection_7",
            "projection_9",
        ],
    },
    HANDEL_FILE: {
        "resource_1": ["claim_3", "claim_4"],
        "resource_2": [
            "note_5",
            "note_6",
            "note_7",
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
    kind: str, location: str | None, manifest: str | None, row: dict[str, Any] | None
) -> dict[str, Any]:
    return {"kind": kind, "location": location, "manifest": manifest, "row": row}


RESOLUTIONS: list[dict[str, Any]] = [
    {
        "path": BACH_FILE,
        "id": "dpt_1",
        "found": [
            resolution(
                "Timeline",
                BACH_FILE,
                BACH_FILE,
                non_event("dpt_1", "Timeline", BACH_FILE),
            )
        ],
    },
    {
        "path": BACH_FILE,
        "id": "projection_1",
        "found": [resolution("Projection", None, BACH_FILE, BACH_EVENTS[0])],
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
                non_event("claim_1", "MatchClaim", MATCH_CLAIMS),
            )
        ],
    },
    {
        "path": BACH_FILE,
        "id": "parse_1",
        "found": [
            resolution(
                "Parse",
                PARSES,
                BACH_FILE,
                non_event("parse_1", "Parse", PARSES),
            )
        ],
    },
    {"path": BACH_FILE, "id": "parse_2", "found": []},
    {
        "path": HANDEL_FILE,
        "id": "projection_5",
        "found": [resolution("Projection", None, HANDEL_FILE, HANDEL_EVENTS[0])],
    },
    {
        "path": ".",
        "id": "resource_1",
        "found": [
            resolution(
                "Resource",
                BACH_FILE,
                BACH_FILE,
                non_event("resource_1", "Resource", BACH_FILE),
            ),
            resolution(
                "Resource",
                HANDEL_FILE,
                HANDEL_FILE,
                non_event("resource_1", "Resource", HANDEL_FILE),
            ),
        ],
    },
    {
        "path": ".",
        "id": "projection_5",
        "found": [resolution("Projection", None, None, HANDEL_EVENTS[0])],
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
            REGISTRY: (copy.deepcopy([*NON_EVENTS, *EVENTS]), REGISTRY_SCHEMA),
            PARSES: (parses(), PARSE_SCHEMA),
            PART_A_FILE: (copy.deepcopy(PART_A), NOTE_SCHEMA),
            PART_B_FILE: (copy.deepcopy(PART_B), NOTE_SCHEMA),
            CLAIM_FILE: (copy.deepcopy(CLAIMS), MATCH_CLAIM_SCHEMA),
        }
        self.metadata = {
            REGISTRY: _metadata("Registry"),
            PARSES: _metadata("Parse"),
            PART_A_FILE: _metadata("Note"),
            PART_B_FILE: _metadata("Note"),
            CLAIM_FILE: {
                **_metadata("MatchClaim"),
                PROVENANCE_METADATA_KEY: json.dumps(SHARED_PROVENANCE, sort_keys=True),
            },
        }
        self.texts = {SOURCE: SOURCE_TEXT}

    @property
    def registry(self) -> list[dict[str, Any]]:
        """The rows of the registry file, in their order."""
        return self.tables[REGISTRY][0]

    def event(self, identifier: str) -> dict[str, Any]:
        """The event row of an ID in the registry."""
        (row,) = (
            row for row in self.registry[len(NON_EVENTS) :] if row["id"] == identifier
        )
        return row

    def insert_after(self, identifier: str, row: dict[str, Any]) -> None:
        """Insert an event row after the event row of an ID."""
        self.registry.insert(self.registry.index(self.event(identifier)) + 1, row)

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


EXTERNAL = "https://example.org/events/note_1"
"""An absolute URI naming the content of an event outside the package."""


def _external_location(package: Package) -> None:
    package.event("note_1")["location"] = EXTERNAL
    rows = package.tables[PART_A_FILE][0]
    rows[:] = [row for row in rows if row["id"] != "note_1"]


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
    package.registry.insert(4, non_event("resource_3", "Resource", BACH_FILE))


def _timeline_in_two_manifests(package: Package) -> None:
    handel = package.manifests[HANDEL_FILE]
    handel["timelines"].insert(1, {"id": "dpt_1", "unit": "samples", "length": 352800})
    handel["resources"][1]["timelines"].append("dpt_1")
    package.registry.insert(6, non_event("dpt_1", "Timeline", HANDEL_FILE))


def _re_parsable_event(package: Package) -> None:
    package.insert_after(
        "projection_7",
        event(
            "onset_9",
            "dpt_1",
            SAMPLES,
            176400,
            "parse_1",
            locator="row 5",
            kind="Onset",
            location=None,
        ),
    )


ACCEPTANCES: dict[
    str, tuple[Callable[[Package], None], str, list[dict[str, Any]] | None]
] = {
    "external_location": (
        _external_location,
        "The content of Bach's first note lies outside the package: its "
        "location is an absolute URI, which the package check does not follow, "
        "and the pre-parsed tables hold no row of it.",
        [
            {
                "path": BACH_FILE,
                "id": "note_1",
                "found": [
                    resolution(
                        "Note",
                        EXTERNAL,
                        BACH_FILE,
                        {**BACH_NOTES[0], "location": EXTERNAL},
                    )
                ],
            }
        ],
    ),
    "recording_resource": (
        _recording_resource,
        "Bach's manifest names a recording beside it, a resource naming no "
        "table, which package.yaml does not list and the package check "
        "passes over; the registry holds its non-event row.",
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
                        non_event("dpt_1", "Timeline", BACH_FILE),
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
                        non_event("dpt_1", "Timeline", HANDEL_FILE),
                    )
                ],
            },
            {
                "path": HANDEL_FILE,
                "id": "projection_1",
                "found": [resolution("Projection", None, HANDEL_FILE, BACH_EVENTS[0])],
            },
            {
                "path": ".",
                "id": "dpt_1",
                "found": [
                    resolution(
                        "Timeline",
                        BACH_FILE,
                        BACH_FILE,
                        non_event("dpt_1", "Timeline", BACH_FILE),
                    ),
                    resolution(
                        "Timeline",
                        HANDEL_FILE,
                        HANDEL_FILE,
                        non_event("dpt_1", "Timeline", HANDEL_FILE),
                    ),
                ],
            },
        ],
    ),
    "re_parsable_event": (
        _re_parsable_event,
        "An onset of Bach's parse has no pre-parsed content: its location "
        "is null, its content re-parsable from the parse's source file.",
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
                            "parse_1",
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
    package.insert_after(
        "projection_6",
        event(
            "onset_9",
            "dpt_9",
            SAMPLES,
            0,
            "parse_1",
            locator="row 5",
            kind="Onset",
            location=None,
        ),
    )


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
    package.registry.insert(14, non_event("claim_6", "MatchClaim", MATCH_CLAIMS))


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
    package.registry.insert(4, non_event("resource_3", "Resource", BACH_FILE))


def _folder_with_size(package: Package) -> None:
    package.package["tables"][3]["size"] = 1024


def _timeline_unlisted(package: Package) -> None:
    package.manifests[HANDEL_FILE]["resources"][1]["timelines"] = ["clt_2", "dpt_2"]


def _axis_mismatch(package: Package) -> None:
    rows = package.registry
    rows[rows.index(package.event("projection_7"))] = event(
        "projection_7",
        "dpt_1",
        ("seconds", "float"),
        3.0,
        "parse_1",
        locator="row 4",
        of=("clt_1", "note_3"),
    )


def _file_of_another_type(package: Package) -> None:
    package.metadata[PART_B_FILE][TYPE_METADATA_KEY] = "MatchClaim"


def _table_listed_twice(package: Package) -> None:
    package.package["tables"].append(
        {"type": "Note", "url": NOTES, "media_type": PARQUET}
    )


def _file_in_a_listed_folder(package: Package) -> None:
    package.package["tables"].append(
        {"type": "Note", "url": PART_B_FILE, "media_type": PARQUET}
    )


def _registry_missing(package: Package) -> None:
    del package.package["tables"][0]
    del package.tables[REGISTRY]
    del package.metadata[REGISTRY]
    for manifest in package.manifests.values():
        del manifest["resources"][1]


def _registry_listed_twice(package: Package) -> None:
    package.package["tables"].append(
        {"type": "Registry", "url": "old/registry.parquet", "media_type": PARQUET}
    )
    package.tables["old/registry.parquet"] = ([], REGISTRY_SCHEMA)
    package.metadata["old/registry.parquet"] = _metadata("Registry")


def _parse_table_listed_twice(package: Package) -> None:
    package.package["tables"].append(
        {"type": "Parse", "url": "old/parses.parquet", "media_type": PARQUET}
    )
    package.tables["old/parses.parquet"] = ([], PARSE_SCHEMA)
    package.metadata["old/parses.parquet"] = _metadata("Parse")


def _unknown_parse(package: Package) -> None:
    package.event("projection_3")["parse_id"] = "parse_9"


def _vanished_in_an_unknown_parse(package: Package) -> None:
    package.event("projection_3")["vanished_in"] = "parse_4"


def _unknown_location(package: Package) -> None:
    package.event("note_2")["location"] = "tables/Box/"


def _missing_content(package: Package) -> None:
    package.insert_after("note_3", note("note_8", "clt_1", 4))


def _unregistered_id(package: Package) -> None:
    package.tables[PART_B_FILE][0].append(pitched("note_9", 72))


def _locator_twice(package: Package) -> None:
    package.event("projection_7")["locator"] = "row 1"


def _registry_id_twice(package: Package) -> None:
    package.insert_after(
        "projection_6",
        event(
            "claim_1",
            "dpt_2",
            SAMPLES,
            176400,
            "parse_2",
            kind="Onset",
            location=None,
        ),
    )


def _non_event_row_with_a_position(package: Package) -> None:
    row = package.registry[0]
    row.update(unit="quarters", number_type="fraction", start=number(0, "fraction"))


def _stale_non_event_row(package: Package) -> None:
    rows = package.registry
    rows[0]["kind"] = "VirtualTimeline"
    rows.insert(4, non_event("region_9", "Region", BACH_FILE, timeline_id="clt_1"))
    package.manifests[HANDEL_FILE]["groups"] = [
        {"id": "group_1", "members": ["clt_2", "dpt_2"]}
    ]


def _registry_folder(package: Package) -> None:
    package.tables[f"registry/{REGISTRY}"] = package.tables.pop(REGISTRY)
    package.metadata[f"registry/{REGISTRY}"] = package.metadata.pop(REGISTRY)
    package.package["tables"][0]["url"] = "registry/"
    for manifest in package.manifests.values():
        manifest["resources"][1]["url"] = "../registry/"


FEATURES = "tables/features.parquet"
"""A carried table of audio features, its rows keyed by no ID."""


def _foreign_table(package: Package) -> None:
    package.package["tables"].append(
        {"type": "Features", "url": FEATURES, "media_type": PARQUET}
    )
    package.tables[FEATURES] = (
        [{"x": 0.25}, {"x": 0.5}],
        pa.schema([pa.field("x", pa.float64())]),
    )
    package.metadata[FEATURES] = _metadata("Features")


def _projection_of_its_own_timeline(package: Package) -> None:
    package.event("projection_1")["projection_of"] = {
        "timeline_id": "dpt_1",
        "event_id": "note_1",
    }


def _projection_of_no_timeline(package: Package) -> None:
    package.event("projection_7")["projection_of"] = {
        "timeline_id": "clt_9",
        "event_id": "note_3",
    }


def _projection_of_on_another_kind(package: Package) -> None:
    package.event("note_1")["projection_of"] = {
        "timeline_id": "dpt_1",
        "event_id": "projection_1",
    }


REJECTIONS: dict[str, tuple[Callable[[Package], None], str, list[dict[str, Any]]]] = {
    "row_of_no_manifest": (
        _row_of_no_manifest,
        "An event row lies on dpt_9, a timeline no manifest of the package holds.",
        [
            problem(
                "unknown_timeline",
                REGISTRY,
                33,
                ["timeline_id"],
                "no manifest of the package has the timeline 'dpt_9'",
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
                NOTES,
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
        "package.yaml states a size for the folder of notes; a folder has none.",
        [
            problem(
                "folder_descriptor",
                "package.yaml",
                None,
                ["tables", 3, "size"],
                "'tables/Note/' names a folder, which has no size",
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
                REGISTRY,
                24,
                ["timeline_id"],
                "the timeline 'clt_3' of 'handel/manifest.yaml' is listed by no "
                "resource of the type Registry naming this table",
            ),
            problem(
                "unlisted_timeline",
                REGISTRY,
                25,
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
                REGISTRY,
                29,
                ["unit"],
                "a coordinate in seconds (float) on the timeline 'dpt_1' in samples "
                "(int)",
            ),
        ],
    ),
    "file_of_another_type": (
        _file_of_another_type,
        "part_b, in the folder of notes, states the type MatchClaim.",
        [
            problem(
                "table_type",
                PART_B_FILE,
                None,
                [],
                "the file holds the type MatchClaim, its table the type Note",
            ),
        ],
    ),
    "table_listed_twice": (
        _table_listed_twice,
        "package.yaml lists the folder of notes twice; a table is listed "
        "once under its URL and type.",
        [
            problem(
                "duplicate_url",
                "package.yaml",
                None,
                ["tables", 4, "url"],
                "the table 'tables/Note/' of the type Note is listed twice, first "
                "at #/tables/3/url",
            ),
        ],
    ),
    "file_in_a_listed_folder": (
        _file_in_a_listed_folder,
        "package.yaml lists part_b, a file of the listed folder of notes, "
        "as a table of its own; its rows would be read twice.",
        [
            problem(
                "duplicate_url",
                "package.yaml",
                None,
                ["tables", 4, "url"],
                "the file 'tables/Note/part_b.parquet' is read by the table "
                "'tables/Note/' already",
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
    "parse_table_listed_twice": (
        _parse_table_listed_twice,
        "package.yaml lists a second Parse table; a package has at most one.",
        [
            problem(
                "duplicate_parse",
                "package.yaml",
                None,
                ["tables", 4, "type"],
                "the package lists a second table of the type Parse, first at "
                "#/tables/1/type",
            ),
        ],
    ),
    "unknown_parse": (
        _unknown_parse,
        "An event row of Handel's names parse_9, which the Parse table does not hold.",
        [
            problem(
                "unknown_parse",
                REGISTRY,
                30,
                ["parse_id"],
                "no parse of the package has the ID 'parse_9'",
            ),
        ],
    ),
    "vanished_in_an_unknown_parse": (
        _vanished_in_an_unknown_parse,
        "An event row of Handel's vanished in parse_4, which the Parse "
        "table does not hold.",
        [
            problem(
                "unknown_parse",
                REGISTRY,
                30,
                ["vanished_in"],
                "no parse of the package has the ID 'parse_4'",
            ),
        ],
    ),
    "unknown_location": (
        _unknown_location,
        "A note's event row names tables/Box/ as its content's table, which "
        "package.yaml does not list.",
        [
            problem(
                "unknown_location",
                REGISTRY,
                18,
                ["location"],
                "the location 'tables/Box/' names no table of the type Note in the "
                "package",
            ),
        ],
    ),
    "missing_content": (
        _missing_content,
        "A note's event row names the pre-parsed notes, which hold no row of its ID.",
        [
            problem(
                "missing_content",
                REGISTRY,
                21,
                ["location"],
                "the table 'tables/Note/' holds no row of the ID 'note_8'",
            ),
        ],
    ),
    "unregistered_id": (
        _unregistered_id,
        "A pre-parsed note has an ID no event row of the registry has.",
        [
            problem(
                "unregistered_id",
                PART_B_FILE,
                3,
                ["id"],
                "no event row of the type Note in the registry has the ID 'note_9'",
            ),
        ],
    ),
    "locator_twice": (
        _locator_twice,
        "Two event rows of Bach's parse give the locator 'row 1'.",
        [
            problem(
                "duplicate_locator",
                REGISTRY,
                29,
                ["locator"],
                "the locator 'row 1' is given twice in the parse 'parse_1'",
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
                REGISTRY,
                33,
                ["id"],
                "the ID 'claim_1' is given twice, first in 'registry.parquet' at row 9",
            ),
        ],
    ),
    "non_event_row_with_a_position": (
        _non_event_row_with_a_position,
        "A non-event row states a position; an element's position lies in its "
        "manifest.",
        [
            problem(
                "schema_violation",
                REGISTRY,
                0,
                ["unit"],
                "a non-event row has no 'unit'",
            ),
            problem(
                "schema_violation",
                REGISTRY,
                0,
                ["number_type"],
                "a non-event row has no 'number_type'",
            ),
            problem(
                "schema_violation",
                REGISTRY,
                0,
                ["start"],
                "a non-event row has no 'start'",
            ),
        ],
    ),
    "stale_non_event_row": (
        _stale_non_event_row,
        "The registry gives Bach's score timeline the kind of a virtual "
        "timeline, holds a region the manifest does not hold, and lacks the "
        "group Handel's manifest gained.",
        [
            problem(
                "stale_non_event_row",
                REGISTRY,
                0,
                ["kind"],
                "the non-event row of the ID 'clt_1' at 'bach/manifest.yaml' has the "
                "kind 'VirtualTimeline', not 'Timeline'",
            ),
            problem(
                "stale_non_event_row",
                REGISTRY,
                4,
                ["id"],
                "the registry holds the non-event row of the ID 'region_9' at "
                "'bach/manifest.yaml', which no manifest or table holds there",
            ),
            problem(
                "stale_non_event_row",
                REGISTRY,
                None,
                ["id"],
                "the registry lacks the non-event row of the ID 'group_1' at "
                "'handel/manifest.yaml'",
            ),
        ],
    ),
    "registry_folder": (
        _registry_folder,
        "package.yaml and both manifests name a folder registry/ as the registry, "
        "the file registry.parquet inside it; a registry is one Parquet file.",
        [
            problem(
                "registry_not_a_file",
                "package.yaml",
                None,
                ["tables", 0, "url"],
                "the registry 'registry/' names a folder; a registry is one Parquet "
                "file",
            ),
            problem(
                "registry_not_a_file",
                BACH_FILE,
                None,
                ["resources", 1, "url"],
                "the registry '../registry/' names a folder; a registry is one "
                "Parquet file",
            ),
            problem(
                "registry_not_a_file",
                HANDEL_FILE,
                None,
                ["resources", 1, "url"],
                "the registry '../registry/' names a folder; a registry is one "
                "Parquet file",
            ),
        ],
    ),
    "foreign_table": (
        _foreign_table,
        "The package carries a table of audio features, whose rows have no ID: "
        "neither registry, Parse table, MatchClaims nor pre-parsed events.",
        [
            problem(
                "foreign_table",
                FEATURES,
                None,
                [],
                "the table 'tables/features.parquet' of type 'Features' has no 'id' "
                "column: a package's tables hold the registry, the Parse table, "
                "MatchClaim tables and pre-parsed tables of events keyed by 'id'",
            ),
        ],
    ),
    "projection_of_its_own_timeline": (
        _projection_of_its_own_timeline,
        "A Projection of Bach's on dpt_1 stands for an event of dpt_1.",
        [
            problem(
                "invalid_projection_of",
                REGISTRY,
                26,
                ["projection_of", "timeline_id"],
                "a Projection stands for an event of another timeline than 'dpt_1'",
            ),
        ],
    ),
    "projection_of_no_timeline": (
        _projection_of_no_timeline,
        "A Projection of Bach's stands for an event of clt_9, a timeline no "
        "manifest holds.",
        [
            problem(
                "unknown_timeline",
                REGISTRY,
                29,
                ["projection_of", "timeline_id"],
                "no manifest of the package has the timeline 'clt_9'",
            ),
        ],
    ),
    "projection_of_on_another_kind": (
        _projection_of_on_another_kind,
        "A note's event row names an event it would stand for; only a "
        "Projection's row states its projection_of.",
        [
            problem(
                "invalid_projection_of",
                REGISTRY,
                17,
                ["projection_of"],
                "'projection_of' is set on a row of the kind 'Note'",
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
