from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from timetoshare import (
    canonical_order,
    complete,
    dumps,
    minimal,
)

from .conftest import bundle, manifest, respellable, respelled, timeline, validate


def _text(value: Any) -> str:
    """The pretty JSON of a value wrapped in an array, which is no manifest.

    The text tells ``8.0`` from ``8`` and shows a manifest as given, neither
    ordered nor respelled.
    """
    return dumps([value], serialization="json")


def test_canonical_order_copies_and_reorders_manifests_only() -> None:
    value = manifest(timeline("b"), timeline("a"))
    text = json.dumps(value)
    assert [root["id"] for root in canonical_order(value)["timelines"]] == ["a", "b"]
    assert json.dumps(value) == text
    other = {"b": [3, 1], "timeline": {"regions": [{"id": "z"}, {"id": "a"}]}}
    assert json.dumps(canonical_order(other)) == json.dumps(other)


def test_the_writer_sorts_every_object_by_key() -> None:
    value = {"b": 1, "\U0001f600": 2, "\ufb00": 3, "A": {"z": 0, "10": 1, "2": 2}}
    assert dumps(value) == (
        'A:\n  "10": 1\n  "2": 2\n  z: 0\nb: 1\n"\ufb00": 3\n"\U0001f600": 2\n'
    )


def _tied_manifest() -> dict[str, Any]:
    """A manifest with ties at every key level, own-axis values in mixed forms."""
    regions = [
        ("rb", [2, 1], [6, 1]),
        ("ra", [2, 1], [6, 1]),
        ("rc", [2, 1], [4, 1]),
        ("rd", [5, 8], [2, 3]),
    ]
    root = timeline(
        "piece",
        length=(16, 1),
        number_type="fraction",
        children=[
            timeline(
                "z",
                offset=(1, 1),
                children=[
                    timeline("y", length=(2, 1), offset=(1, 1)),
                    timeline("x", length=(2, 1), offset=(0, 1)),
                ],
            ),
            timeline("m", offset=(1, 1)),
            timeline("b", offset=(5, 8)),
            timeline("a", offset=(2, 3)),
        ],
        conversion_maps=[
            {
                "type": "LinearMap",
                "id": map_id,
                "source_unit": "quarters",
                "target_unit": None,
                "offset": [1, 2],
            }
            for map_id in ["\U0001f600", "\ufb00", "B2", "a2", "B"]
        ],
        regions=[{"id": i, "start": s, "end": e} for i, s, e in regions],
        flow_control=[
            *[
                {
                    "id": i,
                    "type": "flow_marker",
                    "manifestation": "fine",
                    "coordinate": c,
                }
                for i, c in [("kb", [12, 1]), ("ka", [12, 1]), ("kz", [5, 8])]
            ],
            {
                "id": "jj",
                "type": "jump_from",
                "manifestation": "dal_segno",
                "coordinate": [8, 1],
                "target": "Coda",
            },
            *[
                {
                    "id": i,
                    "type": "jump_from",
                    "manifestation": "da_capo",
                    "coordinate": c,
                }
                for i, c in [("jd", [8, 1]), ("js", [8, 1]), ("je", [5, 8])]
            ],
            *[
                {"id": i, "type": "jump_to", "manifestation": "segno", "coordinate": c}
                for i, c in [
                    ("\U0001f600!", [2, 1]),
                    ("\ufb00!", [2, 1]),
                    ("\u00e9", [2, 1]),
                    ("Coda", [2, 1]),
                    ("starting", [5, 8]),
                ]
            ],
        ],
    )
    rows = [{"count": 1, "qstamp": [0, 1], "actual_length": [4, 1]}]
    return manifest(
        root,
        measure_maps=[
            {"id": measure_map_id, "rows": rows}
            for measure_map_id in ["m\ufb00", "mb", "ma"]
        ],
    )


