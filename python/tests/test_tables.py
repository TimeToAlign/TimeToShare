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
    dumps,
    loads,
    provenance_schema_path,
    with_file_ids,
)
from timetoshare.tables import (  # noqa: E402
    BELIEF_KEYS,
    BELIEF_TYPE,
    COORDINATE_KEYS,
    MATCH_CLAIM_COLUMNS,
    MATCH_CLAIM_SCHEMA,
    PROJECTION_COLUMNS,
    PROJECTION_SCHEMA,
    PROVENANCE_KEYS,
    PROVENANCE_METADATA_KEY,
    PROVENANCE_TYPE,
    TableError,
    check_match_claims,
    check_projections,
    check_succession,
    coordinate_value,
    fixture_path,
    match_claim_problems,
    projection_problems,
    row_provenance,
    succession_problems,
)

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "emit_tables.py"
ACTOR = "https://orcid.org/0000-0002-1825-0097"


def q(numerator: int, denominator: int = 1) -> dict[str, Any]:
    value = Fraction(numerator, denominator)
    return {
        "value": float(value),
        "numerator": value.numerator,
        "denominator": value.denominator,
        "unit": "quarters",
        "number_type": "fraction",
    }


def smp(value: int) -> dict[str, Any]:
    return {
        "value": float(value),
        "numerator": value,
        "denominator": 1,
        "unit": "samples",
        "number_type": "int",
    }


def sec(value: float) -> dict[str, Any]:
    numerator, denominator = value.as_integer_ratio()
    return {
        "value": value,
        "numerator": numerator,
        "denominator": denominator,
        "unit": "seconds",
        "number_type": "float",
    }


def anchor(a: str, cell_a: dict, b: str, cell_b: dict) -> dict[str, Any]:
    return {
        "timeline_a_id": a,
        "coordinate_a": cell_a,
        "timeline_b_id": b,
        "coordinate_b": cell_b,
    }


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


def claim(
    identifier: str,
    event_a: str | None,
    event_b: str | None,
    start: tuple[dict, dict] | None = None,
    end: tuple[dict, dict] | None = None,
    **members: Any,
) -> dict[str, Any]:
    row = {
        "timeline_a_id": "clt_1",
        "timeline_b_id": "dpt_1",
        "start_anchor": None
        if start is None
        else anchor("clt_1", start[0], "dpt_1", start[1]),
        "end_anchor": None if end is None else anchor("clt_1", end[0], "dpt_1", end[1]),
        "is_synchronous": start is not None,
        "is_explicit": True,
        "provenance": None,
        "certainty": 1.0,
        "source_claim_id": None,
        "event_a_id": event_a,
        "event_a_name": None,
        "event_b_id": event_b,
        "event_b_name": None,
        "source_coordinate": None,
        "id": identifier,
        "id_minted": False,
    }
    row.update(members)
    return row


CLAIMS = [
    claim("claim_1", "note_1", "projection_1", (q(0), smp(0)), provenance=PROVENANCE),
    claim("claim_2", "note_2", "projection_2", (q(1), smp(44100)), (q(2), smp(88200))),
    claim("claim_3", "note_3", None, source_coordinate=q(3)),
    claim("claim_4", "note_4", "projection_3"),
]
"""An instant claim, an interval claim, a NOMATCH and a conceptual claim."""


def projection(
    identifier: str,
    start: dict,
    of: tuple[str | None, str | None] | None,
    duration: dict | None = None,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "timeline_id": "dpt_1",
        "start": start,
        "duration": duration,
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
        "is_explicit",
        "provenance",
        "certainty",
        "source_claim_id",
        "event_a_id",
        "event_a_name",
        "event_b_id",
        "event_b_name",
        "source_coordinate",
        "id",
        "id_minted",
    )
    anchor_type = MATCH_CLAIM_SCHEMA.field("start_anchor").type
    assert [field.name for field in anchor_type] == [
        "timeline_a_id",
        "coordinate_a",
        "timeline_b_id",
        "coordinate_b",
    ]
    assert MATCH_CLAIM_SCHEMA.field("end_anchor").type == anchor_type


