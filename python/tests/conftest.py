from __future__ import annotations

from typing import Any

import timetoshare
from timetoshare import with_file_ids

# The inline documents of this suite write IDs bare, as in memory; a check
# reads a manifest file, so these wrappers hand it the file form, every ID
# written '#' + the ID (``with_file_ids``, proven in ``test_ids.py``).


def validate(value: Any) -> None:
    """``timetoshare.validate`` of the file form of an inline document."""
    timetoshare.validate(filed(value))


def unknown_keys(value: Any) -> list[dict]:
    return timetoshare.unknown_keys(filed(value))


def manifest_warnings(value: Any) -> list[dict]:
    return timetoshare.manifest_warnings(filed(value))


def identity_problems(value: Any) -> list:
    return timetoshare.identity_problems(filed(value))


def filed(value: Any) -> Any:
    """The file form of an inline document; any other value as it is."""
    return with_file_ids(value) if isinstance(value, dict) else value


def timeline(
    identifier: str, unit: str = "quarters", length: Any = (8, 1), **members: Any
) -> dict:
    """A timeline of the minimal form; a tuple length or offset is written as a pair."""
    pairs = {"length": length, **members}
    for key in ("length", "offset"):
        if isinstance(pairs.get(key), tuple):
            pairs[key] = list(pairs[key])
    return {"id": identifier, "unit": unit, **pairs}


def manifest(*timelines: dict, **members: Any) -> dict:
    """A manifest of the given roots in the minimal form."""
    return {"timetoshare": "0.2.0", "timelines": list(timelines), **members}


def group(identifier: str, *members: str, **rest: Any) -> dict:
    return {"id": identifier, "members": list(members), **rest}


def bundle() -> dict:
    """A named manifest: two groups, two ungrouped roots, a child as a member."""
    return manifest(
        timeline("annotations"),
        timeline("page", "pixels", 1200),
        timeline("performance", "seconds", 61.5),
        timeline(
            "recording",
            "seconds",
            120.0,
            children=[timeline("excerpt", "seconds", 30.0, offset=2.0)],
        ),
        timeline("score"),
        id="op35",
        name="Mixed",
        groups=[
            group("group_1", "performance", "score"),
            group("group_2", "excerpt", "page"),
        ],
        graphical={
            "order": {
                "group_1": ["score", "performance"],
                "group_2": ["page", "excerpt"],
            }
        },
    )


def _respellable(canonical: bool) -> dict:
    def number(written: Any, spelled: Any) -> Any:
        return spelled if canonical else written

    return manifest(
        timeline(
            "midi",
            "ticks",
            number(480.0, 480),
            children=[timeline("b", "ticks", 120, offset=number(240.0, 240))],
        ),
        timeline(
            "score",
            length=[32, number(1.0, 1)],
            children=[timeline("a", length=[4, 1], offset=[number(8.0, 8), 1])],
            conversion_maps=[
                {
                    "type": "ChainMap",
                    "id": "chain",
                    "source_unit": "quarters",
                    "target_unit": "seconds",
                    "maps": [
                        {
                            "type": "TableMap",
                            "id": "table",
                            "source_unit": "quarters",
                            "target_unit": "seconds",
                            "x_values": [[0, 1], [1.0, 2]],
                            "y_values": [0.0, 0.5],
                            "kind": "linear",
                            "extrapolate": "none",
                        }
                    ],
                },
                {
                    "type": "LinearMap",
                    "id": "linear",
                    "source_unit": "quarters",
                    "target_unit": "seconds",
                    "scalar": 1.0,
                    "offset": [0, 1.0],
                },
            ],
            regions=[
                {"id": "r", "start": [0, number(1.0, 1)], "end": [number(1.0, 1), 2]}
            ],
            flow_control=[
                {
                    "id": "m",
                    "role": "jump_target",
                    "manifestation": "segno",
                    "coordinate": [number(2.0, 2), 1],
                }
            ],
        ),
        timeline(
            "take",
            "seconds",
            number(60, 60.0),
            regions=[{"id": "s", "start": number(0, 0.0), "end": 1.5}],
        ),
        measure_maps=[
            {
                "id": "bars",
                "rows": [
                    {
                        "count": 1,
                        "qstamp": [0, 1.0],
                        "actual_length": [4.0, 1],
                        "nominal_length": 4.0,
                    }
                ],
            }
        ],
    )


