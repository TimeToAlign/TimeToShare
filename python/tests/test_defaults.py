from __future__ import annotations

import json
from typing import Any

import pytest

from timetoshare import FORMAT_CONTEXT, complete, dumps, minimal

from .conftest import bundle, manifest, timeline, validate

SMALLEST = {
    "timetoshare": "0.2.0",
    "timelines": [{"id": "piece", "unit": "quarters", "length": [32, 1]}],
}
REGION = {"id": "r", "start": [0, 1], "end": [1, 1]}


def test_the_smallest_file_completes_to_the_literal_complete_form() -> None:
    assert complete(SMALLEST) == {
        "timetoshare": "0.2.0",
        "name": None,
        "meta": {},
        "groups": [],
        "measure_maps": [],
        "resources": [],
        "timelines": [
            {
                "id": "piece",
                "unit": "quarters",
                "length": [32, 1],
                "name": None,
                "number_type": "fraction",
                "locked": False,
                "is_segment_line": False,
                "meta": {},
                "children": [],
                "conversion_maps": [],
                "regions": [],
                "flow_control": [],
            }
        ],
    }
    assert minimal(complete(SMALLEST)) == SMALLEST


def test_every_object_gains_exactly_its_defaults() -> None:
    linear = {
        "type": "LinearMap",
        "id": "s",
        "source_unit": None,
        "target_unit": None,
    }
    table = {
        "type": "TableMap",
        "id": "t",
        "source_unit": "quarters",
        "target_unit": "seconds",
        "x_values": [[0, 1], [4, 1]],
        "y_values": [0.0, 2.0],
    }
    view = {
        "type": "MeasureNumberMap",
        "id": "bar",
        "source_unit": "quarters",
        "target_unit": None,
        "measure_map": "bars",
    }
    root = timeline(
        "score",
        regions=[{"id": "r", "start": [0, 1], "end": [1, 1]}],
        flow_control=[
            {
                "id": "b",
                "role": "break",
                "manifestation": "fine",
                "coordinate": [1, 1],
                "ends": {"after": {"jump": "j"}},
            },
            {
                "id": "j",
                "role": "jump",
                "coordinate": [2, 1],
                "targets": [
                    {"repeat_count": 1, "manifestation": "da_capo"},
                    {"to": "m", "determined": False, "reset": False, "label": "D.S."},
                ],
            },
            {
                "id": "m",
                "role": "jump_target",
                "manifestation": "segno",
                "coordinate": [0, 1],
            },
        ],
        conversion_maps=[
            {
                "type": "ChainMap",
                "id": "chain",
                "source_unit": None,
                "target_unit": None,
                "maps": [linear],
            },
            {
                "type": "CombinationMap",
                "id": "combo",
                "source_unit": None,
                "target_unit": None,
                "maps": {"x": {**linear, "id": "x"}, "bar": view},
            },
            {
                "type": "PiecewiseMap",
                "id": "pieces",
                "source_unit": "quarters",
                "target_unit": "seconds",
                "breaks": [[0, 1], [4, 1]],
                "maps": [table],
            },
        ],
    )
    rows = [{"count": 1, "qstamp": [0, 1], "actual_length": [4, 1]}]
    value = complete(
        manifest(
            root,
            groups=[{"id": "g", "members": ["score"]}],
            measure_maps=[{"id": "bars", "rows": rows}],
            graphical={},
            flow_maps=[{"id": "f", "timeline": "score", "chunks": ["r"]}],
            virtual_timelines=[
                {
                    "id": "v",
                    "map": "f",
                    "timeline": "score",
                    "unit": "quarters",
                    "number_type": "fraction",
                    "length": [1, 1],
                }
            ],
        )
    )
    assert value["flow_maps"] == [
        {
            "id": "f",
            "timeline": "score",
            "chunks": ["r"],
            "canonical": False,
            "name": None,
        }
    ]
    assert value["virtual_timelines"][0]["name"] is None
    assert len(value["virtual_timelines"][0]) == 7
    done = value["timelines"][0]
    assert done["regions"][0] == {
        "id": "r",
        "start": [0, 1],
        "end": [1, 1],
        "name": None,
        "meta": {},
    }
    defaults = {"name": None, "label": None, "meta": {}}
    marker, origin, target = done["flow_control"]
    assert marker == {
        "id": "b",
        "role": "break",
        "manifestation": "fine",
        "coordinate": [1, 1],
        "ends": {"after": {"jump": "j"}},
        **defaults,
    }
    assert origin == {
        "id": "j",
        "role": "jump",
        "coordinate": [2, 1],
        "targets": [
            {
                "repeat_count": 1,
                "manifestation": "da_capo",
                "determined": True,
                "reset": True,
                "label": None,
            },
            {"to": "m", "determined": False, "reset": False, "label": "D.S."},
        ],
        **defaults,
    }
    assert target == {
        "id": "m",
        "role": "jump_target",
        "manifestation": "segno",
        "coordinate": [0, 1],
        **defaults,
    }
    chain, combo, pieces = done["conversion_maps"]
    assert chain == {
        "type": "ChainMap",
        "id": "chain",
        "source_unit": None,
        "target_unit": None,
        "name": None,
        "maps": [{**linear, "name": None, "scalar": 1, "offset": 0}],
    }
    assert combo["name"] is None
    assert combo["maps"]["x"] == {
        **linear,
        "id": "x",
        "name": None,
        "scalar": 1,
        "offset": 0,
    }
    assert combo["maps"]["bar"] == {**view, "name": None}
    assert pieces["name"] is None
    assert pieces["maps"] == [
        {**table, "name": None, "kind": "linear", "extrapolate": "none"}
    ]
    assert value["groups"] == [
        {"id": "g", "members": ["score"], "name": None, "meta": {}}
    ]
    assert value["measure_maps"] == [
        {"id": "bars", "rows": rows, "name": None, "meta": {}}
    ]
    assert value["graphical"] == {
        "styles": {},
        "rules": [],
        "order": {},
        "timestamps": [],
        "matchstamps": [],
        "elisions": [],
    }
    validate(value)


