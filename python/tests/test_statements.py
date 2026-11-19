"""Statements and their provenance; see README "Statements" and "The rules"."""

from __future__ import annotations

import copy
import math
from typing import Any

import pytest

import timetoshare
from timetoshare import (
    BLANK,
    FORMAT_CONTEXT,
    MATCHES,
    METHODS,
    NAMESPACE,
    STATUSES,
    SchemaValidationError,
    entries,
    expand_iri,
    fixture_paths,
    loads,
    manifest_warnings,
    pairs,
    rejection_case,
    rejection_paths,
    same_pair,
    statement_problems,
    subject_path,
    used_prefixes,
    validate,
    with_confirmation,
    with_context,
    with_pair,
    with_proposal,
    with_rejection,
    without_pair,
)

from .conftest import CATALOGUE_TEST, m1, m2

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
EDITOR = "https://example.org/people/editor"
TILIE = "https://example.org/agents/tilie"
PIRES = {"id": "wd:Q235650", "label": "Maria João Pires"}
ROOT = ("timelines", 0)


def _problem(value: Any) -> tuple[str, tuple, str]:
    with pytest.raises(SchemaValidationError) as raised:
        validate(value)
    return raised.value.code, raised.value.path, raised.value.message


def _described(**members: Any) -> dict:
    """M1 with the given members on its root."""
    value = m1()
    value["timelines"][0].update(members)
    return value


# -- the format's context ---------------------------------------------------------


def test_the_format_context_holds_the_terms_and_no_prefix() -> None:
    assert len(FORMAT_CONTEXT) == 33
    assert list(FORMAT_CONTEXT)[:5] == ["@version", "id", "type", "statements", "list"]
    assert NAMESPACE == "https://timetoalign.github.io/timetoshare/ns#"
    assert FORMAT_CONTEXT["status"] == {"@id": NAMESPACE + "status", "@type": "@vocab"}
    assert FORMAT_CONTEXT["confirmed"] == NAMESPACE + "Confirmed"
    assert STATUSES == ("confirmed", "proposed", "rejected")
    assert METHODS == ("manual", "reconciled", "imported", "inferred")
    assert MATCHES == ("exact", "close", "broad", "narrow", "related")
    assert BLANK.startswith("[\\u0000-\\u0020")


def test_iris_expand_by_the_context() -> None:
    context = m2()["@context"]
    assert expand_iri(context, "type") == RDF + "type"
    assert expand_iri(context, "label") == "http://www.w3.org/2000/01/rdf-schema#label"
    assert expand_iri(context, "property") == RDF + "predicate"
    assert expand_iri(context, "confirmed") == NAMESPACE + "Confirmed"
    for keyword in ("statements", "id", "provenance", "timelines", "@version"):
        assert expand_iri(context, keyword) is None, keyword
    assert expand_iri(context, "wdt:P175") == "http://www.wikidata.org/prop/direct/P175"
    for written in ("http://schema.org/name", "urn:isbn:1", "tag:x", "mailto:a@b"):
        assert expand_iri(context, written) == written
    assert expand_iri(context, "info:x") == "info:x"
    for unknown in ("wdtt:P1", "MusicRecording", "label:x"):
        assert expand_iri(context, unknown) is None, unknown
    assert expand_iri(None, "wdt:P175") is None


# -- prefixes and the context -------------------------------------------------------


