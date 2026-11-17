from __future__ import annotations

import datetime
import json
import math
import re
from collections.abc import Callable
from typing import Any

import pytest

from timetoshare import (
    ABSENCE_REASONS,
    DEFAULTS,
    LEVELS,
    METHODS,
    PARTS_RELATIONS,
    RELATIONS,
    Assertion,
    Descriptor,
    Identifier,
    Link,
    PartOf,
    PartSlot,
    SchemaValidationError,
    Scheme,
    UnsupportedVersionError,
    canonical_order,
    complete,
    default_registry,
    description_problems,
    dumps,
    fixture_paths,
    identity_problems,
    minimal,
    rejection_case,
    rejection_paths,
    unknown_keys,
    unregistered_terms,
    validate,
)

from .conftest import group, manifest, timeline

MB = "http://musicbrainz.org/work/"
MB_WORK = "4a622b0d-b0c0-405e-b49e-05b70c108284"
P435 = "http://www.wikidata.org/entity/P435"
IMSLP = "http://www.wikidata.org/entity/P839"
OP_106 = "Piano_Sonata_No.29,_Op.106_(Beethoven,_Ludwig_van)"
NAME = "Beethoven, Piano Sonata No. 29, Op. 106"
LABEL = "Piano Sonata No. 29 in B♭ major, Op. 106"
SERIES = "https://musicbrainz.org/series/004f17aa-0f46-4fec-b939-c5dfc849e5c6"
SCHEME_NAME = "Works of Ludwig van Beethoven by opus number"
MOVEMENTS = [
    ("80cbaf7b-a1da-3fc5-b650-6eb72a803980", "I. Allegro"),
    ("7813c9cf-6054-3ef3-b9ed-8ae4690581c9", "II. Scherzo. Assai vivace"),
    ("7d110747-f011-41d4-9ce5-a1fad9abed2f", "III. Adagio sostenuto"),
    (
        "cfa82cd6-bcb5-39dd-9beb-c98e275c7c84",
        "IV. Introduzione. Largo – Allegro risoluto",
    ),
]
URLS = (
    "https://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284",
    "https://www.wikidata.org/wiki/Q146730",
    "https://viaf.org/viaf/186299955",
    f"https://imslp.org/wiki/{OP_106}",
)
EDITOR = Assertion(
    asserted_by=("https://example.org/people/editor",),
    asserted_on=datetime.date(2026, 11, 17),
    method="manual",
    status="confirmed",
)

MINIMAL = {
    "timetoshare": "0.2.0",
    "name": NAME,
    "timelines": [],
    "schemes": [{"id": "mb_beethoven_opus", "name": SCHEME_NAME, "uri": [SERIES]}],
    "links": [
        {
            "relation": "pertains_to",
            "level": "work",
            "label": LABEL,
            "uri": [
                f"{MB}4a622b0d-b0c0-405e-b49e-05b70c108284",
                "http://www.wikidata.org/entity/Q146730",
                "http://viaf.org/viaf/186299955",
            ],
            "identifiers": [
                {"scheme": IMSLP, "value": OP_106},
                {"scheme": "mb_beethoven_opus", "value": "op. 106"},
            ],
            "parts_relation": "has_part",
            "parts": [
                {"uri": [f"{MB}{mbid}"], "label": label, "absent": "not_represented"}
                for mbid, label in MOVEMENTS
            ],
            "assertion": {
                "asserted_by": ["https://example.org/people/editor"],
                "asserted_on": "2026-11-17",
                "method": "manual",
                "status": "confirmed",
            },
        }
    ],
}

COMPLETE = {
    "timetoshare": "0.2.0",
    "name": NAME,
    "meta": {},
    "groups": [],
    "measure_maps": [],
    "timelines": [],
    "schemes": [
        {
            "id": "mb_beethoven_opus",
            "name": SCHEME_NAME,
            "uri": [SERIES],
            "criteria": None,
        }
    ],
    "links": [
        {
            "relation": "pertains_to",
            "level": "work",
            "uri": MINIMAL["links"][0]["uri"],
            "identifiers": MINIMAL["links"][0]["identifiers"],
            "records": [],
            "label": LABEL,
            "assertion": {
                "asserted_by": ["https://example.org/people/editor"],
                "asserted_on": "2026-11-17",
                "method": "manual",
                "service": None,
                "based_on": [],
                "match": None,
                "status": "confirmed",
            },
            "parts_relation": "has_part",
            "parts": [
                {
                    "uri": [f"{MB}{mbid}"],
                    "identifiers": [],
                    "label": label,
                    "represented_by": [],
                    "absent": "not_represented",
                    "assertion": None,
                }
                for mbid, label in MOVEMENTS
            ],
            "parts_ordered": True,
            "part_of": [],
        }
    ],
}


def _slots(order: list[int]) -> list[PartSlot]:
    return [
        PartSlot.from_url(
            f"https://musicbrainz.org/work/{MOVEMENTS[index][0]}",
            label=MOVEMENTS[index][1],
            absent="not_represented",
        )
        for index in order
    ]


def _op_106() -> tuple[Scheme, Link]:
    scheme = Scheme("mb_beethoven_opus", name=SCHEME_NAME, uri=(SERIES,))
    link = Link.from_urls(
        *URLS,
        identifiers={"mb_beethoven_opus": "op. 106"},
        label=LABEL,
        assertion=EDITOR,
    ).with_parts("has_part", _slots([0, 1, 2, 3]))
    return scheme, link


