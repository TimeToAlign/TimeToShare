#!/usr/bin/env python
"""Write the table fixture: a manifest, its MatchClaim table, its Projections
table, and the AlignmentAnchors and potential MatchStamps expected of the
MatchClaim table, to ``fixtures/tables/<version>/``.

Every value is written here by hand; the expected anchors and MatchStamps in
particular are literal data, never computed by the derivation they test. The
one exception is what the manifest's resources state of the two Parquet
files, their size and SHA-256 digest, read from the bytes written. A
Parquet file is rewritten only when its table changes, and the files of a
released version, whose tag ``v<version>`` exists, are never overwritten.

Run it from ``python/`` with ``uv run python ../scripts/emit_tables.py``;
pyarrow is a development dependency of the package.

The fixture, on three root timelines (quarters, samples, seconds; one
quarter lasts one second, 44100 samples) and one child of the first:

- ``claim_1``: an instant claim, its sample side a Projection of the note.
- ``claim_2``: an interval claim, two anchors.
- ``claim_3``, ``claim_4``: two MatchClaims stating one anchor, the second
  written in the other orientation.
- ``claim_5``, ``claim_6``: a chain over three timelines.
- ``claim_7``, ``claim_8``: one coordinate in two anchors.
- ``claim_9``, ``claim_10``: an interval claim with another anchor inside
  its span.
- ``claim_11``: a synchronous MatchClaim with CHUNK on both sides: its two
  timelines hold no event at the coordinates its anchor states.
- ``claim_12``: a NOMATCH row; ``claim_14``: a conceptual row.
- ``claim_13``: a row one actor believes false and another true; ``claim_6``
  is believed unlikely, ``claim_1`` and ``claim_11`` true.
- ``claim_15``: a child timeline, whose coordinates never meet its parent's.
- ``claim_16``: an instant MatchClaim between CHUNK on the seconds timeline
  and the note ``claim_2`` states at the quarter 1; its anchor joins
  ``claim_2``'s start into one potential MatchStamp.

A sentinel is written in the event ID column as its reserved string
(``NOMATCH_SENTINEL``, ``CHUNK_SENTINEL``), its name null.

The Projections table holds a Projection of each number type: ints on the
samples timeline (instants and one interval), a float interval on the
seconds timeline, and a fraction interval on the child, the Projection of
an audio onset; the last two name no MatchClaim. A CHUNK
side is no Projection, and the Projections keep their numbers, so
``projection_6`` and ``projection_7`` are not held. Its rows
are written sorted stably by ``timeline_id``, each timeline's rows in the
order listed here: the order in which timetoalign writes a bundle's
Projections table, so that the two files are equal byte for byte.

A number is written by its number type alone (``numerator`` for an int,
``numerator`` and ``denominator`` for a fraction, ``value`` for a float), the
other members null; a Projection's row states the unit and the number type
of its ``start`` and ``duration`` once.
"""

from __future__ import annotations

