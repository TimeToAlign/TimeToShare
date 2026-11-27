#!/usr/bin/env python
"""Write the package fixtures: a package of two manifests sharing their
tables, and one package per rule of the package check that breaks it, to
``fixtures/packages/<version>/``.

Every value is written here by hand: the rows, the manifests, the rows
``read_table`` returns for each resource and the problems expected of each
broken package are literal data, never computed by the code they test; the
script checks that the package check agrees before it writes anything. A
Parquet file is rewritten only when its table changes, and the files of a
released version, whose tag ``v<version>`` exists, are never overwritten.

Run it from ``python/`` with ``uv run python ../scripts/emit_packages.py``;
pyarrow is a development dependency of the package.

The package ``shared/``: two manifests, ``bach/manifest.yaml`` (a score
``clt_1`` in quarters and a performance ``dpt_1`` in samples) and
``handel/manifest.yaml`` (a score ``clt_2`` with a child ``clt_3`` and a
performance ``dpt_2``), share a folder of Projections, ``tables/Projection/``
(two files), and a folder of MatchClaims, ``tables/MatchClaim/`` (one file).
The rows of the two manifests are interleaved in every file. ``part_a`` of
the Projections lies sorted by timeline, start and ID, as a writer writes
it; ``part_b`` lies unsorted, which readers accept. The MatchClaim file
states one provenance for all its rows in its metadata. Each manifest's
resources name the two folders, with the timelines whose rows it reads.

Each rejection under ``rejections/<case>/`` is ``shared/`` with one change,
beside an ``expected.yaml`` listing exactly the problems the package check
reports, in order.
"""

from __future__ import annotations

import copy
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
    PROJECTION_SCHEMA,
    PROVENANCE_METADATA_KEY,
    TYPE_METADATA_KEY,
    VERSION_METADATA_KEY,
    package_problems,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = REPOSITORY_ROOT / "fixtures" / "packages" / SCHEMA_VERSION

PARQUET = "application/vnd.apache.parquet"
PROJECTIONS = "tables/Projection/"
MATCH_CLAIMS = "tables/MatchClaim/"

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
            "type": "Projection",
            "timelines": ["dpt_1"],
            "url": f"../{PROJECTIONS}",
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
            "type": "Projection",
            "timelines": ["clt_3", "dpt_2"],
            "url": f"../{PROJECTIONS}",
            "media_type": PARQUET,
        },
    ],
}
"""The second manifest, IDs bare; its child ``clt_3`` holds rows of its own."""

