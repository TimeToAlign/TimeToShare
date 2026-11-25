"""Statements and their provenance; see README "Statements" and "The rules"."""

from __future__ import annotations

import copy
import math
from typing import Any

import pytest

import timetoshare
from timetoshare import (
    BELIEF_STATES,
    BELIEFS,
    BLANK,
    DEFAULT_BELIEFS,
    FORMAT_CONTEXT,
    MATCHES,
    METHODS,
    NAMESPACE,
    SchemaValidationError,
    candidates,
    check_belief_filter,
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
    with_belief,
    with_candidate,
    with_context,
    with_pair,
    without_pair,
)

from .conftest import CATALOGUE_TEST, MUSICBRAINZ_WORK, m1, m2

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
    assert len(FORMAT_CONTEXT) == 35
    assert list(FORMAT_CONTEXT)[:5] == ["@version", "id", "type", "statements", "list"]
    assert NAMESPACE == "https://timetoalign.github.io/timetoshare/ns#"
    assert FORMAT_CONTEXT["beliefs"] == NAMESPACE + "beliefs"
    assert FORMAT_CONTEXT["actor"] == {"@id": NAMESPACE + "actor", "@type": "@id"}
    assert FORMAT_CONTEXT["belief"] == {"@id": NAMESPACE + "belief", "@type": "@vocab"}
    assert [FORMAT_CONTEXT[word] for word in ("true", "false", "unlikely")] == [
        NAMESPACE + "True",
        NAMESPACE + "False",
        NAMESPACE + "Unlikely",
    ]
    for word in ("status", "confirmed", "proposed", "rejected"):
        assert word not in FORMAT_CONTEXT
    assert BELIEFS == ("true", "false", "unlikely")
    assert METHODS == ("manual", "reconciled", "imported", "inferred")
    assert MATCHES == ("exact", "close", "broad", "narrow", "related")
    assert BLANK.startswith("[\\u0000-\\u0020")


BELIEF_FILTER_REFUSALS = [
    (
        "true",
        "the belief filter takes a collection of states, not the string "
        "'true': write ['true']",
    ),
    (
        ["true", "zzz", "not_false"],
        "'not_false' is no belief state: write 'true', 'undecided', "
        "'unlikely' or 'false'",
    ),
    ([1], "1 is no belief state: write 'true', 'undecided', 'unlikely' or 'false'"),
    (
        [True],
        "true is no belief state: write 'true', 'undecided', 'unlikely' or 'false'",
    ),
    (None, "the belief filter takes a collection of states, not null"),
    ({"true": 1}, 'the belief filter takes a collection of states, not {"true":1}'),
    (
        [["true"]],
        '["true"] is no belief state: write '
        "'true', 'undecided', 'unlikely' or 'false'",
    ),
    (
        ["true", {}, "zzz"],
        "'zzz' is no belief state: write 'true', 'undecided', 'unlikely' or 'false'",
    ),
]
"""Each refusal of a belief filter and its message, the JavaScript package's
too (``statements.test.ts``)."""


def test_the_belief_filter_takes_the_four_states() -> None:
    assert BELIEF_STATES == ("true", "undecided", "unlikely", "false")
    assert DEFAULT_BELIEFS == ("true", "undecided", "unlikely")
    assert check_belief_filter(["false", "true"]) == frozenset({"true", "false"})
    assert check_belief_filter(BELIEF_STATES) == frozenset(BELIEF_STATES)
    assert check_belief_filter(()) == frozenset()


@pytest.mark.parametrize(("beliefs", "message"), BELIEF_FILTER_REFUSALS)
def test_a_belief_filter_of_no_states_is_refused(beliefs: Any, message: str) -> None:
    with pytest.raises(ValueError) as raised:
        check_belief_filter(beliefs)
    assert str(raised.value) == message


def test_iris_expand_by_the_context() -> None:
    context = m2()["@context"]
    assert expand_iri(context, "type") == RDF + "type"
    assert expand_iri(context, "label") == "http://www.w3.org/2000/01/rdf-schema#label"
    assert expand_iri(context, "property") == RDF + "predicate"
    assert expand_iri(context, "beliefs") == NAMESPACE + "beliefs"
    assert expand_iri(context, "belief") == NAMESPACE + "belief"
    assert expand_iri(context, "actor") == NAMESPACE + "actor"
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
                "provenance": [{"property": "k:p", "value": "v"}],
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
    assert list(context)[:35] == list(FORMAT_CONTEXT)
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
        {"property": "rel:prf", "value": {"id": "viaf:1"}}
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