import copy
import hashlib
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from timetoshare import FORMAT_CONTEXT, SCHEMA_VERSION, dumps, validate, with_file_ids
from timetoshare.tables import (
    CHUNK_SENTINEL,
    MATCH_CLAIM_SCHEMA,
    NOMATCH_SENTINEL,
    PROJECTION_SCHEMA,
    check_match_claims,
    check_projections,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = REPOSITORY_ROOT / "fixtures" / "tables" / SCHEMA_VERSION

ACTOR = "https://orcid.org/0000-0002-1825-0097"
"""The actor whose beliefs the filter cases read."""

ACTOR_COMPACT = "orcid:0000-0002-1825-0097"
"""``ACTOR`` as a compact IRI under the manifest's ``@context``."""

OTHER_ACTOR = "https://orcid.org/0000-0001-5109-3700"
SERVICE = "https://example.org/aligner"
DATE = "2026-11-20"
LATER = "2026-11-21"

MANIFEST: dict[str, Any] = {
    "timetoshare": SCHEMA_VERSION,
    "@context": {**copy.deepcopy(FORMAT_CONTEXT), "orcid": "https://orcid.org/"},
    "timelines": [
        {
            "id": "clt_1",
            "unit": "quarters",
            "length": [16, 1],
            "children": [
                {"id": "clt_2", "unit": "quarters", "offset": [8, 1], "length": [4, 1]}
            ],
        },
        {"id": "dpt_1", "unit": "samples", "length": 705600},
        {"id": "cpt_1", "unit": "seconds", "length": 16.0},
    ],
}
"""The manifest without its resources, IDs bare as in memory; its ``@context``
declares the prefix ``orcid``, under which the filter cases read actors."""

PARQUET = "application/vnd.apache.parquet"

RESOURCES: list[dict[str, Any]] = [
    {
        "id": "resource_1",
        "type": "MatchClaim",
        "timelines": ["clt_1", "clt_2", "dpt_1", "cpt_1"],
        "url": "match_claims.parquet",
        "media_type": PARQUET,
    },
    {
        "id": "resource_2",
        "type": "Projection",
        "timelines": ["clt_2", "dpt_1", "cpt_1"],
        "url": "projections.parquet",
        "media_type": PARQUET,
    },
]
"""The two tables the manifest names, IDs bare; :func:`manifest` adds each
file's size and SHA-256 digest as written."""


def manifest(directory: Path = TABLE_DIR) -> dict[str, Any]:
    """The manifest naming the two tables of ``directory`` with the size and
    the SHA-256 digest of their bytes, IDs written ``#``."""
    resources = []
    for resource in RESOURCES:
        data = (directory / resource["url"]).read_bytes()
        integrity = {"algorithm": "SHA-256", "digest": hashlib.sha256(data).hexdigest()}
        resources.append({**resource, "size": len(data), "integrity": integrity})
    return with_file_ids({**MANIFEST, "resources": resources})


def quarters(numerator: int, denominator: int = 1) -> dict[str, Any]:
    value = Fraction(numerator, denominator)
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "value": None,
        "unit": "quarters",
        "number_type": "fraction",
    }


def samples(value: int) -> dict[str, Any]:
    return {
        "numerator": value,
        "denominator": None,
        "value": None,
        "unit": "samples",
        "number_type": "int",
    }


def seconds(value: float) -> dict[str, Any]:
    return {
        "numerator": None,
        "denominator": None,
        "value": value,
        "unit": "seconds",
        "number_type": "float",
    }


def _provenance(**members: Any) -> dict[str, Any]:
    entry = dict.fromkeys(
        ("stated_by", "date", "method", "service", "basis", "match", "note", "beliefs")
    )
    entry.update(members)
    return entry


def belief(actor: str, word: str, note: str | None = None) -> dict[str, Any]:
    return {"actor": actor, "belief": word, "date": LATER, "note": note}


IMPORTED = _provenance(method="imported", service=SERVICE, date=DATE)


def stated() -> dict[str, Any]:
    """A MatchClaim stated by hand by ``ACTOR``, who believes it."""
    return _provenance(
        stated_by=[ACTOR],
        date=DATE,
        method="manual",
        beliefs=[{"actor": ACTOR, "belief": "true", "date": DATE, "note": None}],
    )


def claim(
    identifier: str,
    a: tuple[str, str, str | None],
    b: tuple[str, str, str | None],
    start: tuple[dict[str, Any], dict[str, Any]] | None = None,
    end: tuple[dict[str, Any], dict[str, Any]] | None = None,
    *,
    synchronous: bool = True,
    provenance: dict[str, Any] | None = IMPORTED,
) -> dict[str, Any]:
    """One MatchClaim row; a side is ``(timeline, event ID, event name)``, the
    event ID a sentinel's string on a sentinel side."""

    def anchor(pair: tuple[dict[str, Any], dict[str, Any]] | None) -> Any:
        if pair is None:
            return None
        return {"coordinate_a": pair[0], "coordinate_b": pair[1]}

    return {
        "timeline_a_id": a[0],
        "timeline_b_id": b[0],
        "start_anchor": anchor(start),
        "end_anchor": anchor(end),
        "is_synchronous": synchronous,
        "provenance": provenance,
        "certainty": 1.0,
        "event_a_id": a[1],
        "event_a_name": a[2],
        "event_b_id": b[1],
        "event_b_name": b[2],
        "id": identifier,
    }


def note(timeline: str, number: int, name: str) -> tuple[str, str, str]:
    return (timeline, f"note_{number}", name)


def projection(timeline: str, number: int) -> tuple[str, str, None]:
    return (timeline, f"projection_{number}", None)


def onset(number: int) -> tuple[str, str, None]:
    return ("cpt_1", f"onset_{number}", None)


def chunk(timeline: str) -> tuple[str, str, None]:
    return (timeline, CHUNK_SENTINEL, None)


def nomatch(timeline: str) -> tuple[str, str, None]:
    return (timeline, NOMATCH_SENTINEL, None)