def test_the_projection_columns() -> None:
    assert PROJECTION_COLUMNS == (
        "id",
        "timeline_id",
        "start",
        "duration",
        "projection_of",
    )
    projection_of = PROJECTION_SCHEMA.field("projection_of").type
    assert [field.name for field in projection_of] == ["timeline_id", "event_id"]


def test_a_coordinate_cell() -> None:
    assert COORDINATE_KEYS == (
        "value",
        "numerator",
        "denominator",
        "unit",
        "number_type",
    )
    cell = PROJECTION_SCHEMA.field("start").type
    assert [(field.name, str(field.type)) for field in cell] == [
        ("value", "double"),
        ("numerator", "int64"),
        ("denominator", "int64"),
        ("unit", "string"),
        ("number_type", "string"),
    ]
    assert MATCH_CLAIM_SCHEMA.field("source_coordinate").type == cell
    assert PROJECTION_SCHEMA.field("duration").type == cell


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
        (smp(441000), Fraction(441000)),
        (sec(0.1), Fraction(3602879701896397, 36028797018963968)),
        ({**q(1, 3), "value": 0.0}, Fraction(1, 3)),
    ],
)
def test_a_coordinate_value_is_read_from_its_number_type(
    cell: dict, value: Fraction
) -> None:
    assert coordinate_value(cell) == value


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
    index = table.column_names.index("is_explicit")
    table = table.set_column(index, "is_explicit", pa.array(["yes"] * 4))
    with pytest.raises(TableError) as error:
        check_match_claims(table)
    assert error.value.problem.code == "schema_violation"
    assert error.value.problem.column == ("is_explicit",)
    assert str(error.value) == "the column 'is_explicit' is string, not bool"


