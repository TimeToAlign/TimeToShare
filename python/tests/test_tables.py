"""The table types: their columns, their checks, the succession rule and the
fixture files (see "The table types" in README.md)."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from collections.abc import Callable
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from timetoshare import (  # noqa: E402
    BELIEFS,
    FORMAT_CONTEXT,
    dumps,
    load_schema,
    loads,
    provenance_schema_path,
    with_bare_ids,
    with_file_ids,
)
from timetoshare.tables import (  # noqa: E402
    BELIEF_KEYS,
    BELIEF_TYPE,
    CHUNK_SENTINEL,
    COORDINATE_KEYS,
    COORDINATE_TYPE,
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
    AlignmentAnchor,
    TableError,
    TableProblem,
    TimelineCoordinate,
    alignment_anchors,
    check_extractions,
    check_match_claims,
    check_projections,
    check_registry,
    check_succession,
    coordinate_value,
    extraction_problems,
    fixture_path,
    match_claim_problems,
    number_cell,
    projection_problems,
    registry_problems,
    row_provenance,
    succession_problems,
    tables_path,
)

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "emit_tables.py"
ACTOR = "https://orcid.org/0000-0002-1825-0097"


def q(numerator: int, denominator: int = 1) -> dict[str, Any]:
    """A fraction coordinate in quarters, written as given."""
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": None,
        "unit": "quarters",
        "number_type": "fraction",
    }


def smp(value: int) -> dict[str, Any]:
    """An int coordinate in samples."""
    return {
        "numerator": value,
        "denominator": None,
        "value": None,
        "unit": "samples",
        "number_type": "int",
    }


def sec(value: float) -> dict[str, Any]:
    """A float coordinate in seconds."""
    return {
        "numerator": None,
        "denominator": None,
        "value": value,
        "unit": "seconds",
        "number_type": "float",
    }


def number(cell: dict[str, Any] | None) -> dict[str, Any] | None:
    """A coordinate cell's number: the cell without its unit and number type."""
    if cell is None:
        return None
    return {key: cell[key] for key in ("numerator", "denominator", "value")}


def anchor(cell_a: dict, cell_b: dict) -> dict[str, Any]:
    """An anchor cell: a coordinate on each of the row's two timelines."""
    return {"coordinate_a": cell_a, "coordinate_b": cell_b}


PROVENANCE = {
    "stated_by": [ACTOR],
    "date": "2026-11-20",
    "method": "https://example.org/methods/listening",
    "service": None,
    "basis": ["https://example.org/score.mei"],
    "match": "exact",
    "note": None,
    "beliefs": [{"actor": ACTOR, "belief": "true", "date": "2026-11-20", "note": None}],
}


CHUNK = CHUNK_SENTINEL
NOMATCH = NOMATCH_SENTINEL


def claim(
    identifier: str,
    event_a: str,
    event_b: str,
    start: tuple[dict, dict] | None = None,
    end: tuple[dict, dict] | None = None,
    **members: Any,
) -> dict[str, Any]:
    row = {
        "timeline_a_id": "clt_1",
        "timeline_b_id": "dpt_1",
        "start_anchor": None if start is None else anchor(*start),
        "end_anchor": None if end is None else anchor(*end),
        "is_synchronous": start is not None,
        "provenance": None,
        "certainty": 1.0,
        "event_a_id": event_a,
        "event_a_name": None,
        "event_b_id": event_b,
        "event_b_name": None,
        "id": identifier,
    }
    row.update(members)
    return row


CLAIMS = [
    claim("claim_1", "note_1", "projection_1", (q(0), smp(0)), provenance=PROVENANCE),
    claim("claim_2", "note_2", "projection_2", (q(1), smp(44100)), (q(2), smp(88200))),
    claim("claim_3", "note_3", NOMATCH),
    claim("claim_4", "note_4", "projection_3"),
]
"""An instant claim, an interval claim, a NOMATCH and a conceptual claim."""


def event(
    identifier: str,
    start: dict,
    duration: dict | None = None,
    **members: Any,
) -> dict[str, Any]:
    """A registry's event row of a Projection on ``dpt_1`` from coordinate
    cells: the row states their unit and number type once."""
    row = {
        "id": identifier,
        "kind": "Projection",
        "location": "projections.parquet",
        "timeline_id": "dpt_1",
        "unit": start["unit"],
        "number_type": start["number_type"],
        "start": number(start),
        "duration": number(duration),
        "name": None,
        "extraction_id": "extraction_1",
        "locator": None,
        "vanished_in": None,
    }
    row.update(members)
    return row


def index(identifier: str, kind: str, location: str, **members: Any) -> dict:
    """A registry's index row."""
    row = {key: None for key in REGISTRY_SCHEMA.names}
    row.update(id=identifier, kind=kind, location=location, **members)
    return row


EVENTS = [
    event("projection_1", smp(0), locator="track 0, message 4"),
    event("projection_2", smp(44100), smp(44100), locator="track 0, message 9"),
    event("projection_3", smp(132300)),
]
"""An int instant, an int interval and an instant without a locator."""

REGISTRY = [
    *EVENTS,
    index("clt_1", "Timeline", "manifest.yaml"),
    index("dpt_1", "Timeline", "manifest.yaml", name="the recording"),
    index("region_1", "Region", "manifest.yaml", timeline_id="clt_1"),
    index("claim_1", "MatchClaim", "match_claims.parquet"),
    index("extraction_1", "Extraction", "extractions.parquet"),
]
"""The registry: the three event rows, then index rows of two timelines, a
region, a MatchClaim and the extraction."""


def projection(
    identifier: str, of: tuple[str | None, str | None] | None
) -> dict[str, Any]:
    """A pre-parsed Projection: its ID and the event it stands for."""
    return {
        "id": identifier,
        "projection_of": None
        if of is None
        else {"timeline_id": of[0], "event_id": of[1]},
    }


PROJECTIONS = [
    projection("projection_1", ("clt_1", "note_1")),
    projection("projection_2", ("clt_1", "note_2")),
    projection("projection_3", None),
]
"""The pre-parsed Projections of the three event rows."""

EXTRACTIONS = [
    {
        "id": "extraction_1",
        "source": "performance.mid",
        "source_integrity": {"algorithm": "SHA-256", "digest": "00ff"},
        "parser": "https://example.org/midi-parser",
        "parser_version": "2.1.0",
        "parameters": '{"merge_tracks":false,"resolution":480}',
        "minter": "1",
        "id_length": 8,
        "seed": None,
        "date": "2026-11-27T21:30:00Z",
    },
    {
        "id": "extraction_2",
        "source": None,
        "source_integrity": None,
        "parser": "https://example.org/editor",
        "parser_version": "0.9",
        "parameters": None,
        "minter": "1",
        "id_length": 8,
        "seed": "take 2",
        "date": "2026-11-27T21:31:05.250Z",
    },
]
"""A parser's run over a MIDI file, and a tool's without a source file."""

MANIFEST = with_file_ids(
    {
        "timetoshare": "0.2.0",
        "timelines": [
            {"id": "clt_1", "unit": "quarters", "length": [16, 1]},
            {"id": "dpt_1", "unit": "samples", "length": 705600},
        ],
    }
)
"""The manifest of the inline tables, as read from its file."""


def claims_table(rows: list[dict], **metadata: str) -> Any:
    table = pa.Table.from_pylist(rows, schema=MATCH_CLAIM_SCHEMA)
    return table.replace_schema_metadata(metadata or None)


def projections_table(rows: list[dict]) -> Any:
    return pa.Table.from_pylist(rows, schema=PROJECTION_SCHEMA)


def registry_table(rows: list[dict]) -> Any:
    return pa.Table.from_pylist(rows, schema=REGISTRY_SCHEMA)


def extractions_table(rows: list[dict]) -> Any:
    return pa.Table.from_pylist(rows, schema=EXTRACTION_SCHEMA)


def found(problems: list) -> list[tuple]:
    return [(problem.code, problem.row, problem.column) for problem in problems]


def changed(rows: list[dict], change: Callable[[list[dict]], None]) -> list[dict]:
    rows = copy.deepcopy(rows)
    change(rows)
    return rows


def put(*path: Any, value: Any) -> Callable[[list[dict]], None]:
    """A change setting the member at ``path`` (row index first) to ``value``."""

    def change(rows: list[dict]) -> None:
        holder: Any = rows
        for key in path[:-1]:
            holder = holder[key]
        holder[path[-1]] = value

    return change


# The columns


def test_the_match_claim_columns() -> None:
    assert MATCH_CLAIM_COLUMNS == (
        "timeline_a_id",
        "timeline_b_id",
        "start_anchor",
        "end_anchor",
        "is_synchronous",
        "provenance",
        "certainty",
        "event_a_id",
        "event_a_name",
        "event_b_id",
        "event_b_name",
        "id",
    )
    anchor_type = MATCH_CLAIM_SCHEMA.field("start_anchor").type
    assert [field.name for field in anchor_type] == ["coordinate_a", "coordinate_b"]
    assert MATCH_CLAIM_SCHEMA.field("end_anchor").type == anchor_type


def test_the_projection_columns() -> None:
    assert PROJECTION_COLUMNS == ("id", "projection_of")
    projection_of = PROJECTION_SCHEMA.field("projection_of").type
    assert [field.name for field in projection_of] == ["timeline_id", "event_id"]


def test_the_registry_and_extraction_columns() -> None:
    assert REGISTRY_COLUMNS == (
        "id",
        "kind",
        "location",
        "timeline_id",
        "unit",
        "number_type",
        "start",
        "duration",
        "name",
        "extraction_id",
        "locator",
        "vanished_in",
    )
    assert EXTRACTION_COLUMNS == (
        "id",
        "source",
        "source_integrity",
        "parser",
        "parser_version",
        "parameters",
        "minter",
        "id_length",
        "seed",
        "date",
    )
    assert INDEX_KINDS == (
        "Manifest",
        "Timeline",
        "VirtualTimeline",
        "Group",
        "MeasureMap",
        "ConversionMap",
        "Region",
        "FlowControlElement",
        "Resource",
        "FlowMap",
        "Timestamp",
        "MatchStamp",
        "AlignmentAnchor",
        "Elision",
        "MatchClaim",
        "Extraction",
    )
    # Every kind of a manifest element is the manifest schema's name of it.
    definitions = load_schema()["$defs"]
    elements = INDEX_KINDS[:-2]
    assert [kind for kind in elements if kind not in definitions] == []


