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
                "type": "flow_marker",
                "manifestation": "fine",
                "coordinate": [1, 1],
            },
            {
                "id": "j",
                "type": "jump_from",
                "manifestation": "da_capo",
                "coordinate": [1, 1],
            },
            {
                "id": "again",
                "type": "jump_from",
                "manifestation": "repeat_end",
                "coordinate": [1, 1],
            },
            {
                "id": "m",
                "type": "jump_to",
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
        )
    )
    done = value["timelines"][0]
    assert done["regions"][0] == {
        "id": "r",
        "start": [0, 1],
        "end": [1, 1],
        "name": None,
        "meta": {},
    }
    defaults = {"name": None, "label": None, "meta": {}}
    marker, origin, repeat, target = done["flow_control"]
    assert marker == {
        "id": "b",
        "type": "flow_marker",
        "manifestation": "fine",
        "coordinate": [1, 1],
        **defaults,
    }
    assert origin == {
        "id": "j",
        "type": "jump_from",
        "manifestation": "da_capo",
        "coordinate": [1, 1],
        **defaults,
    }
    assert repeat == {
        "id": "again",
        "type": "jump_from",
        "manifestation": "repeat_end",
        "coordinate": [1, 1],
        **defaults,
        "repeat_count": 1,
    }
    assert target == {
        "id": "m",
        "type": "jump_to",
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
            "status": "confirmed",
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
        _stamp(1, display=default),
        _stamp(2, display=default),
        _stamp(3, display=["wedge", "name"]),
        _stamp(4, display=[]),
    ]
    assert minimal(value)["graphical"]["timestamps"] == [
        _stamp(1),
        _stamp(2),
        _stamp(3, display=["wedge", "name"]),
        _stamp(4, display=[]),
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
                    "type": "jump_from",
                    "manifestation": "repeat_end",
                    "coordinate": 1.0,
                    "repeat_count": 2,
                    "label": None,
                }
            ],
        )
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
                    "type": "jump_from",
                    "manifestation": "repeat_end",
                    "coordinate": 1.0,
                    "repeat_count": 2,
                }
            ],
        )
    )


def _repeat(identifier: str, count: Any) -> dict[str, Any]:
    return {
        "id": identifier,
        "type": "jump_from",
        "manifestation": "repeat_end",
        "coordinate": [1, 1],
        "repeat_count": count,
    }


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
            flow_control=[_repeat("a", 1.0), _repeat("b", 2.0)],
            conversion_maps=[
                _linear("l1", scalar=1.0, offset=0.0),
                _linear("l2", scalar=[1, 1], offset=[0, 3]),
                _linear("l3", scalar=[1, 2], offset=False),
            ],
            regions=[{**REGION, "name": 0}],
        )
    )
    (root,) = minimal(value)["timelines"]
    assert [entry.get("repeat_count") for entry in root["flow_control"]] == [None, 2.0]
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
                        "type": "jump_from",
                        "manifestation": "repeat_end",
                        "coordinate": [4, 1],
                        "repeat_count": 1.0,
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
