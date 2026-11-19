"""The catalogue of systems, verbs and types; see README "The catalogue"."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from timetoshare import (
    Rectangle,
    dumps,
    instantiate,
    load_catalogue,
    loads,
    read_catalogue,
    recognize,
    rectangles,
    verb_of,
)

from .conftest import CATALOGUE_TEST, MUSICBRAINZ_WORK, m1, m2

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = REPOSITORY_ROOT / "catalogue"
PIRES = "Maria João Pires"


def _test() -> Any:
    return read_catalogue(CATALOGUE_TEST)


# -- the shipped file -------------------------------------------------------------


def test_the_shipped_catalogue_is_canonical_and_valid() -> None:
    text = (CATALOGUE / "catalogue.yaml").read_text(encoding="utf-8")
    document = loads(text)
    assert dumps(document) == text
    schema = json.loads((CATALOGUE / "catalogue.schema.json").read_text("utf-8"))
    assert schema["$id"] == (
        "https://timetoalign.github.io/timetoshare/0.2.0/catalogue.schema.json"
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(document)
    assert load_catalogue() is load_catalogue()
    assert load_catalogue() == read_catalogue(document)
    assert load_catalogue().verbs[0]["id"] == "is_a"


# -- reading -----------------------------------------------------------------------


def test_the_test_catalogue_is_read_as_given() -> None:
    catalogue = _test()
    assert catalogue.prefixes == CATALOGUE_TEST["prefixes"]
    assert catalogue.aliases == {"https://schema.org/": "http://schema.org/"}
    assert list(catalogue.systems) == CATALOGUE_TEST["systems"]
    assert list(catalogue.verbs) == CATALOGUE_TEST["verbs"]
    assert list(catalogue.types) == CATALOGUE_TEST["types"]


def _system(document: dict, name: str) -> dict:
    return next(system for system in document["systems"] if system["id"] == name)


def _verb(document: dict, name: str) -> dict:
    return next(verb for verb in document["verbs"] if verb["id"] == name)


def _thing(document: dict) -> dict:
    return _system(document, "wikidata")["things"][0]


BROKEN: dict[str, tuple[Callable[[dict], None], str]] = {
    "system twice": (
        lambda d: d["systems"].append(copy.deepcopy(d["systems"][2])),
        "the catalogue holds the system 'melody' twice",
    ),
    "thing twice": (
        lambda d: _system(d, "fallback")["things"].append(copy.deepcopy(_thing(d))),
        "the catalogue holds the thing 'wikidata' twice",
    ),
    "verb twice": (
        lambda d: d["verbs"].append(copy.deepcopy(d["verbs"][1])),
        "the catalogue holds the verb 'same_as' twice",
    ),
    "type twice": (
        lambda d: d["types"].append(copy.deepcopy(d["types"][0])),
        "the catalogue holds the type 'video' twice",
    ),
    "system prefix": (
        lambda d: _system(d, "melody")["prefixes"].append("nope"),
        "the catalogue uses the prefix 'nope' without declaring it",
    ),
    "thing prefix": (
        lambda d: _thing(d).update(prefix="nope"),
        "the catalogue uses the prefix 'nope' without declaring it",
    ),
    "thing class": (
        lambda d: _thing(d).update(lrmoo_class="nope:F1_Work"),
        "the catalogue uses the prefix 'nope' without declaring it",
    ),
    "pattern key": (
        lambda d: _verb(d, "same_as")["patterns"]["fallback"][0].update(
            pattern={"nope:sameAs": [{"id": "?"}]}
        ),
        "the catalogue uses the prefix 'nope' without declaring it",
    ),
    "pattern type": (
        lambda d: d["types"][0]["is_a"]["fallback"][0].update(
            pattern={"type": ["nope:Video"]}
        ),
        "the catalogue uses the prefix 'nope' without declaring it",
    ),
    "pattern node id": (
        lambda d: _verb(d, "performed_by")["patterns"]["melody"][0]["pattern"][
            "melod:hasContribution"
        ][0].update({"melod:hasRole": [{"id": "nope:Performer"}]}),
        "the catalogue uses the prefix 'nope' without declaring it",
    ),
    "verb system": (
        lambda d: _verb(d, "same_as")["patterns"].update(
            nowhere=[{"pattern": {"schema:sameAs": [{"id": "?"}]}}]
        ),
        "the catalogue names the system 'nowhere', which it does not hold",
    ),
    "type lookup": (
        lambda d: d["types"][0]["lookup"].append("nowhere"),
        "the catalogue names the system 'nowhere', which it does not hold",
    ),
    "when value": (
        lambda d: _verb(d, "same_as")["patterns"]["fallback"][0].update(
            when={"value": ["imslp"]}
        ),
        "the catalogue names the thing 'imslp', which no system holds",
    ),
    "type verb": (
        lambda d: d["types"][0]["verbs"].append("recorded_at"),
        "the catalogue names the verb 'recorded_at', which it does not hold",
    ),
    "when subject": (
        lambda d: _verb(d, "same_as")["patterns"]["fallback"][0].update(
            when={"subject": ["release"]}
        ),
        "the catalogue names the type 'release', which it does not hold",
    ),
    "two groups": (
        lambda d: _thing(d)["patterns"].append("https://x/(a)(b)"),
        "pattern 'https://x/(a)(b)' of thing 'wikidata' has 2 capturing groups; "
        "it needs exactly one",
    ),
    "named group": (
        lambda d: _thing(d)["patterns"].append("https://x/(?P<v>a)"),
        "pattern 'https://x/(?P<v>a)' of thing 'wikidata' uses syntax outside the "
        "shared subset; only (?:, (?= and (?! may follow '(?'",
    ),
    "unbalanced": (
        lambda d: _thing(d)["patterns"].append("https://x/(a"),
        "pattern 'https://x/(a' of thing 'wikidata' is no regular expression",
    ),
    "two rules": (
        lambda d: (
            d["types"][0]["verbs"].append("recorded_at"),
            d["verbs"].append(copy.deepcopy(d["verbs"][1])),
        ),
        "the catalogue holds the verb 'same_as' twice",
    ),
}


@pytest.mark.parametrize("name", list(BROKEN))
def test_each_cross_reference_rule_has_its_message(name: str) -> None:
    document = copy.deepcopy(CATALOGUE_TEST)
    change, message = BROKEN[name]
    change(document)
    with pytest.raises(ValueError) as raised:
        read_catalogue(document)
    assert str(raised.value) == message


def test_a_literal_constant_of_a_pattern_is_no_compact_iri() -> None:
    document = copy.deepcopy(CATALOGUE_TEST)
    _verb(document, "conducted_by")["patterns"]["musicbrainz"][0]["pattern"][
        "schema:contributor"
    ][0]["schema:roleName"] = ["nope:bar"]
    catalogue = read_catalogue(document)
    assert catalogue.verbs == tuple(document["verbs"])


# -- recognising URLs -----------------------------------------------------------------


def test_urls_are_recognised_by_the_things_of_the_systems() -> None:
    catalogue = _test()
    assert recognize(catalogue, "https://www.wikidata.org/wiki/Q235650") == (
        "wikidata",
        "wikidata",
        "Q235650",
        "http://www.wikidata.org/entity/Q235650",
    )
    upper = "https://musicbrainz.org/work/8D331505-4D88-39AE-81C7-BEC5DA77AF96"
    assert recognize(catalogue, upper) == (
        "musicbrainz",
        "musicbrainz_work",
        "8d331505-4d88-39ae-81c7-bec5da77af96",
        MUSICBRAINZ_WORK,
    )
    for url in (
        "not a url",
        "https://www.wikidata.org/wiki/Q 1",
        "https://example.org/Q1",
    ):
        assert recognize(catalogue, url) is None, url


def test_a_thing_without_an_iri_template_gives_its_decoded_value() -> None:
    document = copy.deepcopy(CATALOGUE_TEST)
    _system(document, "fallback")["things"].append(
        {
            "id": "imslp",
            "kind": "work",
            "name": "IMSLP",
            "iri": None,
            "scheme_uri": "http://www.wikidata.org/entity/P839",
            "lrmoo_class": None,
            "lowercase": False,
            "patterns": ["https?://imslp\\.org/wiki/([^?#]+)"],
        }
    )
    catalogue = read_catalogue(document)
    assert recognize(catalogue, "https://imslp.org/wiki/Piano%20Sonata") == (
        "fallback",
        "imslp",
        "Piano_Sonata",
        None,
    )
    assert recognize(catalogue, "https://imslp.org/wiki/%FF") is None


# -- instantiating ------------------------------------------------------------------


def test_a_verb_is_instantiated_in_a_system() -> None:
    catalogue = _test()
    assert instantiate(
        catalogue, "performed_by", "wikidata", "wd:Q235650", label=PIRES
    ) == [("wdt:P175", {"id": "wd:Q235650", "label": PIRES})]
    assert instantiate(
        catalogue, "performed_by", "musicbrainz", "wd:Q235650", slots={"role": "piano"}
    ) == [
        (
            "schema:contributor",
            {
                "type": ["schema:OrganizationRole"],
                "schema:contributor": [{"id": "wd:Q235650"}],
                "schema:roleName": ["piano"],
            },
        )
    ]
    assert instantiate(catalogue, "is_a", "fallback", "schema:VideoObject") == [
        ("type", "schema:VideoObject")
    ]
    assert instantiate(catalogue, "part_of", "fallback", "#cpt_1", alternative=1) == [
        ("dcterms:hasPart", {"id": "#cpt_1"})
    ]


@pytest.mark.parametrize(
    ("arguments", "options", "message"),
    [
        (
            ("performed_by", "musicbrainz", "wd:Q1"),
            {},
            "the pattern of 'performed_by' in 'musicbrainz' needs a value for '?role'",
        ),
        (
            ("part_of", "fallback", "#cpt_1"),
            {"alternative": 2},
            "the verb 'part_of' has 2 patterns in 'fallback'",
        ),
        (("x", "fallback", "y"), {}, "the catalogue has no verb 'x'"),
        (
            ("conducted_by", "wikidata", "wd:Q1"),
            {},
            "the verb 'conducted_by' has no pattern in 'wikidata'",
        ),
    ],
)
def test_instantiating_refuses_with_its_message(
    arguments: tuple, options: dict, message: str
) -> None:
    with pytest.raises(ValueError) as raised:
        instantiate(_test(), *arguments, **options)
    assert str(raised.value) == message


# -- reading a pair as a verb ---------------------------------------------------------


def _role(name: str) -> dict:
    return {
        "type": ["schema:OrganizationRole"],
        "schema:contributor": [{"id": "wd:Q1"}],
        "schema:roleName": [name],
    }


@pytest.mark.parametrize(
    ("property", "value", "expected"),
    [
        ("rel:prf", {"id": "viaf:113931950"}, ("performed_by", False)),
        ("schema:contributor", _role("conductor"), ("conducted_by", False)),
        ("schema:contributor", _role("pianist"), ("performed_by", False)),
        ("dcterms:hasPart", {"id": "#cpt_1"}, ("part_of", True)),
        ("dcterms:isPartOf", {"id": "#cpt_1"}, ("part_of", False)),
        ("dcterms:created", {"@value": "2025-12-05", "@type": "xsd:date"}, None),
        ("type", "schema:VideoObject", ("is_a", False)),
        ("wdt:P31", {"id": "wd:Q98069877"}, ("is_a", False)),
        ("https://schema.org/sameAs", {"id": "wd:Q1"}, ("same_as", False)),
        ("rel:prf", "Maria João Pires", None),
        ("wdtt:P175", {"id": "wd:Q1"}, None),
        ("rdf:type", "schema:MusicRecording", ("is_a", False)),
        ("type", {"list": ["schema:VideoObject"]}, None),
        (
            "schema:contributor",
            {**_role("pianist"), "schema:roleName": [{"list": ["pianist"]}]},
            None,
        ),
    ],
)
def test_a_pair_is_read_as_a_verb(property: str, value: Any, expected: Any) -> None:
    context = {**m2()["@context"], "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}
    assert verb_of(_test(), context, property, value) == expected


def test_a_template_item_matches_any_item_and_counts_once() -> None:
    document = copy.deepcopy(CATALOGUE_TEST)
    thing = {"type": ["schema:Thing"]}
    document["verbs"].extend(
        [
            {
                "id": "about_subject",
                "label": "about a subject",
                "patterns": {
                    "fallback": [
                        {"pattern": {"schema:about": [{"schema:subjectOf": [thing]}]}}
                    ]
                },
            },
            {
                "id": "about_named",
                "label": "about a named thing",
                "patterns": {
                    "fallback": [
                        {"pattern": {"schema:about": [{**thing, "schema:name": ["A"]}]}}
                    ]
                },
            },
        ]
    )
    value = {
        **thing,
        "schema:name": ["B", "A"],
        "schema:subjectOf": [thing, {**thing, "schema:name": ["C"]}],
    }
    catalogue = read_catalogue(document)
    assert verb_of(catalogue, m2()["@context"], "schema:about", value) == (
        "about_named",
        False,
    )


# -- rectangles -----------------------------------------------------------------------


def test_the_rectangles_of_the_video() -> None:
    value = m2()
    held = value["timelines"][1]["statements"]
    assert rectangles(_test(), value, ("timelines", 1)) == [
        Rectangle(
            "is_a",
            False,
            (
                ("type", "schema:VideoObject"),
                ("type", "melod:Manifestation"),
                ("wdt:P31", {"id": "wd:Q98069877"}),
            ),
            (
                "http://schema.org/VideoObject",
                "https://lod.academy/melod/vocab/ontology#Manifestation",
                "http://www.wikidata.org/entity/Q98069877",
            ),
            None,
        ),
        Rectangle(
            "performed_by",
            False,
            (("rel:prf", {"id": "viaf:113931950"}), ("wdt:P175", held["wdt:P175"][0])),
            (
                "http://viaf.org/viaf/113931950",
                "http://www.wikidata.org/entity/Q235650",
                "https://d-nb.info/gnd/124927521",
            ),
            PIRES,
        ),
        Rectangle(
            "same_as",
            False,
            (("schema:sameAs", {"id": "https://www.youtube.com/watch?v=Ch2mrPm1JnM"}),),
            ("https://www.youtube.com/watch?v=Ch2mrPm1JnM",),
            None,
        ),
    ]


def test_the_rectangles_of_the_score_encoding() -> None:
    value = m2()
    held = value["timelines"][0]["statements"]
    assert rectangles(_test(), value, ("timelines", 0)) == [
        Rectangle(
            "is_a",
            False,
            (("type", "melod:Manifestation"), ("type", "schema:SheetMusic")),
            (
                "https://lod.academy/melod/vocab/ontology#Manifestation",
                "http://schema.org/SheetMusic",
            ),
            None,
        ),
        Rectangle(
            None,
            False,
            (("dcterms:created", held["dcterms:created"][0]),),
            (),
            None,
        ),
        Rectangle(
            "version_or_edition_of",
            False,
            (
                ("schema:exampleOfWork", held["schema:exampleOfWork"][0]),
                ("wdt:P629", held["wdt:P629"][0]),
            ),
            (
                MUSICBRAINZ_WORK,
                "http://www.wikidata.org/entity/Q29117946",
                "https://d-nb.info/gnd/300042558",
            ),
            "Clair de lune",
        ),
    ]


def test_an_empty_is_a_and_values_naming_different_things() -> None:
    assert rectangles(_test(), m1(), ("timelines", 0)) == [
        Rectangle("is_a", False, (), (), None)
    ]
    value = m1()
    value["@context"]["rel"] = CATALOGUE_TEST["prefixes"]["rel"]
    value["timelines"][0]["statements"] = {
        "rel:prf": [{"id": "wd:Q1"}, {"id": "wd:Q2"}]
    }
    assert [
        (rectangle.verb, rectangle.things)
        for rectangle in rectangles(_test(), value, ("timelines", 0))
    ] == [
        ("is_a", ()),
        ("performed_by", ("http://www.wikidata.org/entity/Q1",)),
        ("performed_by", ("http://www.wikidata.org/entity/Q2",)),
    ]


def test_a_node_without_id_names_the_things_it_is_the_same_as() -> None:
    value = m1()
    value["@context"].update(
        rel=CATALOGUE_TEST["prefixes"]["rel"],
        viaf=CATALOGUE_TEST["prefixes"]["viaf"],
        owl="http://www.w3.org/2002/07/owl#",
    )
    node = {
        "schema:sameAs": [{"id": "viaf:1"}],
        "owl:sameAs": [{"id": "wd:Q1"}],
    }
    value["timelines"][0]["statements"] = {"rel:prf": [node]}
    assert rectangles(_test(), value, ("timelines", 0)) == [
        Rectangle("is_a", False, (), (), None),
        Rectangle(
            None,
            False,
            (("rel:prf", node),),
            ("http://viaf.org/viaf/1", "http://www.wikidata.org/entity/Q1"),
            None,
        ),
    ]