def respellable() -> dict:
    """A manifest in canonical order whose values are spelled unlike their number types.

    A Fraction member is written as an integral float in a length, a child
    offset, a region and a jump target; a ticks length and offset as integral
    floats; a seconds length and region start as integers. Numbers that are no
    own-axis values keep their spelling: a nested TableMap's x value
    ``[1.0, 2]`` and y values, the LinearMap's ``scalar`` ``1.0`` and
    ``offset`` ``[0, 1.0]``, and the MeasureMap row's ``[0, 1.0]``,
    ``[4.0, 1]`` and ``4.0``.
    """
    return _respellable(canonical=False)


def respelled() -> dict:
    """``respellable()`` with every own-axis value respelled by its number type."""
    return _respellable(canonical=True)


# Statements ------------------------------------------------------------------
# The documents below are written in the file form: the IRIs of statements are
# the same in a file and in memory, and the functions of
# ``timetoshare.statements`` read either ID form.

WIKIDATA_PATTERN = "https?://(?:www\\.|m\\.)?wikidata\\.org/(?:wiki|entity)/(Q[1-9][0-9]*)/?(?:[?#].*)?"
MUSICBRAINZ_WORK_PATTERN = (
    "https?://(?:www\\.)?musicbrainz\\.org/work/([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-"
    "[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})/?(?:[?#].*)?"
)


def _contributor(role: str) -> dict:
    return {
        "type": ["schema:OrganizationRole"],
        "schema:contributor": [{"id": "?"}],
        "schema:roleName": [role],
    }


CATALOGUE_TEST: dict = {
    "prefixes": {
        "dcterms": "http://purl.org/dc/terms/",
        "gnd": "https://d-nb.info/gnd/",
        "melod": "https://lod.academy/melod/vocab/ontology#",
        "melodTerms": "https://lod.academy/melod/vocab/terms#",
        "rel": "http://id.loc.gov/vocabulary/relators/",
        "schema": "http://schema.org/",
        "viaf": "http://viaf.org/viaf/",
        "wd": "http://www.wikidata.org/entity/",
        "wdt": "http://www.wikidata.org/prop/direct/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
    },
    "aliases": {"https://schema.org/": "http://schema.org/"},
    "systems": [
        {
            "id": "wikidata",
            "name": "Wikidata",
            "prefixes": ["wd", "wdt"],
            "things": [
                {
                    "id": "wikidata",
                    "kind": "item",
                    "name": "Wikidata",
                    "iri": "http://www.wikidata.org/entity/{value}",
                    "prefix": "wd",
                    "scheme_uri": "http://id.loc.gov/vocabulary/identifiers/wikidata",
                    "lrmoo_class": None,
                    "lowercase": False,
                    "patterns": [WIKIDATA_PATTERN],
                }
            ],
            "lookup": {"route": "browser"},
        },
        {
            "id": "musicbrainz",
            "name": "MusicBrainz",
            "prefixes": ["schema"],
            "things": [
                {
                    "id": "musicbrainz_work",
                    "kind": "work",
                    "name": "MusicBrainz work ID",
                    "iri": "http://musicbrainz.org/work/{value}",
                    "scheme_uri": "http://www.wikidata.org/entity/P435",
                    "lrmoo_class": None,
                    "lowercase": True,
                    "patterns": [MUSICBRAINZ_WORK_PATTERN],
                }
            ],
            "lookup": {"route": "server"},
        },
        {
            "id": "melody",
            "name": "MeLODy",
            "prefixes": ["melod", "melodTerms"],
            "things": [],
            "lookup": {"route": "none"},
        },
        {
            "id": "fallback",
            "name": "Fallback",
            "prefixes": ["dcterms", "rel", "schema"],
            "things": [],
            "lookup": {"route": "none"},
        },
    ],
    "verbs": [
        {
            "id": "is_a",
            "label": "is a",
            "patterns": {
                "wikidata": [{"pattern": {"wdt:P31": [{"id": "?"}]}}],
                "fallback": [{"pattern": {"type": ["?"]}}],
            },
        },
        {
            "id": "same_as",
            "label": "same as",
            "patterns": {"fallback": [{"pattern": {"schema:sameAs": [{"id": "?"}]}}]},
        },
        {
            "id": "performed_by",
            "label": "performed by",
            "patterns": {
                "wikidata": [{"pattern": {"wdt:P175": [{"id": "?"}]}}],
                "musicbrainz": [
                    {"pattern": {"schema:contributor": [_contributor("?role")]}}
                ],
                "melody": [
                    {
                        "pattern": {
                            "melod:hasContribution": [
                                {
                                    "type": ["melod:Contribution"],
                                    "melod:hasAgent": [{"id": "?"}],
                                    "melod:hasRole": [{"id": "melodTerms:Performer"}],
                                }
                            ]
                        }
                    }
                ],
                "fallback": [{"pattern": {"rel:prf": [{"id": "?"}]}}],
            },
        },
        {
            "id": "conducted_by",
            "label": "conducted by",
            "patterns": {
                "musicbrainz": [
                    {"pattern": {"schema:contributor": [_contributor("conductor")]}}
                ]
            },
        },
        {
            "id": "version_or_edition_of",
            "label": "version or edition of",
            "patterns": {
                "wikidata": [{"pattern": {"wdt:P629": [{"id": "?"}]}}],
                "fallback": [{"pattern": {"schema:exampleOfWork": [{"id": "?"}]}}],
            },
        },
        {
            "id": "part_of",
            "label": "part of",
            "inverse_label": "has part",
            "patterns": {
                "fallback": [
                    {"pattern": {"dcterms:isPartOf": [{"id": "?"}]}},
                    {"pattern": {"dcterms:hasPart": [{"id": "?"}]}, "inverse": True},
                ]
            },
        },
    ],
    "types": [
        {
            "id": "video",
            "label": "video",
            "is_a": {
                "wikidata": [{"pattern": {"wdt:P31": [{"id": "wd:Q98069877"}]}}],
                "fallback": [{"pattern": {"type": ["schema:VideoObject"]}}],
            },
            "verbs": ["performed_by", "same_as"],
            "lookup": ["wikidata"],
        }
    ],
}
"""The test catalogue, the same in the JavaScript suite."""


