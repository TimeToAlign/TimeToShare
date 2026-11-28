#!/usr/bin/env python
"""Write the Parquet files of the version cases of tables under
``fixtures/versions/<case>/``.

A version case is two trees, ``old/`` and ``new/``, beside an
``expected.yaml`` of the step and the findings ``tree_step`` gives. The
cases of tables are packages: ``package.yaml``, the manifest ``score.yaml``
(the quarters timeline ``score`` and the seconds timeline ``take``), the
registry ``registry.parquet`` and the Parse table ``parses.parquet``. Their
YAML files and ``expected.yaml`` are written by hand; this script writes
their Parquet files. Every row is literal data here, never computed by the
code the cases test: each ``old/`` tree holds the same three event rows on
``score`` (the MIDI notes ``note_1`` and ``note_2``, re-parsable from their
parse's source file, and the Projection ``proj_1`` of the onset ``onset_1``
on ``take``, which lies in the registry alone) and one parse, and each
``new/`` tree the one change of its case. The non-event rows of each
tree's registry are then written into it by
``timetoshare.tables.write_non_event_rows`` from the tree's hand-written
manifest and tables, so that no case's non-event rows are stale.

A Parquet file is rewritten only when its table changes, and the files of
a released version, whose tag ``v<version>`` exists, are never overwritten.

Run it from ``python/`` with ``uv run python ../scripts/emit_versions.py``;
pyarrow is a development dependency of the package.
"""

from __future__ import annotations

import copy
import subprocess
import sys
from collections.abc import Callable
from fractions import Fraction
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from timetoshare import SCHEMA_VERSION
from timetoshare.tables import (
    PARSE_SCHEMA,
    REGISTRY_SCHEMA,
    TYPE_METADATA_KEY,
    VERSION_METADATA_KEY,
    write_non_event_rows,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VERSIONS_DIR = REPOSITORY_ROOT / "fixtures" / "versions"

REGISTRY = "registry.parquet"
PARSES = "parses.parquet"


def number(value: Fraction) -> dict[str, Any]:
    """A fraction of the registry's number column."""
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "value": None,
    }


def event(
    identifier: str,
    start: Fraction,
    *,
    kind: str = "MidiNote",
    duration: Fraction | None = Fraction(1),
    locator: str | None = None,
    vanished_in: str | None = None,
    projection_of: str | None = None,
) -> dict[str, Any]:
    """An event row on the quarters timeline ``score``, of the first parse; a
    Projection's stands for an event of ``take``."""
    return {
        "id": identifier,
        "kind": kind,
        "location": None,
        "timeline_id": "score",
        "unit": "quarters",
        "number_type": "fraction",
        "start": number(start),
        "duration": None if duration is None else number(duration),
        "parse_id": "parse_1",
        "locator": locator,
        "vanished_in": vanished_in,
        "projection_of": None
        if projection_of is None
        else {"timeline_id": "take", "event_id": projection_of},
    }


def parse(identifier: str, date: str) -> dict[str, Any]:
    """A run of a MIDI parser over ``score.mid``."""
    return {
        "id": identifier,
        "source": "score.mid",
        "source_integrity": {"algorithm": "SHA-256", "digest": "0" * 64},
        "parser": "mido",
        "parser_version": "1.3.3",
        "parameters": None,
        "minter": "1",
        "id_length": 8,
        "seed": None,
        "date": date,
    }


EVENTS: list[dict[str, Any]] = [
    event("note_1", Fraction(0), locator="track 0 message 0"),
    event("note_2", Fraction(1), locator="track 0 message 1"),
    event(
        "proj_1",
        Fraction(2),
        kind="Projection",
        duration=None,
        projection_of="onset_1",
    ),
]
"""The event rows of every ``old/`` tree, sorted by timeline, start and ID."""

PARSE_ROWS = [parse("parse_1", "2026-11-27T00:00:00Z")]


class Tree:
    """The Parquet files of one tree, as rows."""

    def __init__(self) -> None:
        self.tables: dict[str, tuple[list[dict[str, Any]], pa.Schema, str]] = {
            PARSES: (
                copy.deepcopy(PARSE_ROWS),
                PARSE_SCHEMA,
                "Parse",
            ),
            REGISTRY: (copy.deepcopy(EVENTS), REGISTRY_SCHEMA, "Registry"),
        }

    def rows(self, name: str) -> list[dict[str, Any]]:
        return self.tables[name][0]

    def write(self, root: Path) -> None:
        for name, (rows, schema, kind) in self.tables.items():
            table = pa.Table.from_pylist(rows, schema=schema).replace_schema_metadata(
                {TYPE_METADATA_KEY: kind, VERSION_METADATA_KEY: SCHEMA_VERSION}
            )
            _write_table(root / name, table)
        write_non_event_rows(root)


def _row_removed(tree: Tree) -> None:
    del tree.rows(REGISTRY)[1]


def _row_added(tree: Tree) -> None:
    tree.rows(REGISTRY).append(
        event("note_3", Fraction(3), locator="track 0 message 2")
    )


def _projection_moved(tree: Tree) -> None:
    tree.rows(REGISTRY)[2]["start"] = number(Fraction(5, 2))


def _row_vanished(tree: Tree) -> None:
    tree.rows(REGISTRY)[1]["vanished_in"] = "parse_2"
    tree.rows(PARSES).append(parse("parse_2", "2026-11-28T00:00:00Z"))


def _non_event_rows_only(tree: Tree) -> None:
    """No row changes: the manifest renames its timeline, by hand."""


def _projection_edited(tree: Tree) -> None:
    tree.rows(REGISTRY)[2]["projection_of"]["event_id"] = "onset_2"


def _projection_removed(tree: Tree) -> None:
    del tree.rows(REGISTRY)[2]


CASES: dict[str, Callable[[Tree], None]] = {
    "registry_row_removed": _row_removed,
    "registry_row_added": _row_added,
    "registry_projection_moved": _projection_moved,
    "registry_row_vanished": _row_vanished,
    "registry_non_event_rows_only": _non_event_rows_only,
    "projection_row_edited": _projection_edited,
    "projection_row_removed": _projection_removed,
}
"""Each case of tables and the one change of its ``new/`` tree."""


def _write_table(path: Path, table: pa.Table) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file() or not pq.read_table(path).equals(table, check_metadata=True):
        pq.write_table(table, path)


def main() -> int:
    """Write the Parquet files of every case of tables."""
    tag = f"v{SCHEMA_VERSION}"
    tagged = subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "tag", "--list", tag],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    if tag in tagged:
        raise SystemExit(f"{tag} is released; its version cases are frozen.")
    for name, change in CASES.items():
        directory = VERSIONS_DIR / name
        for side in ("old", "new"):
            if not (directory / side / "package.yaml").is_file():
                raise SystemExit(f"{name}/{side} has no hand-written package.yaml")
        Tree().write(directory / "old")
        tree = Tree()
        change(tree)
        tree.write(directory / "new")
    return 0


if __name__ == "__main__":
    sys.exit(main())