def test_the_used_prefixes_are_found_at_every_iri_position() -> None:
    assert used_prefixes(m2()) == [
        "dcterms",
        "gnd",
        "melod",
        "rel",
        "schema",
        "viaf",
        "wd",
        "wdt",
        "xsd",
    ]
    value = m1()
    value["timelines"][0]["regions"][0]["provenance"] = [
        {
            "property": "a:p",
            "value": {"id": "b:v", "c:k": [{"id": "d:w"}]},
            "status": "proposed",
            "method": "e:how",
            "basis": ["f:x", "#cpt_2", "other.yaml#x"],
            "stated_by": ["g:who"],
            "service": "h:svc",
        }
    ]
    value["timelines"][0]["statements"] = {
        "http://schema.org/name": ["x"],
        "i:p": [
            {
                "id": "urn:x:1",
                "type": ["j:T"],
                "provenance": [{"property": "k:p", "value": "v", "status": "rejected"}],
            },
            {"@value": "1", "@type": "l:t"},
            {"list": [{"id": "m:x"}, {"id": "tag:a"}]},
        ],
        "type": ["n:C", "mailto:a@b", "info:x"],
    }
    assert used_prefixes(value) == list("abcdefghijklmn")
    value["timelines"][0]["regions"][0]["provenance"][0]["method"] = "manual"
    assert "e" not in used_prefixes(value)


def test_the_context_holds_the_terms_and_the_used_prefixes() -> None:
    described = m2()
    bare = {key: value for key, value in described.items() if key != "@context"}
    before = copy.deepcopy(bare)
    assert (
        with_context(bare, CATALOGUE_TEST["prefixes"])["@context"]
        == (described["@context"])
    )
    assert bare == before
    own = {**described, "@context": {"schema": "https://schema.org/"}}
    context = with_context(own, CATALOGUE_TEST["prefixes"])["@context"]
    assert context["schema"] == "https://schema.org/"
    assert list(context)[:33] == list(FORMAT_CONTEXT)
    assert with_context(m1(), {})["@context"] == FORMAT_CONTEXT
    with pytest.raises(ValueError) as raised:
        with_context(bare, {"wd": "http://www.wikidata.org/entity/"})
    assert str(raised.value) == (
        "the prefix 'dcterms' is declared neither in the manifest's @context "
        "nor in the given prefixes"
    )


# -- subjects, pairs and entries ----------------------------------------------------


def test_a_subject_is_addressed_by_its_path() -> None:
    value = m1()
    assert subject_path(value, None) == ()
    assert subject_path(value, "#cpt_1") == ("timelines", 0)
    assert subject_path(value, "#cpt_2") == ("timelines", 0, "children", 0)
    assert subject_path(value, "#region_1") == ("timelines", 0, "regions", 0)
    with pytest.raises(ValueError) as raised:
        subject_path(value, "cpt_1")
    assert str(raised.value) == (
        "no timeline or region of the manifest has the ID 'cpt_1'"
    )


@pytest.mark.parametrize(
    "path",
    [
        ("timelines", 9),
        ("groups", 0),
        ("timelines", 1, "statements", "dcterms:created", 0),
        ("timelines", 1, "statements", "rel:prf"),
        ("timelines", 1, "statements"),
        ("timelines", 1, "statements", "wdt:P175", 0, "schema:sameAs"),
        ("timelines", 0, "regions", 0),
        ("timelines", 1, "provenance", 0, "value"),
        ("timelines", 1, "statements", "wdt:P175", 0, "label"),
    ],
)
def test_a_path_that_reaches_no_subject_is_refused(path: tuple) -> None:
    value = m2()
    value["timelines"][1]["provenance"] = [
        {"property": "rel:prf", "value": {"id": "viaf:1"}, "status": "rejected"}
    ]
    value["timelines"][1]["statements"]["dcterms:created"] = [
        {"@value": "2025", "@language": "en"}
    ]
    with pytest.raises(ValueError) as raised:
        pairs(value, path)
    pointer = "#" + "".join(f"/{segment}" for segment in path)
    assert str(raised.value) == f"{pointer} addresses no element and no value node"


def test_the_pairs_of_an_element_and_of_a_node() -> None:
    value = m2()
    assert pairs(value, ("timelines", 1)) == [
        ("rel:prf", {"id": "viaf:113931950"}),
        ("schema:sameAs", {"id": "https://www.youtube.com/watch?v=Ch2mrPm1JnM"}),
        ("type", "schema:VideoObject"),
        ("type", "melod:Manifestation"),
        ("wdt:P175", value["timelines"][1]["statements"]["wdt:P175"][0]),
        ("wdt:P31", {"id": "wd:Q98069877"}),
    ]
    node = ("timelines", 1, "statements", "wdt:P175", 0)
    assert pairs(value, node) == [
        ("schema:sameAs", {"id": "viaf:113931950"}),
        ("schema:sameAs", {"id": "gnd:124927521"}),
    ]
    assert pairs(value, ()) == []