_NUMBER = pa.struct(
    [("numerator", pa.int64()), ("denominator", pa.int64()), ("value", pa.float64())]
)
_COORDINATE = pa.struct([*_NUMBER, ("unit", pa.string()), ("number_type", pa.string())])
_ANCHOR = pa.struct([("coordinate_a", _COORDINATE), ("coordinate_b", _COORDINATE)])
_BELIEF = pa.struct([(key, pa.string()) for key in ("actor", "belief", "date", "note")])
_PROVENANCE = pa.struct(
    [
        ("stated_by", pa.list_(pa.string())),
        ("date", pa.string()),
        ("method", pa.string()),
        ("service", pa.string()),
        ("basis", pa.list_(pa.string())),
        ("match", pa.string()),
        ("note", pa.string()),
        ("beliefs", pa.list_(_BELIEF)),
    ]
)


def test_the_match_claim_schema_field_by_field() -> None:
    assert [
        (field.name, field.type, field.nullable) for field in MATCH_CLAIM_SCHEMA
    ] == [
        ("timeline_a_id", pa.string(), True),
        ("timeline_b_id", pa.string(), True),
        ("start_anchor", _ANCHOR, True),
        ("end_anchor", _ANCHOR, True),
        ("is_synchronous", pa.bool_(), True),
        ("provenance", _PROVENANCE, True),
        ("certainty", pa.float64(), True),
        ("event_a_id", pa.string(), True),
        ("event_a_name", pa.string(), True),
        ("event_b_id", pa.string(), True),
        ("event_b_name", pa.string(), True),
        ("id", pa.string(), True),
    ]


def test_the_projection_schema_field_by_field() -> None:
    assert [
        (field.name, field.type, field.nullable) for field in PROJECTION_SCHEMA
    ] == [
        ("id", pa.string(), True),
        (
            "projection_of",
            pa.struct([("timeline_id", pa.string()), ("event_id", pa.string())]),
            True,
        ),
    ]


def test_the_registry_and_extraction_schemas_field_by_field() -> None:
    assert [(field.name, field.type, field.nullable) for field in REGISTRY_SCHEMA] == [
        ("id", pa.string(), True),
        ("kind", pa.string(), True),
        ("location", pa.string(), True),
        ("timeline_id", pa.string(), True),
        ("unit", pa.string(), True),
        ("number_type", pa.string(), True),
        ("start", _NUMBER, True),
        ("duration", _NUMBER, True),
        ("name", pa.string(), True),
        ("extraction_id", pa.string(), True),
        ("locator", pa.string(), True),
        ("vanished_in", pa.string(), True),
    ]
    integrity = pa.struct([("algorithm", pa.string()), ("digest", pa.string())])
    assert INTEGRITY_TYPE == integrity
    assert [
        (field.name, field.type, field.nullable) for field in EXTRACTION_SCHEMA
    ] == [
        ("id", pa.string(), True),
        ("source", pa.string(), True),
        ("source_integrity", integrity, True),
        ("parser", pa.string(), True),
        ("parser_version", pa.string(), True),
        ("parameters", pa.string(), True),
        ("minter", pa.string(), True),
        ("id_length", pa.int64(), True),
        ("seed", pa.string(), True),
        ("date", pa.string(), True),
    ]


def test_the_column_types_are_published_as_data() -> None:
    assert tables_path() == SCRIPT.parents[1] / "schema" / "0.2.0" / TABLES_DOCUMENT
    assert TABLES_DOCUMENT == "tables.json"
    document = json.loads(tables_path().read_text(encoding="utf-8"))
    assert (
        document["$id"] == "https://timetoalign.github.io/timetoshare/0.2.0/tables.json"
    )
    assert sorted(document) == ["$id", "description", "tables", "types"]
    types = document["types"]
    assert sorted(types) == [
        "anchor",
        "coordinate",
        "integrity",
        "number",
        "projection_of",
        "provenance",
    ]
    members = {
        name: [(member["name"], member["type"]) for member in declared["struct"]]
        for name, declared in types.items()
        if "struct" in declared
    }
    assert members["number"] == [
        ("numerator", "int64"),
        ("denominator", "int64"),
        ("value", "float64"),
    ]
    assert members["coordinate"] == [
        *members["number"],
        ("unit", "string"),
        ("number_type", "string"),
    ]
    assert members["anchor"] == [
        ("coordinate_a", "coordinate"),
        ("coordinate_b", "coordinate"),
    ]
    assert members["projection_of"] == [
        ("timeline_id", "string"),
        ("event_id", "string"),
    ]
    assert members["integrity"] == [("algorithm", "string"), ("digest", "string")]
    assert types["provenance"]["schema"] == "provenance.schema.json"
    assert (tables_path().parent / "provenance.schema.json").is_file()
    tables = document["tables"]
    assert {name: table["status"] for name, table in tables.items()} == {
        "Registry": "experimental",
        "Extraction": "experimental",
        "Projection": "experimental",
        "MatchClaim": "stable",
    }
    assert {name: sorted(table) for name, table in tables.items()} == {
        "Registry": ["columns", "description", "index_kinds", "status"],
        "Extraction": ["columns", "description", "status"],
        "Projection": ["columns", "description", "status"],
        "MatchClaim": ["columns", "description", "status"],
    }
    assert tuple(tables["Registry"]["index_kinds"]) == INDEX_KINDS
    columns = {
        name: [(column["name"], column["type"]) for column in table["columns"]]
        for name, table in tables.items()
    }
    assert columns["MatchClaim"] == [
        ("timeline_a_id", "string"),
        ("timeline_b_id", "string"),
        ("start_anchor", "anchor"),
        ("end_anchor", "anchor"),
        ("is_synchronous", "bool"),
        ("provenance", "provenance"),
        ("certainty", "float64"),
        ("event_a_id", "string"),
        ("event_a_name", "string"),
        ("event_b_id", "string"),
        ("event_b_name", "string"),
        ("id", "string"),
    ]
    assert columns["Projection"] == [
        ("id", "string"),
        ("projection_of", "projection_of"),
    ]
    assert columns["Registry"] == [
        ("id", "string"),
        ("kind", "string"),
        ("location", "string"),
        ("timeline_id", "string"),
        ("unit", "string"),
        ("number_type", "string"),
        ("start", "number"),
        ("duration", "number"),
        ("name", "string"),
        ("extraction_id", "string"),
        ("locator", "string"),
        ("vanished_in", "string"),
    ]
    assert columns["Extraction"] == [
        ("id", "string"),
        ("source", "string"),
        ("source_integrity", "integrity"),
        ("parser", "string"),
        ("parser_version", "string"),
        ("parameters", "string"),
        ("minter", "string"),
        ("id_length", "int64"),
        ("seed", "string"),
        ("date", "string"),
    ]
    required = {
        name: [column["name"] for column in table["columns"] if not column["nullable"]]
        for name, table in tables.items()
    }
    assert required == {
        "MatchClaim": [
            "timeline_a_id",
            "timeline_b_id",
            "is_synchronous",
            "event_a_id",
            "event_b_id",
            "id",
        ],
        "Projection": ["id"],
        "Registry": ["id", "kind"],
        "Extraction": ["id", "parser", "parser_version", "minter", "id_length", "date"],
    }
    assert MATCH_CLAIM_REQUIRED == (
        "timeline_a_id",
        "timeline_b_id",
        "is_synchronous",
        "event_a_id",
        "event_b_id",
        "id",
    )
    assert PROJECTION_REQUIRED == ("id",)
    assert REGISTRY_REQUIRED == ("id", "kind")
    assert REGISTRY_EVENT_REQUIRED == (
        "timeline_id",
        "unit",
        "number_type",
        "start",
        "extraction_id",
    )
    assert EXTRACTION_REQUIRED == (
        "id",
        "parser",
        "parser_version",
        "minter",
        "id_length",
        "date",
    )
    named = {
        *(member["type"] for t in types.values() for member in t.get("struct", ())),
        *(column["type"] for table in tables.values() for column in table["columns"]),
    }
    assert sorted(named - set(types)) == ["bool", "float64", "int64", "string"]
    assert [
        pa.type_for_alias(name) for name in ("string", "bool", "int64", "float64")
    ] == [
        pa.string(),
        pa.bool_(),
        pa.int64(),
        pa.float64(),
    ]


def test_a_number_and_a_coordinate_cell() -> None:
    assert NUMBER_KEYS == ("numerator", "denominator", "value")
    assert dict(NUMBER_MEMBERS) == {
        "int": ("numerator",),
        "fraction": ("numerator", "denominator"),
        "float": ("value",),
    }
    assert [(field.name, str(field.type)) for field in NUMBER_TYPE] == [
        ("numerator", "int64"),
        ("denominator", "int64"),
        ("value", "double"),
    ]
    assert REGISTRY_SCHEMA.field("start").type == NUMBER_TYPE
    assert REGISTRY_SCHEMA.field("duration").type == NUMBER_TYPE
    assert str(REGISTRY_SCHEMA.field("unit").type) == "string"
    assert str(REGISTRY_SCHEMA.field("number_type").type) == "string"
    assert COORDINATE_KEYS == (
        "numerator",
        "denominator",
        "value",
        "unit",
        "number_type",
    )
    assert [(field.name, str(field.type)) for field in COORDINATE_TYPE] == [
        ("numerator", "int64"),
        ("denominator", "int64"),
        ("value", "double"),
        ("unit", "string"),
        ("number_type", "string"),
    ]
    anchor_type = MATCH_CLAIM_SCHEMA.field("start_anchor").type
    assert [field.type for field in anchor_type] == [COORDINATE_TYPE, COORDINATE_TYPE]


@pytest.mark.parametrize(
    ("value", "number_type", "members"),
    [
        (3, "int", (3, None, None)),
        (Fraction(4, 2), "int", (2, None, None)),
        (Fraction(3, 6), "fraction", (1, 2, None)),
        (2, "fraction", (2, 1, None)),
        (0.25, "float", (None, None, 0.25)),
        (2, "float", (None, None, 2.0)),
    ],
)
def test_a_number_holds_its_number_types_members_alone(
    value: Any, number_type: str, members: tuple
) -> None:
    cell = number_cell(value, number_type)
    assert cell == dict(zip(NUMBER_KEYS, members, strict=True))
    assert type(cell["value"]) is (float if number_type == "float" else type(None))
    assert coordinate_value(cell, number_type) == Fraction(value)


@pytest.mark.parametrize(
    ("value", "number_type", "message"),
    [
        (0.5, "int", "an int number is exact, not 0.5"),
        (0.5, "fraction", "a fraction number is exact, not 0.5"),
        (Fraction(1, 2), "int", "an int number is an integer, not Fraction(1, 2)"),
        (True, "int", "an int number is exact, not True"),
        (
            Fraction(1, 2),
            "float",
            "a float number is a finite float, not Fraction(1, 2)",
        ),
        (float("nan"), "float", "a float number is a finite float, not nan"),
        (
            2**53 + 1,
            "float",
            "a float number is a finite float, not 9007199254740993",
        ),
        (2**1024, "float", f"a float number is a finite float, not {2**1024}"),
        (
            2**70,
            "int",
            "an int number is written in 64-bit integers, not 1180591620717411303424",
        ),
        (
            Fraction(1, 2**64),
            "fraction",
            "a fraction number is written in 64-bit integers, "
            "not Fraction(1, 18446744073709551616)",
        ),
        (1, "decimal", "'decimal' is no number type"),
    ],
)
def test_a_number_of_another_type_is_refused(
    value: Any, number_type: str, message: str
) -> None:
    with pytest.raises(ValueError) as raised:
        number_cell(value, number_type)
    assert str(raised.value) == message