def _terms(*prefixes: str) -> dict:
    context = dict(timetoshare.FORMAT_CONTEXT)
    names = {**CATALOGUE_TEST["prefixes"], "gnd": "https://d-nb.info/gnd/"}
    context.update((prefix, names[prefix]) for prefix in prefixes)
    return context


def m1() -> dict:
    """A recording with a root, a region and a child, without statements."""
    return {
        "@context": _terms("schema", "wd", "wdt"),
        "timetoshare": "0.2.0",
        "id": "#rec",
        "timelines": [
            {
                "id": "#cpt_1",
                "unit": "seconds",
                "length": None,
                "regions": [{"id": "#region_1", "start": 0.0, "end": 10.0}],
                "children": [
                    {"id": "#cpt_2", "unit": "seconds", "offset": 0.0, "length": 5.0}
                ],
            }
        ],
    }


MUSICBRAINZ_WORK = "http://musicbrainz.org/work/8d331505-4d88-39ae-81c7-bec5da77af96"


def m2() -> dict:
    """The two described timelines of a score encoding and its video."""
    return {
        "@context": _terms(
            "dcterms", "gnd", "melod", "rel", "schema", "viaf", "wd", "wdt", "xsd"
        ),
        "timetoshare": "0.2.0",
        "timelines": [
            {
                "id": "#clt_6",
                "unit": "quarters",
                "length": [27, 1],
                "statements": {
                    "dcterms:created": [{"@value": "2025-12-05", "@type": "xsd:date"}],
                    "schema:exampleOfWork": [
                        {"id": MUSICBRAINZ_WORK, "label": "Clair de lune"}
                    ],
                    "type": ["melod:Manifestation", "schema:SheetMusic"],
                    "wdt:P629": [
                        {
                            "id": "wd:Q29117946",
                            "label": "Clair de lune",
                            "schema:sameAs": [
                                {"id": MUSICBRAINZ_WORK},
                                {"id": "gnd:300042558"},
                            ],
                        }
                    ],
                },
            },
            {
                "id": "#cpt_1",
                "unit": "seconds",
                "length": None,
                "statements": {
                    "rel:prf": [{"id": "viaf:113931950"}],
                    "schema:sameAs": [
                        {"id": "https://www.youtube.com/watch?v=Ch2mrPm1JnM"}
                    ],
                    "type": ["schema:VideoObject", "melod:Manifestation"],
                    "wdt:P175": [
                        {
                            "id": "wd:Q235650",
                            "label": "Maria João Pires",
                            "schema:sameAs": [
                                {"id": "viaf:113931950"},
                                {"id": "gnd:124927521"},
                            ],
                        }
                    ],
                    "wdt:P31": [{"id": "wd:Q98069877"}],
                },
            },
        ],
    }