@pytest.mark.parametrize(
    ("unit", "number_type"),
    [
        ("ticks", "int"),
        ("seconds", "float"),
        ("whole_notes", "fraction"),
        ("pixels", "int"),
        ("css_pixels", "float"),
        ("user_units", "float"),
    ],
)
def test_the_unit_decides_the_default_number_type(unit: str, number_type: str) -> None:
    value = complete(manifest(timeline("t", unit, None)))
    assert value["timelines"][0]["number_type"] == number_type
    assert "number_type" not in minimal(value)["timelines"][0]


def test_absent_defaults_are_never_added_or_removed() -> None:
    value = complete(SMALLEST)
    assert "id" not in value and "graphical" not in value
    assert "offset" not in value["timelines"][0]
    styled = manifest(timeline("score"), graphical={})
    assert minimal(styled)["graphical"] == {}
    assert complete(styled)["graphical"] == {
        "styles": {},
        "rules": [],
        "order": {},
        "timestamps": [],
        "matchstamps": [],
        "elisions": [],
    }
    child = manifest(timeline("score", children=[timeline("c", offset=(0, 1))]))
    assert minimal(child)["timelines"][0]["children"][0]["offset"] == [0, 1]


def _described() -> dict[str, Any]:
    """A manifest with statements and provenance on itself, its root and a region."""
    statements = {
        "type": ["schema:MusicComposition"],
        "wdt:P86": [{"id": "wd:Q255", "label": "Beethoven"}],
    }
    provenance = [
        {
            "property": "wdt:P86",
            "value": {"id": "wd:Q255"},
            "date": "2026-11-18",
        }
    ]
    described = {"statements": statements, "provenance": provenance}
    context = {
        **FORMAT_CONTEXT,
        "schema": "http://schema.org/",
        "wd": "http://www.wikidata.org/entity/",
        "wdt": "http://www.wikidata.org/prop/direct/",
    }
    return {
        "@context": context,
        **manifest(
            timeline("score", **described, regions=[{**REGION, **described}]),
            id="op106",
            **described,
        ),
    }


def test_statements_provenance_and_the_context_have_no_default() -> None:
    value = _described()
    done = complete(value)
    for key in ("@context", "statements", "provenance"):
        assert done[key] == value[key]
    root = done["timelines"][0]
    for element, given in (
        (root, value["timelines"][0]),
        (root["regions"][0], value["timelines"][0]["regions"][0]),
    ):
        assert element["statements"] == given["statements"]
        assert element["provenance"] == given["provenance"]
    assert minimal(done) == value
    assert minimal(value) == value
    validate(done)


def _stamp(number: int, **members: Any) -> dict[str, Any]:
    """A named timestamp on ``score`` at 1, with the given further members."""
    return {
        "id": f"timestamp_{number}",
        "timeline": "score",
        "coordinate": [1, 1],
        "name": "Entry",
        **members,
    }


def test_a_named_timestamp_completes_its_display() -> None:
    value = manifest(
        timeline("score"),
        graphical={
            "timestamps": [
                _stamp(1),
                _stamp(2, display=["cross_section", "wedge", "name"]),
                _stamp(3, display=["name", "wedge"]),
                _stamp(4, display=[]),
            ]
        },
    )
    default = ["wedge", "name", "cross_section"]
    assert complete(value)["graphical"]["timestamps"] == [
        _stamp(1, display=default, matchstamp=False, groupstamp=False),
        _stamp(2, display=default, matchstamp=False, groupstamp=False),
        _stamp(3, display=["wedge", "name"], matchstamp=False, groupstamp=False),
        _stamp(4, display=[], matchstamp=False, groupstamp=False),
    ]
    assert minimal(value)["graphical"]["timestamps"] == [
        _stamp(1),
        _stamp(2),
        _stamp(3, display=["wedge", "name"]),
        _stamp(4, display=[]),
    ]