def test_every_tie_resolves_to_the_canonical_order() -> None:
    result = canonical_order(_tied_manifest())
    validate(result)
    root = result["timelines"][0]
    assert [child["id"] for child in root["children"]] == ["b", "a", "m", "z"]
    assert [child["id"] for child in root["children"][3]["children"]] == ["x", "y"]
    assert [entry["id"] for entry in root["conversion_maps"]] == [
        "B",
        "B2",
        "a2",
        "\ufb00",
        "\U0001f600",
    ]
    assert [entry["id"] for entry in root["regions"]] == ["rd", "rc", "ra", "rb"]
    assert [entry["id"] for entry in root["flow_control"]] == [
        "je",
        "kz",
        "starting",
        "Coda",
        "\u00e9",
        "\ufb00!",
        "\U0001f600!",
        "jd",
        "jj",
        "js",
        "ka",
        "kb",
    ]
    assert [entry["id"] for entry in result["measure_maps"]] == ["ma", "mb", "m\ufb00"]


def test_bare_values_compare_by_exact_value() -> None:
    root = timeline(
        "take",
        "seconds",
        10.0,
        children=[
            timeline("late", "seconds", 1.0, offset=2),
            timeline("tie-b", "seconds", 1.0, offset=0.625),
            timeline("tie-a", "seconds", 1.0, offset=0.625),
            timeline("early", "seconds", 1.0, offset=0.5),
        ],
        regions=[
            {"id": "r2", "start": 1, "end": 2.5},
            {"id": "r1", "start": 1.0, "end": 2},
        ],
    )
    result = canonical_order(manifest(root))["timelines"][0]
    assert [child["id"] for child in result["children"]] == [
        "early",
        "tie-a",
        "tie-b",
        "late",
    ]
    assert [region["id"] for region in result["regions"]] == ["r1", "r2"]
    mixed = canonical_order(
        {
            "timelines": [
                {
                    "id": "q",
                    "children": [
                        {"id": "c", "offset": [5, 8]},
                        {"id": "b", "offset": 0.625},
                        {"id": "a", "offset": [2, 1]},
                    ],
                }
            ]
        }
    )
    assert [child["id"] for child in mixed["timelines"][0]["children"]] == [
        "b",
        "c",
        "a",
    ]


def test_roots_groups_and_members_are_ordered_and_display_orders_kept() -> None:
    value = bundle()
    value["timelines"].reverse()
    value["groups"].reverse()
    for group in value["groups"]:
        group["members"].reverse()
    value["graphical"]["order"] = {
        "group_2": ["excerpt", "page"],
        "group_1": ["performance", "score"],
    }
    given = copy.deepcopy(value)
    result = canonical_order(value)
    assert value == given
    assert [root["id"] for root in result["timelines"]] == [
        "annotations",
        "page",
        "performance",
        "recording",
        "score",
    ]
    assert [group["id"] for group in result["groups"]] == ["group_1", "group_2"]
    assert [group["members"] for group in result["groups"]] == [
        ["performance", "score"],
        ["excerpt", "page"],
    ]
    assert result["graphical"]["order"] == {
        "group_2": ["excerpt", "page"],
        "group_1": ["performance", "score"],
    }
    validate(result)


def _stamp(identifier: str, line: str, coordinate: Any) -> dict:
    return {"id": identifier, "timeline": line, "coordinate": coordinate, "name": "x"}


def test_named_timestamps_are_ordered_by_timeline_coordinate_and_id() -> None:
    value = manifest(
        timeline("a"),
        timeline("b"),
        graphical={
            "timestamps": [
                _stamp("timestamp_4", "b", [1, 1]),
                _stamp("timestamp_3", "a", [3, 2]),
                _stamp("timestamp_2", "a", [3, 2]),
                _stamp("timestamp_1", "a", [5, 1]),
            ]
        },
    )
    given = copy.deepcopy(value)
    result = canonical_order(value)
    assert value == given
    assert [entry["id"] for entry in result["graphical"]["timestamps"]] == [
        "timestamp_2",
        "timestamp_3",
        "timestamp_1",
        "timestamp_4",
    ]
    validate(result)