def test_the_provenance_and_belief_keys() -> None:
    assert PROVENANCE_KEYS == (
        "stated_by",
        "date",
        "method",
        "service",
        "basis",
        "match",
        "note",
        "beliefs",
    )
    assert BELIEF_KEYS == ("actor", "belief", "date", "note")
    assert BELIEFS == ("true", "false", "unlikely")
    schema = json.loads(provenance_schema_path().read_text(encoding="utf-8"))
    assert tuple(schema["properties"]) == PROVENANCE_KEYS
    assert tuple(schema["$defs"]["Belief"]["properties"]) == BELIEF_KEYS
    assert schema["$defs"]["Belief"]["properties"]["belief"]["enum"] == list(BELIEFS)
    assert MATCH_CLAIM_SCHEMA.field("provenance").type == PROVENANCE_TYPE
    assert [(field.name, str(field.type)) for field in BELIEF_TYPE] == [
        ("actor", "string"),
        ("belief", "string"),
        ("date", "string"),
        ("note", "string"),
    ]
    assert [(field.name, str(field.type)) for field in PROVENANCE_TYPE] == [
        ("stated_by", "list<item: string>"),
        ("date", "string"),
        ("method", "string"),
        ("service", "string"),
        ("basis", "list<item: string>"),
        ("match", "string"),
        ("note", "string"),
        ("beliefs", f"list<item: {BELIEF_TYPE}>"),
    ]


@pytest.mark.parametrize(
    ("cell", "value"),
    [
        (q(15, 2), Fraction(15, 2)),
        (q(2, 6), Fraction(1, 3)),
        (smp(441000), Fraction(441000)),
        (sec(0.1), Fraction(3602879701896397, 36028797018963968)),
    ],
)
def test_a_coordinate_value_is_read_from_its_number_type(
    cell: dict, value: Fraction
) -> None:
    assert coordinate_value(cell) == value
    assert coordinate_value(number(cell), cell["number_type"]) == value


# The MatchClaim table


def test_the_valid_table_has_no_problem_with_or_without_its_manifest() -> None:
    table = claims_table(CLAIMS)
    assert match_claim_problems(table) == []
    assert match_claim_problems(table, MANIFEST) == []
    check_match_claims(table, MANIFEST)


def test_a_parquet_round_trip_changes_nothing(tmp_path: Path) -> None:
    path = tmp_path / "match_claims.parquet"
    pq.write_table(claims_table(CLAIMS), path)
    read = pq.read_table(path)
    assert match_claim_problems(read, MANIFEST) == []
    assert read.to_pylist() == CLAIMS


def test_a_column_the_type_does_not_declare_is_kept() -> None:
    table = claims_table(CLAIMS).append_column(
        "comment", pa.array(["x", None, None, None])
    )
    assert match_claim_problems(table, MANIFEST) == []


def test_a_missing_column() -> None:
    table = claims_table(CLAIMS).drop_columns(["certainty"])
    assert found(match_claim_problems(table)) == [
        ("schema_violation", None, ("certainty",))
    ]
    with pytest.raises(TableError, match="^the table has no column 'certainty'$"):
        check_match_claims(table)


def test_a_column_of_another_type() -> None:
    table = claims_table(CLAIMS)
    index = table.column_names.index("is_synchronous")
    table = table.set_column(index, "is_synchronous", pa.array(["yes"] * 4))
    with pytest.raises(TableError) as error:
        check_match_claims(table)
    assert error.value.problem.code == "schema_violation"
    assert error.value.problem.column == ("is_synchronous",)
    assert str(error.value) == "the column 'is_synchronous' is string, not bool"


def test_an_anchor_cell_holding_its_timelines_is_another_type() -> None:
    held = pa.struct(
        [
            pa.field("timeline_a_id", pa.string()),
            pa.field("coordinate_a", COORDINATE_TYPE),
            pa.field("timeline_b_id", pa.string()),
            pa.field("coordinate_b", COORDINATE_TYPE),
        ]
    )
    rows = [
        None
        if row["start_anchor"] is None
        else {"timeline_a_id": "clt_1", "timeline_b_id": "dpt_1", **row["start_anchor"]}
        for row in CLAIMS
    ]
    table = claims_table(CLAIMS)
    index = table.column_names.index("start_anchor")
    table = table.set_column(index, "start_anchor", pa.array(rows, type=held))
    assert found(match_claim_problems(table)) == [
        ("schema_violation", None, ("start_anchor",))
    ]
    with pytest.raises(TableError) as error:
        check_match_claims(table)
    assert str(error.value) == (
        f"the column 'start_anchor' is {held}, "
        f"not {MATCH_CLAIM_SCHEMA.field('start_anchor').type}"
    )


CLAIM_CASES = [
    (
        "id_null",
        put(1, "id", value=None),
        [("schema_violation", 1, ("id",))],
        "'id' is null",
    ),
    (
        "flag_null",
        put(0, "is_synchronous", value=None),
        [("schema_violation", 0, ("is_synchronous",))],
        "'is_synchronous' is null",
    ),
    (
        "id_empty",
        put(0, "id", value=""),
        [("invalid_id", 0, ("id",))],
        "the ID is empty",
    ),
    (
        "id_control",
        put(0, "id", value="claim\x01"),
        [("invalid_id", 0, ("id",))],
        "the ID 'claim\\x01' holds a control character",
    ),
    (
        "id_twice",
        put(1, "id", value="claim_1"),
        [("duplicate_id", 1, ("id",))],
        "the ID 'claim_1' is given twice",
    ),
    (
        "id_nomatch_sentinel",
        put(1, "id", value=NOMATCH),
        [("invalid_id", 1, ("id",))],
        "'NOMATCH_SENTINEL' is reserved for a sentinel",
    ),
    (
        "id_chunk_sentinel",
        put(0, "id", value=CHUNK),
        [("invalid_id", 0, ("id",))],
        "'CHUNK_SENTINEL' is reserved for a sentinel",
    ),
    (
        "event_id_null",
        put(2, "event_b_id", value=None),
        [("schema_violation", 2, ("event_b_id",))],
        "'event_b_id' is null",
    ),
    (
        "event_ids_null",
        lambda rows: rows[3].update(event_a_id=None, event_b_id=None),
        [
            ("schema_violation", 3, ("event_a_id",)),
            ("schema_violation", 3, ("event_b_id",)),
        ],
        "'event_a_id' is null",
    ),
    (
        "unit_unknown",
        put(0, "start_anchor", "coordinate_a", "unit", value="parsecs"),
        [("invalid_coordinate", 0, ("start_anchor", "coordinate_a"))],
        "'parsecs' is no unit",
    ),
    (
        "number_type_unknown",
        put(0, "start_anchor", "coordinate_b", "number_type", value="decimal"),
        [("invalid_coordinate", 0, ("start_anchor", "coordinate_b"))],
        "'decimal' is no number type",
    ),
    (
        "discrete_unit_float",
        put(0, "start_anchor", "coordinate_b", value={**sec(0.0), "unit": "samples"}),
        [("invalid_coordinate", 0, ("start_anchor", "coordinate_b"))],
        "'samples' admits no number type 'float'",
    ),
    (
        "continuous_unit_int",
        put(1, "end_anchor", "coordinate_a", value={**smp(2), "unit": "quarters"}),
        [("invalid_coordinate", 1, ("end_anchor", "coordinate_a"))],
        "'quarters' admits no number type 'int'",
    ),
    (
        "numerator_missing",
        put(1, "end_anchor", "coordinate_a", "numerator", value=None),
        [("invalid_coordinate", 1, ("end_anchor", "coordinate_a"))],
        "a fraction coordinate has no numerator",
    ),
    (
        "denominator_missing",
        put(1, "start_anchor", "coordinate_a", "denominator", value=None),
        [("invalid_coordinate", 1, ("start_anchor", "coordinate_a"))],
        "a fraction coordinate has no denominator",
    ),
    (
        "value_missing",
        put(0, "start_anchor", "coordinate_b", value={**sec(0.0), "value": None}),
        [("invalid_coordinate", 0, ("start_anchor", "coordinate_b"))],
        "a float coordinate has no value",
    ),
    (
        "denominator_zero",
        put(1, "start_anchor", "coordinate_a", "denominator", value=0),
        [("invalid_coordinate", 1, ("start_anchor", "coordinate_a"))],
        "the coordinate's denominator 0 is below 1",
    ),
    (
        "cell_unit_null",
        put(0, "start_anchor", "coordinate_a", "unit", value=None),
        [("invalid_coordinate", 0, ("start_anchor", "coordinate_a"))],
        "the coordinate has no unit",
    ),
    (
        "cell_number_type_null",
        put(0, "start_anchor", "coordinate_b", "number_type", value=None),
        [("invalid_coordinate", 0, ("start_anchor", "coordinate_b"))],
        "the coordinate has no number_type",
    ),
    (
        "int_denominator",
        put(1, "start_anchor", "coordinate_b", "denominator", value=1),
        [("invalid_coordinate", 1, ("start_anchor", "coordinate_b"))],
        "an int coordinate holds its numerator alone, not a denominator",
    ),
    (
        "int_mirror",
        put(1, "start_anchor", "coordinate_b", "value", value=44100.0),
        [("invalid_coordinate", 1, ("start_anchor", "coordinate_b"))],
        "an int coordinate holds its numerator alone, not a value",
    ),
    (
        "fraction_mirror",
        put(0, "start_anchor", "coordinate_a", "value", value=0.0),
        [("invalid_coordinate", 0, ("start_anchor", "coordinate_a"))],
        "a fraction coordinate holds its numerator and denominator alone, not a value",
    ),
    (
        "float_mirror",
        put(0, "start_anchor", "coordinate_b", value={**sec(0.5), "numerator": 1}),
        [("invalid_coordinate", 0, ("start_anchor", "coordinate_b"))],
        "a float coordinate holds its value alone, not a numerator",
    ),
    (
        "not_finite",
        put(0, "start_anchor", "coordinate_b", value=sec(float("inf"))),
        [("invalid_coordinate", 0, ("start_anchor", "coordinate_b"))],
        "the coordinate's value inf is not finite",
    ),
    (
        "same_timeline",
        put(3, "timeline_b_id", value="clt_1"),
        [("claim_timelines", 3, ("timeline_b_id",))],
        "both sides are 'clt_1'",
    ),
    (
        "chunk_not_synchronous",
        put(3, "event_a_id", value=CHUNK),
        [("claim_events", 3, ("event_a_id",))],
        "CHUNK_SENTINEL stands only on a synchronous MatchClaim",
    ),
    (
        "chunk_both_not_synchronous",
        lambda rows: rows[3].update(event_a_id=CHUNK, event_b_id=CHUNK),
        [("claim_events", 3, ("event_a_id",)), ("claim_events", 3, ("event_b_id",))],
        "CHUNK_SENTINEL stands only on a synchronous MatchClaim",
    ),
    (
        "chunk_beside_nomatch",
        put(2, "event_a_id", value=CHUNK),
        [("claim_events", 2, ("event_a_id",))],
        "CHUNK_SENTINEL stands only on a synchronous MatchClaim",
    ),
    (
        "nomatch_synchronous",
        put(2, "is_synchronous", value=True),
        [("claim_events", 2, ("event_b_id",)), ("claim_anchors", 2, ("start_anchor",))],
        "NOMATCH_SENTINEL stands only on a MatchClaim that is not synchronous",
    ),
    (
        "nomatch_synchronous_anchored",
        put(0, "event_a_id", value=NOMATCH),
        [("claim_events", 0, ("event_a_id",))],
        "NOMATCH_SENTINEL stands only on a MatchClaim that is not synchronous",
    ),
    (
        "nomatch_both",
        put(2, "event_a_id", value=NOMATCH),
        [("claim_events", 2, ("event_b_id",))],
        "a NOMATCH MatchClaim names an event on its other side",
    ),
    (
        "nomatch_both_synchronous",
        lambda rows: rows[0].update(event_a_id=NOMATCH, event_b_id=NOMATCH),
        [
            ("claim_events", 0, ("event_a_id",)),
            ("claim_events", 0, ("event_b_id",)),
            ("claim_events", 0, ("event_b_id",)),
        ],
        "NOMATCH_SENTINEL stands only on a MatchClaim that is not synchronous",
    ),
    (
        "nomatch_side_named",
        put(2, "event_b_name", value="E4"),
        [("claim_events", 2, ("event_b_name",))],
        "a NOMATCH side has no name",
    ),
    (
        "nomatch_a_named",
        lambda rows: rows[2].update(
            event_a_id=NOMATCH, event_a_name="", event_b_id="projection_3"
        ),
        [("claim_events", 2, ("event_a_name",))],
        "a NOMATCH side has no name",
    ),
    (
        "nomatch_anchor",
        put(2, "start_anchor", value=anchor(q(3), smp(132300))),
        [("claim_anchors", 2, ("start_anchor",))],
        "a NOMATCH MatchClaim has no anchors",
    ),
    (
        "nomatch_end_anchor",
        lambda rows: rows[2].update(
            event_a_id=NOMATCH,
            event_b_id="projection_3",
            end_anchor=rows[1]["end_anchor"],
        ),
        [("claim_anchors", 2, ("end_anchor",)), ("claim_anchors", 2, ("end_anchor",))],
        "a NOMATCH MatchClaim has no anchors",
    ),
    (
        "conceptual_anchor",
        put(3, "end_anchor", value=anchor(q(3), smp(132300))),
        [("claim_anchors", 3, ("end_anchor",)), ("claim_anchors", 3, ("end_anchor",))],
        "a conceptual MatchClaim has no anchors",
    ),
    (
        "synchronous_without_start",
        put(0, "start_anchor", value=None),
        [("claim_anchors", 0, ("start_anchor",))],
        "a synchronous MatchClaim has a start anchor",
    ),
    (
        "chunk_without_start",
        lambda rows: rows[0].update(event_b_id=CHUNK, start_anchor=None),
        [("claim_anchors", 0, ("start_anchor",))],
        "a synchronous MatchClaim has a start anchor",
    ),
    (
        "chunk_chunk_without_start",
        lambda rows: rows[0].update(
            event_a_id=CHUNK, event_b_id=CHUNK, start_anchor=None
        ),
        [("claim_anchors", 0, ("start_anchor",))],
        "a synchronous MatchClaim has a start anchor",
    ),
    (
        "end_without_start",
        put(1, "start_anchor", value=None),
        [
            ("claim_anchors", 1, ("start_anchor",)),
            ("claim_anchors", 1, ("end_anchor",)),
        ],
        "a synchronous MatchClaim has a start anchor",
    ),
    (
        "chunk_end_without_start",
        lambda rows: rows[1].update(event_a_id=CHUNK, start_anchor=None),
        [
            ("claim_anchors", 1, ("start_anchor",)),
            ("claim_anchors", 1, ("end_anchor",)),
        ],
        "a synchronous MatchClaim has a start anchor",
    ),
    (
        "certainty",
        put(1, "certainty", value=1.5),
        [("invalid_certainty", 1, ("certainty",))],
        "the certainty 1.5 lies outside [0, 1]",
    ),
    (
        "two_axes",
        put(1, "end_anchor", "coordinate_b", value=sec(2.0)),
        [("axis_mismatch", 1, ("end_anchor", "coordinate_b"))],
        "the timeline 'dpt_1' has coordinates in samples (int) and in seconds (float)",
    ),
]