MATCH_CLAIMS: list[dict[str, Any]] = [
    claim(
        "claim_1",
        note("clt_1", 1, "C4"),
        projection("dpt_1", 1),
        (quarters(0), samples(0)),
        provenance=stated(),
    ),
    claim(
        "claim_2",
        note("clt_1", 2, "D4"),
        projection("dpt_1", 2),
        (quarters(1), samples(44100)),
        (quarters(2), samples(88200)),
    ),
    claim(
        "claim_3",
        note("clt_1", 3, "E4"),
        projection("dpt_1", 3),
        (quarters(3), samples(132300)),
    ),
    claim(
        "claim_4",
        projection("dpt_1", 4),
        note("clt_1", 4, "G4"),
        (samples(132300), quarters(3)),
    ),
    claim(
        "claim_5",
        note("clt_1", 5, "F4"),
        projection("dpt_1", 5),
        (quarters(4), samples(176400)),
    ),
    claim(
        "claim_6",
        projection("dpt_1", 5),
        onset(1),
        (samples(176400), seconds(4.0)),
        provenance={
            **IMPORTED,
            "beliefs": [belief(ACTOR, "unlikely", "the onset is blurred")],
        },
    ),
    claim(
        "claim_7",
        note("clt_1", 6, "A4"),
        onset(2),
        (quarters(5), seconds(5.0)),
    ),
    claim(
        "claim_8",
        note("clt_1", 7, "C5"),
        onset(3),
        (quarters(5), seconds(5.25)),
    ),
    claim(
        "claim_9",
        note("clt_1", 8, "B4"),
        ("cpt_1", "span_1", None),
        (quarters(6), seconds(6.0)),
        (quarters(8), seconds(8.0)),
    ),
    claim(
        "claim_10",
        note("clt_1", 9, "D5"),
        onset(4),
        (quarters(15, 2), seconds(7.5)),
    ),
    claim(
        "claim_11",
        chunk("dpt_1"),
        chunk("cpt_1"),
        (samples(441000), seconds(10.0)),
        provenance=stated(),
    ),
    claim(
        "claim_12",
        note("clt_1", 10, "E5"),
        nomatch("dpt_1"),
        synchronous=False,
    ),
    claim(
        "claim_13",
        note("clt_1", 11, "F5"),
        projection("dpt_1", 8),
        (quarters(10), samples(441000)),
        provenance={
            **IMPORTED,
            "beliefs": [
                belief(ACTOR, "false", "a grace note, played late"),
                belief(OTHER_ACTOR, "true"),
            ],
        },
    ),
    claim(
        "claim_14",
        note("clt_1", 12, "G5"),
        onset(5),
        synchronous=False,
        provenance=_provenance(
            stated_by=[OTHER_ACTOR],
            date=DATE,
            method="manual",
            note="the same gesture, not the same moment",
            beliefs=[belief(OTHER_ACTOR, "true")],
        ),
    ),
    claim(
        "claim_15",
        note("clt_2", 13, "A5"),
        projection("dpt_1", 9),
        (quarters(1), samples(396900)),
        provenance=None,
    ),
    claim(
        "claim_16",
        chunk("cpt_1"),
        note("clt_1", 2, "D4"),
        (seconds(1.0), quarters(1)),
    ),
]
"""The MatchClaim table, row by row."""