def _bundle(scheme: Scheme, *links: Link, minimal_form: bool) -> dict[str, Any]:
    return {
        "timetoshare": "0.2.0",
        "name": NAME,
        "timelines": [],
        "schemes": [scheme.to_dict(minimal=minimal_form)],
        "links": [link.to_dict(minimal=minimal_form) for link in links],
    }


# -- the work bundle of Op. 106 ------------------------------------------------------


def test_the_work_bundle_of_op_106_in_both_forms() -> None:
    scheme, link = _op_106()
    built = _bundle(scheme, link, minimal_form=True)
    assert built == MINIMAL
    assert dumps(built) == dumps(MINIMAL)
    assert [link.to_dict()] == COMPLETE["links"]
    assert [scheme.to_dict()] == COMPLETE["schemes"]
    assert dumps(complete(MINIMAL)) == dumps(COMPLETE)
    assert dumps(minimal(COMPLETE)) == dumps(MINIMAL)
    for form in (MINIMAL, COMPLETE):
        validate(form)
        assert unknown_keys(form) == []
        assert unregistered_terms(form) == []
        assert Link.from_dict(form["links"][0]) == link
        assert Scheme.from_dict(form["schemes"][0]) == scheme
    assert "♭" in dumps(MINIMAL) and "–" in dumps(MINIMAL)


def test_two_readings_of_one_work_survive_in_their_order() -> None:
    scheme, first = _op_106()
    second = first.with_parts("has_part", _slots([0, 2, 1, 3])).with_assertion(
        Assertion(
            asserted_by=("https://example.org/people/second-editor",),
            asserted_on=datetime.date(2026, 11, 18),
            method="imported",
            based_on=("https://example.org/editions/london-1819",),
            status="unconfirmed",
        )
    )
    value = _bundle(scheme, first, second, minimal_form=True)
    validate(value)
    read = json.loads(dumps(value))
    assert [Link.from_dict(entry) for entry in read["links"]] == [first, second]
    labels = [[slot["label"] for slot in entry["parts"]] for entry in read["links"]]
    assert labels == [
        [MOVEMENTS[index][1] for index in order]
        for order in ([0, 1, 2, 3], [0, 2, 1, 3])
    ]
    assert canonical_order(value)["links"] == value["links"]


def test_the_canonical_order_sorts_schemes_and_keeps_every_array_of_a_link() -> None:
    link = {
        "relation": "pertains_to",
        "level": "work",
        "uri": ["https://example.org/z", "https://example.org/a"],
        "parts_relation": "has_part",
        "parts": [{"absent": "lost", "label": "z"}, {"absent": "lost", "label": "a"}],
    }
    value = manifest(
        timeline("score", links=[link, {**link, "level": "expression"}]),
        schemes=[{"id": "zz"}, {"id": "aa"}],
        links=[link, {**link, "relation": "about"}],
    )
    ordered = canonical_order(value)
    assert [scheme["id"] for scheme in ordered["schemes"]] == ["aa", "zz"]
    assert ordered["links"] == value["links"]
    assert ordered["timelines"][0]["links"] == value["timelines"][0]["links"]


# -- the errors of the model ---------------------------------------------------------


def _work(**options: Any) -> Link:
    return Link.from_urls(URLS[0], **options)


