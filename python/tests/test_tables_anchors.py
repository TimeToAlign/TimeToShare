"""The derivation of AlignmentAnchors and potential MatchStamps, checked
against the fixture's expected values, written by hand (see "From
MatchClaims to anchors" in README.md)."""

from __future__ import annotations

import json
from fractions import Fraction
from typing import Any

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from timetoshare import loads  # noqa: E402
from timetoshare.tables import (  # noqa: E402
    BELIEF_FILTERS,
    MATCH_CLAIM_SCHEMA,
    PROVENANCE_METADATA_KEY,
    AlignmentAnchor,
    TimelineCoordinate,
    alignment_anchors,
    believed_rows,
    fixture_path,
    potential_matchstamps,
)

ACTOR = "https://orcid.org/0000-0002-1825-0097"
OTHER_ACTOR = "https://orcid.org/0000-0001-5109-3700"


def _table() -> Any:
    return pq.read_table(fixture_path("match_claims.parquet"))


def _cases() -> list[dict[str, Any]]:
    return loads(fixture_path("expected.yaml").read_text(encoding="utf-8"))["cases"]


def _coordinate(entry: dict[str, Any]) -> TimelineCoordinate:
    value = entry["value"]
    exact = Fraction(*value) if isinstance(value, list) else Fraction(value)
    return TimelineCoordinate(entry["timeline_id"], exact)


def _case_id(case: dict[str, Any]) -> str:
    believer = {None: "nobody", ACTOR: "actor", OTHER_ACTOR: "other"}[case["believer"]]
    return f"{believer}-{case['belief']}"


def test_the_expected_file_has_the_four_filter_cases() -> None:
    assert [(case["believer"], case["belief"]) for case in _cases()] == [
        (None, "not_false"),
        (ACTOR, "not_false"),
        (ACTOR, "true"),
        (OTHER_ACTOR, "true"),
    ]


@pytest.mark.parametrize("case", _cases(), ids=_case_id)
def test_the_unique_anchors(case: dict[str, Any]) -> None:
    derived = alignment_anchors(_table(), case["believer"], case["belief"])
    expected = [
        (
            AlignmentAnchor(
                tuple(_coordinate(entry) for entry in anchor["coordinates"])
            ),
            tuple(anchor["match_claims"]),
        )
        for anchor in case["alignment_anchors"]
    ]
    assert list(derived.items()) == expected


@pytest.mark.parametrize("case", _cases(), ids=_case_id)
def test_the_potential_matchstamps(case: dict[str, Any]) -> None:
    table = _table()
    derived = potential_matchstamps(table, case["believer"], case["belief"])
    expected = [
        (
            tuple(_coordinate(entry) for entry in stamp["coordinates"]),
            tuple(stamp["match_claims"]),
        )
        for stamp in case["potential_matchstamps"]
    ]
    assert [(stamp.coordinates, stamp.match_claims) for stamp in derived] == expected
    anchors = alignment_anchors(table, case["believer"], case["belief"])
    for stamp in derived:
        assert stamp.alignment_anchors == tuple(
            anchor for anchor in anchors if anchor.coordinates[0] in stamp.coordinates
        )


def test_the_counts_of_the_fixture() -> None:
    table = _table()
    assert len(alignment_anchors(table)) == 14
    assert len(potential_matchstamps(table)) == 11
    coordinates = {
        coordinate
        for stamp in potential_matchstamps(table)
        for coordinate in stamp.coordinates
    }
    assert len(coordinates) == 25


@pytest.mark.parametrize(
    ("believer", "belief", "rows"),
    [
        (None, "not_false", list(range(15))),
        (None, "true", list(range(15))),
        (ACTOR, "not_false", [index for index in range(15) if index != 12]),
        (ACTOR, "true", [0, 10]),
        (OTHER_ACTOR, "not_false", list(range(15))),
        (OTHER_ACTOR, "true", [12, 13]),
        ("https://orcid.org/0000-0000-0000-0000", "not_false", list(range(15))),
        ("https://orcid.org/0000-0000-0000-0000", "true", []),
    ],
)
def test_the_belief_filter(believer: str | None, belief: str, rows: list[int]) -> None:
    assert believed_rows(_table(), believer, belief) == rows


def test_the_belief_filter_takes_two_words() -> None:
    assert BELIEF_FILTERS == ("not_false", "true")
    with pytest.raises(ValueError) as raised:
        believed_rows(_table(), ACTOR, "false")
    assert (
        str(raised.value) == "'false' is no belief filter: write 'not_false' or 'true'"
    )


def test_the_belief_filter_reads_a_provenance_shared_by_every_row() -> None:
    rows = _table().to_pylist()[:2]
    for row in rows:
        row["provenance"] = None
    shared = {"beliefs": [{"actor": ACTOR, "belief": "false", "date": "2026-11-21"}]}
    table = pa.Table.from_pylist(
        rows, schema=MATCH_CLAIM_SCHEMA
    ).replace_schema_metadata({PROVENANCE_METADATA_KEY: json.dumps(shared)})
    assert believed_rows(table, ACTOR) == []
    assert believed_rows(table) == [0, 1]
    assert alignment_anchors(table, ACTOR) == {}
