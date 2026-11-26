"""The table types: their columns, their checks, the succession rule and the
fixture files (see "The MatchClaim table", "The Projections table" and
"Checking the tables" in README.md)."""

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
    TABLES_DOCUMENT,
    AlignmentAnchor,
    TableError,
    TableProblem,
    TimelineCoordinate,
    alignment_anchors,
    check_match_claims,
    check_projections,
    check_succession,
    coordinate_value,
    fixture_path,
    match_claim_problems,
    number_cell,
    projection_problems,
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


def projection(
    identifier: str,
    start: dict,
    of: tuple[str | None, str | None] | None,
    duration: dict | None = None,
) -> dict[str, Any]:
    """A Projection on ``dpt_1`` from coordinate cells: the row states their
    unit and number type once."""
    return {
        "id": identifier,
        "timeline_id": "dpt_1",
        "unit": start["unit"],
        "number_type": start["number_type"],
        "start": number(start),
        "duration": number(duration),
        "projection_of": None
        if of is None
        else {"timeline_id": of[0], "event_id": of[1]},
    }


PROJECTIONS = [
    projection("projection_1", smp(0), ("clt_1", "note_1")),
    projection("projection_2", smp(44100), ("clt_1", "note_2"), smp(44100)),
    projection("projection_3", smp(132300), None),
]

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
    assert PROJECTION_COLUMNS == (
        "id",
        "timeline_id",
        "unit",
        "number_type",
        "start",
        "duration",
        "projection_of",
    )
    projection_of = PROJECTION_SCHEMA.field("projection_of").type
    assert [field.name for field in projection_of] == ["timeline_id", "event_id"]


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
        ("timeline_id", pa.string(), True),
        ("unit", pa.string(), True),
        ("number_type", pa.string(), True),
        ("start", _NUMBER, True),
        ("duration", _NUMBER, True),
        (
            "projection_of",
            pa.struct([("timeline_id", pa.string()), ("event_id", pa.string())]),
            True,
        ),
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
    assert types["provenance"]["schema"] == "provenance.schema.json"
    assert (tables_path().parent / "provenance.schema.json").is_file()
    tables = document["tables"]
    assert {name: table["status"] for name, table in tables.items()} == {
        "MatchClaim": "stable",
        "Projection": "experimental",
    }
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
        ("timeline_id", "string"),
        ("unit", "string"),
        ("number_type", "string"),
        ("start", "number"),
        ("duration", "number"),
        ("projection_of", "projection_of"),
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
        "Projection": ["id", "timeline_id", "unit", "number_type", "start"],
    }
    assert MATCH_CLAIM_REQUIRED == (
        "timeline_a_id",
        "timeline_b_id",
        "is_synchronous",
        "event_a_id",
        "event_b_id",
        "id",
    )
    assert PROJECTION_REQUIRED == ("id", "timeline_id", "unit", "number_type", "start")
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
    assert PROJECTION_SCHEMA.field("start").type == NUMBER_TYPE
    assert PROJECTION_SCHEMA.field("duration").type == NUMBER_TYPE
    assert str(PROJECTION_SCHEMA.field("unit").type) == "string"
    assert str(PROJECTION_SCHEMA.field("number_type").type) == "string"
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
        "a sentinel side has no name",
    ),
    (
        "chunk_side_named",
        lambda rows: rows[0].update(event_a_id=CHUNK, event_a_name=""),
        [("claim_events", 0, ("event_a_name",))],
        "a sentinel side has no name",
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
        "nomatch_a",
        lambda rows: rows[2].update(event_a_id=NOMATCH, event_b_id="projection_3"),
    ),
]
"""Rows the format admits, each one change of the inline table: CHUNK on
either side and on both of a synchronous instant and interval, and a
NOMATCH on side A (the inline table's NOMATCH stands on side B)."""


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
    projections = projections_table(
        changed(
            PROJECTIONS,
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
    assert projection_problems(projections) == expected
    assert projection_problems(projections, MANIFEST) == expected


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


# The Projections table


def test_the_valid_projections_have_no_problem_with_or_without_the_manifest() -> None:
    table = projections_table(PROJECTIONS)
    assert projection_problems(table) == []
    assert projection_problems(table, MANIFEST) == []
    check_projections(table, MANIFEST)


PROJECTION_CASES = [
    (
        "start_null",
        put(0, "start", value=None),
        [("schema_violation", 0, ("start",))],
        "'start' is null",
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
        "source_on_own_timeline",
        put(0, "projection_of", "timeline_id", value="dpt_1"),
        [("invalid_projection_of", 0, ("projection_of", "timeline_id"))],
        "a Projection stands for an event of another timeline than 'dpt_1'",
    ),
    (
        "negative_duration",
        put(1, "duration", value=number(smp(-1))),
        [("invalid_duration", 1, ("duration",))],
        "the duration is negative",
    ),
    (
        "unit_null",
        put(0, "unit", value=None),
        [("schema_violation", 0, ("unit",))],
        "'unit' is null",
    ),
    (
        "number_type_null",
        put(0, "number_type", value=None),
        [("schema_violation", 0, ("number_type",))],
        "'number_type' is null",
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


@pytest.mark.parametrize(
    ("start", "duration", "values"),
    [
        (q(4, 2), None, (Fraction(2), None)),
        (q(7, 2), q(2, 4), (Fraction(7, 2), Fraction(1, 2))),
    ],
    ids=["start_unreduced", "duration_unreduced"],
)
def test_an_unreduced_projection_number_is_read_as_its_value(
    start: dict, duration: dict | None, values: tuple[Fraction, Fraction | None]
) -> None:
    table = projections_table(
        changed(
            PROJECTIONS,
            lambda rows: rows[2].update(
                timeline_id="clt_1",
                unit="quarters",
                number_type="fraction",
                start=number(start),
                duration=number(duration),
            ),
        )
    )
    assert projection_problems(table) == []
    assert projection_problems(table, MANIFEST) == []
    check_projections(table, MANIFEST)
    row = table.to_pylist()[2]
    read = tuple(
        None if row[key] is None else coordinate_value(row[key], "fraction")
        for key in ("start", "duration")
    )
    assert read == values


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


def test_one_id_on_two_timelines_is_a_duplicate() -> None:
    rows = [
        *PROJECTIONS,
        {
            **projection("projection_1", q(1), ("dpt_1", "projection_2")),
            "timeline_id": "clt_1",
        },
    ]
    table = projections_table(rows)
    assert found(projection_problems(table)) == [("duplicate_id", 3, ("id",))]
    assert found(projection_problems(table, MANIFEST)) == [("duplicate_id", 3, ("id",))]
    with pytest.raises(TableError) as error:
        check_projections(table, MANIFEST)
    assert str(error.value) == "the ID 'projection_1' is given twice"


def test_projections_against_the_manifest() -> None:
    rows = changed(PROJECTIONS, put(0, "projection_of", "timeline_id", value="clt_9"))
    for row in rows:
        row.update(
            unit="seconds",
            number_type="float",
            start=number(sec(row["start"]["numerator"] / 44100)),
        )
    rows[1]["duration"] = number(sec(1.0))
    rows[2]["unit"] = "samples"
    table = projections_table(rows)
    assert found(projection_problems(table)) == [
        ("invalid_coordinate", 2, ("number_type",))
    ]
    assert found(projection_problems(table, MANIFEST)) == [
        ("axis_mismatch", 0, ("unit",)),
        ("unknown_timeline", 0, ("projection_of", "timeline_id")),
        ("axis_mismatch", 1, ("unit",)),
        ("invalid_coordinate", 2, ("number_type",)),
    ]
    with pytest.raises(TableError) as error:
        check_projections(table, MANIFEST)
    assert str(error.value) == (
        "a coordinate in seconds (float) on the timeline 'dpt_1' in samples (int)"
    )


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
        "manifest.yaml",
        "match_claims.parquet",
        "projections.parquet",
    ]
    assert pq.read_table(fixture_path("match_claims.parquet")).equals(
        script.match_claims_table()
    )
    assert pq.read_table(fixture_path("projections.parquet")).equals(
        script.projections_table()
    )
    manifest = fixture_path("manifest.yaml").read_text(encoding="utf-8")
    assert manifest == dumps(script.manifest(directory))
    expected = fixture_path("expected.yaml").read_text(encoding="utf-8")
    assert expected == dumps(script.EXPECTED)


def test_the_manifest_names_its_tables_with_their_size_and_digest() -> None:
    manifest = loads(fixture_path("manifest.yaml").read_text(encoding="utf-8"))
    claims = pq.read_table(fixture_path("match_claims.parquet")).to_pylist()
    projections = pq.read_table(fixture_path("projections.parquet")).to_pylist()
    named = {
        "match_claims.parquet": {
            *(row["timeline_a_id"] for row in claims),
            *(row["timeline_b_id"] for row in claims),
        },
        "projections.parquet": {row["timeline_id"] for row in projections},
    }
    order = ["clt_1", "clt_2", "dpt_1", "cpt_1"]
    resources = manifest["resources"]
    assert [(r["id"], r["type"], r["url"]) for r in resources] == [
        ("#resource_1", "MatchClaim", "match_claims.parquet"),
        ("#resource_2", "Projection", "projections.parquet"),
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
    projections = pq.read_table(fixture_path("projections.parquet"))
    assert claims.num_rows == 16
    assert projections.num_rows == 9
    assert match_claim_problems(claims, manifest) == []
    assert projection_problems(projections, manifest) == []


def test_each_projection_a_claim_names_stands_at_its_anchor() -> None:
    claims = pq.read_table(fixture_path("match_claims.parquet")).to_pylist()
    projections = {
        row["id"]: row
        for row in pq.read_table(fixture_path("projections.parquet")).to_pylist()
    }
    named = set()
    for row in claims:
        for side in ("a", "b"):
            event = row[f"event_{side}_id"]
            if not event.startswith("projection_"):
                continue
            named.add(event)
            standing = projections[event]
            assert standing["timeline_id"] == row[f"timeline_{side}_id"]
            kind = standing["number_type"]
            start = coordinate_value(standing["start"], kind)
            assert start == coordinate_value(row["start_anchor"][f"coordinate_{side}"])
            if row["end_anchor"] is None:
                assert standing["duration"] is None
            else:
                end = coordinate_value(row["end_anchor"][f"coordinate_{side}"])
                assert start + coordinate_value(standing["duration"], kind) == end
    assert set(projections) - named == {"projection_10", "projection_11"}
    sentinels = [
        (row["id"], side, row[f"event_{side}_id"])
        for row in claims
        for side in ("a", "b")
        if row[f"event_{side}_id"] in (NOMATCH, CHUNK)
    ]
    assert sentinels == [
        ("claim_11", "a", CHUNK),
        ("claim_11", "b", CHUNK),
        ("claim_12", "b", NOMATCH),
        ("claim_16", "a", CHUNK),
    ]


def test_the_projections_lie_sorted_by_timeline() -> None:
    rows = pq.read_table(fixture_path("projections.parquet")).to_pylist()
    assert [(row["timeline_id"], row["id"]) for row in rows] == [
        ("clt_2", "projection_10"),
        ("cpt_1", "projection_11"),
        ("dpt_1", "projection_1"),
        ("dpt_1", "projection_2"),
        ("dpt_1", "projection_3"),
        ("dpt_1", "projection_4"),
        ("dpt_1", "projection_5"),
        ("dpt_1", "projection_8"),
        ("dpt_1", "projection_9"),
    ]