def test_the_entries_and_the_candidates_of_a_subject() -> None:
    value = with_candidate(
        m1(),
        ROOT,
        "wdt:P175",
        PIRES,
        stated_by=[TILIE],
        date="2026-11-18",
        method="inferred",
    )
    value = with_pair(value, ROOT, "type", "schema:VideoObject", provenance={})
    assert [entry["property"] for entry in entries(value, ROOT)] == [
        "wdt:P175",
        "rdf:type",
    ]
    assert candidates(value, ROOT) == [entries(value, ROOT)[0]]
    assert candidates(value, ROOT, EDITOR) == [entries(value, ROOT)[0]]
    believed = with_belief(
        value, ROOT, "wdt:P175", PIRES, actor=EDITOR, belief="false", date="2026-11-19"
    )
    assert candidates(believed, ROOT) == [entries(believed, ROOT)[0]]
    assert candidates(believed, ROOT, EDITOR) == []
    assert candidates(believed, ROOT, TILIE) == [entries(believed, ROOT)[0]]


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
        }
    ]


def test_a_candidate_is_stated_by_a_person_then_believed_false() -> None:
    work = {"id": "wd:Q29117946"}
    candidate = with_candidate(
        m1(),
        ROOT,
        "wdt:P2550",
        work,
        stated_by=[TILIE],
        date="2026-11-18",
        method="inferred",
        basis=["#cpt_2"],
    )
    root = candidate["timelines"][0]
    assert "statements" not in root
    assert root["provenance"] == [
        {
            "property": "wdt:P2550",
            "value": work,
            "stated_by": [TILIE],
            "date": "2026-11-18",
            "method": "inferred",
            "basis": ["#cpt_2"],
        }
    ]
    validate(candidate)
    doubted = with_belief(
        candidate,
        ROOT,
        "wdt:P2550",
        work,
        actor=EDITOR,
        belief="unlikely",
        date="2026-11-19",
        note="n",
    )
    again = with_candidate(
        doubted,
        ROOT,
        "wdt:P2550",
        work,
        stated_by=[EDITOR],
        date="2026-11-19",
        method="manual",
    )
    assert again["timelines"][0]["provenance"] == [
        {
            "property": "wdt:P2550",
            "value": work,
            "stated_by": [EDITOR],
            "date": "2026-11-19",
            "method": "manual",
            "beliefs": [
                {
                    "actor": EDITOR,
                    "belief": "unlikely",
                    "date": "2026-11-19",
                    "note": "n",
                }
            ],
        }
    ]
    labelled = {**work, "label": "Clair de lune"}
    stated = with_pair(
        candidate, ROOT, "wdt:P2550", labelled, actor=EDITOR, date="2026-11-20"
    )
    root = stated["timelines"][0]
    assert root["statements"] == {"wdt:P2550": [labelled]}
    assert root["provenance"] == [
        {
            "property": "wdt:P2550",
            "value": work,
            "stated_by": [TILIE],
            "date": "2026-11-18",
            "method": "inferred",
            "basis": ["#cpt_2"],
            "beliefs": [{"actor": EDITOR, "belief": "true", "date": "2026-11-20"}],
        }
    ]
    assert candidates(stated, ROOT) == []
    validate(stated)
    with pytest.raises(ValueError) as raised:
        with_candidate(
            stated,
            ROOT,
            "wdt:P2550",
            work,
            stated_by=[TILIE],
            date="2026-11-18",
            method="inferred",
        )
    assert str(raised.value) == (
        "'wdt:P2550' already has this value; a stated pair is no candidate"
    )
    disbelieved = with_belief(
        stated, ROOT, "wdt:P2550", work, actor=TILIE, belief="false", date="2026-11-21"
    )
    changed = with_belief(
        disbelieved,
        ROOT,
        "wdt:P2550",
        work,
        actor=EDITOR,
        belief="false",
        date="2026-11-22",
    )
    root = changed["timelines"][0]
    assert root["statements"] == {"wdt:P2550": [labelled]}
    assert root["provenance"][0]["beliefs"] == [
        {"actor": EDITOR, "belief": "false", "date": "2026-11-22"},
        {"actor": TILIE, "belief": "false", "date": "2026-11-21"},
    ]
    validate(changed)
    unstated = without_pair(changed, ROOT, "wdt:P2550", work)
    assert unstated == m1()
    with pytest.raises(ValueError) as raised:
        with_pair(m1(), ROOT, "wdt:P2550", work, actor=EDITOR)
    assert str(raised.value) == "a belief needs a date"