CLAIM_CASES = [
    (
        "id_null",
        put(1, "id", value=None),
        [("schema_violation", 1, ("id",))],
        "'id' is null",
    ),
    (
        "flag_null",
        put(0, "is_explicit", value=None),
        [("schema_violation", 0, ("is_explicit",))],
        "'is_explicit' is null",
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
        "side_missing",
        put(1, "end_anchor", "coordinate_a", "numerator", value=None),
        [("invalid_coordinate", 1, ("end_anchor", "coordinate_a"))],
        "the coordinate has no numerator",
    ),
    (
        "denominator_zero",
        put(2, "source_coordinate", "denominator", value=0),
        [("invalid_coordinate", 2, ("source_coordinate",))],
        "the coordinate's denominator 0 is below 1",
    ),
    (
        "int_denominator",
        put(1, "start_anchor", "coordinate_b", "denominator", value=2),
        [("invalid_coordinate", 1, ("start_anchor", "coordinate_b"))],
        "an int coordinate has the denominator 2",
    ),
    (
        "not_finite",
        put(0, "start_anchor", "coordinate_a", "value", value=float("inf")),
        [("invalid_coordinate", 0, ("start_anchor", "coordinate_a"))],
        "the coordinate's value inf is not finite",
    ),
    (
        "no_event",
        lambda rows: rows[3].update(event_a_id=None, event_b_id=None),
        [("claim_events", 3, ("event_a_id",))],
        "the MatchClaim names no event",
    ),
    (
        "same_timeline",
        put(3, "timeline_b_id", value="clt_1"),
        [("claim_timelines", 3, ("timeline_b_id",))],
        "both sides are 'clt_1'",
    ),
    (
        "nomatch_synchronous",
        put(2, "is_synchronous", value=True),
        [("claim_anchors", 2, ("is_synchronous",))],
        "a NOMATCH MatchClaim is not synchronous",
    ),
    (
        "nomatch_anchor",
        put(2, "start_anchor", value=anchor("clt_1", q(3), "dpt_1", smp(132300))),
        [("claim_anchors", 2, ("start_anchor",))],
        "a NOMATCH MatchClaim has no anchors",
    ),
    (
        "conceptual_anchor",
        put(3, "end_anchor", value=anchor("clt_1", q(3), "dpt_1", smp(132300))),
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
        "end_without_start",
        put(1, "start_anchor", value=None),
        [
            ("claim_anchors", 1, ("start_anchor",)),
            ("claim_anchors", 1, ("end_anchor",)),
        ],
        "a synchronous MatchClaim has a start anchor",
    ),
    (
        "source_coordinate_not_nomatch",
        put(0, "source_coordinate", value=q(0)),
        [("claim_anchors", 0, ("source_coordinate",))],
        "only a NOMATCH MatchClaim has a source coordinate",
    ),
    (
        "anchor_reversed",
        put(0, "start_anchor", value=anchor("dpt_1", smp(0), "clt_1", q(0))),
        [("anchor_timelines", 0, ("start_anchor",))],
        "the anchor joins 'dpt_1' and 'clt_1', the MatchClaim 'clt_1' and 'dpt_1'",
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
                    if value[f"timeline_{side}_id"] == timeline:
                        value[f"coordinate_{side}"] = cell(value[f"coordinate_{side}"])
        if row["source_coordinate"] is not None and timeline == "clt_1":
            row["source_coordinate"] = cell(row["source_coordinate"])


def test_seconds_on_a_samples_timeline_are_refused_only_against_the_manifest() -> None:
    table = claims_table(
        changed(
            CLAIMS,
            lambda rows: _every_cell_of(
                rows, "dpt_1", lambda c: sec(c["value"] / 44100)
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
                rows, "clt_1", lambda c: {**c, "number_type": "float"}
            ),
        )
    )
    assert match_claim_problems(table) == []
    assert found(match_claim_problems(table, MANIFEST)) == [
        ("axis_mismatch", 0, ("start_anchor", "coordinate_a")),
        ("axis_mismatch", 1, ("start_anchor", "coordinate_a")),
        ("axis_mismatch", 1, ("end_anchor", "coordinate_a")),
        ("axis_mismatch", 2, ("source_coordinate",)),
    ]


def test_an_unknown_timeline_is_refused_only_against_the_manifest() -> None:
    table = claims_table(changed(CLAIMS, put(3, "timeline_b_id", value="dpt_9")))
    assert match_claim_problems(table) == []
    assert found(match_claim_problems(table, MANIFEST)) == [
        ("unknown_timeline", 3, ("timeline_b_id",))
    ]
    with pytest.raises(TableError, match="^the manifest has no timeline 'dpt_9'$"):
        check_match_claims(table, MANIFEST)


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
        put(1, "duration", value=smp(-1)),
        [("invalid_duration", 1, ("duration",))],
        "the duration is negative",
    ),
    (
        "duration_on_another_axis",
        put(1, "duration", value=sec(1.0)),
        [("axis_mismatch", 1, ("duration",))],
        "the timeline 'dpt_1' has coordinates in samples (int) and in seconds (float)",
    ),
    (
        "start_malformed",
        put(2, "start", "unit", value="parsecs"),
        [("invalid_coordinate", 2, ("start",))],
        "'parsecs' is no unit",
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


def test_projections_against_the_manifest() -> None:
    rows = changed(PROJECTIONS, put(0, "projection_of", "timeline_id", value="clt_9"))
    for row in rows:
        row["start"] = sec(row["start"]["value"] / 44100)
    rows[1]["duration"] = sec(1.0)
    table = projections_table(rows)
    assert found(projection_problems(table)) == []
    assert found(projection_problems(table, MANIFEST)) == [
        ("axis_mismatch", 0, ("start",)),
        ("unknown_timeline", 0, ("projection_of", "timeline_id")),
        ("axis_mismatch", 1, ("start",)),
        ("axis_mismatch", 1, ("duration",)),
        ("axis_mismatch", 2, ("start",)),
    ]


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
        put(0, "start_anchor", "coordinate_a", "value", value=1e-300),
    ],
    ids=["same", "appended", "provenance", "reordered", "mirror"],
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
    assert claims.num_rows == 15
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
            if event is None or not event.startswith("projection_"):
                continue
            named.add(event)
            standing = projections[event]
            assert standing["timeline_id"] == row[f"timeline_{side}_id"]
            start = coordinate_value(standing["start"])
            assert start == coordinate_value(row["start_anchor"][f"coordinate_{side}"])
            if row["end_anchor"] is None:
                assert standing["duration"] is None
            else:
                end = coordinate_value(row["end_anchor"][f"coordinate_{side}"])
                assert start + coordinate_value(standing["duration"]) == end
    assert named == set(projections)