def _provenance_case(name: str, path: tuple, value: Any, message: str) -> tuple:
    return (
        f"provenance_{name}",
        put(0, "provenance", *path, value=value),
        [("invalid_provenance", 0, ("provenance",))],
        message,
    )


PROVENANCE_CASES = [
    _provenance_case(
        "stated_by_empty",
        ("stated_by",),
        [],
        "the provenance #/stated_by: [] should be non-empty",
    ),
    _provenance_case(
        "basis_twice",
        ("basis",),
        ["https://example.org/a", "https://example.org/a"],
        "the provenance #/basis: ['https://example.org/a', 'https://example.org/a'] "
        "has non-unique elements",
    ),
    _provenance_case(
        "date",
        ("date",),
        "20.11.2026",
        "the provenance #/date: '20.11.2026' does not match "
        "'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'",
    ),
    _provenance_case(
        "date_impossible",
        ("date",),
        "2026-02-30",
        "the provenance #/date: '2026-02-30' is no Gregorian calendar date "
        "written YYYY-MM-DD",
    ),
    _provenance_case(
        "method",
        ("method",),
        "by ear",
        "the provenance #/method: 'by ear' is not one of "
        "['manual', 'reconciled', 'imported', 'inferred']",
    ),
    _provenance_case(
        "match",
        ("match",),
        "same",
        "the provenance #/match: 'same' is not one of "
        "['exact', 'close', 'broad', 'narrow', 'related']",
    ),
    _provenance_case(
        "belief_word",
        ("beliefs", 0, "belief"),
        "maybe",
        "the provenance #/beliefs/0/belief: 'maybe' is not one of "
        "['true', 'false', 'unlikely']",
    ),
    _provenance_case(
        "belief_date",
        ("beliefs", 0, "date"),
        None,
        "the provenance #/beliefs/0: 'date' is a required property",
    ),
    _provenance_case(
        "belief_date_impossible",
        ("beliefs", 0, "date"),
        "2026-02-30",
        "the provenance #/beliefs/0/date: '2026-02-30' is no Gregorian calendar "
        "date written YYYY-MM-DD",
    ),
    _provenance_case(
        "belief_actor",
        ("beliefs", 0, "actor"),
        None,
        "the provenance #/beliefs/0: 'actor' is a required property",
    ),
    _provenance_case(
        "two_beliefs",
        ("beliefs",),
        [
            {"actor": ACTOR, "belief": "true", "date": "2026-11-20", "note": None},
            {"actor": ACTOR, "belief": "false", "date": "2026-11-21", "note": None},
        ],
        f"the provenance #/beliefs/1/actor: '{ACTOR}' already holds belief 0 of "
        "this entry; an actor holds one belief",
    ),
]


ADMITTED_CASES = [
    ("chunk_a_instant", put(0, "event_a_id", value=CHUNK)),
    ("chunk_b_instant", put(0, "event_b_id", value=CHUNK)),
    (
        "chunk_both_instant",
        lambda rows: rows[0].update(
            event_a_id=CHUNK, event_a_name=None, event_b_id=CHUNK
        ),
    ),
    ("chunk_a_interval", put(1, "event_a_id", value=CHUNK)),
    ("chunk_b_interval", put(1, "event_b_id", value=CHUNK)),
    (
        "chunk_both_interval",
        lambda rows: rows[1].update(event_a_id=CHUNK, event_b_id=CHUNK),
    ),
    (
        "chunk_a_named",
        lambda rows: rows[0].update(event_a_id=CHUNK, event_a_name="downbeat 3"),
    ),
    (
        "chunk_both_named_interval",
        lambda rows: rows[1].update(
            event_a_id=CHUNK, event_a_name="", event_b_id=CHUNK, event_b_name="bar 2"
        ),
    ),
    (
        "nomatch_a",
        lambda rows: rows[2].update(event_a_id=NOMATCH, event_b_id="projection_3"),
    ),
]
"""Rows the format admits, each one change of the inline table: CHUNK on
either side and on both of a synchronous instant and interval, a CHUNK side
with a name (the empty name too), and a NOMATCH on side A (the inline
table's NOMATCH stands on side B)."""


def test_the_sentinels() -> None:
    assert NOMATCH_SENTINEL == "NOMATCH_SENTINEL"
    assert CHUNK_SENTINEL == "CHUNK_SENTINEL"


@pytest.mark.parametrize(
    "change", [case[1] for case in ADMITTED_CASES], ids=[c[0] for c in ADMITTED_CASES]
)
@pytest.mark.parametrize("manifest", [None, MANIFEST], ids=["alone", "manifest"])
def test_each_admitted_row(change: Callable[[list[dict]], None], manifest: Any) -> None:
    table = claims_table(changed(CLAIMS, change))
    assert match_claim_problems(table, manifest) == []
    check_match_claims(table, manifest)


@pytest.mark.parametrize(
    ("change", "expected", "message"),
    [case[1:] for case in CLAIM_CASES + PROVENANCE_CASES],
    ids=[case[0] for case in CLAIM_CASES + PROVENANCE_CASES],
)
def test_each_claim_rule(
    change: Callable[[list[dict]], None], expected: list[tuple], message: str
) -> None:
    table = claims_table(changed(CLAIMS, change))
    assert found(match_claim_problems(table)) == expected
    with pytest.raises(TableError) as error:
        check_match_claims(table)
    assert str(error.value) == message