def test_a_belief_in_a_pair_never_stated_creates_its_entry() -> None:
    value = with_belief(
        m1(),
        ("timelines", 0, "regions", 0),
        "type",
        "schema:MusicVideoObject",
        actor=EDITOR,
        belief="false",
        date="2026-11-18",
    )
    assert value["timelines"][0]["regions"][0]["provenance"] == [
        {
            "property": "rdf:type",
            "value": {"id": "schema:MusicVideoObject"},
            "beliefs": [{"actor": EDITOR, "belief": "false", "date": "2026-11-18"}],
        }
    ]
    spelled = [
        (True, "true"),
        (False, "false"),
        (1, "1"),
        ("likely", '"likely"'),
        (None, "null"),
    ]
    for belief, written in spelled:
        with pytest.raises(ValueError) as raised:
            with_belief(
                m1(),
                ROOT,
                "type",
                "schema:Thing",
                actor=EDITOR,
                belief=belief,
                date="2026-11-18",
            )
        assert str(raised.value) == (
            f"{written} is no belief: write 'true', 'false' or 'unlikely'"
        )


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
            lambda: with_candidate(
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
    "belief_actor_repeated": (
        "'https://example.org/people/editor' already holds belief 0 of this entry; "
        "an actor holds one belief"
    ),
    "belief_date_impossible": (
        "'2026-02-30' is no Gregorian calendar date written YYYY-MM-DD"
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
    believed = [
        {
            "property": "wdt:P86",
            "value": {"id": "wd:Q255"},
            "beliefs": [
                {"actor": "wd:Q1", "belief": "true", "date": "2026-11-18"},
                {"actor": "#clt_1", "belief": "unlikely", "date": "2026-11-18"},
                {
                    "actor": "http://www.wikidata.org/entity/Q1",
                    "belief": "false",
                    "date": "2026-11-19",
                },
            ],
        }
    ]
    assert _problem(
        _with_statements({"wdt:P86": [{"id": "wd:Q255"}]}, provenance=believed)
    ) == (
        "belief_actor",
        ("timelines", 0, "provenance", 0, "beliefs", 2, "actor"),
        "'http://www.wikidata.org/entity/Q1' already holds belief 0 of this entry; "
        "an actor holds one belief",
    )
    believed[0]["beliefs"][1]["actor"] = "#cpt_9"
    assert _problem(_with_statements(None, provenance=believed)) == (
        "dangling_target",
        ("timelines", 0, "provenance", 0, "beliefs", 1, "actor"),
        "'#cpt_9' names no element of this manifest",
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
                "role": "jump_target",
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
    value["provenance"] = [{"property": "wdt:P86", "value": {"id": "wd:Q255"}}]
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
        "belief",
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
        {"property": "wdt:P86", "value": "x", "date": math.inf}
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
    value["provenance"] = [{"property": "wdt:P86", "value": {"id": "wd:Q255"}}]
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


# -- references to elements --------------------------------------------------------

RECORD = "https://example.org/record"


def _referring(reference: str) -> dict:
    """M1 naming an element by ``reference`` at every reference position once."""
    value = m1()
    value["@context"]["dcterms"] = "http://purl.org/dc/terms/"
    value["@context"]["rdfs"] = "http://www.w3.org/2000/01/rdf-schema#"
    value["statements"] = {
        "rdfs:seeAlso": [{"id": reference}, {"id": "other.yaml#cpt_2"}]
    }
    value["timelines"][0]["statements"] = {
        "dcterms:source": [{"id": reference}],
        "type": ["schema:VideoObject"],
    }
    value["timelines"][0]["provenance"] = [
        {
            "property": "dcterms:source",
            "value": {"id": reference},
            "basis": [reference, RECORD],
        },
        {
            "property": "rdf:type",
            "value": {"id": "schema:VideoObject"},
            "basis": [reference],
            "service": reference,
        },
        {
            "property": "dcterms:isPartOf",
            "value": {"id": reference},
        },
    ]
    return value


def _nesting(reference: str) -> dict:
    """M1 whose region names an element in nodes, ordered values and ``stated_by``."""
    value = m1()
    value["timelines"][0]["regions"][0]["statements"] = {
        "schema:about": [
            {"schema:mentions": [{"id": reference}]},
            {"label": "Intro", "schema:mentions": [{"id": reference}]},
        ],
        "schema:hasPart": [
            {"list": [{"id": reference}, {"id": reference}]},
            {"list": [{"id": reference}, {"id": "wd:Q1"}]},
        ],
    }
    value["timelines"][0]["regions"][0]["provenance"] = [
        {
            "property": "schema:about",
            "value": {"id": "wd:Q2"},
            "stated_by": [reference, EDITOR],
        },
        {
            "property": "schema:about",
            "value": {"id": "wd:Q3"},
            "stated_by": [reference],
        },
    ]
    return value


def test_references_to_a_renamed_element_are_renamed() -> None:
    for build in (_referring, _nesting):
        given = build("#cpt_2")
        kept = copy.deepcopy(given)
        assert timetoshare.with_references_renamed(given, {"cpt_2": "cpt_3"}) == build(
            "#cpt_3"
        )
        assert given == kept


def test_references_to_a_dropped_element_are_dropped() -> None:
    given = _referring("#cpt_2")
    kept = copy.deepcopy(given)
    result = timetoshare.with_references_renamed(given, {"cpt_2": None})
    expected = _referring("#cpt_2")
    expected["statements"] = {"rdfs:seeAlso": [{"id": "other.yaml#cpt_2"}]}
    expected["timelines"][0]["statements"] = {"type": ["schema:VideoObject"]}
    expected["timelines"][0]["provenance"] = [
        {
            "property": "rdf:type",
            "value": {"id": "schema:VideoObject"},
        }
    ]
    assert result == expected
    assert "provenance" not in result
    assert given == kept


def test_the_actors_of_beliefs_are_renamed_and_dropped() -> None:
    held = {"belief": "true", "date": "2026-11-18"}
    given = m1()
    given["timelines"][0]["provenance"] = [
        {
            "property": "wdt:P86",
            "value": {"id": "wd:Q255"},
            "beliefs": [{"actor": "#cpt_2", **held}, {"actor": EDITOR, **held}],
        },
        {
            "property": "wdt:P175",
            "value": {"id": "wd:Q1"},
            "beliefs": [{"actor": "#cpt_2", **held}],
        },
    ]
    renamed = timetoshare.with_references_renamed(given, {"cpt_2": "cpt_3"})
    entries = renamed["timelines"][0]["provenance"]
    assert [belief["actor"] for belief in entries[0]["beliefs"]] == ["#cpt_3", EDITOR]
    assert entries[1]["beliefs"] == [{"actor": "#cpt_3", **held}]
    dropped = timetoshare.with_references_renamed(given, {"cpt_2": None})
    assert dropped["timelines"][0]["provenance"] == [
        {
            "property": "wdt:P86",
            "value": {"id": "wd:Q255"},
            "beliefs": [{"actor": EDITOR, **held}],
        },
        {"property": "wdt:P175", "value": {"id": "wd:Q1"}},
    ]


def test_nodes_and_ordered_values_left_empty_are_dropped() -> None:
    result = timetoshare.with_references_renamed(_nesting("#cpt_2"), {"cpt_2": None})
    region = result["timelines"][0]["regions"][0]
    assert region["statements"] == {
        "schema:about": [{"label": "Intro"}],
        "schema:hasPart": [{"list": [{"id": "wd:Q1"}]}],
    }
    assert region["provenance"] == [
        {
            "property": "schema:about",
            "value": {"id": "wd:Q2"},
            "stated_by": [EDITOR],
        },
        {"property": "schema:about", "value": {"id": "wd:Q3"}},
    ]


def test_a_rename_of_an_id_nothing_names_changes_nothing() -> None:
    for build in (_referring, _nesting):
        assert timetoshare.with_references_renamed(
            build("#cpt_2"), {"cpt_9": "x"}
        ) == build("#cpt_2")


def test_renames_are_read_in_one_pass() -> None:
    result = timetoshare.with_references_renamed(
        _referring("#cpt_1"), {"cpt_1": "cpt_2", "cpt_2": "cpt_3"}
    )
    assert result == _referring("#cpt_2")


# -- compact IRIs ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("iri", "compact"),
    [
        ("http://www.wikidata.org/entity/Q235650", "wd:Q235650"),
        ("http://www.wikidata.org/prop/direct/P175", "wdt:P175"),
        ("https://schema.org/name", "https://schema.org/name"),
        ("http://d-nb.info/gnd/11862119X", "http://d-nb.info/gnd/11862119X"),
        ("https://d-nb.info/gnd/119018934", "gnd:119018934"),
        ("https://lod.academy/melod/vocab/ontology#Work", "melod:Work"),
        ("http://www.wikidata.org/entity/", "http://www.wikidata.org/entity/"),
        ("urn:uuid:works/1", "urn:uuid:works/1"),
        (MUSICBRAINZ_WORK, MUSICBRAINZ_WORK),
    ],
)
def test_an_iri_is_compacted_by_the_catalogues_prefixes(iri: str, compact: str) -> None:
    prefixes = timetoshare.load_catalogue().prefixes
    assert timetoshare.compact_iri(prefixes, iri) == compact


def test_an_alias_is_read_before_compacting() -> None:
    catalogue = timetoshare.load_catalogue()
    compact = timetoshare.compact_iri(
        catalogue.prefixes, "https://schema.org/name", aliases=catalogue.aliases
    )
    assert compact == "schema:name"
    unaliased = timetoshare.compact_iri(
        catalogue.prefixes, "https://example.org/x/y", aliases=catalogue.aliases
    )
    assert unaliased == "https://example.org/x/y"


def test_the_longest_namespace_wins_and_a_tie_goes_to_the_smaller_name() -> None:
    prefixes = {
        "ex": "http://a.example/",
        "exs": "http://a.example/sub/",
        "a": "http://b/",
    }
    assert timetoshare.compact_iri(prefixes, "http://a.example/sub/x") == "exs:x"
    assert timetoshare.compact_iri(prefixes, "http://a.example/x.1_-") == "ex:x.1_-"
    tied = {"z": "http://b/", "b": "http://b/", "é": "http://b/"}
    assert timetoshare.compact_iri(tied, "http://b/x") == "b:x"
    for rest in ("a/b", "a:b", ".a", "-a", "a b", "a\n"):
        assert (
            timetoshare.compact_iri(prefixes, "http://b/" + rest) == "http://b/" + rest
        )


def _walked() -> dict[str, Any]:
    """Two roots: ``a`` with regions and nested children, then ``e``."""
    return {
        "timetoshare": "0.2.0",
        "timelines": [
            {
                "id": "a",
                "regions": [{"id": "a1"}, 7, {"id": "a2"}],
                "children": [
                    {"id": "b", "regions": [{"id": "b1"}], "children": [{"id": "c"}]},
                    {"id": "d"},
                ],
            },
            {"id": "e"},
        ],
        "groups": [{"id": "g", "members": ["a", "e"]}],
    }


def test_subjects_are_walked_in_subject_order() -> None:
    manifest = _walked()
    walked = list(timetoshare.subjects(manifest))
    assert [(path, kind, element.get("id")) for path, element, kind in walked] == [
        ((), "manifest", None),
        (("timelines", 0), "timeline", "a"),
        (("timelines", 0, "regions", 0), "region", "a1"),
        (("timelines", 0, "regions", 2), "region", "a2"),
        (("timelines", 0, "children", 0), "timeline", "b"),
        (("timelines", 0, "children", 0, "regions", 0), "region", "b1"),
        (("timelines", 0, "children", 0, "children", 0), "timeline", "c"),
        (("timelines", 0, "children", 1), "timeline", "d"),
        (("timelines", 1), "timeline", "e"),
    ]
    assert walked[0][1] is manifest
    assert list(timetoshare.subjects([manifest])) == []