def _projection(
    number: int,
    timeline: str,
    start: dict[str, Any],
    of: tuple[str, str] | None,
    duration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A Projection row from coordinate cells: the row states their unit and
    number type once, and ``start`` and ``duration`` hold the numbers."""

    def members(cell: dict[str, Any] | None) -> dict[str, Any] | None:
        if cell is None:
            return None
        return {key: cell[key] for key in ("numerator", "denominator", "value")}

    return {
        "id": f"projection_{number}",
        "timeline_id": timeline,
        "unit": start["unit"],
        "number_type": start["number_type"],
        "start": members(start),
        "duration": members(duration),
        "projection_of": None
        if of is None
        else {"timeline_id": of[0], "event_id": of[1]},
    }


PROJECTIONS: list[dict[str, Any]] = [
    _projection(1, "dpt_1", samples(0), ("clt_1", "note_1")),
    _projection(2, "dpt_1", samples(44100), ("clt_1", "note_2"), samples(44100)),
    _projection(3, "dpt_1", samples(132300), ("clt_1", "note_3")),
    _projection(4, "dpt_1", samples(132300), ("clt_1", "note_4")),
    _projection(5, "dpt_1", samples(176400), ("clt_1", "note_5")),
    _projection(8, "dpt_1", samples(441000), ("clt_1", "note_11")),
    _projection(9, "dpt_1", samples(396900), ("clt_2", "note_13")),
    _projection(10, "clt_2", quarters(7, 2), ("dpt_1", "onset_1"), quarters(1, 2)),
    _projection(11, "cpt_1", seconds(12.5), ("clt_1", "note_16"), seconds(0.75)),
]
"""The Projections, numbered in the order listed; the table writes them
sorted stably by ``timeline_id``."""


# The expected values, written by hand. A coordinate is its timeline and its
# value as the timeline's number type writes it: a fraction as a pair, an int
# as an integer, a float as a number.


def c(timeline: str, value: Any) -> dict[str, Any]:
    return {"timeline_id": timeline, "value": value}


def a(first: dict[str, Any], second: dict[str, Any], *claims: str) -> dict[str, Any]:
    return {"coordinates": [first, second], "match_claims": list(claims)}


def s(coordinates: list[dict[str, Any]], *claims: str) -> dict[str, Any]:
    return {"coordinates": coordinates, "match_claims": list(claims)}


A_1 = a(c("clt_1", [0, 1]), c("dpt_1", 0), "claim_1")
A_CHUNK = a(c("clt_1", [1, 1]), c("cpt_1", 1.0), "claim_16")
A_2 = a(c("clt_1", [1, 1]), c("dpt_1", 44100), "claim_2")
A_3 = a(c("clt_1", [2, 1]), c("dpt_1", 88200), "claim_2")
A_4 = a(c("clt_1", [3, 1]), c("dpt_1", 132300), "claim_3", "claim_4")
A_5 = a(c("clt_1", [4, 1]), c("dpt_1", 176400), "claim_5")
A_6 = a(c("clt_1", [5, 1]), c("cpt_1", 5.0), "claim_7")
A_7 = a(c("clt_1", [5, 1]), c("cpt_1", 5.25), "claim_8")
A_8 = a(c("clt_1", [6, 1]), c("cpt_1", 6.0), "claim_9")
A_9 = a(c("clt_1", [15, 2]), c("cpt_1", 7.5), "claim_10")
A_10 = a(c("clt_1", [8, 1]), c("cpt_1", 8.0), "claim_9")
A_11 = a(c("clt_1", [10, 1]), c("dpt_1", 441000), "claim_13")
A_12 = a(c("clt_2", [1, 1]), c("dpt_1", 396900), "claim_15")
A_13 = a(c("cpt_1", 4.0), c("dpt_1", 176400), "claim_6")
A_14 = a(c("cpt_1", 10.0), c("dpt_1", 441000), "claim_11")

S_1 = s([c("clt_1", [0, 1]), c("dpt_1", 0)], "claim_1")
S_2 = s([c("clt_1", [1, 1]), c("cpt_1", 1.0), c("dpt_1", 44100)], "claim_16", "claim_2")
S_3 = s([c("clt_1", [2, 1]), c("dpt_1", 88200)], "claim_2")
S_4 = s([c("clt_1", [3, 1]), c("dpt_1", 132300)], "claim_3", "claim_4")
S_5 = s([c("clt_1", [4, 1]), c("cpt_1", 4.0), c("dpt_1", 176400)], "claim_5", "claim_6")
S_6 = s([c("clt_1", [5, 1]), c("cpt_1", 5.0), c("cpt_1", 5.25)], "claim_7", "claim_8")
S_7 = s([c("clt_1", [6, 1]), c("cpt_1", 6.0)], "claim_9")
S_8 = s([c("clt_1", [15, 2]), c("cpt_1", 7.5)], "claim_10")
S_9 = s([c("clt_1", [8, 1]), c("cpt_1", 8.0)], "claim_9")
S_10 = s(
    [c("clt_1", [10, 1]), c("cpt_1", 10.0), c("dpt_1", 441000)],
    "claim_11",
    "claim_13",
)
S_11 = s([c("clt_2", [1, 1]), c("dpt_1", 396900)], "claim_15")
S_10_WITHOUT_13 = s([c("cpt_1", 10.0), c("dpt_1", 441000)], "claim_11")
S_13_ALONE = s([c("clt_1", [10, 1]), c("dpt_1", 441000)], "claim_13")
S_5_WITHOUT_6 = s([c("clt_1", [4, 1]), c("dpt_1", 176400)], "claim_5")
S_6_ALONE = s([c("cpt_1", 4.0), c("dpt_1", 176400)], "claim_6")

EVERY_STATE_BUT_FALSE = ["true", "undecided", "unlikely"]
"""The default belief filter: every state but ``"false"``."""

EVERY_ANCHOR = [
    A_1,
    A_CHUNK,
    A_2,
    A_3,
    A_4,
    A_5,
    A_6,
    A_7,
    A_8,
    A_9,
    A_10,
    A_11,
    A_12,
    A_13,
    A_14,
]

EXPECTED: dict[str, Any] = {
    "cases": [
        {
            "believer": None,
            "beliefs": EVERY_STATE_BUT_FALSE,
            "alignment_anchors": EVERY_ANCHOR,
            "potential_matchstamps": [
                S_1,
                S_2,
                S_3,
                S_4,
                S_5,
                S_6,
                S_7,
                S_8,
                S_9,
                S_10,
                S_11,
            ],
        },
        {
            "believer": ACTOR,
            "beliefs": EVERY_STATE_BUT_FALSE,
            "alignment_anchors": [
                anchor for anchor in EVERY_ANCHOR if anchor is not A_11
            ],
            "potential_matchstamps": [
                S_1,
                S_2,
                S_3,
                S_4,
                S_5,
                S_6,
                S_7,
                S_8,
                S_9,
                S_11,
                S_10_WITHOUT_13,
            ],
        },
        {
            "believer": ACTOR,
            "beliefs": ["true"],
            "alignment_anchors": [A_1, A_14],
            "potential_matchstamps": [S_1, S_10_WITHOUT_13],
        },
        {
            "believer": OTHER_ACTOR,
            "beliefs": ["true"],
            "alignment_anchors": [A_11],
            "potential_matchstamps": [S_13_ALONE],
        },
        {
            "believer": ACTOR,
            "beliefs": ["undecided"],
            "alignment_anchors": [
                A_CHUNK,
                A_2,
                A_3,
                A_4,
                A_5,
                A_6,
                A_7,
                A_8,
                A_9,
                A_10,
                A_12,
            ],
            "potential_matchstamps": [
                S_2,
                S_3,
                S_4,
                S_5_WITHOUT_6,
                S_6,
                S_7,
                S_8,
                S_9,
                S_11,
            ],
        },
        {
            "believer": ACTOR,
            "beliefs": ["unlikely", "false"],
            "alignment_anchors": [A_11, A_13],
            "potential_matchstamps": [S_13_ALONE, S_6_ALONE],
        },
        {
            "believer": ACTOR_COMPACT,
            "beliefs": ["true"],
            "alignment_anchors": [A_1, A_14],
            "potential_matchstamps": [S_1, S_10_WITHOUT_13],
        },
    ]
}
"""Per filter case, the unique anchors (each with the MatchClaims stating it)
and the potential MatchStamps, in the derivation's sorted order. Every case
reads actors under the manifest's ``@context``: the last names ``ACTOR``
compactly, the rows absolutely, and keeps what the third keeps."""


def match_claims_table() -> pa.Table:
    return pa.Table.from_pylist(MATCH_CLAIMS, schema=MATCH_CLAIM_SCHEMA)


def projections_table() -> pa.Table:
    rows = sorted(PROJECTIONS, key=lambda row: row["timeline_id"])
    return pa.Table.from_pylist(rows, schema=PROJECTION_SCHEMA)


def _write_text(path: Path, text: str) -> None:
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.write_bytes(text.encode("utf-8"))


def _write_table(path: Path, table: pa.Table) -> None:
    if not path.is_file() or not pq.read_table(path).equals(table):
        pq.write_table(table, path)


def main() -> int:
    """Check the fixture and write every file that changed."""
    tag = f"v{SCHEMA_VERSION}"
    tagged = subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "tag", "--list", tag],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    if tag in tagged:
        raise SystemExit(f"{tag} is released; its tables in {TABLE_DIR} are frozen.")
    claims, projections = match_claims_table(), projections_table()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    _write_table(TABLE_DIR / "match_claims.parquet", claims)
    _write_table(TABLE_DIR / "projections.parquet", projections)
    named = manifest()
    validate(named)
    check_match_claims(claims, named)
    check_projections(projections, named)
    _write_text(TABLE_DIR / "manifest.yaml", dumps(named))
    _write_text(TABLE_DIR / "expected.yaml", dumps(EXPECTED))
    return 0


if __name__ == "__main__":
    sys.exit(main())