def test_the_entries_of_a_subject_by_status() -> None:
    value = with_proposal(
        m1(),
        ROOT,
        "wdt:P175",
        PIRES,
        stated_by=[TILIE],
        date="2026-11-18",
        method="inferred",
    )
    value = with_pair(value, ROOT, "type", "schema:VideoObject", provenance={})
    assert [entry["status"] for entry in entries(value, ROOT)] == [
        "proposed",
        "confirmed",
    ]
    assert entries(value, ROOT, "proposed") == [entries(value, ROOT)[0]]
    assert entries(value, ROOT, "rejected") == []


# -- the same pair ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("a", "b", "same"),
    [
        (("type", "schema:X"), ("rdf:type", {"id": "schema:X"}), True),
        (("type", "schema:X"), ("rdf:type", {"id": "http://schema.org/X"}), True),
        (
            ("wdt:P175", PIRES),
            ("http://www.wikidata.org/prop/direct/P175", {"id": "wd:Q235650"}),
            True,
        ),
        (
            ("wdt:P175", PIRES),
            ("wdt:P175", {"id": "http://www.wikidata.org/entity/Q235650"}),
            True,
        ),
        (("wdt:P175", PIRES), ("wdt:P175", {"id": "wd:Q1"}), False),
        (("wdt:P175", PIRES), ("wdt:P86", PIRES), False),
        (("schema:p", True), ("schema:p", 1), False),
        (("schema:p", "1"), ("schema:p", 1), False),
        (("schema:p", 1), ("schema:p", 1), True),
        (
            ("schema:p", {"@value": "x", "@type": "xsd:date"}),
            (
                "schema:p",
                {"@value": "x", "@type": "http://www.w3.org/2001/XMLSchema#date"},
            ),
            True,
        ),
        (
            ("schema:p", {"@value": "x", "@language": "en"}),
            ("schema:p", {"@value": "x", "@language": "de"}),
            False,
        ),
        (
            ("schema:p", {"label": "A", "rel:x": [1]}),
            ("schema:p", {"label": "A", "rel:x": [1], "provenance": []}),
            True,
        ),
        (("schema:p", {"label": "A"}), ("schema:p", {"label": "B"}), False),
        (
            ("schema:p", {"list": [{"id": "wd:Q1"}, 2]}),
            ("schema:p", {"list": [{"id": "wd:Q1"}, 2]}),
            True,
        ),
        (
            ("schema:p", {"list": [2, {"id": "wd:Q1"}]}),
            ("schema:p", {"list": [{"id": "wd:Q1"}, 2]}),
            False,
        ),
        (
            ("schema:p", {"id": "#cpt_1"}),
            ("schema:p", {"id": "#cpt_1", "label": "x"}),
            True,
        ),
        (
            ("schema:p", {"id": "#cpt_1"}),
            ("schema:p", {"id": "https://example.org/m.yaml#cpt_1"}),
            False,
        ),
        (("schema:p", "x"), ("schema:p", {"@value": "x", "@language": "en"}), False),
    ],
)
def test_the_same_pair(a: tuple, b: tuple, same: bool) -> None:
    context = {**m2()["@context"], "rdf": RDF}
    assert same_pair(context, a, b) is same
    assert same_pair(context, b, a) is same


# -- writing pairs ----------------------------------------------------------------


PROVENANCE = {"stated_by": [EDITOR], "date": "2026-11-18", "method": "manual"}