def _elision(number: int, **members: Any) -> dict[str, Any]:
    """An elision on ``score`` from 1 to 3, with the given further members."""
    return {
        "id": f"elision_{number}",
        "timeline": "score",
        "start": [1, 1],
        "end": [3, 1],
        **members,
    }


def test_an_elision_completes_its_display_and_never_its_width() -> None:
    value = manifest(
        timeline("score"),
        graphical={
            "elisions": [
                _elision(1),
                _elision(2, display=["name", "ellipsis"]),
                _elision(3, display=["ellipsis"]),
                _elision(4, display=["continuation", "name", "ellipsis"]),
                _elision(5, name="Coda", width={"ratio": 1}),
                _elision(6, display=[]),
            ]
        },
    )
    default = ["ellipsis", "name"]
    stated = ["ellipsis", "name", "continuation"]
    assert complete(value)["graphical"]["elisions"] == [
        _elision(1, display=default),
        _elision(2, display=default),
        _elision(3, display=["ellipsis"]),
        _elision(4, display=stated),
        _elision(5, name="Coda", width={"ratio": 1}, display=default),
        _elision(6, display=[]),
    ]
    assert minimal(value)["graphical"]["elisions"] == [
        _elision(1),
        _elision(2),
        _elision(3, display=["ellipsis"]),
        _elision(4, display=stated),
        _elision(5, name="Coda", width={"ratio": 1}),
        _elision(6, display=[]),
    ]


def test_values_other_than_the_default_stay() -> None:
    value = manifest(
        timeline(
            "score",
            locked=True,
            number_type="float",
            length=8.0,
            flow_control=[
                {
                    "id": "b",
                    "role": "jump",
                    "coordinate": 1.0,
                    "targets": [
                        {
                            "repeat_count": 1,
                            "determined": False,
                            "reset": False,
                            "label": "Repeat",
                        },
                        {"by": -1, "determined": True, "reset": True, "label": None},
                    ],
                    "label": None,
                }
            ],
        ),
        flow_maps=[
            {
                "id": "f",
                "timeline": "score",
                "chunks": [],
                "canonical": True,
                "name": None,
            },
            {"id": "g", "timeline": "score", "chunks": [], "canonical": False},
        ],
        virtual_timelines=[],
    )
    assert minimal(value) == manifest(
        timeline(
            "score",
            locked=True,
            number_type="float",
            length=8.0,
            flow_control=[
                {
                    "id": "b",
                    "role": "jump",
                    "coordinate": 1.0,
                    "targets": [
                        {
                            "repeat_count": 1,
                            "determined": False,
                            "reset": False,
                            "label": "Repeat",
                        },
                        {"by": -1.0},
                    ],
                }
            ],
        ),
        flow_maps=[
            {"id": "f", "timeline": "score", "chunks": [], "canonical": True},
            {"id": "g", "timeline": "score", "chunks": []},
        ],
        virtual_timelines=[],
    )


def _linear(identifier: str, **members: Any) -> dict[str, Any]:
    return {
        "type": "LinearMap",
        "id": identifier,
        "source_unit": "quarters",
        "target_unit": "seconds",
        **members,
    }


def test_numbers_equal_to_the_default_in_value_are_the_default() -> None:
    value = manifest(
        timeline(
            "score",
            conversion_maps=[
                _linear("l1", scalar=1.0, offset=0.0),
                _linear("l2", scalar=[1, 1], offset=[0, 3]),
                _linear("l3", scalar=[1, 2], offset=False),
            ],
            regions=[{**REGION, "name": 0}],
        )
    )
    (root,) = minimal(value)["timelines"]
    maps = {entry["id"]: entry for entry in root["conversion_maps"]}
    assert (
        sorted(maps["l1"])
        == sorted(maps["l2"])
        == [
            "id",
            "source_unit",
            "target_unit",
            "type",
        ]
    )
    assert (maps["l3"]["scalar"], maps["l3"]["offset"]) == ([1, 2], False)
    assert root["regions"][0]["name"] == 0


def test_values_are_compared_after_respelling_and_ordering() -> None:
    value = manifest(
        timeline("score", children=[timeline("c", length=(1, 1), offset=(4, 8))]),
        graphical={
            "timestamps": [
                {
                    "id": "timestamp_1",
                    "timeline": "score",
                    "coordinate": [0, 1],
                    "name": "x",
                    "display": ["name", "wedge", "cross_section"],
                }
            ]
        },
    )
    done = minimal(value)
    assert done["timelines"][0]["children"][0]["offset"] == [1, 2]
    assert "display" not in done["graphical"]["timestamps"][0]