ERRORS: list[tuple[Callable[[], object], str]] = [
    (
        lambda: PartSlot(represented_by=("intro",), absent="lost"),
        "a part slot is represented or absent, not both",
    ),
    (
        lambda: PartSlot(label="I."),
        "a part slot is represented by an element or absent",
    ),
    (
        lambda: Link.from_urls("musicbrainz.org/work/x"),
        "'musicbrainz.org/work/x' is no absolute URI",
    ),
    (
        lambda: PartSlot.from_url("not a url", absent="lost"),
        "'not a url' is no absolute URI",
    ),
    (lambda: Link.from_urls(), "a link from URLs needs one URL at least"),
    (
        lambda: Link.from_urls(
            URLS[0],
            "https://musicbrainz.org/release/814c53fd-0732-4819-9753-4578f5ab992c",
        ),
        "'https://musicbrainz.org/release/814c53fd-0732-4819-9753-4578f5ab992c' is "
        f"recognised at the level 'manifestation', '{URLS[0]}' at 'work'",
    ),
    (
        lambda: Link.from_urls(URLS[0], level="expression"),
        f"the level 'expression' contradicts '{URLS[0]}', recognised at the level "
        "'work'",
    ),
    (
        lambda: _work().with_uri(
            "https://musicbrainz.org/release/814c53fd-0732-4819-9753-4578f5ab992c"
        ),
        "the level 'work' contradicts "
        "'https://musicbrainz.org/release/814c53fd-0732-4819-9753-4578f5ab992c', "
        "recognised at the level 'manifestation'",
    ),
    (
        lambda: Link.from_urls(URLS[1], URLS[2]),
        f"no level is recognised from '{URLS[1]}', '{URLS[2]}'; state the level",
    ),
    (lambda: Link.from_urls(URLS[1], level="score"), "'score' is no level"),
    (lambda: Link("pertains_to", "score"), "'score' is no level"),
    (
        lambda: Link.from_urls("https://example.org/people/composer", level="agent"),
        "an agent link states its relation, the agent's role",
    ),
    (
        lambda: Link.from_urls(
            "https://example.org/people/composer", level="agent", relation="pertains_to"
        ),
        "an agent link never uses the relation 'pertains_to'",
    ),
    (
        lambda: Link("pertains_to", "work", parts=(PartSlot(absent="lost"),)),
        "a link with parts states its parts_relation",
    ),
    (
        lambda: Link("pertains_to", "work", parts_relation="has_part"),
        "a link without parts states no parts_relation",
    ),
    (
        lambda: _work().with_parts("has_part", []),
        "a link without parts states no parts_relation",
    ),
    (
        lambda: Link("pertains_to", "work", parts_ordered=False),
        "a link without parts keeps parts_ordered true",
    ),
    *[
        (
            lambda value=value: Link.from_urls(URLS[1], identifiers={P435: value}),
            f"'{value}' is no value of the scheme 'MusicBrainz work ID'",
        )
        for value in ("op. 106", "x")
    ],
    (
        lambda: _work().with_identifier(P435, "op. 106"),
        "'op. 106' is no value of the scheme 'MusicBrainz work ID'",
    ),
    (
        lambda: Link.from_urls(URLS[1], level="expression").with_identifier(
            P435, MB_WORK
        ),
        f"the level 'expression' contradicts '{MB}{MB_WORK}', recognised at the level "
        "'work'",
    ),
    (
        lambda: _work().with_parts(
            "has_part",
            [
                *_slots([0]),
                PartSlot.from_url(
                    "https://musicbrainz.org/release/814c53fd-0732-4819-9753-4578f5ab992c",
                    absent="lost",
                ),
            ],
        ),
        "part slot 2 is recognised at the level 'manifestation', the link's level "
        "is 'work'",
    ),
    *[
        (
            lambda date=date, read=read: read(date),
            f"'{date}' is no Gregorian calendar date written YYYY-MM-DD",
        )
        for date in (
            "2026-02-30",
            "2100-02-29",
            "0000-01-01",
            "20261117",
            "17 November 2026",
        )
        for read in (
            lambda date: Assertion.from_dict({"asserted_on": date}),
            lambda date: Assertion(asserted_on=date),
        )
    ],
    (
        lambda: Assertion(asserted_on=20261117),  # type: ignore[arg-type]
        "'20261117' is no Gregorian calendar date written YYYY-MM-DD",
    ),
    (
        lambda: Assertion(asserted_on=datetime.datetime(2026, 11, 17)),
        "'2026-11-17 00:00:00' is no Gregorian calendar date written YYYY-MM-DD",
    ),
    (
        lambda: Link.from_dict(
            {
                "relation": "pertains_to",
                "level": "work",
                "parts_relation": "has_part",
                "parts": [
                    {"absent": "lost", "assertion": {"asserted_on": "2026-11-31"}}
                ],
            }
        ),
        "'2026-11-31' is no Gregorian calendar date written YYYY-MM-DD",
    ),
    (
        lambda: Link.from_dict(
            {
                "relation": "pertains_to",
                "level": "work",
                "part_of": [
                    {
                        "parts_relation": "has_part",
                        "assertion": {"asserted_on": "2026-13-01"},
                    }
                ],
            }
        ),
        "'2026-13-01' is no Gregorian calendar date written YYYY-MM-DD",
    ),
]


@pytest.mark.parametrize(("build", "message"), ERRORS)
def test_every_error_of_the_model(build: Callable[[], object], message: str) -> None:
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        build()


def test_an_assertion_reads_a_day_of_the_calendar() -> None:
    read = Assertion.from_dict({"asserted_on": "2024-02-29"})
    assert read.asserted_on == datetime.date(2024, 2, 29)
    assert read.to_dict()["asserted_on"] == "2024-02-29"
    built = Assertion(asserted_on="2024-02-29")  # type: ignore[arg-type]
    assert built.asserted_on == datetime.date(2024, 2, 29)
    assert built == read
    assert Assertion(asserted_on=datetime.date(2024, 2, 29)) == read


# -- normalisation and copy-on-write -------------------------------------------------


def test_urls_collapse_into_their_first_normal_form() -> None:
    link = Link.from_urls(
        URLS[0],
        f"{MB}4a622b0d-b0c0-405e-b49e-05b70c108284/",
        URLS[3],
        "https://imslp.org/wiki/Piano_Sonata_No.29%2C_Op.106_%28Beethoven%2C_Ludwig_van%29",
        "https://example.org/anything",
        identifiers=[
            Identifier("mb_beethoven_opus", "op. 106"),
            Identifier(IMSLP, OP_106),
        ],
    )
    assert link.uri == (
        f"{MB}4a622b0d-b0c0-405e-b49e-05b70c108284",
        "https://example.org/anything",
    )
    assert link.identifiers == (
        Identifier(IMSLP, OP_106),
        Identifier("mb_beethoven_opus", "op. 106"),
    )
    assert (link.relation, link.level) == ("pertains_to", "work")
    agent = Link.from_url(
        "https://example.org/people/composer", level="agent", relation="marcrel:cmp"
    )
    assert (agent.relation, agent.level, agent.uri) == (
        "marcrel:cmp",
        "agent",
        ("https://example.org/people/composer",),
    )


