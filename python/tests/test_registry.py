from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from timetoshare import Identifier, KnownScheme, default_registry, dumps

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPOSITORY_ROOT / "registry" / "schemes.json"
WIKIDATA = "http://www.wikidata.org/entity/"
IMSLP = f"{WIKIDATA}P839"
OP_106 = "Piano_Sonata_No.29,_Op.106_(Beethoven,_Ludwig_van)"
MB_WORK = "4a622b0d-b0c0-405e-b49e-05b70c108284"

ENTRIES = [
    (
        "musicbrainz_work",
        f"{WIKIDATA}P435",
        "work",
        "http://musicbrainz.org/work/{value}",
    ),
    (
        "musicbrainz_recording",
        f"{WIKIDATA}P4404",
        "expression",
        "http://musicbrainz.org/recording/{value}",
    ),
    (
        "musicbrainz_release",
        f"{WIKIDATA}P5813",
        "manifestation",
        "http://musicbrainz.org/release/{value}",
    ),
    (
        "wikidata",
        "http://id.loc.gov/vocabulary/identifiers/wikidata",
        None,
        "http://www.wikidata.org/entity/{value}",
    ),
    ("viaf", f"{WIKIDATA}P214", None, "http://viaf.org/viaf/{value}"),
    ("gnd", f"{WIKIDATA}P227", None, "https://d-nb.info/gnd/{value}"),
    ("imslp", IMSLP, "work", None),
    ("doi", f"{WIKIDATA}P356", None, "https://doi.org/{value}"),
]


def test_the_default_registry_is_the_shipped_file() -> None:
    text = REGISTRY.read_text(encoding="utf-8")
    assert dumps(json.loads(text)) == text
    schemes = default_registry().schemes
    assert [
        (scheme.id, scheme.uri, scheme.level, scheme.entity_uri) for scheme in schemes
    ] == ENTRIES
    assert [scheme.to_dict() for scheme in schemes] == json.loads(text)
    assert default_registry() is default_registry()


def test_every_pattern_has_one_group_and_shared_syntax_only() -> None:
    for scheme in default_registry().schemes:
        assert scheme.patterns, scheme.id
        for pattern in scheme.patterns:
            assert re.compile(pattern).groups == 1, pattern
            assert re.search(r"\(\?[^:=!]", pattern) is None, pattern


RECOGNISED = [
    (
        f"https://musicbrainz.org/work/{MB_WORK}",
        f"http://musicbrainz.org/work/{MB_WORK}",
        None,
        "work",
    ),
    (
        "http://musicbrainz.org/work/80cbaf7b-a1da-3fc5-b650-6eb72a803980/",
        "http://musicbrainz.org/work/80cbaf7b-a1da-3fc5-b650-6eb72a803980",
        None,
        "work",
    ),
    (
        "https://musicbrainz.org/release/814c53fd-0732-4819-9753-4578f5ab992c",
        "http://musicbrainz.org/release/814c53fd-0732-4819-9753-4578f5ab992c",
        None,
        "manifestation",
    ),
    (
        "https://www.wikidata.org/wiki/Q146730",
        "http://www.wikidata.org/entity/Q146730",
        None,
        None,
    ),
    ("https://viaf.org/viaf/186299955", "http://viaf.org/viaf/186299955", None, None),
    (
        f"https://imslp.org/wiki/{OP_106}",
        None,
        Identifier(IMSLP, OP_106),
        "work",
    ),
    (
        "https://imslp.org/wiki/Piano_Sonata_No.29%2C_Op.106_%28Beethoven%2C_Ludwig_van%29",
        None,
        Identifier(IMSLP, OP_106),
        "work",
    ),
    (
        "https://doi.org/10.5281/zenodo.7473560",
        "https://doi.org/10.5281/zenodo.7473560",
        None,
        None,
    ),
]


@pytest.mark.parametrize(("url", "uri", "identifier", "level"), RECOGNISED)
def test_the_recognition_table(
    url: str, uri: str | None, identifier: Identifier | None, level: str | None
) -> None:
    recognition = default_registry().recognize(url)
    assert recognition is not None
    assert (recognition.uri, recognition.identifier, recognition.level) == (
        uri,
        identifier,
        level,
    )