def test_a_named_timestamp_s_display_is_put_in_canonical_order() -> None:
    displays = [
        ["cross_section", "coordinate", "id", "name", "wedge"],
        ["zeta", "alpha", "wedge"],
        [2, "name", 1, "zeta", "wedge"],
    ]
    value = manifest(
        timeline("a"),
        graphical={
            "timestamps": [
                {**_stamp(f"timestamp_{index}", "a", [index, 1]), "display": display}
                for index, display in enumerate(displays, start=1)
            ]
        },
    )
    given = copy.deepcopy(value)
    result = canonical_order(value)
    assert value == given
    assert [entry["display"] for entry in result["graphical"]["timestamps"]] == [
        ["wedge", "name", "id", "coordinate", "cross_section"],
        ["wedge", "alpha", "zeta"],
        ["wedge", "name", "zeta", 2, 1],
    ]
    validate(
        result | {"graphical": {"timestamps": result["graphical"]["timestamps"][:1]}}
    )


def test_a_named_timestamp_is_spelled_on_its_timelines_axis() -> None:
    value = manifest(
        timeline("score"),
        timeline("take", "seconds", 60.0),
        graphical={
            "timestamps": [
                _stamp("timestamp_1", "score", [6.0, 1]),
                _stamp("timestamp_2", "take", 2),
                _stamp("timestamp_3", "ghost", 2),
            ]
        },
    )
    for convert in (complete, minimal, canonical_order):
        timestamps = convert(value)["graphical"]["timestamps"]
        coordinates = {entry["id"]: entry["coordinate"] for entry in timestamps}
        assert _text(coordinates) == _text(
            {"timestamp_1": [6, 1], "timestamp_2": 2.0, "timestamp_3": 2}
        ), convert


def test_members_are_ordered_by_code_point() -> None:
    value = {
        "timelines": [],
        "groups": [{"id": "g", "members": ["\U0001f600", "\ufb00", "b"]}],
    }
    assert canonical_order(value)["groups"][0]["members"] == [
        "b",
        "\ufb00",
        "\U0001f600",
    ]


def test_a_member_that_is_no_string_is_refused() -> None:
    value = {"timelines": [], "groups": [{"id": "g", "members": ["a", 5]}]}
    with pytest.raises(ValueError, match="cannot put members in canonical order"):
        canonical_order(value)


def test_readers_coerce_and_writers_spell_canonically() -> None:
    value, twin = respellable(), respelled()
    written = _text(value)
    assert written != _text(twin)
    assert _text(canonical_order(twin)) == _text(twin)
    for convert in (complete, minimal, canonical_order):
        assert _text(convert(value)) == _text(convert(twin)), convert
    assert dumps(value) == dumps(twin)
    assert _text(value) == written


def test_a_value_without_an_exact_respelling_is_left_as_written() -> None:
    value = manifest(timeline("take", "seconds", 9007199254740993))
    (root,) = canonical_order(value)["timelines"]
    assert type(root["length"]) is int
    assert root["length"] == 9007199254740993


def test_rfc8785_json_sorts_keys_by_utf16_code_units() -> None:
    value = {
        "\U0001f600": {"b": True, "a": [1, 2.5, None]},
        "\ufb00": "\u00fc",
        "\u00e9": 1,
        "z": "\n",
        "a": [],
    }
    assert dumps(value, serialization="jcs") == (
        '{"a":[],"z":"\\n","\u00e9":1,"\U0001f600":{"a":[1,2.5,null],"b":true},'
        '"\ufb00":"\u00fc"}'
    )


def test_an_unorderable_collection_is_refused() -> None:
    value = {"timelines": [{"id": "t", "regions": [{"id": "r"}] * 2}]}
    with pytest.raises(ValueError, match="cannot put regions in canonical order"):
        dumps(value)