def test_every_change_gives_a_new_link() -> None:
    base = _work(label="Op. 106")
    before = base.to_dict()
    extended = base.with_uri(
        "https://www.wikidata.org/wiki/Q146730",
        "http://www.wikidata.org/entity/Q146730",
        URLS[0],
        URLS[3],
    )
    assert extended.uri == (
        f"{MB}4a622b0d-b0c0-405e-b49e-05b70c108284",
        "http://www.wikidata.org/entity/Q146730",
    )
    assert extended.identifiers == (Identifier(IMSLP, OP_106),)
    identified = extended.with_identifier("mb_beethoven_opus", "op. 106")
    assert identified.with_identifier("mb_beethoven_opus", "op. 106") == identified
    record = Descriptor("https://example.org/records/op106.json", size=812)
    recorded = identified.with_record(record).with_record(record)
    assert recorded.records == (record, record)
    assert recorded.with_label("Hammerklavier").label == "Hammerklavier"
    assert recorded.with_assertion(EDITOR).assertion == EDITOR
    first = base.with_parts("has_part", _slots([0, 1]), ordered=False)
    second = first.with_parts("has_part", _slots([2]))
    assert (len(first.parts), first.parts_ordered) == (2, False)
    assert (second.parts, second.parts_ordered) == (tuple(_slots([2])), True)
    whole = PartOf("has_part", label="The thirty-two piano sonatas", position=29)
    assert base.with_part_of(whole).with_part_of(whole).part_of == (whole, whole)
    assert base.to_dict() == before


def test_an_identifier_of_a_scheme_minting_uris_is_stored_as_its_uri() -> None:
    upper = MB_WORK.upper()
    link = Link.from_urls(URLS[1], identifiers={P435: upper})
    assert (link.uri, link.identifiers, link.level) == (
        ("http://www.wikidata.org/entity/Q146730", f"{MB}{MB_WORK}"),
        (),
        "work",
    )
    assert Link.from_urls(URLS[0], identifiers=[Identifier(P435, upper)]).uri == (
        f"{MB}{MB_WORK}",
    )
    doi = Link.from_urls(
        URLS[1],
        level="work",
        identifiers={
            "http://www.wikidata.org/entity/P356": "10.5281/zenodo.7473560",
            IMSLP: OP_106,
            "mb_beethoven_opus": "op. 106",
        },
    )
    assert doi.uri == (
        "http://www.wikidata.org/entity/Q146730",
        "https://doi.org/10.5281/zenodo.7473560",
    )
    assert doi.identifiers == (
        Identifier(IMSLP, OP_106),
        Identifier("mb_beethoven_opus", "op. 106"),
    )
    bare = Link.from_urls(URLS[1], level="work")
    assert bare.with_identifier(P435, upper).uri == (
        "http://www.wikidata.org/entity/Q146730",
        f"{MB}{MB_WORK}",
    )
    held = _work()
    assert held.with_identifier(P435, upper) == held
    extended = default_registry().with_schemes(
        {
            "id": "x",
            "name": "Example",
            "uri": "https://example.org/scheme",
            "entity_uri": "https://example.org/entity/{value}",
            "patterns": ["https://example\\.org/entity/([0-9]+)"],
        }
    )
    example = Link.from_urls("https://example.org/anything", level="work")
    assert example.with_identifier(
        "https://example.org/scheme", "12", registry=extended
    ).uri == ("https://example.org/anything", "https://example.org/entity/12")
    assert example.with_identifier("https://example.org/scheme", "12").identifiers == (
        Identifier("https://example.org/scheme", "12"),
    )
    validate(manifest(timeline("score"), links=[_link(identifiers=_opus(P435))]))


def test_a_value_in_capitals_gives_the_one_uri() -> None:
    held = _work()
    assert held.with_uri(f"https://musicbrainz.org/work/{MB_WORK.upper()}") == held
    assert held.uri == (f"{MB}{MB_WORK}",)


def test_an_entry_inherits_its_links_assertion_unless_it_states_one() -> None:
    own = Assertion(method="reconciled", service="https://example.org/reconcile")
    slot = PartSlot(represented_by=("intro",))
    stated = PartSlot(represented_by=("intro",), assertion=own)
    whole = PartOf("has_part")
    link = _work(assertion=EDITOR).with_parts("has_part", [slot, stated])
    assert [link.assertion_for(entry) for entry in (slot, stated, whole)] == [
        EDITOR,
        own,
        EDITOR,
    ]
    assert _work().assertion_for(slot) is None


# -- forms and unknown keys ----------------------------------------------------------

_CLASSES = {
    "scheme": Scheme,
    "link": Link,
    "descriptor": Descriptor,
    "assertion": Assertion,
    "part_slot": PartSlot,
    "part_of": PartOf,
}
_SAMPLES: dict[str, dict[str, Any]] = {
    "scheme": {"id": "opus"},
    "link": {"relation": "pertains_to", "level": "work"},
    "descriptor": {"url": "records/op106.json"},
    "assertion": {},
    "part_slot": {"absent": "lost"},
    "part_of": {"parts_relation": "has_part"},
}


@pytest.mark.parametrize("kind", list(_CLASSES))
def test_both_forms_come_from_the_defaults_table(kind: str) -> None:
    value = _CLASSES[kind].from_dict(_SAMPLES[kind])
    assert value.to_dict() == {**DEFAULTS[kind], **_SAMPLES[kind]}
    assert value.to_dict(minimal=True) == _SAMPLES[kind]
    assert type(value).from_dict(value.to_dict()) == value


def test_identifiers_have_no_defaults() -> None:
    identifier = Identifier.from_dict({"scheme": "opus", "value": "106"})
    assert identifier.to_dict() == identifier.to_dict(minimal=True)
    assert identifier.to_dict() == {"scheme": "opus", "value": "106"}