FORMS = [
    (f"http://www.musicbrainz.org/work/{MB_WORK}?tab=details#top", "musicbrainz_work"),
    (
        "https://musicbrainz.org/recording/5f1a7c3e-2b4d-4e6f-8a9b-0c1d2e3f4a5b",
        "musicbrainz_recording",
    ),
    ("https://m.wikidata.org/wiki/Q146730", "wikidata"),
    ("http://www.wikidata.org/entity/Q146730", "wikidata"),
    ("https://www.wikidata.org/wiki/Q146730#P435", "wikidata"),
    ("https://viaf.org/en/viaf/186299955", "viaf"),
    ("https://www.viaf.org/viaf/186299955/", "viaf"),
    ("https://d-nb.info/gnd/118508288", "gnd"),
    ("https://dx.doi.org/10.5281/zenodo.7473560", "doi"),
    (f"https://www.imslp.org/wiki/{OP_106}?action=history", "imslp"),
]


@pytest.mark.parametrize(("url", "scheme"), FORMS)
def test_the_url_forms_of_a_scheme(url: str, scheme: str) -> None:
    recognition = default_registry().recognize(url)
    assert recognition is not None
    assert recognition.scheme.id == scheme


def test_every_form_gives_one_uri() -> None:
    def uri(url: str) -> str | None:
        recognition = default_registry().recognize(url)
        assert recognition is not None, url
        return recognition.uri

    assert {uri(url) for url, scheme in FORMS if scheme == "wikidata"} == {
        "http://www.wikidata.org/entity/Q146730"
    }
    assert {uri(url) for url, scheme in FORMS if scheme == "viaf"} == {
        "http://viaf.org/viaf/186299955"
    }
    assert uri("https://d-nb.info/gnd/118508288") == "https://d-nb.info/gnd/118508288"


@pytest.mark.parametrize(
    "url",
    [
        "https://imslp.org/wiki/Special:ReverseLookup/534071",
        "https://example.org/anything",
        "https://imslp.org/wiki/File:PMLP01477-Beethoven_Op106.pdf",
        "https://imslp.org/wiki/Category:Beethoven,_Ludwig_van",
        "https://imslp.org/wiki/Help:Contents",
        "https://imslp.org/wiki/IMSLP:About",
        "https://imslp.org/wiki/Special%3AReverseLookup/534071",
        f"https://musicbrainz.org/work/{MB_WORK} ",
        "https://imslp.org/wiki/Sonata%E2%80",
        f"musicbrainz.org/work/{MB_WORK}",
    ],
)
def test_what_is_not_recognised(url: str) -> None:
    assert default_registry().recognize(url) is None


def test_an_identifier_is_decoded_and_its_spaces_written_as_underscores() -> None:
    recognition = default_registry().recognize(
        "https://imslp.org/wiki/Piano%20Sonata%20No.29"
    )
    assert recognition is not None
    assert recognition.identifier == Identifier(IMSLP, "Piano_Sonata_No.29")
    assert recognition.value == "Piano_Sonata_No.29"


def test_a_scheme_yields_an_entity_uri_or_an_identifier_never_both() -> None:
    samples = {
        "musicbrainz_work": f"https://musicbrainz.org/work/{MB_WORK}",
        "musicbrainz_recording": f"https://musicbrainz.org/recording/{MB_WORK}",
        "musicbrainz_release": f"https://musicbrainz.org/release/{MB_WORK}",
        "wikidata": "https://www.wikidata.org/wiki/Q146730",
        "viaf": "https://viaf.org/viaf/186299955",
        "gnd": "https://d-nb.info/gnd/118508288",
        "imslp": f"https://imslp.org/wiki/{OP_106}",
        "doi": "https://doi.org/10.5281/zenodo.7473560",
    }
    for scheme in default_registry().schemes:
        recognition = default_registry().recognize(samples[scheme.id])
        assert recognition is not None
        assert recognition.scheme == scheme
        if scheme.entity_uri is None:
            assert recognition.uri is None
            assert recognition.identifier == Identifier(scheme.uri, recognition.value)
        else:
            assert recognition.identifier is None
            assert recognition.uri == scheme.entity_uri.replace(
                "{value}", recognition.value
            )