def test_unknown_keys_pass_through() -> None:
    value = manifest(
        timeline("score", lenght=1, flow_control=[], regions=[{**REGION, "codas": []}]),
        extra={"meta": {}},
    )
    assert minimal(value) == manifest(
        timeline("score", lenght=1, regions=[{**REGION, "codas": []}]),
        extra={"meta": {}},
    )
    assert complete(value)["extra"] == {"meta": {}}
    assert complete(value)["timelines"][0]["regions"][0]["codas"] == []


def test_length_survives_both_forms() -> None:
    for length in (None, [8, 1]):
        value = manifest(timeline("score", length=length))
        assert complete(value)["timelines"][0]["length"] == length
        assert minimal(value)["timelines"][0]["length"] == length


def _documents() -> list[dict[str, Any]]:
    return [
        SMALLEST,
        complete(SMALLEST),
        bundle(),
        _described(),
        manifest(timeline("score", lenght=1, regions=[{**REGION, "codas": []}])),
        manifest(
            timeline("score", locked=True, children=[timeline("c", offset=(0, 1))]),
            graphical={},
        ),
        manifest(
            timeline(
                "score",
                flow_control=[
                    {
                        "id": "j",
                        "role": "jump",
                        "coordinate": [4, 1],
                        "targets": [{"repeat_count": 1.0, "reset": True}],
                    }
                ],
            )
        ),
    ]


@pytest.mark.parametrize("value", _documents())
def test_the_round_trips(value: dict) -> None:
    given = json.dumps(value)
    assert dumps(minimal(complete(value))) == dumps(minimal(value))
    assert dumps(complete(minimal(value)), serialization="jcs") == dumps(
        complete(value), serialization="jcs"
    )
    assert complete(value) is not value and minimal(value) is not value
    assert json.dumps(value) == given
    validate(complete(value))
    validate(minimal(value))


def test_a_match_timestamp_and_an_anchor_gain_their_own_defaults() -> None:
    ordinary = {"id": "timestamp_1", "timeline": "score", "coordinate": [1, 1]}
    ordinary["name"] = "Entry"
    matched = {"id": "timestamp_2", "timeline": "score", "coordinate": [2, 1]}
    matched["matchstamp"] = True
    shown = {**matched, "id": "timestamp_3", "display": ["cross_section", "name"]}
    anchors = [
        {"id": "anchor_1", "timestamps": ["timestamp_2", "timestamp_3"]},
        {"id": "anchor_2", "timestamps": ["timestamp_2", "timestamp_3"]},
    ]
    anchors[1]["display"] = ["name", "line"]
    matchstamp = {"id": "matchstamp_1", "name": "M", "alignment_anchors": anchors}
    matchstamp["match_claims"] = []
    graphical = {"timestamps": [ordinary, matched, shown], "matchstamps": [matchstamp]}
    value = manifest(timeline("score"), graphical=graphical)
    completed = complete(value)["graphical"]
    assert [stamp.get("display") for stamp in completed["timestamps"]] == [
        ["wedge", "name", "cross_section"],
        ["cross_section"],
        ["name", "cross_section"],
    ]
    assert [stamp.get("matchstamp") for stamp in completed["timestamps"]] == [
        False,
        True,
        True,
    ]
    assert [stamp.get("groupstamp") for stamp in completed["timestamps"]] == [
        False,
        False,
        False,
    ]
    held = completed["matchstamps"][0]["alignment_anchors"]
    assert [anchor["display"] for anchor in held] == [["line"], ["line", "name"]]
    stripped = minimal(value)["graphical"]
    assert ["display" in stamp for stamp in stripped["timestamps"]] == [
        False,
        False,
        True,
    ]
    assert [stamp.get("matchstamp") for stamp in stripped["timestamps"]] == [
        None,
        True,
        True,
    ]
    held = stripped["matchstamps"][0]["alignment_anchors"]
    assert ["display" in anchor for anchor in held] == [False, True]
    assert minimal(complete(value)) == minimal(value)
    other = {**ordinary, "display": ["cross_section"]}
    kept = minimal(manifest(timeline("score"), graphical={"timestamps": [other]}))
    assert kept["graphical"]["timestamps"][0]["display"] == ["cross_section"]
    assert ["groupstamp" in stamp for stamp in stripped["timestamps"]] == [
        False,
        False,
        False,
    ]
    grouped = {**ordinary, "groupstamp": True}
    graphical = {"timestamps": [grouped]}
    kept = minimal(manifest(timeline("score"), graphical=graphical))
    assert kept["graphical"]["timestamps"][0]["groupstamp"] is True