def _noted(value: dict[str, Any], note: str) -> dict[str, Any]:
    return {**value, "x-note": note}


def test_unknown_keys_survive_on_every_object() -> None:
    assertion = _noted({"method": "manual"}, "assertion")
    data = _noted(
        {
            "relation": "pertains_to",
            "level": "work",
            "identifiers": [_noted({"scheme": "opus", "value": "106"}, "identifier")],
            "records": [_noted({"url": "records/op106.json"}, "record")],
            "assertion": assertion,
            "parts_relation": "has_part",
            "parts": [_noted({"absent": "lost", "assertion": assertion}, "slot")],
            "part_of": [_noted({"parts_relation": "has_part"}, "whole")],
        },
        "link",
    )
    link = Link.from_dict(data)
    for written in (link.to_dict(), link.to_dict(minimal=True)):
        assert written["x-note"] == "link"
        assert written["identifiers"][0]["x-note"] == "identifier"
        assert written["records"][0]["x-note"] == "record"
        assert written["assertion"]["x-note"] == "assertion"
        assert written["parts"][0]["x-note"] == "slot"
        assert written["parts"][0]["assertion"]["x-note"] == "assertion"
        assert written["part_of"][0]["x-note"] == "whole"
    assert link.to_dict(minimal=True) == data
    plain = json.loads(json.dumps(data).replace('"x-note"', '"x-other"'))
    assert Link.from_dict(plain) == link
    scheme = Scheme.from_dict(_noted({"id": "opus"}, "scheme"))
    assert scheme.to_dict()["x-note"] == "scheme"
    assert scheme.to_dict(minimal=True) == {"id": "opus", "x-note": "scheme"}
    assert scheme == Scheme("opus")


def test_unknown_keys_lists_the_unknown_keys_of_every_object() -> None:
    assertion = _noted({"method": "manual"}, "assertion")
    link = _noted(
        {
            "relation": "pertains_to",
            "level": "work",
            "identifiers": [_noted({"scheme": "opus", "value": "106"}, "identifier")],
            "records": [_noted({"url": "records/op106.json"}, "record")],
            "assertion": assertion,
            "parts_relation": "has_part",
            "parts": [_noted({"absent": "lost", "assertion": assertion}, "slot")],
            "part_of": [_noted({"parts_relation": "has_part"}, "whole")],
        },
        "link",
    )
    value = manifest(schemes=[_noted({"id": "opus"}, "scheme")], links=[link])
    assert unknown_keys(value) == [
        {"path": path, "key": "x-note"}
        for path in [
            ["links", 0],
            ["links", 0, "assertion"],
            ["links", 0, "identifiers", 0],
            ["links", 0, "part_of", 0],
            ["links", 0, "parts", 0],
            ["links", 0, "parts", 0, "assertion"],
            ["links", 0, "records", 0],
            ["schemes", 0],
        ]
    ]


# -- the rules of links --------------------------------------------------------------


def _link(**members: Any) -> dict[str, Any]:
    return {"relation": "pertains_to", "level": "work", **members}


def _slot_link(*targets: str) -> dict[str, Any]:
    return _link(
        parts_relation="has_part",
        parts=[{"represented_by": [target]} for target in targets],
    )


def _listed(problems: list[SchemaValidationError]) -> list[tuple[Any, ...]]:
    return [(problem.path, problem.code, problem.message) for problem in problems]


def _problems(value: dict[str, Any]) -> list[tuple[tuple[Any, ...], str, str]]:
    """The problems of a document breaking description rules only, both ways."""
    found = _listed(identity_problems(value))
    assert _listed(description_problems(value)) == found
    return found


def _segmented() -> dict[str, Any]:
    return timeline(
        "score",
        length=(16, 1),
        is_segment_line=True,
        children=[
            timeline("a", offset=(0, 1)),
            timeline("b", offset=(8, 1), children=[timeline("b1", offset=(0, 1))]),
        ],
        regions=[{"id": "intro", "start": [0, 1], "end": [4, 1]}],
    )


def test_a_slot_is_represented_by_timelines_and_regions() -> None:
    value = manifest(_segmented(), links=[_slot_link("score", "a", "b1", "intro")])
    validate(value)
    assert _problems(value) == []


@pytest.mark.parametrize("target", ["ghost", "g", "bars"])
def test_a_slot_names_a_timeline_or_a_region(target: str) -> None:
    rows = [{"count": 1, "qstamp": [0, 1], "actual_length": [4, 1]}]
    value = manifest(
        _segmented(),
        groups=[group("g", "score")],
        measure_maps=[{"id": "bars", "rows": rows}],
        links=[_slot_link("intro", target)],
    )
    problem = (
        ("links", 0, "parts", 1, "represented_by", 0),
        "dangling_target",
        f"'{target}' names no timeline or region of this manifest",
    )
    assert _problems(value) == [problem]
    with pytest.raises(SchemaValidationError) as caught:
        validate(value)
    assert (caught.value.path, caught.value.code) == problem[:2]


def _opus(scheme: str) -> list[dict[str, str]]:
    return [{"scheme": scheme, "value": "106"}]