def _every_cell_of(
    rows: list[dict], timeline: str, cell: Callable[[dict], dict]
) -> None:
    for row in rows:
        for key in ("start_anchor", "end_anchor"):
            value = row[key]
            if value is not None:
                for side in ("a", "b"):
                    if row[f"timeline_{side}_id"] == timeline:
                        value[f"coordinate_{side}"] = cell(value[f"coordinate_{side}"])


@pytest.mark.parametrize(
    ("cell", "value"),
    [(q(2, 2), Fraction(1)), (q(0, 4), Fraction(0))],
    ids=["unreduced", "unreduced_zero"],
)
def test_an_unreduced_fraction_is_read_as_its_value(
    cell: dict, value: Fraction
) -> None:
    table = claims_table(
        changed(CLAIMS, put(1, "start_anchor", "coordinate_a", value=cell))
    )
    assert match_claim_problems(table) == []
    assert match_claim_problems(table, MANIFEST) == []
    check_match_claims(table, MANIFEST)
    read = table.column("start_anchor")[1].as_py()["coordinate_a"]
    assert coordinate_value(read) == value


def test_an_unreduced_anchor_is_the_reduced_one() -> None:
    reduced = claims_table(CLAIMS)
    unreduced = claims_table(
        changed(CLAIMS, put(1, "start_anchor", "coordinate_a", value=q(2, 2)))
    )
    anchors = alignment_anchors(unreduced)
    assert anchors == alignment_anchors(reduced)
    assert anchors[
        AlignmentAnchor(
            (
                TimelineCoordinate("clt_1", Fraction(1)),
                TimelineCoordinate("dpt_1", Fraction(44100)),
            )
        )
    ] == ("claim_2",)


def test_seconds_on_a_samples_timeline_are_refused_only_against_the_manifest() -> None:
    table = claims_table(
        changed(
            CLAIMS,
            lambda rows: _every_cell_of(
                rows, "dpt_1", lambda c: sec(c["numerator"] / 44100)
            ),
        )
    )
    assert match_claim_problems(table) == []
    assert found(match_claim_problems(table, MANIFEST)) == [
        ("axis_mismatch", 0, ("start_anchor", "coordinate_b")),
        ("axis_mismatch", 1, ("start_anchor", "coordinate_b")),
        ("axis_mismatch", 1, ("end_anchor", "coordinate_b")),
    ]
    with pytest.raises(TableError) as error:
        check_match_claims(table, MANIFEST)
    assert str(error.value) == (
        "a coordinate in seconds (float) on the timeline 'dpt_1' in samples (int)"
    )


def test_a_float_on_a_fraction_axis_is_refused_only_against_the_manifest() -> None:
    table = claims_table(
        changed(
            CLAIMS,
            lambda rows: _every_cell_of(
                rows,
                "clt_1",
                lambda c: {
                    **sec(c["numerator"] / c["denominator"]),
                    "unit": "quarters",
                },
            ),
        )
    )
    assert match_claim_problems(table) == []
    assert found(match_claim_problems(table, MANIFEST)) == [
        ("axis_mismatch", 0, ("start_anchor", "coordinate_a")),
        ("axis_mismatch", 1, ("start_anchor", "coordinate_a")),
        ("axis_mismatch", 1, ("end_anchor", "coordinate_a")),
    ]


COMPACT_ACTOR = "orcid:0000-0002-1825-0097"
"""``ACTOR`` as a compact IRI under ``CONTEXT_MANIFEST``'s ``@context``."""

CONTEXT_MANIFEST = {
    **MANIFEST,
    "@context": {**FORMAT_CONTEXT, "orcid": "https://orcid.org/"},
}
"""``MANIFEST`` with a context declaring the prefix ``orcid``."""

TWO_SPELLINGS = [
    {"actor": COMPACT_ACTOR, "belief": "true", "date": "2026-11-20", "note": None},
    {"actor": ACTOR, "belief": "false", "date": "2026-11-21", "note": None},
]
"""Two beliefs of one actor, written compactly and absolutely."""


def test_one_actor_under_two_spellings_is_refused_against_the_manifest() -> None:
    table = claims_table(
        changed(CLAIMS, put(0, "provenance", "beliefs", value=TWO_SPELLINGS))
    )
    assert match_claim_problems(table) == []
    assert match_claim_problems(table, MANIFEST) == []
    assert found(match_claim_problems(table, CONTEXT_MANIFEST)) == [
        ("invalid_provenance", 0, ("provenance",))
    ]
    with pytest.raises(TableError) as error:
        check_match_claims(table, CONTEXT_MANIFEST)
    assert str(error.value) == (
        f"the provenance #/beliefs/1/actor: '{ACTOR}' already holds belief 0 of "
        "this entry; an actor holds one belief"
    )
    rows = changed(CLAIMS, put(0, "provenance", value=None))
    shared = json.dumps(
        {
            "beliefs": [
                {"actor": b["actor"], "belief": b["belief"], "date": b["date"]}
                for b in TWO_SPELLINGS
            ]
        }
    )
    table = claims_table(rows, **{PROVENANCE_METADATA_KEY: shared})
    assert match_claim_problems(table) == []
    assert found(match_claim_problems(table, CONTEXT_MANIFEST)) == [
        ("invalid_provenance", None, ("provenance",))
    ]
    with pytest.raises(TableError) as error:
        check_match_claims(table, CONTEXT_MANIFEST)
    assert str(error.value) == (
        f"the file's provenance #/beliefs/1/actor: '{ACTOR}' already holds belief "
        "0 of this entry; an actor holds one belief"
    )


def test_a_number_type_the_unit_does_not_admit_needs_no_manifest() -> None:
    claims = claims_table(
        changed(
            CLAIMS,
            put(
                0, "start_anchor", "coordinate_b", value={**sec(0.0), "unit": "samples"}
            ),
        )
    )
    expected = [
        TableProblem(
            "invalid_coordinate",
            0,
            ("start_anchor", "coordinate_b"),
            "'samples' admits no number type 'float'",
        )
    ]
    assert match_claim_problems(claims) == expected
    assert match_claim_problems(claims, MANIFEST) == expected
    registry = registry_table(
        changed(
            REGISTRY,
            lambda rows: rows[0].update(number_type="float", start=number(sec(0.0))),
        )
    )
    expected = [
        TableProblem(
            "invalid_coordinate",
            0,
            ("number_type",),
            "'samples' admits no number type 'float'",
        )
    ]
    assert registry_problems(registry) == expected
    assert registry_problems(registry, MANIFEST) == expected


def test_an_unknown_timeline_is_refused_only_against_the_manifest() -> None:
    table = claims_table(changed(CLAIMS, put(3, "timeline_b_id", value="dpt_9")))
    assert match_claim_problems(table) == []
    assert found(match_claim_problems(table, MANIFEST)) == [
        ("unknown_timeline", 3, ("timeline_b_id",))
    ]
    with pytest.raises(TableError, match="^the manifest has no timeline 'dpt_9'$"):
        check_match_claims(table, MANIFEST)


def test_a_virtual_timeline_of_the_manifest_is_known() -> None:
    virtual = {
        "id": "virtual_1",
        "map": "flow_map_1",
        "timeline": "dpt_1",
        "unit": "samples",
        "number_type": "int",
        "length": 705600,
    }
    manifest = with_file_ids(with_bare_ids(MANIFEST) | {"virtual_timelines": [virtual]})
    table = claims_table(changed(CLAIMS, put(1, "timeline_b_id", value="virtual_1")))
    assert match_claim_problems(table, manifest) == []
    assert found(match_claim_problems(table, MANIFEST)) == [
        ("unknown_timeline", 1, ("timeline_b_id",))
    ]


SHARED = {
    PROVENANCE_METADATA_KEY: json.dumps({"method": "imported", "date": "2026-11-20"})
}


def test_a_provenance_shared_by_every_row_is_stated_once() -> None:
    rows = changed(CLAIMS, put(0, "provenance", value=None))
    table = claims_table(rows, **SHARED)
    assert match_claim_problems(table, MANIFEST) == []
    shared = dict.fromkeys(PROVENANCE_KEYS) | {
        "method": "imported",
        "date": "2026-11-20",
    }
    assert row_provenance(table) == [shared] * 4


def test_a_provenance_stated_in_the_file_and_in_a_row() -> None:
    table = claims_table(CLAIMS, **SHARED)
    assert found(match_claim_problems(table)) == [
        ("invalid_provenance", 0, ("provenance",))
    ]
    with pytest.raises(TableError) as error:
        check_match_claims(table)
    assert str(error.value) == (
        "the provenance is stated in the file's metadata and in the row"
    )


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("{", "the file's provenance is no JSON text"),
        ("[]", "the file's provenance is no object"),
        (
            '{"status": "confirmed"}',
            "the file's provenance #: 'status' is no key of a provenance entry",
        ),
        (
            '{"beliefs": [{"actor": "https://example.org/a", "belief": "true", '
            '"date": "2026-11-20", "weight": 1}]}',
            "the file's provenance #/beliefs/0: 'weight' is no key of a belief",
        ),
        (
            '{"match": "same"}',
            "the file's provenance #/match: 'same' is not one of "
            "['exact', 'close', 'broad', 'narrow', 'related']",
        ),
        (
            '{"beliefs": "x"}',
            "the file's provenance #/beliefs: 'x' is not of type 'array'",
        ),
        ('{"date": 5}', "the file's provenance #/date: 5 is not of type 'string'"),
        (
            '{"stated_by": 5}',
            "the file's provenance #/stated_by: 5 is not of type 'array'",
        ),
        (
            '{"date": "2026-02-30"}',
            "the file's provenance #/date: '2026-02-30' is no Gregorian calendar date "
            "written YYYY-MM-DD",
        ),
    ],
)
def test_a_malformed_shared_provenance(text: str, message: str) -> None:
    rows = changed(CLAIMS, put(0, "provenance", value=None))
    table = claims_table(rows, **{PROVENANCE_METADATA_KEY: text})
    assert found(match_claim_problems(table)) == [
        ("invalid_provenance", None, ("provenance",))
    ]
    with pytest.raises(TableError) as error:
        check_match_claims(table)
    assert str(error.value) == message


# Further columns


def with_scope(rows: list[dict], values: list[Any], data_type: Any = None) -> Any:
    """A MatchClaim table with a further column ``scope``, which the type
    does not declare."""
    return claims_table(rows).append_column("scope", pa.array(values, data_type))


def test_an_id_twice_is_a_duplicate() -> None:
    table = claims_table(changed(CLAIMS, put(1, "id", value="claim_1")))
    assert found(match_claim_problems(table)) == [("duplicate_id", 1, ("id",))]
    with pytest.raises(TableError) as error:
        check_match_claims(table)
    assert str(error.value) == "the ID 'claim_1' is given twice"


