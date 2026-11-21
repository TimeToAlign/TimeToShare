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
    BELIEF_STATES,
    DEFAULT_BELIEFS,
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


NOT_FALSE = ["true", "undecided", "unlikely"]


def _case_id(case: dict[str, Any]) -> str:
    believer = {None: "nobody", ACTOR: "actor", OTHER_ACTOR: "other"}[case["believer"]]
    return f"{believer}-{'+'.join(case['beliefs'])}"


def test_the_expected_file_has_the_six_filter_cases() -> None:
    assert [(case["believer"], case["beliefs"]) for case in _cases()] == [
        (None, NOT_FALSE),
        (ACTOR, NOT_FALSE),
        (ACTOR, ["true"]),
        (OTHER_ACTOR, ["true"]),
        (ACTOR, ["undecided"]),
        (ACTOR, ["unlikely", "false"]),
    ]


@pytest.mark.parametrize("case", _cases(), ids=_case_id)
def test_the_unique_anchors(case: dict[str, Any]) -> None:
    derived = alignment_anchors(_table(), case["believer"], case["beliefs"])
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
    derived = potential_matchstamps(table, case["believer"], case["beliefs"])
    expected = [
        (
            tuple(_coordinate(entry) for entry in stamp["coordinates"]),
            tuple(stamp["match_claims"]),
        )
        for stamp in case["potential_matchstamps"]
    ]
    assert [(stamp.coordinates, stamp.match_claims) for stamp in derived] == expected
    anchors = alignment_anchors(table, case["believer"], case["beliefs"])
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


NOBODY = "https://orcid.org/0000-0000-0000-0000"
UNDECIDED_FOR_ACTOR = [1, 2, 3, 4, 6, 7, 8, 9, 11, 13, 14]


@pytest.mark.parametrize(
    ("believer", "beliefs", "rows"),
    [
        (None, NOT_FALSE, list(range(15))),
        (None, ["true"], list(range(15))),
        (None, [], list(range(15))),
        (ACTOR, NOT_FALSE, [index for index in range(15) if index != 12]),
        (ACTOR, ["true"], [0, 10]),
        (ACTOR, ["undecided"], UNDECIDED_FOR_ACTOR),
        (ACTOR, ["unlikely"], [5]),
        (ACTOR, ["false"], [12]),
        (ACTOR, ["unlikely", "false"], [5, 12]),
        (ACTOR, [], []),
        (ACTOR, list(BELIEF_STATES), list(range(15))),
        (OTHER_ACTOR, NOT_FALSE, list(range(15))),
        (OTHER_ACTOR, ["true"], [12, 13]),
        (OTHER_ACTOR, ["false"], []),
        (NOBODY, NOT_FALSE, list(range(15))),
        (NOBODY, ["true"], []),
        (NOBODY, ["undecided"], list(range(15))),
    ],
)
def test_the_belief_filter(
    believer: str | None, beliefs: list[str], rows: list[int]
) -> None:
    assert believed_rows(_table(), believer, beliefs) == rows


def test_the_belief_filter_keeps_every_state_but_false_by_default() -> None:
    assert BELIEF_STATES == ("true", "undecided", "unlikely", "false")
    assert DEFAULT_BELIEFS == ("true", "undecided", "unlikely")
    table = _table()
    assert believed_rows(table, ACTOR) == believed_rows(table, ACTOR, NOT_FALSE)
    assert believed_rows(table, ACTOR, {"undecided", "true", "unlikely"}) == [
        index for index in range(15) if index != 12
    ]


@pytest.mark.parametrize(
    ("beliefs", "message"),
    [
        (
            "true",
            "the belief filter takes a collection of states, not the string "
            "'true': write ['true']",
        ),
        (
            ["true", "not_false"],
            "'not_false' is no belief state: write 'true', 'undecided', "
            "'unlikely' or 'false'",
        ),
    ],
)
def test_the_belief_filter_refuses_what_is_no_collection_of_states(
    beliefs: Any, message: str
) -> None:
    for believer in (ACTOR, None):
        with pytest.raises(ValueError) as raised:
            believed_rows(_table(), believer, beliefs)
        assert str(raised.value) == message


def test_the_belief_filter_compares_actors_as_iris() -> None:
    table = _table()
    compact = "orcid:0000-0002-1825-0097"
    context = {"orcid": "https://orcid.org/"}
    assert believed_rows(table, compact, ["true"], context=context) == [0, 10]
    assert believed_rows(table, compact, ["false"], context=context) == [12]
    assert believed_rows(table, compact, ["true"]) == []
    assert believed_rows(table, compact, ["undecided"]) == list(range(15))
    assert [
        anchor.coordinates
        for anchor in alignment_anchors(table, compact, ["true"], context=context)
    ] == [anchor.coordinates for anchor in alignment_anchors(table, ACTOR, ["true"])]
    assert potential_matchstamps(
        table, compact, ["unlikely"], context=context
    ) == potential_matchstamps(table, ACTOR, ["unlikely"])


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