def test_an_identifier_names_a_scheme_or_an_absolute_uri() -> None:
    accepted = manifest(
        timeline("score"),
        schemes=[{"id": "opus"}],
        links=[_link(identifiers=[*_opus("opus"), *_opus(IMSLP)])],
    )
    validate(accepted)
    assert _problems(accepted) == []
    message = "'opus' names no scheme of this manifest and is no absolute URI"
    whole = {"parts_relation": "has_part", "identifiers": _opus("opus")}
    slot = {"absent": "lost", "identifiers": _opus("opus")}
    value = manifest(
        timeline(
            "score",
            links=[_link(identifiers=_opus("opus"))],
            regions=[
                {
                    "id": "intro",
                    "start": [0, 1],
                    "end": [4, 1],
                    "links": [_link(identifiers=_opus("opus"))],
                }
            ],
            children=[
                timeline(
                    "verse",
                    offset=(0, 1),
                    links=[_link(identifiers=_opus("opus"))],
                )
            ],
        ),
        links=[
            _link(
                identifiers=_opus("opus"),
                parts_relation="has_part",
                parts=[slot],
                part_of=[whole],
            )
        ],
    )
    root = ("timelines", 0)
    assert _problems(value) == [
        (path, "dangling_target", message)
        for path in [
            ("links", 0, "identifiers", 0, "scheme"),
            ("links", 0, "parts", 0, "identifiers", 0, "scheme"),
            ("links", 0, "part_of", 0, "identifiers", 0, "scheme"),
            (*root, "links", 0, "identifiers", 0, "scheme"),
            (*root, "regions", 0, "links", 0, "identifiers", 0, "scheme"),
            (*root, "children", 0, "links", 0, "identifiers", 0, "scheme"),
        ]
    ]


@pytest.mark.parametrize(
    ("schemes", "path", "first"),
    [
        ([{"id": "score"}], ("schemes", 0, "id"), "#/timelines/0/id"),
        ([{"id": "intro"}], ("schemes", 0, "id"), "#/timelines/0/regions/0/id"),
        ([{"id": "opus"}, {"id": "opus"}], ("schemes", 1, "id"), "#/schemes/0/id"),
    ],
)
def test_a_scheme_id_is_unique_in_the_manifest(
    schemes: list[dict[str, str]], path: tuple[Any, ...], first: str
) -> None:
    value = manifest(
        timeline("score", regions=[{"id": "intro", "start": [0, 1], "end": [4, 1]}]),
        schemes=schemes,
    )
    identifier = schemes[-1]["id"]
    assert _problems(value) == [
        (
            path,
            "duplicate_id",
            f"'{identifier}' is not unique in the manifest, first at {first}",
        )
    ]


def test_the_manifest_id_is_no_scheme_id() -> None:
    value = manifest(timeline("score"), id="opus", schemes=[{"id": "opus"}])
    assert _problems(value) == [
        (
            ("id",),
            "manifest_id",
            "'opus' is not unique in the manifest, first at #/schemes/0/id",
        )
    ]


def test_a_links_identifier_comes_before_its_slot() -> None:
    link = _slot_link("ghost")
    link["identifiers"] = _opus("opus")
    assert [
        path for path, _, _ in _problems(manifest(timeline("score"), links=[link]))
    ] == [
        ("links", 0, "identifiers", 0, "scheme"),
        ("links", 0, "parts", 0, "represented_by", 0),
    ]


CALENDAR_DATES = ["2024-02-29", "2000-02-29", "0001-01-01", "9999-12-31"]
IMPOSSIBLE_DATES = [
    "2026-02-30",
    "2023-02-29",
    "2100-02-29",
    "2026-11-31",
    "2026-13-01",
    "2026-00-10",
    "2026-11-00",
    "0000-01-01",
]


def _no_date(date: str) -> str:
    return f"'{date}' is no Gregorian calendar date written YYYY-MM-DD"


@pytest.mark.parametrize("date", CALENDAR_DATES)
def test_an_assertion_dated_by_the_calendar_validates(date: str) -> None:
    value = manifest(timeline("score"), links=[_link(assertion={"asserted_on": date})])
    validate(value)
    assert _problems(value) == []


@pytest.mark.parametrize("date", IMPOSSIBLE_DATES)
def test_an_assertion_dated_by_no_day_of_the_calendar_is_refused(date: str) -> None:
    value = manifest(timeline("score"), links=[_link(assertion={"asserted_on": date})])
    problem = (
        ("links", 0, "assertion", "asserted_on"),
        "calendar_date",
        _no_date(date),
    )
    assert _problems(value) == [problem]
    with pytest.raises(SchemaValidationError) as caught:
        validate(value)
    assert (caught.value.path, caught.value.code, caught.value.message) == problem


def test_the_dates_of_a_link_come_with_its_references() -> None:
    def dated(day: str) -> dict[str, str]:
        return {"asserted_on": f"2026-02-{day}"}

    link = _link(
        assertion=dated("30"),
        identifiers=_opus("opus"),
        parts_relation="has_part",
        parts=[{"represented_by": ["ghost"], "assertion": dated("31")}],
        part_of=[{"parts_relation": "has_part", "assertion": dated("29")}],
    )
    at = ("links", 0)
    assert _problems(manifest(timeline("score"), links=[link])) == [
        ((*at, "assertion", "asserted_on"), "calendar_date", _no_date("2026-02-30")),
        (
            (*at, "identifiers", 0, "scheme"),
            "dangling_target",
            "'opus' names no scheme of this manifest and is no absolute URI",
        ),
        (
            (*at, "parts", 0, "assertion", "asserted_on"),
            "calendar_date",
            _no_date("2026-02-31"),
        ),
        (
            (*at, "parts", 0, "represented_by", 0),
            "dangling_target",
            "'ghost' names no timeline or region of this manifest",
        ),
        (
            (*at, "part_of", 0, "assertion", "asserted_on"),
            "calendar_date",
            _no_date("2026-02-29"),
        ),
    ]