PACKAGE: dict[str, Any] = {
    "timetoshare": SCHEMA_VERSION,
    "name": "Two manifests sharing their tables",
    "manifests": [
        {"url": "bach/manifest.yaml", "media_type": "application/yaml"},
        {"url": "handel/manifest.yaml", "media_type": "application/yaml"},
    ],
    "tables": [
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


def projection(
    identifier: str,
    timeline: str,
    axis: tuple[str, str],
    start: Any,
    of: tuple[str, str] | None,
    duration: Any = None,
) -> dict[str, Any]:
    unit, number_type = axis
    return {
        "id": identifier,
        "timeline_id": timeline,
        "unit": unit,
        "number_type": number_type,
        "start": number(start, number_type),
        "duration": None if duration is None else number(duration, number_type),
        "projection_of": None
        if of is None
        else {"timeline_id": of[0], "event_id": of[1]},
    }


SAMPLES = ("samples", "int")
QUARTERS = ("quarters", "fraction")

PART_A: list[dict[str, Any]] = [
    projection(
        "projection_5",
        "clt_3",
        QUARTERS,
        Fraction(1, 2),
        ("dpt_2", "onset_1"),
        Fraction(1, 2),
    ),
    projection("projection_1", "dpt_1", SAMPLES, 0, ("clt_1", "note_1")),
    projection("projection_2", "dpt_1", SAMPLES, 44100, ("clt_1", "note_2")),
    projection("projection_3", "dpt_2", SAMPLES, 0, ("clt_2", "note_5")),
    projection("projection_4", "dpt_2", SAMPLES, 88200, ("clt_2", "note_6"), 44100),
]
"""The first Projections file, sorted by timeline, start and ID."""

PART_B: list[dict[str, Any]] = [
    projection("projection_6", "dpt_2", SAMPLES, 132300, ("clt_2", "note_7")),
    projection("projection_7", "dpt_1", SAMPLES, 132300, ("clt_1", "note_3")),
    projection("projection_8", "clt_3", QUARTERS, Fraction(3, 2), ("dpt_2", "onset_2")),
    projection("projection_9", "dpt_1", SAMPLES, 88200, ("clt_1", "note_4")),
]
"""The second Projections file, deliberately unsorted."""


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
    "bach/manifest.yaml": {
        "resource_1": ["claim_1", "claim_2", "claim_5"],
        "resource_2": ["projection_1", "projection_2", "projection_7", "projection_9"],
    },
    "handel/manifest.yaml": {
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


class Package:
    """A package's files as data: its ``package.yaml``, its manifests, its
    Parquet files with their metadata."""

    def __init__(self) -> None:
        self.package = copy.deepcopy(PACKAGE)
        self.manifests = {
            "bach/manifest.yaml": copy.deepcopy(BACH),
            "handel/manifest.yaml": copy.deepcopy(HANDEL),
        }
        self.tables: dict[str, tuple[list[dict[str, Any]], pa.Schema]] = {
            f"{PROJECTIONS}part_a.parquet": (copy.deepcopy(PART_A), PROJECTION_SCHEMA),
            f"{PROJECTIONS}part_b.parquet": (copy.deepcopy(PART_B), PROJECTION_SCHEMA),
            f"{MATCH_CLAIMS}part_a.parquet": (
                copy.deepcopy(CLAIMS),
                MATCH_CLAIM_SCHEMA,
            ),
        }
        self.metadata = {
            f"{PROJECTIONS}part_a.parquet": _metadata("Projection"),
            f"{PROJECTIONS}part_b.parquet": _metadata("Projection"),
            f"{MATCH_CLAIMS}part_a.parquet": {
                **_metadata("MatchClaim"),
                PROVENANCE_METADATA_KEY: json.dumps(SHARED_PROVENANCE, sort_keys=True),
            },
        }

    def table(self, name: str) -> pa.Table:
        rows, schema = self.tables[name]
        table = pa.Table.from_pylist(rows, schema=schema)
        return table.replace_schema_metadata(self.metadata[name])

    def write(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        _write_text(directory / "package.yaml", dumps(self.package))
        for name, manifest in self.manifests.items():
            _write_text(directory / name, dumps(with_file_ids(manifest)))
        for name in self.tables:
            _write_table(directory / name, self.table(name))


def _metadata(kind: str) -> dict[str, str]:
    return {TYPE_METADATA_KEY: kind, VERSION_METADATA_KEY: SCHEMA_VERSION}


def problem(
    code: str, file: str, row: int | None, path: list[Any], message: str
) -> dict[str, Any]:
    return {"code": code, "file": file, "row": row, "path": path, "message": message}


# The rejections: each a change to the shared package, with its reason and
# the problems expected, written by hand.

PART_B_FILE = f"{PROJECTIONS}part_b.parquet"


def _row_of_no_manifest(package: Package) -> None:
    package.tables[PART_B_FILE][0].append(
        projection("projection_10", "dpt_9", SAMPLES, 0, None)
    )


def _projection_id_in_two_files(package: Package) -> None:
    package.tables[PART_B_FILE][0][3]["id"] = "projection_3"


def _timeline_in_two_manifests(package: Package) -> None:
    timelines = package.manifests["handel/manifest.yaml"]["timelines"]
    timelines.insert(1, {"id": "dpt_1", "unit": "samples", "length": 352800})


def _claim_across_manifests(package: Package) -> None:
    package.tables[f"{MATCH_CLAIMS}part_a.parquet"][0].insert(
        2,
        claim(
            "claim_6",
            ("clt_1", "note_4"),
            ("dpt_2", "projection_6"),
            (coordinate(3, QUARTERS), coordinate(132300, SAMPLES)),
        ),
    )


def _column_in_two_types(package: Package) -> None:
    for name, kind in (
        (f"{PROJECTIONS}part_a.parquet", pa.int64()),
        (PART_B_FILE, pa.string()),
    ):
        rows, schema = package.tables[name]
        for index, row in enumerate(rows):
            row["velocity"] = 64 + index if kind == pa.int64() else "mf"
        package.tables[name] = (rows, schema.append(pa.field("velocity", kind)))


def _version_mismatch(package: Package) -> None:
    package.metadata[PART_B_FILE][VERSION_METADATA_KEY] = "0.1.0"


def _resource_naming_no_table(package: Package) -> None:
    package.manifests["bach/manifest.yaml"]["resources"].append(
        {
            "id": "resource_3",
            "type": "Box",
            "timelines": ["clt_1"],
            "url": "../tables/Box/",
        }
    )


def _folder_with_size(package: Package) -> None:
    package.package["tables"][1]["size"] = 1024


def _timeline_unlisted(package: Package) -> None:
    package.manifests["handel/manifest.yaml"]["resources"][1]["timelines"] = ["dpt_2"]


def _axis_mismatch(package: Package) -> None:
    rows = package.tables[PART_B_FILE][0]
    rows[1] = projection(
        "projection_7", "dpt_1", ("seconds", "float"), 3.0, ("clt_1", "note_3")
    )


def _file_of_another_type(package: Package) -> None:
    package.metadata[PART_B_FILE][TYPE_METADATA_KEY] = "MatchClaim"


REJECTIONS: dict[str, tuple[Callable[[Package], None], str, list[dict[str, Any]]]] = {
    "row_of_no_manifest": (
        _row_of_no_manifest,
        "A Projection lies on dpt_9, a timeline no manifest of the package holds.",
        [
            problem(
                "unknown_timeline",
                PART_B_FILE,
                4,
                ["timeline_id"],
                "no manifest of the package has the timeline 'dpt_9'",
            )
        ],
    ),
    "projection_id_in_two_files": (
        _projection_id_in_two_files,
        "The ID projection_3 names a Projection of Handel's in part_a and one of "
        "Bach's in part_b; an event ID is held once in the package.",
        [
            problem(
                "duplicate_id",
                PART_B_FILE,
                3,
                ["id"],
                "the event ID 'projection_3' is given twice, first in "
                "'tables/Projection/part_a.parquet' at row 3",
            )
        ],
    ),
    "timeline_in_two_manifests": (
        _timeline_in_two_manifests,
        "Handel's manifest holds a timeline dpt_1, which Bach's holds; a timeline "
        "ID is held by one manifest of the package.",
        [
            problem(
                "duplicate_timeline",
                "handel/manifest.yaml",
                None,
                ["timelines", 1, "id"],
                "the timeline 'dpt_1' is a timeline of 'bach/manifest.yaml' as well",
            )
        ],
    ),
    "claim_across_manifests": (
        _claim_across_manifests,
        "A MatchClaim joins Bach's score and Handel's performance; a MatchClaim "
        "lies within one manifest.",
        [
            problem(
                "claim_across_manifests",
                f"{MATCH_CLAIMS}part_a.parquet",
                2,
                ["timeline_b_id"],
                "the MatchClaim joins the timeline 'clt_1' of 'bach/manifest.yaml' "
                "and the timeline 'dpt_2' of 'handel/manifest.yaml'",
            )
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
            )
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
            )
        ],
    ),
    "resource_naming_no_table": (
        _resource_naming_no_table,
        "Bach's manifest names a folder of Box events that package.yaml does not list.",
        [
            problem(
                "unknown_table",
                "bach/manifest.yaml",
                None,
                ["resources", 2, "url"],
                "the resource 'resource_3' names '../tables/Box/', which is no table "
                "of the type Box in the package",
            )
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
                ["tables", 1, "size"],
                "'tables/Projection/' names a folder, which has no size",
            )
        ],
    ),
    "timeline_unlisted": (
        _timeline_unlisted,
        "Handel's Projection resource no longer lists its child clt_3, whose rows "
        "the folder holds; a reader of the manifest would not find them.",
        [
            problem(
                "unlisted_timeline",
                f"{PROJECTIONS}part_a.parquet",
                0,
                ["timeline_id"],
                "the timeline 'clt_3' of 'handel/manifest.yaml' is listed by no "
                "resource of the type Projection naming this table",
            ),
            problem(
                "unlisted_timeline",
                PART_B_FILE,
                2,
                ["timeline_id"],
                "the timeline 'clt_3' of 'handel/manifest.yaml' is listed by no "
                "resource of the type Projection naming this table",
            ),
        ],
    ),
    "axis_mismatch": (
        _axis_mismatch,
        "A Projection on the samples timeline dpt_1 is written in seconds.",
        [
            problem(
                "axis_mismatch",
                PART_B_FILE,
                1,
                ["unit"],
                "a coordinate in seconds (float) on the timeline 'dpt_1' in "
                "samples (int)",
            )
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
            )
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
    _write_text(PACKAGE_DIR / "shared" / "expected.yaml", dumps({"read": READ}))
    found = _found(PACKAGE_DIR / "shared")
    if found:
        raise SystemExit(f"the shared package has problems: {found}")
    cases = PACKAGE_DIR / "rejections"
    for stale in cases.iterdir() if cases.is_dir() else ():
        if stale.name not in REJECTIONS:
            shutil.rmtree(stale)
    for name, (change, reason, expected) in REJECTIONS.items():
        package = Package()
        change(package)
        directory = cases / name
        package.write(directory)
        _write_text(
            directory / "expected.yaml", dumps({"problems": expected, "reason": reason})
        )
        found = _found(directory)
        if found != expected:
            raise SystemExit(f"{name}: expected {expected}, found {found}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