def test_a_pair_is_stated_with_its_confirmed_entry() -> None:
    original = m1()
    value = with_pair(original, ROOT, "wdt:P175", PIRES, provenance=PROVENANCE)
    assert original == m1()
    root = value["timelines"][0]
    assert root["statements"] == {"wdt:P175": [PIRES]}
    assert root["provenance"] == [
        {
            "date": "2026-11-18",
            "method": "manual",
            "property": "wdt:P175",
            "stated_by": [EDITOR],
            "status": "confirmed",
            "value": {"id": "wd:Q235650"},
        }
    ]
    validate(value)
    for again in (PIRES, {"id": "http://www.wikidata.org/entity/Q235650"}):
        with pytest.raises(ValueError) as raised:
            with_pair(value, ROOT, "wdt:P175", again)
        assert str(raised.value) == "'wdt:P175' already has this value"
    typed = with_pair(value, ROOT, "type", "schema:VideoObject", provenance=PROVENANCE)
    root = typed["timelines"][0]
    assert root["statements"]["type"] == ["schema:VideoObject"]
    assert root["provenance"][1]["property"] == "rdf:type"
    assert root["provenance"][1]["value"] == {"id": "schema:VideoObject"}
    unstated = without_pair(typed, ROOT, "wdt:P175", PIRES)
    unstated = without_pair(unstated, ROOT, "type", "schema:VideoObject")
    assert "statements" not in unstated["timelines"][0]
    assert "provenance" not in unstated["timelines"][0]
    assert unstated == m1()
    with pytest.raises(ValueError) as raised:
        without_pair(unstated, ROOT, "wdt:P175", PIRES)
    assert str(raised.value) == "'wdt:P175' does not have this value"


def test_a_pair_without_provenance_has_no_entry() -> None:
    value = with_pair(m1(), (), "schema:name", "Recording")
    assert value["statements"] == {"schema:name": ["Recording"]}
    assert "provenance" not in value
    literal = with_pair(
        value, (), "schema:position", {"@value": "1", "@language": "en"}, provenance={}
    )
    assert literal["provenance"] == [
        {
            "property": "schema:position",
            "value": {"@value": "1", "@language": "en"},
            "status": "confirmed",
        }
    ]


def test_a_proposal_is_confirmed_then_rejected() -> None:
    work = {"id": "wd:Q29117946"}
    proposed = with_proposal(
        m1(),
        ROOT,
        "wdt:P2550",
        work,
        stated_by=[TILIE],
        date="2026-11-18",
        method="inferred",
        basis=["#cpt_2"],
    )
    root = proposed["timelines"][0]
    assert "statements" not in root
    assert root["provenance"] == [
        {
            "property": "wdt:P2550",
            "value": work,
            "status": "proposed",
            "stated_by": [TILIE],
            "date": "2026-11-18",
            "method": "inferred",
            "basis": ["#cpt_2"],
        }
    ]
    validate(proposed)
    again = with_proposal(
        proposed,
        ROOT,
        "wdt:P2550",
        work,
        stated_by=[EDITOR],
        date="2026-11-19",
        method="manual",
        note="n",
    )
    assert again["timelines"][0]["provenance"] == [
        {
            "property": "wdt:P2550",
            "value": work,
            "status": "proposed",
            "stated_by": [EDITOR],
            "date": "2026-11-19",
            "method": "manual",
            "note": "n",
        }
    ]
    labelled = {**work, "label": "Clair de lune"}
    confirmed = with_confirmation(
        proposed, ROOT, "wdt:P2550", labelled, stated_by=[EDITOR], date="2026-11-19"
    )
    root = confirmed["timelines"][0]
    assert root["statements"] == {"wdt:P2550": [labelled]}
    assert root["provenance"] == [
        {
            "property": "wdt:P2550",
            "value": work,
            "status": "confirmed",
            "stated_by": [EDITOR],
            "date": "2026-11-19",
            "method": "inferred",
            "basis": ["#cpt_2"],
        }
    ]
    validate(confirmed)
    with pytest.raises(ValueError) as raised:
        with_proposal(
            confirmed,
            ROOT,
            "wdt:P2550",
            work,
            stated_by=[TILIE],
            date="2026-11-18",
            method="inferred",
        )
    assert str(raised.value) == (
        "'wdt:P2550' already has this value; a stated pair is not proposed"
    )
    rejected = with_rejection(
        confirmed,
        ROOT,
        "wdt:P2550",
        work,
        stated_by=[EDITOR],
        date="2026-11-20",
        note="the video holds an excerpt",
    )
    root = rejected["timelines"][0]
    assert "statements" not in root
    assert root["provenance"] == [
        {
            "property": "wdt:P2550",
            "value": work,
            "status": "rejected",
            "stated_by": [EDITOR],
            "date": "2026-11-20",
            "method": "inferred",
            "basis": ["#cpt_2"],
            "note": "the video holds an excerpt",
        }
    ]
    validate(rejected)
    restated = with_pair(rejected, ROOT, "wdt:P2550", work)
    assert "provenance" not in restated["timelines"][0]
    reconfirmed = with_confirmation(
        rejected, ROOT, "wdt:P2550", work, stated_by=[EDITOR], date="2026-11-21"
    )
    assert reconfirmed["timelines"][0]["provenance"][0]["status"] == "confirmed"
    with pytest.raises(ValueError) as raised:
        with_confirmation(
            m1(), ROOT, "wdt:P2550", work, stated_by=[EDITOR], date="2026-11-19"
        )
    assert str(raised.value) == "no proposal or rejection of this value of 'wdt:P2550'"