def _path_of(value: dict[str, Any]) -> tuple[Any, ...]:
    with pytest.raises(SchemaValidationError) as caught:
        validate(value)
    assert caught.value.code == "schema"
    return caught.value.path


def test_the_schema_rules_of_slots_and_links() -> None:
    def slots(*entries: dict[str, Any]) -> dict[str, Any]:
        return manifest(
            timeline("score"),
            links=[_link(parts_relation="has_part", parts=list(entries))],
        )

    slot = ("links", 0, "parts", 0)
    assert _path_of(slots({"represented_by": ["score"], "absent": "lost"})) == (
        *slot,
        "absent",
    )
    assert _path_of(slots({"represented_by": [], "absent": None})) == (*slot, "absent")
    assert _path_of(slots({"label": "I."})) == slot
    agent = {"relation": "pertains_to", "level": "agent"}
    assert _path_of(manifest(timeline("score"), links=[agent])) == ("links", 0)
    validate(manifest(timeline("score"), links=[{**agent, "relation": "marcrel:cmp"}]))
    parts = [{"absent": "lost"}]
    assert _path_of(
        manifest(timeline("score"), links=[_link(parts=parts, parts_relation=None)])
    ) == ("links", 0, "parts_relation")
    assert _path_of(manifest(timeline("score"), links=[_link(parts=parts)])) == (
        "links",
        0,
    )
    validate(manifest(timeline("score"), links=[_link(parts=[], parts_relation=None)]))
    validate(manifest(timeline("score"), links=[_link(parts=[])]))


@pytest.mark.parametrize(
    ("members", "member"),
    [
        ({"parts_relation": "has_part"}, "parts_relation"),
        ({"parts": [], "parts_relation": "has_part"}, "parts_relation"),
        ({"parts_ordered": False}, "parts_ordered"),
        ({"parts": [], "parts_ordered": False}, "parts_ordered"),
    ],
)
def test_a_link_without_parts_states_no_parts_relation_and_no_display_order(
    members: dict[str, Any], member: str
) -> None:
    value = manifest(timeline("score"), links=[_link(**members)])
    assert _path_of(value) == ("links", 0, member)


def test_unordered_parts_validate() -> None:
    link = _link(
        parts_relation="has_part", parts=[{"absent": "lost"}], parts_ordered=False
    )
    validate(manifest(timeline("score"), links=[link]))


@pytest.mark.parametrize(
    ("criteria", "refused"),
    [
        ("criteria/opus-numbers.html", False),
        ("https://example.org/criteria", False),
        ("", True),
        ("criteria/opus numbers", True),
    ],
)
def test_the_criteria_of_a_scheme_are_a_uri_reference(
    criteria: str, refused: bool
) -> None:
    value = manifest(timeline("score"), schemes=[{"id": "opus", "criteria": criteria}])
    if refused:
        assert _path_of(value) == ("schemes", 0, "criteria")
    else:
        validate(value)
        assert Scheme.from_dict(value["schemes"][0]).criteria == criteria


# -- the shared cases of links -------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "message"),
    [
        (
            "description_slot_represented_by_unresolved",
            "'ghost' names no timeline or region of this manifest",
        ),
        (
            "description_identifier_scheme_unresolved",
            "'opus' names no scheme of this manifest and is no absolute URI",
        ),
        (
            "description_scheme_id_duplicate",
            "'score' is not unique in the manifest, first at #/timelines/0/id",
        ),
        (
            "description_asserted_on_impossible_date",
            "'2026-02-30' is no Gregorian calendar date written YYYY-MM-DD",
        ),
    ],
)
def test_the_messages_of_the_shared_cases_of_links(name: str, message: str) -> None:
    (path,) = [path for path in rejection_paths() if path.stem == name]
    case = rejection_case(path)
    with pytest.raises(SchemaValidationError) as caught:
        validate(case.manifest)
    assert (caught.value.path, caught.value.code, caught.value.message) == (
        case.path,
        case.code,
        message,
    )


# -- the description layer alone ----------------------------------------------------


def test_the_shared_cases_through_the_description_layer_alone() -> None:
    described = 0
    for path in rejection_paths():
        case = rejection_case(path)
        problems = description_problems(case.manifest)
        if path.stem.startswith("description_"):
            described += 1
            assert [(problem.path, problem.code) for problem in problems] == [
                (case.path, case.code)
            ], path.stem
        else:
            assert problems == [], path.stem
    assert described == 19
    for path in fixture_paths():
        assert description_problems(json.loads(path.read_text(encoding="utf-8"))) == []


def _broken_elsewhere(**members: Any) -> dict[str, Any]:
    """A manifest breaking every kind of rule outside its sound links and schemes."""
    return {
        "timetoshare": "9.9.9",
        "timelines": [
            {
                "id": "a",
                "unit": "beats",
                "length": [8, 1],
                "regions": [{"id": "r", "start": [0, 1], "end": [4, 1]}, 7],
                "children": [
                    {"id": "c", "unit": "seconds", "length": 60.5, "offset": 100.5}
                ],
            },
            {"id": "a", "unit": "quarters", "length": [8, 1]},
        ],
        "groups": [{"id": "grp", "members": ["ghost"]}],
        "graphical": "none",
        "links": [_slot_link("r")],
        **members,
    }