def _entry(**members: object) -> dict[str, object]:
    return {
        "id": "x",
        "name": "Example",
        "uri": "https://example.org/scheme",
        "level": None,
        "entity_uri": "https://example.org/entity/{value}",
        "patterns": ["https://example.org/page/([0-9]+)"],
        **members,
    }


def test_an_extension_is_a_new_registry() -> None:
    default = default_registry()
    extended = default.with_schemes(_entry(), KnownScheme.from_dict(_entry(id="y")))
    assert [scheme.id for scheme in extended.schemes][-2:] == ["x", "y"]
    assert len(default.schemes) == 8
    assert default.recognize("https://example.org/page/12") is None
    recognition = extended.recognize("https://example.org/page/12")
    assert recognition is not None
    assert (recognition.scheme.id, recognition.uri) == (
        "x",
        "https://example.org/entity/12",
    )


def test_an_entry_replaces_the_one_of_its_id_in_place() -> None:
    replaced = default_registry().with_schemes(
        _entry(
            id="doi",
            entity_uri="http://dx.doi.org/{value}",
            patterns=["https?://doi\\.org/(10\\.[0-9]+/[^?#]+)"],
        )
    )
    assert [scheme.id for scheme in replaced.schemes] == [entry[0] for entry in ENTRIES]
    recognition = replaced.recognize("https://doi.org/10.5281/zenodo.7473560")
    assert recognition is not None
    assert recognition.uri == "http://dx.doi.org/10.5281/zenodo.7473560"


def test_the_first_matching_entry_recognises() -> None:
    late = default_registry().with_schemes(
        _entry(patterns=["https://musicbrainz\\.org/work/([0-9a-f-]+)"])
    )
    recognition = late.recognize(f"https://musicbrainz.org/work/{MB_WORK}")
    assert recognition is not None
    assert recognition.scheme.id == "musicbrainz_work"


@pytest.mark.parametrize(
    ("members", "message"),
    [
        (
            {"patterns": ["https://example.org/x"]},
            "pattern 'https://example.org/x' of scheme 'x' has 0 capturing groups; "
            "it needs exactly one",
        ),
        (
            {"patterns": ["https://example.org/(a)(b)"]},
            "pattern 'https://example.org/(a)(b)' of scheme 'x' has 2 capturing "
            "groups; it needs exactly one",
        ),
        (
            {"patterns": ["https://example.org/(?P<v>a)"]},
            "pattern 'https://example.org/(?P<v>a)' of scheme 'x' uses syntax "
            "outside the shared subset; only (?:, (?= and (?! may follow '(?'",
        ),
        (
            {"patterns": ["https://example.org/(?<v>a)"]},
            "pattern 'https://example.org/(?<v>a)' of scheme 'x' uses syntax "
            "outside the shared subset; only (?:, (?= and (?! may follow '(?'",
        ),
        (
            {"patterns": ["(?<=a)(b)"]},
            "pattern '(?<=a)(b)' of scheme 'x' uses syntax outside the shared "
            "subset; only (?:, (?= and (?! may follow '(?'",
        ),
        (
            {"patterns": ["(?i)(b)"]},
            "pattern '(?i)(b)' of scheme 'x' uses syntax outside the shared subset; "
            "only (?:, (?= and (?! may follow '(?'",
        ),
        (
            {"patterns": ["(b"]},
            "pattern '(b' of scheme 'x' is no regular expression",
        ),
        ({"level": "score"}, "scheme 'x' has the level 'score', which is no level"),
        (
            {"entity_uri": "https://example.org/entity/"},
            "the entity URI template 'https://example.org/entity/' of scheme 'x' "
            "holds no {value}",
        ),
    ],
)
def test_an_entry_is_refused(members: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        default_registry().with_schemes(_entry(**members))