def test_a_rejection_of_a_pair_never_stated_creates_its_entry() -> None:
    value = with_rejection(
        m1(),
        ("timelines", 0, "regions", 0),
        "type",
        "schema:MusicVideoObject",
        stated_by=[EDITOR],
        date="2026-11-18",
    )
    assert value["timelines"][0]["regions"][0]["provenance"] == [
        {
            "property": "rdf:type",
            "value": {"id": "schema:MusicVideoObject"},
            "status": "rejected",
            "stated_by": [EDITOR],
            "date": "2026-11-18",
        }
    ]


def test_a_node_states_its_own_pairs() -> None:
    value = m2()
    node = ("timelines", 1, "statements", "wdt:P175", 0)
    stated = with_pair(
        value, node, "schema:sameAs", {"id": "wd:Q1"}, provenance={"date": "2026-11-18"}
    )
    held = stated["timelines"][1]["statements"]["wdt:P175"][0]
    assert held["schema:sameAs"][-1] == {"id": "wd:Q1"}
    assert held["provenance"] == [
        {
            "property": "schema:sameAs",
            "value": {"id": "wd:Q1"},
            "status": "confirmed",
            "date": "2026-11-18",
        }
    ]
    validate(stated)
    unstated = without_pair(stated, node, "schema:sameAs", {"id": "wd:Q1"})
    assert unstated == value


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (
            lambda: with_pair(m1(), ROOT, "performer", "x"),
            "'performer' is no property: write 'type', a compact IRI or an "
            "absolute IRI",
        ),
        (
            lambda: with_pair(m1(), ROOT, "schema:a b", "x"),
            "'schema:a b' is no property: write 'type', a compact IRI or an "
            "absolute IRI",
        ),
        (
            lambda: with_pair(
                m1(), ROOT, "wdt:P1", "x", provenance={"date": "2026-02-30"}
            ),
            "'2026-02-30' is no Gregorian calendar date written YYYY-MM-DD",
        ),
        (
            lambda: with_proposal(
                m1(),
                ROOT,
                "wdt:P1",
                "x",
                stated_by=[],
                date="18.11.2026",
                method="manual",
            ),
            "'18.11.2026' is no Gregorian calendar date written YYYY-MM-DD",
        ),
        (
            lambda: with_pair(m1(), ("timelines", 9), "wdt:P1", "x"),
            "#/timelines/9 addresses no element and no value node",
        ),
    ],
)
def test_the_writers_refuse_with_their_messages(call: Any, message: str) -> None:
    with pytest.raises(ValueError) as raised:
        call()
    assert str(raised.value) == message


# -- the statement rules -------------------------------------------------------------