def test_the_description_layer_alone_refuses_nothing_outside_it() -> None:
    sound = _broken_elsewhere(schemes=[{"id": "s"}])
    sound["links"][0]["identifiers"] = _opus("s")
    with pytest.raises(UnsupportedVersionError):
        validate(sound)
    assert description_problems(sound) == []
    broken = _broken_elsewhere(id="g", schemes=[{"id": "a"}, {"id": "g"}])
    broken["links"][0]["identifiers"] = _opus("q")
    assert _listed(description_problems(broken)) == [
        (
            ("schemes", 0, "id"),
            "duplicate_id",
            "'a' is not unique in the manifest, first at #/timelines/0/id",
        ),
        (
            ("id",),
            "manifest_id",
            "'g' is not unique in the manifest, first at #/schemes/1/id",
        ),
        (
            ("links", 0, "identifiers", 0, "scheme"),
            "dangling_target",
            "'q' names no scheme of this manifest and is no absolute URI",
        ),
    ]


def test_the_description_layer_alone_checks_each_array() -> None:
    value = manifest(
        timeline(
            "score",
            links=[{"relation": "pertains_to"}],
            regions=[
                {
                    "id": "r",
                    "start": [0, 1],
                    "end": [4, 1],
                    "links": [_link(level="score")],
                },
                {
                    "id": "s",
                    "start": [4, 1],
                    "end": [8, 1],
                    "links": [_link(identifiers=_opus("q"))],
                },
            ],
            children=[
                timeline(
                    "verse",
                    offset=(0, 1),
                    links=[_link(records=[{"url": "r.json", "size": math.inf}])],
                )
            ],
        ),
        schemes=[{"name": "Opus"}],
        links="none",
    )
    problems = description_problems(value)
    assert [(problem.path, problem.code) for problem in problems] == [
        (("schemes", 0), "schema"),
        (("links",), "schema"),
        (("timelines", 0, "links", 0), "schema"),
        (("timelines", 0, "regions", 0, "links", 0, "level"), "schema"),
        (
            ("timelines", 0, "children", 0, "links", 0, "records", 0, "size"),
            "finite_number",
        ),
    ]
    assert problems[-1].message == "size of 'verse' is not a finite number"


# -- unregistered terms --------------------------------------------------------------


def _terms(value: dict[str, Any]) -> list[tuple[list[Any], str]]:
    return [(entry["path"], entry["term"]) for entry in unregistered_terms(value)]


def test_the_vocabularies() -> None:
    assert RELATIONS == ("pertains_to",)
    assert METHODS == ("manual", "reconciled", "imported", "inferred")
    assert PARTS_RELATIONS == ("has_part", "aggregates", "incorporates")
    assert ABSENCE_REASONS == (
        "not_represented",
        "lost",
        "unfinished",
        "unknown",
        "not_recorded",
    )
    assert LEVELS == ("work", "expression", "manifestation", "item", "agent")


def _described(
    relation: str, method: str, parts_relation: str, absent: str, whole: str
) -> dict[str, Any]:
    assertion = {"method": method}
    return _link(
        relation=relation,
        assertion=assertion,
        parts_relation=parts_relation,
        parts=[{"absent": absent, "assertion": assertion}],
        part_of=[{"parts_relation": whole, "assertion": assertion}],
    )


def test_registered_words_and_extension_terms_are_not_listed() -> None:
    links = [
        _described("pertains_to", method, relation, absent, relation)
        for method, relation, absent in zip(
            [*METHODS, METHODS[0]],
            [*PARTS_RELATIONS, *PARTS_RELATIONS[:2]],
            ABSENCE_REASONS,
            strict=True,
        )
    ]
    premis = "http://id.loc.gov/vocabulary/preservation/eventType/val"
    links.append(
        _described(
            "http://id.loc.gov/vocabulary/relators/cmp",
            premis,
            "frbr:hasPart",
            "ex:destroyed",
            "dcterms:isPartOf",
        )
    )
    links.append(
        {"relation": "marcrel:cmp", "level": "agent", "assertion": {"method": premis}}
    )
    assert _terms(manifest(timeline("score"), links=links)) == []


def test_every_unregistered_word_is_listed_in_path_order() -> None:
    odd = _described("has_part", "lost", "contains", "destroyed", "holds")
    value = manifest(
        timeline(
            "score",
            links=[_link(relation="about")],
            regions=[
                {
                    "id": "intro",
                    "start": [0, 1],
                    "end": [4, 1],
                    "links": [_link(assertion={"method": "guessed"})],
                }
            ],
        ),
        links=[odd],
    )
    validate(value)
    assert _terms(value) == [
        (["links", 0, "assertion", "method"], "lost"),
        (["links", 0, "part_of", 0, "assertion", "method"], "lost"),
        (["links", 0, "part_of", 0, "parts_relation"], "holds"),
        (["links", 0, "parts", 0, "absent"], "destroyed"),
        (["links", 0, "parts", 0, "assertion", "method"], "lost"),
        (["links", 0, "parts_relation"], "contains"),
        (["links", 0, "relation"], "has_part"),
        (["timelines", 0, "links", 0, "relation"], "about"),
        (
            ["timelines", 0, "regions", 0, "links", 0, "assertion", "method"],
            "guessed",
        ),
    ]


def test_an_invalid_manifest_raises_before_any_term_is_listed() -> None:
    with pytest.raises(SchemaValidationError):
        unregistered_terms(manifest(timeline("score"), links=[{"relation": "about"}]))
