"""IDs between the file form ``#id`` and the bare form; see README "IDs in a file"."""

from __future__ import annotations

import pytest

from timetoshare import (
    from_file_id,
    to_file_id,
    with_bare_ids,
    with_file_ids,
)
from timetoshare.ids import FileIdError


def every_position() -> dict:
    """A bare manifest naming an ID at every position of the table, once each."""
    return {
        "timetoshare": "0.2.0",
        "id": "op35",
        "timelines": [
            {
                "id": "score",
                "unit": "quarters",
                "length": [8, 1],
                "extra": "score",
                "children": [{"id": "verse", "unit": "quarters", "length": 2.0}],
                "conversion_maps": [
                    {
                        "type": "ChainMap",
                        "id": "chain",
                        "maps": [
                            {"type": "LinearMap", "id": "inner", "scalar": 2.0},
                            {
                                "type": "MeasureRecordMap",
                                "id": "view",
                                "measure_map": "mm",
                            },
                        ],
                    },
                    {
                        "type": "CombinationMap",
                        "id": "combined",
                        "maps": {"out": {"type": "ConstantMap", "id": "constant"}},
                    },
                ],
                "regions": [
                    {
                        "id": "intro",
                        "links": [
                            {
                                "parts": [
                                    {
                                        "represented_by": ["verse", "intro"],
                                        "identifiers": [
                                            {"scheme": "opus", "value": "1"}
                                        ],
                                    }
                                ],
                                "part_of": [
                                    {"identifiers": [{"scheme": "opus", "value": "2"}]}
                                ],
                            }
                        ],
                    }
                ],
                "flow_control": [
                    {"id": "jump_to_1", "type": "jump_to"},
                    {"id": "jump_from_1", "type": "jump_from", "target": "jump_to_1"},
                ],
            }
        ],
        "groups": [{"id": "g", "members": ["score"]}],
        "measure_maps": [{"id": "mm", "rows": []}],
        "schemes": [{"id": "opus"}],
        "links": [
            {
                "identifiers": [
                    {"scheme": "opus", "value": "3"},
                    {"scheme": "http://www.wikidata.org/entity/P839", "value": "4"},
                ]
            }
        ],
        "graphical": {
            "order": {"score": ["line", "children"], "g": ["score"]},
            "statements": [
                {
                    "select": {
                        "addresses": [{"id": "verse", "part": ["name"]}],
                        "within": "score",
                    },
                    "set": {"stroke": "red"},
                }
            ],
            "timestamps": [{"id": "timestamp_1", "timeline": "verse", "coordinate": 1}],
        },
        "meta": {"id": "untouched"},
    }


def every_position_in_file_form() -> dict:
    value = every_position()
    score = value["timelines"][0]
    value["id"] = "#op35"
    score["id"] = "#score"
    score["children"][0]["id"] = "#verse"
    chain, combined = score["conversion_maps"]
    chain["id"] = "#chain"
    chain["maps"][0]["id"] = "#inner"
    chain["maps"][1]["id"] = "#view"
    chain["maps"][1]["measure_map"] = "#mm"
    combined["id"] = "#combined"
    combined["maps"]["out"]["id"] = "#constant"
    region = score["regions"][0]
    region["id"] = "#intro"
    region["links"][0]["parts"][0]["represented_by"] = ["#verse", "#intro"]
    region["links"][0]["parts"][0]["identifiers"][0]["scheme"] = "#opus"
    region["links"][0]["part_of"][0]["identifiers"][0]["scheme"] = "#opus"
    score["flow_control"][0]["id"] = "#jump_to_1"
    score["flow_control"][1]["id"] = "#jump_from_1"
    score["flow_control"][1]["target"] = "#jump_to_1"
    value["groups"][0] = {"id": "#g", "members": ["#score"]}
    value["measure_maps"][0]["id"] = "#mm"
    value["schemes"][0]["id"] = "#opus"
    value["links"][0]["identifiers"][0]["scheme"] = "#opus"
    graphical = value["graphical"]
    graphical["order"] = {"#score": ["line", "children"], "#g": ["#score"]}
    graphical["statements"][0]["select"] = {
        "addresses": [{"id": "#verse", "part": ["name"]}],
        "within": "#score",
    }
    graphical["timestamps"][0]["id"] = "#timestamp_1"
    graphical["timestamps"][0]["timeline"] = "#verse"
    return value