PINNED = {
    "context_absent_with_statements": (
        "statements and provenance need the manifest's @context"
    ),
    "reserved_key_term_on_timeline": "'label' is reserved on a timeline",
    "subject_id_not_fragment": (
        "the ID 'Bass Kick' of an element with statements is no IRI fragment"
    ),
    "iri_prefix_undeclared_key": (
        "'wdtt:P175': the prefix 'wdtt' is not declared in @context"
    ),
    "element_value_dangling": "'#cpt_9' names no element of this manifest",
    "element_value_with_label": (
        "'#clt_2' names an element; a value naming an element holds its id alone"
    ),
    "provenance_date_impossible": (
        "'2026-02-30' is no Gregorian calendar date written YYYY-MM-DD"
    ),
    "provenance_repeated": "the entry repeats the pair of entry 0",
    "provenance_type_value_literal": (
        "no pair of this subject matches the entry; an entry that matches none is "
        "proposed or rejected"
    ),
}


@pytest.mark.parametrize("name", sorted(PINNED))
def test_a_statement_case_pins_its_message(name: str) -> None:
    (path,) = [path for path in rejection_paths() if path.stem == name]
    case = rejection_case(path)
    with pytest.raises(SchemaValidationError) as raised:
        timetoshare.validate(case.manifest)
    assert raised.value.message == PINNED[name]


def _with_statements(statements: dict | None = None, **members: Any) -> dict:
    value = m2()
    value["timelines"][0] = {
        "id": "#clt_1",
        "unit": "quarters",
        "length": [8, 1],
        **members,
    }
    if statements is not None:
        value["timelines"][0]["statements"] = statements
    return value


def test_every_message_of_the_statement_rules() -> None:
    region = {"id": "#r", "start": [0, 1], "end": [1, 1], "label": "x"}
    assert _problem(_with_statements(regions=[region])) == (
        "reserved_key",
        ("timelines", 0, "regions", 0, "label"),
        "'label' is reserved on a region",
    )
    value = _with_statements()
    value["value"] = 1
    assert _problem(value) == (
        "reserved_key",
        ("value",),
        "'value' is reserved on the manifest",
    )
    value = _with_statements()
    value["groups"] = [{"id": "#g", "members": ["#clt_1"], "type": "x"}]
    assert _problem(value) == (
        "reserved_key",
        ("groups", 0, "type"),
        "'type' is reserved on a group",
    )
    assert _problem(_with_statements({"schema:position": [1.0]})) == (
        "representation",
        ("timelines", 0, "statements", "schema:position", 0),
        "a statement value is an integer or a string, never a float: 1.0",
    )
    proposed = [
        {"property": "wdt:P86", "value": {"id": "wd:Q255"}, "status": "rejected"}
    ]
    assert _problem(
        _with_statements({"wdt:P86": [{"id": "wd:Q255"}]}, provenance=proposed)
    ) == (
        "provenance_match",
        ("timelines", 0, "provenance", 0),
        "the pair is stated; a rejected pair is never stated",
    )
    confirmed = [{**proposed[0], "status": "confirmed"}]
    assert _problem(
        _with_statements({"wdt:P31": [{"id": "wd:Q1"}]}, provenance=confirmed)
    ) == (
        "provenance_match",
        ("timelines", 0, "provenance", 0),
        "no pair of this subject matches the entry; an entry that matches none is "
        "proposed or rejected",
    )


@pytest.mark.parametrize(
    ("identifier", "fragment"),
    [
        ("clt_1", True),
        ("perf/take:2?x=1", True),
        ("%41b", True),
        ("é", True),
        ("%4", False),
        ("%zz", False),
        ("a|b", False),
        ("a#b", False),
        ("a b", False),
    ],
)
def test_the_id_of_a_described_element_is_an_iri_fragment(
    identifier: str, fragment: bool
) -> None:
    value = _with_statements({"type": ["schema:MusicRecording"]})
    value["timelines"][0]["id"] = "#" + identifier
    if fragment:
        validate(value)
    else:
        assert _problem(value) == (
            "iri",
            ("timelines", 0, "id"),
            f"the ID '{identifier}' of an element with statements is no IRI fragment",
        )