def test_a_scope_column_is_kept_and_never_checked() -> None:
    table = with_scope(CLAIMS, [0, 0, 1, 1])
    assert match_claim_problems(table) == []
    assert match_claim_problems(table, MANIFEST) == []
    assert table.column_names[-1] == "scope"


def test_a_scope_column_never_tells_one_id_apart() -> None:
    rows = changed(CLAIMS, put(2, "id", value="claim_1"))
    table = with_scope(rows, [None, None, "take_2", "take_2"], pa.string())
    assert found(match_claim_problems(table, MANIFEST)) == [
        ("duplicate_id", 2, ("id",))
    ]
    with pytest.raises(TableError) as error:
        check_match_claims(table, MANIFEST)
    assert str(error.value) == "the ID 'claim_1' is given twice"


# The pre-parsed Projection table


def test_the_valid_projections_have_no_problem_with_or_without_the_manifest() -> None:
    table = projections_table(PROJECTIONS)
    assert projection_problems(table) == []
    assert projection_problems(table, MANIFEST) == []
    check_projections(table, MANIFEST)


PROJECTION_CASES = [
    (
        "id_null",
        put(0, "id", value=None),
        [("schema_violation", 0, ("id",))],
        "'id' is null",
    ),
    (
        "id_twice",
        put(2, "id", value="projection_1"),
        [("duplicate_id", 2, ("id",))],
        "the ID 'projection_1' is given twice",
    ),
    (
        "id_chunk_sentinel",
        put(2, "id", value=CHUNK),
        [("invalid_id", 2, ("id",))],
        "'CHUNK_SENTINEL' is reserved for a sentinel",
    ),
    (
        "source_without_event",
        put(0, "projection_of", "event_id", value=None),
        [("invalid_projection_of", 0, ("projection_of", "event_id"))],
        "the projected event has no event_id",
    ),
    (
        "source_event_sentinel",
        put(0, "projection_of", "event_id", value=NOMATCH),
        [("invalid_projection_of", 0, ("projection_of", "event_id"))],
        "'NOMATCH_SENTINEL' is reserved for a sentinel",
    ),
    (
        "source_without_timeline_of_a_sentinel",
        put(0, "projection_of", value={"timeline_id": "", "event_id": CHUNK}),
        [
            ("invalid_projection_of", 0, ("projection_of", "timeline_id")),
            ("invalid_projection_of", 0, ("projection_of", "event_id")),
        ],
        "the projected event has no timeline_id",
    ),
    (
        "source_event_sentinel_on_dpt_1",
        put(0, "projection_of", value={"timeline_id": "dpt_1", "event_id": CHUNK}),
        [("invalid_projection_of", 0, ("projection_of", "event_id"))],
        "'CHUNK_SENTINEL' is reserved for a sentinel",
    ),
]


@pytest.mark.parametrize(
    ("change", "expected", "message"),
    [case[1:] for case in PROJECTION_CASES],
    ids=[case[0] for case in PROJECTION_CASES],
)
def test_each_projection_rule(
    change: Callable[[list[dict]], None], expected: list[tuple], message: str
) -> None:
    table = projections_table(changed(PROJECTIONS, change))
    assert found(projection_problems(table)) == expected
    with pytest.raises(TableError) as error:
        check_projections(table)
    assert str(error.value) == message


def test_a_projection_of_its_own_timeline_is_the_package_checks() -> None:
    # The Projection's timeline is its registry row's: alone, the pre-parsed
    # table cannot tell it from another timeline.
    table = projections_table(
        changed(PROJECTIONS, put(0, "projection_of", "timeline_id", value="dpt_1"))
    )
    assert projection_problems(table) == []
    assert projection_problems(table, MANIFEST) == []


def test_a_joined_string_is_no_projected_event() -> None:
    table = projections_table(PROJECTIONS)
    index = table.column_names.index("projection_of")
    joined = pa.array(["clt_1/note_1", "clt_1/note_2", None])
    table = table.set_column(index, "projection_of", joined)
    assert found(projection_problems(table)) == [
        ("schema_violation", None, ("projection_of",))
    ]
    with pytest.raises(TableError) as error:
        check_projections(table)
    assert str(error.value) == (
        "the column 'projection_of' is string, "
        "not struct<timeline_id: string, event_id: string>"
    )


def test_a_projection_table_with_positions_keeps_them_unchecked() -> None:
    # Former columns are further columns: kept, never checked.
    rows = [{**row, "timeline_id": None, "start": "x"} for row in PROJECTIONS]
    table = pa.Table.from_pylist(rows)
    assert projection_problems(table) == []


def test_projections_against_the_manifest() -> None:
    rows = changed(PROJECTIONS, put(0, "projection_of", "timeline_id", value="clt_9"))
    table = projections_table(rows)
    assert projection_problems(table) == []
    assert found(projection_problems(table, MANIFEST)) == [
        ("unknown_timeline", 0, ("projection_of", "timeline_id"))
    ]
    with pytest.raises(TableError) as error:
        check_projections(table, MANIFEST)
    assert str(error.value) == "the manifest has no timeline 'clt_9'"


# The registry


def test_the_valid_registry_has_no_problem_with_or_without_the_manifest() -> None:
    table = registry_table(REGISTRY)
    assert registry_problems(table) == []
    assert registry_problems(table, MANIFEST) == []
    check_registry(table, MANIFEST)


REGISTRY_CASES = [
    (
        "id_null",
        put(3, "id", value=None),
        [("schema_violation", 3, ("id",))],
        "'id' is null",
    ),
    (
        "kind_null",
        put(0, "kind", value=None),
        [("schema_violation", 0, ("kind",))],
        "'kind' is null",
    ),
    *(
        (
            f"event_{key}_null",
            put(1, key, value=None),
            [("schema_violation", 1, (key,))],
            f"'{key}' is null",
        )
        for key in ("timeline_id", "unit", "number_type", "start", "extraction_id")
    ),
    (
        "index_location_null",
        put(4, "location", value=None),
        [("schema_violation", 4, ("location",))],
        "'location' is null",
    ),
    *(
        (
            f"index_{key}_stated",
            put(5, key, value=value),
            [("schema_violation", 5, (key,))],
            f"an index row has no '{key}'",
        )
        for key, value in (
            ("unit", "quarters"),
            ("number_type", "fraction"),
            ("start", number(q(0))),
            ("duration", number(q(1))),
            ("extraction_id", "extraction_1"),
            ("locator", "bar 1"),
            ("vanished_in", "extraction_1"),
        )
    ),
    (
        "nulls_by_row_then_column",
        lambda rows: [
            rows[2].update(start=None, extraction_id=None),
            rows[0].update(unit=None),
            rows[6].update(start=number(q(0))),
        ],
        [
            ("schema_violation", 0, ("unit",)),
            ("schema_violation", 2, ("start",)),
            ("schema_violation", 2, ("extraction_id",)),
            ("schema_violation", 6, ("start",)),
        ],
        "'unit' is null",
    ),
    (
        "id_twice",
        put(2, "id", value="projection_1"),
        [("duplicate_id", 2, ("id",))],
        "the ID 'projection_1' is given twice",
    ),
    (
        "event_id_is_a_match_claim_id",
        put(6, "id", value="projection_2"),
        [("duplicate_id", 6, ("id",))],
        "the ID 'projection_2' is given twice",
    ),
    (
        "extraction_id_is_a_match_claim_id",
        put(7, "id", value="claim_1"),
        [("duplicate_id", 7, ("id",))],
        "the ID 'claim_1' is given twice",
    ),
    (
        "element_id_twice_at_one_location",
        put(4, "id", value="clt_1"),
        [("duplicate_id", 4, ("id",))],
        "the ID 'clt_1' is given twice at 'manifest.yaml'",
    ),
    (
        "id_chunk_sentinel",
        put(2, "id", value=CHUNK),
        [("invalid_id", 2, ("id",))],
        "'CHUNK_SENTINEL' is reserved for a sentinel",
    ),
    (
        "id_empty",
        put(4, "id", value=""),
        [("invalid_id", 4, ("id",))],
        "the ID is empty",
    ),
    (
        "negative_duration",
        put(1, "duration", value=number(smp(-1))),
        [("invalid_duration", 1, ("duration",))],
        "the duration is negative",
    ),
    (
        "unit_unknown",
        put(2, "unit", value="parsecs"),
        [("invalid_coordinate", 2, ("unit",))],
        "'parsecs' is no unit",
    ),
    (
        "number_type_unknown",
        put(2, "number_type", value="decimal"),
        [("invalid_coordinate", 2, ("number_type",))],
        "'decimal' is no number type",
    ),
    (
        "number_type_not_admitted",
        put(2, "number_type", value="fraction"),
        [("invalid_coordinate", 2, ("number_type",))],
        "'samples' admits no number type 'fraction'",
    ),
    (
        "start_mirror",
        put(2, "start", "value", value=132300.0),
        [("invalid_coordinate", 2, ("start",))],
        "an int coordinate holds its numerator alone, not a value",
    ),
    (
        "duration_of_another_number_type",
        put(1, "duration", value=number(sec(1.0))),
        [("invalid_coordinate", 1, ("duration",))],
        "an int duration has no numerator",
    ),
    (
        "duration_mirror",
        put(1, "duration", "denominator", value=1),
        [("invalid_coordinate", 1, ("duration",))],
        "an int duration holds its numerator alone, not a denominator",
    ),
    (
        "two_units",
        lambda rows: rows[2].update(
            unit="seconds", number_type="float", start=number(sec(3.0))
        ),
        [("axis_mismatch", 2, ("unit",))],
        "the timeline 'dpt_1' has coordinates in samples (int) and in seconds (float)",
    ),
    (
        "two_number_types",
        lambda rows: [
            rows[0].update(unit="seconds", number_type="float", start=number(sec(0.0))),
            rows[1].update(
                unit="seconds",
                number_type="float",
                start=number(sec(1.0)),
                duration=number(sec(1.0)),
            ),
            rows[2].update(unit="seconds", number_type="fraction", start=number(q(3))),
        ],
        [("axis_mismatch", 2, ("number_type",))],
        "the timeline 'dpt_1' has coordinates in seconds (float) and in seconds "
        "(fraction)",
    ),
    (
        "locator_twice_in_one_extraction",
        put(2, "locator", value="track 0, message 4"),
        [("duplicate_locator", 2, ("locator",))],
        "the locator 'track 0, message 4' is given twice in the extraction "
        "'extraction_1'",
    ),
]


@pytest.mark.parametrize(
    ("change", "expected", "message"),
    [case[1:] for case in REGISTRY_CASES],
    ids=[case[0] for case in REGISTRY_CASES],
)
def test_each_registry_rule(
    change: Callable[[list[dict]], None], expected: list[tuple], message: str
) -> None:
    table = registry_table(changed(REGISTRY, change))
    assert found(registry_problems(table)) == expected
    with pytest.raises(TableError) as error:
        check_registry(table)
    assert str(error.value) == message