def test_a_bare_id_gains_one_hash() -> None:
    assert to_file_id("clt_1") == "#clt_1"
    assert to_file_id("#x") == "##x"


def test_exactly_one_hash_is_stripped() -> None:
    assert from_file_id("#clt_1") == "clt_1"
    assert from_file_id("##x") == "#x"
    assert from_file_id("# x") == " x"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("clt_1", "'clt_1' is not written as an ID: it does not start with '#'"),
        ("", "'' is not written as an ID: it does not start with '#'"),
        ("#", "'#' is not written as an ID: nothing follows the '#'"),
    ],
)
def test_a_text_without_hash_or_id_is_refused(text: str, message: str) -> None:
    with pytest.raises(ValueError) as raised:
        from_file_id(text)
    assert str(raised.value) == message
    assert isinstance(raised.value, FileIdError)
    assert raised.value.path == ()


def test_every_position_is_converted_and_nothing_else() -> None:
    assert with_file_ids(every_position()) == every_position_in_file_form()
    assert with_bare_ids(every_position_in_file_form()) == every_position()


def test_conversion_keeps_key_order_and_numbers() -> None:
    converted = with_file_ids(every_position())
    assert list(converted) == list(every_position())
    assert list(converted["graphical"]["order"]) == ["#score", "#g"]
    assert list(with_bare_ids(converted)["graphical"]["order"]) == ["score", "g"]
    verse = converted["timelines"][0]["children"][0]
    assert type(verse["length"]) is float
    timestamp = converted["graphical"]["timestamps"][0]
    assert type(timestamp["coordinate"]) is int


def test_conversion_is_pure() -> None:
    original = every_position()
    converted = with_file_ids(original)
    converted["timelines"][0]["length"].append(0)
    converted["meta"]["id"] = "changed"
    assert original == every_position()
    file_form = every_position_in_file_form()
    with_bare_ids(file_form)
    assert file_form == every_position_in_file_form()


@pytest.mark.parametrize(
    ("change", "path", "message"),
    [
        (
            lambda m: m["timelines"][0].update(id="score"),
            ("timelines", 0, "id"),
            "'score' is not written as an ID: it does not start with '#'",
        ),
        (
            lambda m: m["groups"][0]["members"].__setitem__(0, "score"),
            ("groups", 0, "members", 0),
            "'score' is not written as an ID: it does not start with '#'",
        ),
        (
            lambda m: m["graphical"]["order"].__setitem__("#g", ["score"]),
            ("graphical", "order", "#g", 0),
            "'score' is not written as an ID: it does not start with '#'",
        ),
        (
            lambda m: m["graphical"]["timestamps"][0].update(timeline="#"),
            ("graphical", "timestamps", 0, "timeline"),
            "'#' is not written as an ID: nothing follows the '#'",
        ),
        (
            lambda m: m["links"][0]["identifiers"][0].update(scheme="opus"),
            ("links", 0, "identifiers", 0, "scheme"),
            "'opus' names a scheme of this manifest, so it is written '#opus'",
        ),
    ],
)
def test_a_bare_id_in_a_file_is_refused_where_it_stands(change, path, message) -> None:
    value = every_position_in_file_form()
    change(value)
    with pytest.raises(FileIdError) as raised:
        with_bare_ids(value)
    assert raised.value.path == path
    assert str(raised.value) == message


def test_band_words_and_uris_stay_as_written() -> None:
    value = with_bare_ids(every_position_in_file_form())
    assert value["graphical"]["order"]["score"] == ["line", "children"]
    scheme = value["links"][0]["identifiers"][1]["scheme"]
    assert scheme == "http://www.wikidata.org/entity/P839"