@pytest.mark.parametrize(
    "date", ["2024-02-29", "2000-02-29", "0001-01-01", "9999-12-31"]
)
def test_a_calendar_date_validates(date: str) -> None:
    entry = {
        "property": "wdt:P31",
        "value": {"id": "wd:Q1"},
        "status": "confirmed",
        "date": date,
    }
    validate(_with_statements({"wdt:P31": [{"id": "wd:Q1"}]}, provenance=[entry]))


@pytest.mark.parametrize(
    "date",
    [
        "2026-02-30",
        "2023-02-29",
        "2100-02-29",
        "2026-11-31",
        "2026-13-01",
        "2026-00-10",
        "2026-11-00",
        "0000-01-01",
    ],
)
def test_an_impossible_date_is_refused(date: str) -> None:
    entry = {
        "property": "wdt:P31",
        "value": {"id": "wd:Q1"},
        "status": "confirmed",
        "date": date,
    }
    assert _problem(
        _with_statements({"wdt:P31": [{"id": "wd:Q1"}]}, provenance=[entry])
    ) == (
        "calendar_date",
        ("timelines", 0, "provenance", 0, "date"),
        f"'{date}' is no Gregorian calendar date written YYYY-MM-DD",
    )


def test_a_reference_names_an_id_of_any_kind() -> None:
    value = _with_statements(
        conversion_maps=[
            {
                "id": "#chain",
                "type": "ChainMap",
                "source_unit": "quarters",
                "target_unit": "seconds",
                "maps": [
                    {
                        "id": "#inner",
                        "type": "LinearMap",
                        "source_unit": "quarters",
                        "target_unit": "seconds",
                    }
                ],
            }
        ],
        flow_control=[
            {
                "id": "#segno",
                "type": "jump_to",
                "manifestation": "segno",
                "coordinate": [0, 1],
            }
        ],
    )
    value["id"] = "#bundle"
    value["groups"] = [{"id": "#g", "members": ["#clt_1"]}]
    value["measure_maps"] = [{"id": "#mm", "rows": [{"count": 1, "qstamp": [0, 1]}]}]
    value["graphical"] = {
        "timestamps": [
            {
                "id": "#timestamp_1",
                "timeline": "#clt_1",
                "coordinate": [0, 1],
                "name": "x",
            }
        ]
    }
    names = [
        "#bundle",
        "#g",
        "#mm",
        "#chain",
        "#inner",
        "#segno",
        "#timestamp_1",
        "#cpt_1",
    ]
    value["timelines"][0]["statements"] = {
        "dcterms:source": [{"id": name} for name in names]
    }
    value["timelines"][0]["provenance"] = [
        {
            "property": "dcterms:source",
            "value": {"id": "#g"},
            "status": "confirmed",
            "basis": ["#mm", "other.yaml#nothing", "urn:x:1"],
            "stated_by": ["#bundle", "tag:example.org,2026:x"],
            "service": "#segno",
        }
    ]
    validate(value)
    value["timelines"][0]["provenance"][0]["service"] = "#nowhere"
    assert _problem(value) == (
        "dangling_target",
        ("timelines", 0, "provenance", 0, "service"),
        "'#nowhere' names no element of this manifest",
    )


def test_allowed_keys_and_a_manifest_without_statements_pass() -> None:
    value = _with_statements(
        regions=[
            {
                "id": "#r",
                "start": [0, 1],
                "end": [1, 1],
                "statements": {"type": ["schema:Thing"]},
            }
        ]
    )
    value["groups"] = [{"id": "#g", "members": ["#clt_1"]}]
    value["provenance"] = [
        {"property": "wdt:P86", "value": {"id": "wd:Q255"}, "status": "proposed"}
    ]
    value["id"] = "#bundle"
    validate(value)
    plain = {
        "timetoshare": "0.2.0",
        "timelines": [{"id": "#a", "unit": "seconds", "length": 1.0}],
    }
    validate(plain)