@pytest.mark.parametrize(
    "change",
    [
        None,
        lambda rows: rows.insert(4, index("clt_1", "Timeline", "other/manifest.yaml")),
        lambda rows: rows[2].update(
            extraction_id="extraction_2", locator=rows[0]["locator"]
        ),
        lambda rows: rows[0].update(kind="MidiNote", location=None),
        lambda rows: rows[1].update(vanished_in="extraction_2"),
    ],
    ids=[
        "the_valid_registry",
        "element_id_at_two_locations",
        "locator_in_two_extractions",
        "event_re_parsable_only",
        "vanished_row_kept",
    ],
)
def test_each_admitted_registry(change: Callable[[list[dict]], None] | None) -> None:
    rows = REGISTRY if change is None else changed(REGISTRY, change)
    table = registry_table(rows)
    assert registry_problems(table) == []
    assert registry_problems(table, MANIFEST) == []


@pytest.mark.parametrize(
    ("start", "duration", "values"),
    [
        (q(4, 2), None, (Fraction(2), None)),
        (q(7, 2), q(2, 4), (Fraction(7, 2), Fraction(1, 2))),
    ],
    ids=["start_unreduced", "duration_unreduced"],
)
def test_an_unreduced_event_number_is_read_as_its_value(
    start: dict, duration: dict | None, values: tuple[Fraction, Fraction | None]
) -> None:
    table = registry_table(
        changed(
            REGISTRY,
            lambda rows: rows[2].update(
                timeline_id="clt_1",
                unit="quarters",
                number_type="fraction",
                start=number(start),
                duration=number(duration),
            ),
        )
    )
    assert registry_problems(table) == []
    assert registry_problems(table, MANIFEST) == []
    check_registry(table, MANIFEST)
    row = table.to_pylist()[2]
    read = tuple(
        None if row[key] is None else coordinate_value(row[key], "fraction")
        for key in ("start", "duration")
    )
    assert read == values


def test_one_id_on_two_timelines_is_a_duplicate() -> None:
    rows = [
        *REGISTRY,
        event("projection_1", q(1), timeline_id="clt_1"),
    ]
    table = registry_table(rows)
    assert found(registry_problems(table)) == [("duplicate_id", 8, ("id",))]
    assert found(registry_problems(table, MANIFEST)) == [("duplicate_id", 8, ("id",))]
    with pytest.raises(TableError) as error:
        check_registry(table, MANIFEST)
    assert str(error.value) == "the ID 'projection_1' is given twice"


def test_event_rows_against_the_manifest() -> None:
    rows = copy.deepcopy(REGISTRY)
    for row in rows[:3]:
        row.update(
            unit="seconds",
            number_type="float",
            start=number(sec(row["start"]["numerator"] / 44100)),
        )
    rows[1]["duration"] = number(sec(1.0))
    rows[2]["unit"] = "samples"
    table = registry_table(rows)
    assert found(registry_problems(table)) == [
        ("invalid_coordinate", 2, ("number_type",))
    ]
    assert found(registry_problems(table, MANIFEST)) == [
        ("axis_mismatch", 0, ("unit",)),
        ("axis_mismatch", 1, ("unit",)),
        ("invalid_coordinate", 2, ("number_type",)),
    ]
    with pytest.raises(TableError) as error:
        check_registry(table, MANIFEST)
    assert str(error.value) == (
        "a coordinate in seconds (float) on the timeline 'dpt_1' in samples (int)"
    )


def test_index_rows_are_not_checked_against_the_manifest() -> None:
    # An element of another manifest, a Region on a timeline the manifest
    # lacks: the package check compares index rows with the manifests.
    rows = [*REGISTRY, index("region_9", "Region", "x.yaml", timeline_id="ghost")]
    assert registry_problems(registry_table(rows), MANIFEST) == []


def test_an_event_row_on_an_unknown_timeline_is_refused_only_against_the_manifest() -> (
    None
):
    table = registry_table(changed(REGISTRY, put(2, "timeline_id", value="ghost")))
    assert registry_problems(table) == []
    assert found(registry_problems(table, MANIFEST)) == [
        ("unknown_timeline", 2, ("timeline_id",))
    ]
    with pytest.raises(TableError, match="^the manifest has no timeline 'ghost'$"):
        check_registry(table, MANIFEST)


# The Extraction table


def test_the_valid_extractions_have_no_problem() -> None:
    table = extractions_table(EXTRACTIONS)
    assert extraction_problems(table) == []
    check_extractions(table)


EXTRACTION_CASES = [
    *(
        (
            f"{key}_null",
            put(0, key, value=None),
            [("schema_violation", 0, (key,))],
            f"'{key}' is null",
        )
        for key in ("id", "parser", "parser_version", "minter", "id_length", "date")
    ),
    (
        "id_twice",
        put(1, "id", value="extraction_1"),
        [("duplicate_id", 1, ("id",))],
        "the ID 'extraction_1' is given twice",
    ),
    (
        "id_nomatch_sentinel",
        put(1, "id", value=NOMATCH),
        [("invalid_id", 1, ("id",))],
        "'NOMATCH_SENTINEL' is reserved for a sentinel",
    ),
    (
        "source_without_integrity",
        put(0, "source_integrity", value=None),
        [("schema_violation", 0, ("source_integrity",))],
        "'source_integrity' is null where 'source' is given",
    ),
    (
        "integrity_without_digest",
        put(0, "source_integrity", "digest", value=None),
        [("schema_violation", 0, ("source_integrity", "digest"))],
        "'source_integrity' has no digest",
    ),
]


ADMITTED_EXTRACTIONS = [
    (
        "integrity_of_an_unknown_algorithm",
        put(0, "source_integrity", "algorithm", value="SHA-3"),
    ),
    ("digest_in_capitals", put(0, "source_integrity", "digest", value="00FF")),
    ("parameters_no_json", put(0, "parameters", value="{merge_tracks: false}")),
    ("parameters_no_object", put(0, "parameters", value="[480]")),
    (
        "parameters_not_canonical",
        put(0, "parameters", value='{"resolution": 480, "merge_tracks": false}'),
    ),
    ("id_length_zero", put(1, "id_length", value=0)),
    ("date_with_a_zero_offset", put(0, "date", value="2026-11-27T21:30:00+00:00")),
    ("date_without_zone", put(0, "date", value="2026-11-27T21:30:00")),
    ("date_impossible", put(1, "date", value="2026-02-30T00:00:00Z")),
    ("date_without_time", lambda rows: [row.update(date="2026-11-27") for row in rows]),
]
"""Values a writer spells otherwise than the README writes them, each
admitted: a reader refuses only the shape and a source without its
integrity."""


@pytest.mark.parametrize(
    "change",
    [case[1] for case in ADMITTED_EXTRACTIONS],
    ids=[case[0] for case in ADMITTED_EXTRACTIONS],
)
def test_an_extraction_is_read_as_written(change: Callable[[list[dict]], None]) -> None:
    table = extractions_table(changed(EXTRACTIONS, change))
    assert extraction_problems(table) == []
    check_extractions(table)


@pytest.mark.parametrize(
    ("change", "expected", "message"),
    [case[1:] for case in EXTRACTION_CASES],
    ids=[case[0] for case in EXTRACTION_CASES],
)
def test_each_extraction_rule(
    change: Callable[[list[dict]], None], expected: list[tuple], message: str
) -> None:
    table = extractions_table(changed(EXTRACTIONS, change))
    assert found(extraction_problems(table)) == expected
    with pytest.raises(TableError) as error:
        check_extractions(table)
    assert str(error.value) == message


# The succession rule


def _with_belief(rows: list[dict]) -> None:
    for row in rows:
        row["provenance"] = {
            **dict.fromkeys(PROVENANCE_KEYS),
            "beliefs": [
                {"actor": ACTOR, "belief": "false", "date": "2026-11-21", "note": None}
            ],
        }


@pytest.mark.parametrize(
    "change",
    [
        lambda rows: None,
        lambda rows: rows.append(
            claim("claim_5", "note_5", "projection_4", (q(4), smp(176400)))
        ),
        _with_belief,
        lambda rows: rows.reverse(),
        put(1, "start_anchor", "coordinate_a", value=q(2, 2)),
    ],
    ids=["same", "appended", "provenance", "reordered", "unreduced"],
)
def test_a_successor_keeps_every_claim(change: Callable[[list[dict]], None]) -> None:
    old = claims_table(CLAIMS)
    new = claims_table(changed(CLAIMS, change))
    assert succession_problems(old, new) == []
    check_succession(old, new)


def test_a_missing_claim_breaks_the_succession() -> None:
    old, new = claims_table(CLAIMS), claims_table(CLAIMS[1:])
    assert found(succession_problems(old, new)) == [
        ("succession_missing", None, ("id",))
    ]
    with pytest.raises(TableError, match="^the MatchClaim 'claim_1' is missing$"):
        check_succession(old, new)


@pytest.mark.parametrize(
    ("change", "expected", "message"),
    [
        (
            put(0, "start_anchor", "coordinate_b", value=smp(1)),
            [("succession_changed", 0, ("start_anchor",))],
            "the MatchClaim 'claim_1' changed its 'start_anchor'",
        ),
        (
            put(1, "event_b_id", value="projection_9"),
            [("succession_changed", 1, ("event_b_id",))],
            "the MatchClaim 'claim_2' changed its 'event_b_id'",
        ),
        (
            put(3, "timeline_b_id", value="cpt_1"),
            [("succession_changed", 3, ("timeline_b_id",))],
            "the MatchClaim 'claim_4' changed its 'timeline_b_id'",
        ),
        (
            lambda rows: (rows.reverse(), rows[0].update(certainty=0.5)),
            [("succession_changed", 0, ("certainty",))],
            "the MatchClaim 'claim_4' changed its 'certainty'",
        ),
    ],
    ids=["anchor", "event", "timeline", "reordered"],
)
def test_a_changed_claim_breaks_the_succession(
    change: Callable[[list[dict]], None], expected: list[tuple], message: str
) -> None:
    old, new = claims_table(CLAIMS), claims_table(changed(CLAIMS, change))
    assert found(succession_problems(old, new)) == expected
    with pytest.raises(TableError) as error:
        check_succession(old, new)
    assert str(error.value) == message


def test_a_further_column_takes_no_part_in_the_succession() -> None:
    old = with_scope(CLAIMS, [None, None, "take_2", "take_2"], pa.string())
    assert succession_problems(claims_table(CLAIMS), old) == []
    new = with_scope(CLAIMS, ["take_3"] * 4, pa.string())
    assert succession_problems(old, new) == []
    check_succession(old, new)


