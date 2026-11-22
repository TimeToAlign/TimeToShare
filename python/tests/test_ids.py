"""IDs between the file form ``#id`` and the bare form; see README "IDs in a file"."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

import timetoshare
from timetoshare import (
    SchemaValidationError,
    fixture_paths,
    from_file_id,
    load_schema,
    loads,
    to_file_id,
    with_bare_ids,
    with_file_ids,
)
from timetoshare.ids import (
    CONTAINERS,
    ID_POSITIONS,
    MEASURE_VIEWS,
    FileIdError,
    definitions_of,
)


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
                        "statements": {"dcterms:source": [{"id": "#verse"}]},
                        "provenance": [
                            {
                                "property": "dcterms:source",
                                "value": {"id": "#verse"},
                                "basis": ["#intro", "other.yaml#score"],
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
        "@context": {"id": "@id", "dcterms": "http://purl.org/dc/terms/"},
        "statements": {"dcterms:hasPart": [{"id": "#score"}]},
        "graphical": {
            "order": {"score": ["line", "children"], "g": ["score"]},
            "rules": [
                {
                    "select": {
                        "addresses": [{"id": "verse", "part": ["name"]}],
                        "within": "score",
                    },
                    "set": {"stroke": "red"},
                }
            ],
            "timestamps": [{"id": "timestamp_1", "timeline": "verse", "coordinate": 1}],
            "elisions": [
                {"id": "elision_1", "timeline": "verse", "start": 0, "end": 1}
            ],
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
    score["flow_control"][0]["id"] = "#jump_to_1"
    score["flow_control"][1]["id"] = "#jump_from_1"
    score["flow_control"][1]["target"] = "#jump_to_1"
    value["groups"][0] = {"id": "#g", "members": ["#score"]}
    value["measure_maps"][0]["id"] = "#mm"
    graphical = value["graphical"]
    graphical["order"] = {"#score": ["line", "children"], "#g": ["#score"]}
    graphical["rules"][0]["select"] = {
        "addresses": [{"id": "#verse", "part": ["name"]}],
        "within": "#score",
    }
    graphical["timestamps"][0]["id"] = "#timestamp_1"
    graphical["timestamps"][0]["timeline"] = "#verse"
    graphical["elisions"][0]["id"] = "#elision_1"
    graphical["elisions"][0]["timeline"] = "#verse"
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
    ],
)
def test_a_bare_id_in_a_file_is_refused_where_it_stands(change, path, message) -> None:
    value = every_position_in_file_form()
    change(value)
    with pytest.raises(FileIdError) as raised:
        with_bare_ids(value)
    assert raised.value.path == path
    assert str(raised.value) == message


def test_band_words_and_the_iris_of_statements_stay_as_written() -> None:
    value = with_bare_ids(every_position_in_file_form())
    assert value["graphical"]["order"]["score"] == ["line", "children"]
    region = value["timelines"][0]["regions"][0]
    assert region["statements"] == {"dcterms:source": [{"id": "#verse"}]}
    assert region["provenance"][0]["basis"] == ["#intro", "other.yaml#score"]
    assert value["statements"] == {"dcterms:hasPart": [{"id": "#score"}]}
    assert with_file_ids(every_position())["statements"] == value["statements"]


# -- the tables against the schema ------------------------------------------------

ID = "#/$defs/Id"
HOW = {"id": "value", "ids": "items", "order": "propertyNames"}


def _schema_id_positions(defs: dict[str, Any]) -> Iterator[tuple[str, str, str]]:
    """Where the schema types a value as ``$defs/Id``, and how."""
    for definition, node in defs.items():
        for member, declared in node.get("properties", {}).items():
            if declared.get("$ref") == ID:
                yield definition, member, "value"
            if declared.get("items", {}).get("$ref") == ID:
                yield definition, member, "items"
            if declared.get("propertyNames", {}).get("$ref") == ID:
                yield definition, member, "propertyNames"


def _name(reference: str) -> str:
    return reference.removeprefix("#/$defs/")


def _held(declared: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """The definitions a member refers to, and how it holds them."""
    if "$ref" in declared:
        yield "one", _name(declared["$ref"])
    if "$ref" in declared.get("items", {}):
        yield "list", _name(declared["items"]["$ref"])
    if "$ref" in declared.get("additionalProperties", {}):
        yield "values", _name(declared["additionalProperties"]["$ref"])


def _reaching(defs: dict[str, Any]) -> set[str]:
    """The definitions that hold an ID position or hold one that does."""
    reaching = {definition for definition, _, _ in _schema_id_positions(defs)}
    changed = True
    while changed:
        changed = False
        for definition, node in defs.items():
            if definition in reaching:
                continue
            refers = {_name(entry["$ref"]) for entry in node.get("allOf", ())}
            refers |= {
                _name(entry["$ref"])
                for entry in node.get("oneOf", ())
                if "$ref" in entry
            }
            for declared in node.get("properties", {}).values():
                refers |= {child for _, child in _held(declared)}
            if refers & reaching:
                reaching.add(definition)
                changed = True
    return reaching


def test_the_id_positions_are_the_schemas() -> None:
    defs = load_schema()["$defs"]
    table = {
        (definition, member, HOW[shape]) for definition, member, shape in ID_POSITIONS
    }
    assert table == set(_schema_id_positions(defs))
    assert len(table) == len(ID_POSITIONS)


def test_the_containers_are_the_schemas() -> None:
    defs = load_schema()["$defs"]
    reaching = _reaching(defs) - {"Id"}
    expected = {
        (definition, member, holding, child)
        for definition, node in defs.items()
        for member, declared in node.get("properties", {}).items()
        for holding, child in _held(declared)
        if child in reaching
    }
    assert set(CONTAINERS) == expected
    assert len(CONTAINERS) == len(expected)


def test_a_conversion_map_carries_its_types_definitions() -> None:
    defs = load_schema()["$defs"]
    views = {
        name
        for name, node in defs.items()
        if node.get("allOf") == [{"$ref": "#/$defs/MeasureView"}]
    }
    assert set(MEASURE_VIEWS) == views
    for branch in defs["ConversionMap"]["oneOf"]:
        name = _name(branch["$ref"])
        bases = [_name(entry["$ref"]) for entry in defs[name]["allOf"]]
        while bases[-1] != "MapBase":
            bases += [_name(entry["$ref"]) for entry in defs[bases[-1]]["allOf"]]
        assert definitions_of("ConversionMap", {"type": name}) == (name, *bases)


@pytest.mark.parametrize("path", fixture_paths(), ids=lambda path: path.name)
def test_every_fixture_round_trips(path) -> None:
    value = loads(path.read_text(encoding="utf-8"))
    assert with_file_ids(with_bare_ids(value)) == value


# -- the validators read the file form ----------------------------------------------


def _small(order_value: str) -> dict:
    return {
        "@context": {
            **timetoshare.FORMAT_CONTEXT,
            "dcterms": "http://purl.org/dc/terms/",
        },
        "timetoshare": "0.2.0",
        "id": "#bundle",
        "timelines": [{"id": "#score", "unit": "quarters", "length": [8, 1]}],
        "groups": [{"id": "#g", "members": ["#score"]}],
        "statements": {"dcterms:hasPart": [{"id": "#score"}]},
        "graphical": {
            "order": {
                "#g": [order_value],
                "#score": [
                    "line",
                    "markers",
                    "conversion_maps",
                    "children",
                    "regions",
                    "flow_control",
                ],
            }
        },
    }


def test_a_file_form_manifest_validates() -> None:
    timetoshare.validate(_small("#score"))


def test_an_id_the_schema_cannot_type_is_refused_where_it_stands() -> None:
    with pytest.raises(SchemaValidationError) as raised:
        timetoshare.validate(_small("score"))
    assert (raised.value.code, raised.value.path, raised.value.message) == (
        "schema",
        ("graphical", "order", "#g", 0),
        "'score' is not written as an ID: it does not start with '#'",
    )


def test_the_statement_check_reads_ids_outside_it_as_they_stand() -> None:
    assert timetoshare.statement_problems(_small("score")) == []
    value = _small("#score")
    value["timelines"][0]["id"] = "score"
    assert timetoshare.statement_problems(value) == []
    value["statements"] = {"dcterms:hasPart": [{"id": "#ghost"}]}
    assert [
        (problem.code, problem.path, problem.message)
        for problem in timetoshare.statement_problems(value)
    ] == [
        (
            "dangling_target",
            ("statements", "dcterms:hasPart", 0, "id"),
            "'#ghost' names no element of this manifest",
        )
    ]


@pytest.mark.parametrize(
    ("written", "message"),
    [
        ("s", "'s' does not match '^#[\\\\s\\\\S]'"),
        ("score", "'score' does not match '^#[\\\\s\\\\S]'"),
        ("#", "'#' does not match '^#[\\\\s\\\\S]'"),
    ],
)
def test_a_bare_id_of_any_length_is_refused_by_the_hash_rule(
    written: str, message: str
) -> None:
    value = _small("#score")
    value["timelines"][0]["id"] = written
    with pytest.raises(SchemaValidationError) as raised:
        timetoshare.validate(value)
    assert (raised.value.code, raised.value.path, raised.value.message) == (
        "schema",
        ("timelines", 0, "id"),
        message,
    )


def test_any_character_after_the_hash_writes_an_id() -> None:
    value = _small("#score")
    value["timelines"][0]["id"] = "# "
    value["statements"] = {"dcterms:hasPart": [{"id": "#g"}]}
    value["groups"][0]["members"] = ["# "]
    value["graphical"]["order"] = {
        "#g": ["# "],
        "# ": [
            "line",
            "markers",
            "conversion_maps",
            "children",
            "regions",
            "flow_control",
        ],
    }
    timetoshare.validate(value)


def test_matchstamps_and_resources_hold_ids_but_claims_do_not() -> None:
    graphical = {
        "timestamps": [
            {"id": "#ts_a", "timeline": "#score", "coordinate": 0, "matchstamp": True},
        ],
        "matchstamps": [
            {
                "id": "#matchstamp_1",
                "name": "M",
                "alignment_anchors": [
                    {"id": "#anchor_1", "timestamps": ["#ts_a", "#ts_b"]},
                ],
                "match_claims": ["claim_1", "#claim_2"],
            }
        ],
    }
    resources = [
        {
            "id": "#resource_1",
            "type": "MatchClaim",
            "timelines": ["#score", "#perf"],
            "url": "#fragment.parquet",
        }
    ]
    value = {"timetoshare": "0.2.0", "timelines": [], "graphical": graphical}
    value["resources"] = resources
    bare = with_bare_ids(value)
    assert bare["graphical"]["matchstamps"] == [
        {
            "id": "matchstamp_1",
            "name": "M",
            "alignment_anchors": [{"id": "anchor_1", "timestamps": ["ts_a", "ts_b"]}],
            "match_claims": ["claim_1", "#claim_2"],
        }
    ]
    assert bare["resources"] == [
        {
            "id": "resource_1",
            "type": "MatchClaim",
            "timelines": ["score", "perf"],
            "url": "#fragment.parquet",
        }
    ]
    assert with_file_ids(bare) == value