def test_the_rules_come_in_their_order() -> None:
    value = m1()
    del value["@context"]
    value["timelines"][0].update(statements={"wdtt:P1": ["x"]}, label="x")
    problems = statement_problems(value)
    assert [(problem.code, problem.path) for problem in problems] == [
        ("context", ("timelines", 0, "statements")),
        ("reserved_key", ("timelines", 0, "label")),
        ("iri", ("timelines", 0, "statements", "wdtt:P1")),
    ]
    assert _problem(value)[:2] == (problems[0].code, problems[0].path)


# -- statements alone ------------------------------------------------------------


def _is_statement_case(name: str) -> bool:
    return name.split("_")[0] in (
        "context",
        "iri",
        "type",
        "statement",
        "statements",
        "ordered",
        "value",
        "provenance",
        "element",
        "subject",
        "reserved",
    )


@pytest.mark.parametrize("path", rejection_paths(), ids=lambda path: path.stem)
def test_the_statement_check_alone_reports_the_statement_cases(path: Any) -> None:
    case = rejection_case(path)
    found = [
        (problem.code, problem.path) for problem in statement_problems(case.manifest)
    ]
    if path.stem.startswith("context_absent"):
        assert found[0] == (case.code, case.path)
        assert {code for code, _ in found[1:]} == {"iri"}
    elif _is_statement_case(path.stem):
        assert found == [(case.code, case.path)]
    else:
        assert found == []


@pytest.mark.parametrize("path", fixture_paths(), ids=lambda path: path.name)
def test_the_statement_check_finds_nothing_in_a_fixture(path: Any) -> None:
    assert statement_problems(loads(path.read_text(encoding="utf-8"))) == []


def test_the_statement_check_ignores_everything_else() -> None:
    value = m2()
    value["timetoshare"] = "9.9.9"
    value["timelines"].append({"id": "#clt_6", "unit": "beats", "length": 1})
    value["groups"] = [{"id": "#g", "members": ["#ghost"]}]
    assert statement_problems(value) == []


def test_the_statement_check_reports_each_broken_member() -> None:
    value = m1()
    del value["@context"]["provenance"]
    value["timelines"][0]["statements"] = {}
    value["timelines"][0]["regions"][0]["provenance"] = [
        {"property": "wdt:P86", "value": "x", "status": "proposed", "date": math.inf}
    ]
    assert [
        (problem.code, problem.path, problem.message)
        for problem in statement_problems(value)
    ] == [
        ("schema", ("@context",), "'provenance' is a required property"),
        ("schema", ("timelines", 0, "statements"), "{} should be non-empty"),
        (
            "finite_number",
            ("timelines", 0, "regions", 0, "provenance", 0, "date"),
            "date of 'region_1' is not a finite number",
        ),
    ]


# -- warnings ------------------------------------------------------------------


def test_the_warnings_of_a_valid_manifest() -> None:
    plain = {"timetoshare": "0.2.0", "timelines": []}
    assert manifest_warnings(plain) == [
        {
            "code": "context_absent",
            "path": [],
            "message": "the manifest has no @context",
        }
    ]
    blank = "the manifest has statements but no ID; its subject is a blank node"
    value = {**m2(), "statements": {"type": ["schema:MusicComposition"]}}
    assert manifest_warnings(value) == [
        {"code": "bundle_blank", "path": ["statements"], "message": blank}
    ]
    value["provenance"] = [
        {"property": "wdt:P86", "value": {"id": "wd:Q255"}, "status": "proposed"}
    ]
    assert manifest_warnings(value) == [
        {"code": "bundle_blank", "path": ["statements"], "message": blank}
    ]
    del value["statements"]
    assert manifest_warnings(value) == [
        {"code": "bundle_blank", "path": ["provenance"], "message": blank}
    ]
    assert manifest_warnings({**value, "id": "#bundle"}) == []
    assert manifest_warnings(m1()) == []
    with pytest.raises(SchemaValidationError):
        manifest_warnings({**m1(), "statements": {}})