# The fixture


def _script() -> Any:
    spec = importlib.util.spec_from_file_location("emit_tables", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_fixture_files_are_the_scripts() -> None:
    script = _script()
    directory = fixture_path("manifest.yaml").parent
    assert sorted(path.name for path in directory.iterdir()) == [
        "expected.yaml",
        "extractions.parquet",
        "manifest.yaml",
        "match_claims.parquet",
        "projections.parquet",
        "registry.parquet",
    ]
    for name, table in (
        ("match_claims.parquet", script.match_claims_table()),
        ("registry.parquet", script.registry_table()),
        ("projections.parquet", script.projections_table()),
        ("extractions.parquet", script.extractions_table()),
    ):
        assert pq.read_table(fixture_path(name)).equals(table), name
    manifest = fixture_path("manifest.yaml").read_text(encoding="utf-8")
    assert manifest == dumps(script.manifest(directory))
    expected = fixture_path("expected.yaml").read_text(encoding="utf-8")
    assert expected == dumps(script.EXPECTED)


def _events() -> list[dict[str, Any]]:
    rows = pq.read_table(fixture_path("registry.parquet")).to_pylist()
    return [row for row in rows if row["kind"] not in INDEX_KINDS]


def test_the_manifest_names_its_tables_with_their_size_and_digest() -> None:
    manifest = loads(fixture_path("manifest.yaml").read_text(encoding="utf-8"))
    claims = pq.read_table(fixture_path("match_claims.parquet")).to_pylist()
    named = {
        "match_claims.parquet": {
            *(row["timeline_a_id"] for row in claims),
            *(row["timeline_b_id"] for row in claims),
        },
        "registry.parquet": {row["timeline_id"] for row in _events()},
    }
    order = ["clt_1", "clt_2", "dpt_1", "cpt_1"]
    resources = manifest["resources"]
    assert [(r["id"], r["type"], r["url"]) for r in resources] == [
        ("#resource_1", "MatchClaim", "match_claims.parquet"),
        ("#resource_2", "Registry", "registry.parquet"),
    ]
    for resource in resources:
        data = fixture_path(resource["url"]).read_bytes()
        assert resource["media_type"] == "application/vnd.apache.parquet"
        assert resource["size"] == len(data)
        assert resource["integrity"] == {
            "algorithm": "SHA-256",
            "digest": hashlib.sha256(data).hexdigest(),
        }
        held = [
            identifier for identifier in order if identifier in named[resource["url"]]
        ]
        assert resource["timelines"] == [f"#{identifier}" for identifier in held]


def test_the_fixture_tables_pass_every_check_against_their_manifest() -> None:
    manifest = loads(fixture_path("manifest.yaml").read_text(encoding="utf-8"))
    claims = pq.read_table(fixture_path("match_claims.parquet"))
    registry = pq.read_table(fixture_path("registry.parquet"))
    projections = pq.read_table(fixture_path("projections.parquet"))
    extractions = pq.read_table(fixture_path("extractions.parquet"))
    assert claims.num_rows == 18
    assert registry.num_rows == 36
    assert projections.num_rows == 11
    assert extractions.num_rows == 1
    assert match_claim_problems(claims, manifest) == []
    assert registry_problems(registry, manifest) == []
    assert projection_problems(projections, manifest) == []
    assert extraction_problems(extractions) == []


def test_the_registry_indexes_the_manifest_the_claims_and_the_extraction() -> None:
    rows = pq.read_table(fixture_path("registry.parquet")).to_pylist()
    index = [
        (row["location"], row["id"], row["kind"])
        for row in rows
        if row["kind"] in INDEX_KINDS
    ]
    claims = pq.read_table(fixture_path("match_claims.parquet")).column("id")
    assert index == sorted(
        [
            ("extractions.parquet", "extraction_1", "Extraction"),
            *(
                ("manifest.yaml", identifier, "Timeline")
                for identifier in ("clt_1", "clt_2", "cpt_1", "dpt_1")
            ),
            ("manifest.yaml", "resource_1", "Resource"),
            ("manifest.yaml", "resource_2", "Resource"),
            *(
                ("match_claims.parquet", identifier, "MatchClaim")
                for identifier in claims.to_pylist()
            ),
        ]
    )
    assert {
        (row["kind"], row["location"], row["extraction_id"]) for row in _events()
    } == {("Projection", "projections.parquet", "extraction_1")}
    content = pq.read_table(fixture_path("projections.parquet")).column("id")
    assert content.to_pylist() == [row["id"] for row in _events()]


def test_each_projection_a_claim_names_stands_at_its_anchor() -> None:
    claims = pq.read_table(fixture_path("match_claims.parquet")).to_pylist()
    standing = {row["id"]: row for row in _events()}
    sources = {
        row["id"]: row["projection_of"]
        for row in pq.read_table(fixture_path("projections.parquet")).to_pylist()
    }
    # The child clt_2 starts at the quarter 8 of its root clt_1: a registry
    # position lies on the root's axis, an anchor on the row's own timeline.
    offsets = {"clt_2": Fraction(8)}
    named = set()
    unanchored = []
    for row in claims:
        for side in ("a", "b"):
            event = row[f"event_{side}_id"]
            if event not in standing:
                continue
            named.add(event)
            held = standing[event]
            timeline = row[f"timeline_{side}_id"]
            assert held["timeline_id"] == timeline
            if row["start_anchor"] is None:
                unanchored.append((row["id"], side, event, sources[event]))
                continue
            kind = held["number_type"]
            start = coordinate_value(held["start"], kind) - offsets.get(timeline, 0)
            assert start == coordinate_value(row["start_anchor"][f"coordinate_{side}"])
            if row["end_anchor"] is None:
                assert held["duration"] is None
            else:
                end = coordinate_value(row["end_anchor"][f"coordinate_{side}"])
                assert start + coordinate_value(held["duration"], kind) == end
    assert set(standing) - named == {"projection_10", "projection_11"}
    assert unanchored == [("claim_18", "a", "inserted_1", None)]
    assert [key for key, value in sources.items() if value is None] == ["inserted_1"]
    ten = standing["projection_10"]
    assert (ten["timeline_id"], coordinate_value(ten["start"], "fraction")) == (
        "clt_2",
        Fraction(23, 2),
    )
    sentinels = [
        (row["id"], side, row[f"event_{side}_id"], row[f"event_{side}_name"])
        for row in claims
        for side in ("a", "b")
        if row[f"event_{side}_id"] in (NOMATCH, CHUNK)
    ]
    assert sentinels == [
        ("claim_11", "a", CHUNK, "downbeat 3"),
        ("claim_11", "b", CHUNK, None),
        ("claim_12", "b", NOMATCH, None),
        ("claim_16", "a", CHUNK, None),
        ("claim_18", "b", NOMATCH, None),
    ]


def test_the_event_rows_lie_sorted_by_timeline_start_and_id() -> None:
    order = [
        (
            row["timeline_id"],
            coordinate_value(row["start"], row["number_type"]),
            row["id"],
        )
        for row in _events()
    ]
    assert order == sorted(order)
    assert [(timeline, identifier) for timeline, _, identifier in order] == [
        ("clt_2", "projection_10"),
        ("cpt_1", "projection_12"),
        ("cpt_1", "projection_11"),
        ("dpt_1", "projection_1"),
        ("dpt_1", "projection_2"),
        ("dpt_1", "projection_3"),
        ("dpt_1", "projection_4"),
        ("dpt_1", "projection_5"),
        ("dpt_1", "projection_9"),
        ("dpt_1", "projection_8"),
        ("dpt_1", "inserted_1"),
    ]


# The rows of other manifests


def _foreign_claim(identifier: str, **members: Any) -> dict[str, Any]:
    """A MatchClaim on two timelines the manifest lacks."""
    sides = {"timeline_a_id": "dpt_8", "timeline_b_id": "dpt_9"}
    return claim(
        identifier, "note_9", "note_10", (q(0), smp(0)), **{**sides, **members}
    )


def _foreign_event(identifier: str) -> dict[str, Any]:
    """An event row on a timeline the manifest lacks."""
    return event(identifier, smp(0), timeline_id="dpt_9")


def _interleaved(own: list[dict], foreign: list[dict]) -> list[dict]:
    """The foreign rows before, between and after the manifest's own."""
    return [foreign[0], own[0], own[1], foreign[1], *own[2:], foreign[2]]


def test_the_rows_of_other_manifests_are_unknown_timelines() -> None:
    foreign = [_foreign_claim(f"claim_{n}") for n in (7, 8, 9)]
    claims = claims_table(_interleaved(CLAIMS, foreign))
    problems = match_claim_problems(claims, MANIFEST)
    assert found(problems) == [
        ("unknown_timeline", row, (column,))
        for row in (0, 3, 6)
        for column in ("timeline_a_id", "timeline_b_id")
    ]
    assert [problem.message for problem in problems[:2]] == [
        "the manifest has no timeline 'dpt_8'",
        "the manifest has no timeline 'dpt_9'",
    ]
    assert match_claim_problems(claims) == []
    foreign = [_foreign_event(f"projection_{n}") for n in (7, 8, 9)]
    registry = registry_table(_interleaved(EVENTS, foreign))
    problems = registry_problems(registry, MANIFEST)
    assert found(problems) == [
        ("unknown_timeline", row, ("timeline_id",)) for row in (0, 3, 5)
    ]
    assert problems[0].message == "the manifest has no timeline 'dpt_9'"
    assert registry_problems(registry) == []


def test_a_claim_half_in_the_manifest_is_refused_at_its_other_side() -> None:
    rows = [*CLAIMS, _foreign_claim("claim_9", timeline_a_id="clt_1")]
    problems = match_claim_problems(claims_table(rows), MANIFEST)
    assert found(problems) == [("unknown_timeline", 4, ("timeline_b_id",))]
    assert problems[0].message == "the manifest has no timeline 'dpt_9'"


def test_a_null_timeline_is_refused_with_a_manifest() -> None:
    rows = changed(REGISTRY, put(1, "timeline_id", value=None))
    for manifest in (MANIFEST, None):
        problems = registry_problems(registry_table(rows), manifest)
        assert found(problems) == [("schema_violation", 1, ("timeline_id",))]
        assert problems[0].message == "'timeline_id' is null"
    rows = changed(CLAIMS, put(1, "timeline_a_id", value=None))
    rows = changed(rows, put(1, "timeline_b_id", value=None))
    for manifest in (MANIFEST, None):
        problems = match_claim_problems(claims_table(rows), manifest)
        assert found(problems) == [
            ("schema_violation", 1, ("timeline_a_id",)),
            ("schema_violation", 1, ("timeline_b_id",)),
        ]
        assert problems[0].message == "'timeline_a_id' is null"
