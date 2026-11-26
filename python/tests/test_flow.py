"""Flow control, FlowMaps and virtual timelines (see "Flow" in tests/README.md)."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

import timetoshare
from timetoshare import (
    ATOMIC_SECTION,
    NAMESPACE,
    canonical_order,
    complete,
    dumps,
    load_schema,
    loads,
    minimal,
    used_prefixes,
    with_bare_ids,
    with_context,
)
from timetoshare.manifest import exact
from timetoshare.validation.flow import (
    CONVENTIONS,
    CONVERTER,
    EARLIER_ROLES,
    MANIFESTATIONS,
    rejected,
)

from .conftest import (
    identity_problems,
    manifest,
    manifest_warnings,
    timeline,
    unknown_keys,
    validate,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPOSITORY_ROOT / "fixtures" / "0.2.0"
FLOWS = REPOSITORY_ROOT / "fixtures" / "flows" / "0.2.0"
EDITOR = "https://example.org/people/editor"
FALSE = {"beliefs": [{"actor": EDITOR, "belief": "false", "date": "2026-11-25"}]}


def jump(identifier: str, at: int, *targets: dict, **members: Any) -> dict:
    return {
        "id": identifier,
        "role": "jump",
        "coordinate": [at, 1],
        "targets": list(targets),
        **members,
    }


def element(identifier: str, role: str, at: int, **members: Any) -> dict:
    return {"id": identifier, "role": role, "coordinate": [at, 1], **members}


def _problems(value: dict) -> list[tuple[str, tuple, str]]:
    return [
        (problem.code, problem.path, problem.message)
        for problem in identity_problems(value)
    ]


# -- the schema -------------------------------------------------------------------


def test_the_five_roles_and_what_each_carries() -> None:
    defs = load_schema()["$defs"]
    flow = defs["FlowControlElement"]
    assert flow["properties"]["role"]["enum"] == [
        "jump",
        "jump_target",
        "break",
        "section_break",
        "barline",
    ]
    assert flow["required"] == ["id", "role", "coordinate"]
    assert list(flow["properties"]) == [
        "id",
        "role",
        "coordinate",
        "targets",
        "manifestation",
        "ends",
        "name",
        "label",
        "meta",
        "provenance",
    ]
    assert not set(EARLIER_ROLES) & set(flow["properties"]["role"]["enum"])
    for key in ("type", "target", "repeat_count"):
        assert key not in flow["properties"]
    assert flow["properties"]["manifestation"]["type"] == "string"
    assert "enum" not in flow["properties"]["manifestation"]
    record = {"$ref": "#/$defs/ProvenanceRecord"}
    for holder in ("FlowControlElement", "FlowMap"):
        provenance = defs[holder]["properties"]["provenance"]
        assert provenance["items"] == record and provenance["minItems"] == 1


def test_a_destination_and_its_conditions() -> None:
    defs = load_schema()["$defs"]
    destination = defs["JumpDestination"]
    assert list(destination["properties"]) == [
        "to",
        "by",
        "passes",
        "repeat_count",
        "after",
        "determined",
        "reset",
        "manifestation",
        "label",
    ]
    assert "required" not in destination
    assert destination["not"] == {"required": ["to", "by"]}
    assert destination["properties"]["repeat_count"] == {
        "type": "integer",
        "minimum": 1,
        "description": destination["properties"]["repeat_count"]["description"],
    }
    listed, since = defs["Passes"]["oneOf"]
    assert listed == {
        "type": "array",
        "items": {"type": "integer", "minimum": 1},
        "minItems": 1,
        "uniqueItems": True,
    }
    assert since["properties"] == {"from": {"type": "integer", "minimum": 1}}
    assert since["required"] == ["from"]
    reference = defs["DestinationReference"]
    assert list(reference["properties"]) == ["jump", "to", "by"]
    assert reference["required"] == ["jump"]
    assert reference["not"] == {"required": ["to", "by"]}
    ends = defs["BreakCondition"]
    assert list(ends["properties"]) == ["passes", "after"]
    assert ends["minProperties"] == 1
    assert ends["anyOf"] == [{"required": ["passes"]}, {"required": ["after"]}]


def test_flow_maps_and_virtual_timelines_are_top_level_lists() -> None:
    defs = load_schema()["$defs"]
    members = defs["Manifest"]["properties"]
    assert members["flow_maps"]["items"] == {"$ref": "#/$defs/FlowMap"}
    assert members["virtual_timelines"]["items"] == {"$ref": "#/$defs/VirtualTimeline"}
    flow_map = defs["FlowMap"]
    assert list(flow_map["properties"]) == [
        "id",
        "timeline",
        "chunks",
        "convention",
        "canonical",
        "name",
        "provenance",
    ]
    assert flow_map["required"] == ["id", "timeline", "chunks"]
    assert flow_map["properties"]["convention"]["type"] == "string"
    assert "enum" not in flow_map["properties"]["convention"]
    assert defs["Gap"]["properties"]["gap"]["$ref"] == "#/$defs/NumberPositive"
    assert defs["Gap"]["required"] == ["gap"]
    virtual = defs["VirtualTimeline"]
    assert list(virtual["properties"]) == [
        "id",
        "map",
        "timeline",
        "unit",
        "number_type",
        "length",
        "through",
        "name",
    ]
    assert virtual["required"] == [
        "id",
        "map",
        "timeline",
        "unit",
        "number_type",
        "length",
    ]
    axis = defs["Timeline"]
    for keyword in ("if", "then", "else"):
        assert virtual[keyword] == axis[keyword], keyword


def test_the_schema_names_every_word_of_the_open_vocabularies() -> None:
    defs = load_schema()["$defs"]
    element_words = defs["FlowControlElement"]["properties"]["manifestation"]
    for role in ("jump_target", "break", "barline"):
        for word in MANIFESTATIONS[role]:
            assert f"`{word}`" in element_words["description"], word
    assert MANIFESTATIONS["section_break"] == ()
    destination = defs["JumpDestination"]["properties"]["manifestation"]
    for word in MANIFESTATIONS["destination"]:
        assert f"`{word}`" in destination["description"], word
    convention = defs["FlowMap"]["properties"]["convention"]["description"]
    assert CONVENTIONS == ("default", "single", "printed")
    for word in CONVENTIONS:
        assert f"`{word}`" in convention, word


def test_the_atomic_section_class_lies_in_the_formats_namespace() -> None:
    assert ATOMIC_SECTION == NAMESPACE + "AtomicSection"
    assert f"`{ATOMIC_SECTION}`" in load_schema()["$defs"]["Region"]["description"]


# -- the earlier form -------------------------------------------------------------


@pytest.mark.parametrize(
    "earlier",
    [
        {"type": "jump_from", "manifestation": "da_capo"},
        {"type": "jump_to", "manifestation": "segno"},
        {"type": "flow_marker", "manifestation": "fine"},
        {"role": "flow_marker", "manifestation": "fine"},
        {"manifestation": "dal_segno", "target": "s"},
        {"role": "jump", "type": "jump_from", "targets": [{}]},
    ],
)
def test_the_earlier_form_is_refused_with_the_converter_named(earlier: dict) -> None:
    child = timeline("c", offset=(0, 1), flow_control=[element("ok", "barline", 1)])
    child["flow_control"].append({"id": "old", "coordinate": [2, 1], **earlier})
    value = manifest(timeline("score", children=[child]))
    with pytest.raises(timetoshare.SchemaValidationError) as caught:
        validate(value)
    assert (caught.value.code, caught.value.path, caught.value.message) == (
        "flow_control_form",
        ("timelines", 0, "children", 0, "flow_control", 1),
        "flow-control element 'old' is written in the earlier form of flow control "
        f"(type, target): convert the manifest with {CONVERTER}",
    )
    assert (REPOSITORY_ROOT / CONVERTER).is_file()


def test_the_earlier_form_is_reported_before_the_schema() -> None:
    value = manifest(timeline("score", "furlongs", flow_control=[{"type": "jump_to"}]))
    with pytest.raises(timetoshare.SchemaValidationError) as caught:
        timetoshare.validate(value)
    assert (caught.value.code, caught.value.message) == (
        "flow_control_form",
        "the flow-control element at #/timelines/0/flow_control/0 is written in the "
        f"earlier form of flow control (type, target): convert the manifest with "
        f"{CONVERTER}",
    )


def test_a_key_named_type_beside_a_role_is_an_unknown_key() -> None:
    value = manifest(
        timeline("score", flow_control=[element("b", "barline", 1, type="thin")])
    )
    validate(value)
    assert unknown_keys(value) == [
        {"path": ["timelines", 0, "flow_control", 0], "key": "type"}
    ]


# -- rejected elements -------------------------------------------------------------


def test_an_element_is_rejected_by_a_belief_false() -> None:
    assert not rejected({})
    assert not rejected({"provenance": [{"method": "imported"}]})
    unlikely = {"beliefs": [{"actor": EDITOR, "belief": "unlikely", "date": "x"}]}
    assert not rejected({"provenance": [unlikely]})
    assert rejected({"provenance": [{"method": "imported"}, FALSE]})


def test_a_rejected_jump_and_its_replacement_share_a_coordinate() -> None:
    flow = [
        element("start", "jump_target", 2),
        jump("old", 8, {"repeat_count": 1}, provenance=[FALSE]),
        jump("new", 8, {"to": "start", "repeat_count": 1}),
    ]
    value = manifest(timeline("score", flow_control=flow))
    assert _problems(value) == []
    del flow[1]["provenance"]
    assert _problems(value) == [
        (
            "jump_repeated",
            ("timelines", 0, "flow_control", 2),
            "'new' is a second jump at coordinate [8, 1] of 'score', after 'old': "
            "several signs at one place are destinations of one jump",
        )
    ]


def test_a_rejected_element_is_neither_checked_nor_named() -> None:
    flow = [
        element("gone", "jump_target", 2, provenance=[FALSE]),
        jump("wild", 99, {"to": "nowhere"}, {"to": "nowhere"}, provenance=[FALSE]),
        jump("j", 4, {"to": "gone"}),
        element("fine", "break", 6, ends={"after": {"jump": "wild"}}),
    ]
    assert _problems(manifest(timeline("score", flow_control=flow))) == [
        (
            "dangling_target",
            ("timelines", 0, "flow_control", 2, "targets", 0, "to"),
            "'gone' names no jump target, region or child of this timeline, nor the "
            "timeline itself",
        ),
        (
            "dangling_target",
            ("timelines", 0, "flow_control", 3, "ends", "after", "jump"),
            "'wild' names no jump of this timeline",
        ),
    ]


# -- coordinates and places ---------------------------------------------------------


def test_a_timeline_of_unknown_length_bounds_its_flow_control_at_zero_only() -> None:
    flow = [jump("far", 1000, {"by": [500, 1]}), jump("back", 4, {"by": [-5, 1]})]
    value = manifest(timeline("score", length=None, flow_control=flow))
    assert _problems(value) == [
        (
            "flow_coordinate",
            ("timelines", 0, "flow_control", 1, "targets", 0, "by"),
            "by [-5, 1] from coordinate [4, 1] of 'back' is not on 'score': it lies "
            "before 0",
        )
    ]


def test_the_ends_of_the_axis_are_on_it() -> None:
    flow = [
        jump("first", 0, {"by": [8, 1]}),
        jump("last", 8, {"by": [-8, 1]}),
    ]
    assert _problems(manifest(timeline("score", flow_control=flow))) == []


def test_a_place_on_a_float_axis_is_the_double_sum() -> None:
    assert 0.1 + 0.2 > 0.3
    assert exact(0.1) + exact(0.2) != Fraction(0.1 + 0.2)
    flow = [
        {"id": "j", "role": "jump", "coordinate": 0.1, "targets": [{"by": 0.2}]},
    ]
    value = manifest(
        timeline("take", "seconds", 0.30000000000000004, flow_control=flow)
    )
    assert _problems(value) == []
    value["timelines"][0]["length"] = 0.3
    assert _problems(value) == [
        (
            "flow_coordinate",
            ("timelines", 0, "flow_control", 0, "targets", 0, "by"),
            "by 0.2 from coordinate 0.1 of 'j' is not on 'take': it lies outside 0 "
            "to the length 0.3",
        )
    ]


def test_a_distance_and_an_element_at_one_coordinate_are_two_places() -> None:
    flow = [
        element("there", "jump_target", 2),
        jump("j", 4, {"to": "there", "passes": [1]}, {"by": [-2, 1], "passes": [2]}),
    ]
    assert _problems(manifest(timeline("score", flow_control=flow))) == []


# -- after ----------------------------------------------------------------------


def _after(reference: dict, *targets: dict) -> list[tuple[str, tuple, str]]:
    flow = [
        element("there", "jump_target", 1),
        jump("leap", 6, *targets),
        element("fine", "break", 4, ends={"after": reference}),
    ]
    return _problems(manifest(timeline("score", flow_control=flow)))


def test_an_after_names_one_destination_by_its_place() -> None:
    there, back, bare = {"to": "there"}, {"by": [-2, 1]}, {"repeat_count": 1}
    assert _after({"jump": "leap"}, there) == []
    assert _after({"jump": "leap"}, there, bare) == []
    assert _after({"jump": "leap", "to": "there"}, there, back, bare) == []
    assert _after({"jump": "leap", "by": [-4, 2]}, there, back, bare) == []
    at = ("timelines", 0, "flow_control", 2, "ends", "after")
    assert _after({"jump": "leap"}, there, back) == [
        (
            "dangling_target",
            at,
            "jump 'leap' has 2 destinations and none without a place; after names "
            "one by its to or by",
        )
    ]
    assert _after({"jump": "leap", "by": [-3, 1]}, there, back) == [
        ("dangling_target", (*at, "by"), "jump 'leap' has no destination by [-3, 1]")
    ]
    assert _after({"jump": "leap", "to": "score"}, there, back) == [
        ("dangling_target", (*at, "to"), "jump 'leap' has no destination to 'score'")
    ]


def test_an_after_stays_within_its_timeline() -> None:
    child = timeline(
        "c", offset=(0, 1), flow_control=[jump("inner", 2, {"repeat_count": 1})]
    )
    root = timeline(
        "score",
        children=[child],
        flow_control=[element("fine", "break", 4, ends={"after": {"jump": "inner"}})],
    )
    assert _problems(manifest(root)) == [
        (
            "dangling_target",
            ("timelines", 0, "flow_control", 0, "ends", "after", "jump"),
            "'inner' names no jump of this timeline",
        )
    ]


# -- FlowMaps and virtual timelines ----------------------------------------------------


def _mapped(**members: Any) -> dict:
    child = timeline("verse", length=(4, 1), offset=(2, 1))
    child["regions"] = [{"id": "line", "start": [0, 1], "end": [1, 1]}]
    score = timeline("score", children=[child])
    score["regions"] = [{"id": "intro", "start": [0, 1], "end": [2, 1]}]
    other = timeline("sketch")
    other["regions"] = [{"id": "idea", "start": [0, 1], "end": [1, 1]}]
    return manifest(score, other, **members)


def _virtual(
    identifier: str, map_id: str, timeline_id: str, length: Any = (2, 1), **more: Any
) -> dict:
    return {
        "id": identifier,
        "map": map_id,
        "timeline": timeline_id,
        "unit": "quarters",
        "number_type": "fraction",
        "length": list(length) if isinstance(length, tuple) else length,
        **more,
    }


def test_a_chunk_is_anything_giving_an_interval_inside_the_roots_tree() -> None:
    flow_maps = [
        {"id": "f", "timeline": "score", "chunks": ["intro", "verse", "line", "v2"]},
        {"id": "g", "timeline": "sketch", "chunks": ["idea", "v3"]},
        {"id": "h", "timeline": "score", "chunks": ["intro"]},
        {"id": "k", "timeline": "sketch", "chunks": ["idea"]},
    ]
    virtual = [
        _virtual("v1", "h", "verse"),
        _virtual("v2", "h", "v1"),
        _virtual("v3", "k", "sketch", (1, 1)),
    ]
    value = _mapped(flow_maps=flow_maps, virtual_timelines=virtual)
    assert _problems(value) == []
    flow_maps[0]["chunks"] = ["v3", "idea", "sketch", "score", "f", "nowhere"]
    message = "'{}' names no region, child timeline or virtual timeline in the tree "
    message += "of 'score'"
    assert _problems(value) == [
        ("flow_map_chunk", ("flow_maps", 0, "chunks", index), message.format(name))
        for index, name in enumerate(flow_maps[0]["chunks"])
    ]


def _from_itself(identifier: str, index: int, *through: str) -> tuple[str, tuple, str]:
    return (
        "virtual_timeline",
        ("virtual_timelines", index, "timeline"),
        f"'{identifier}' comes from itself through "
        + ", ".join(f"'{other}'" for other in through)
        + ": a virtual timeline comes, virtual timeline by virtual timeline, from a "
        "timeline of this manifest",
    )


def test_virtual_timelines_naming_each_other_come_from_no_timeline() -> None:
    flow_maps = [{"id": "f", "timeline": "score", "chunks": ["a"]}]
    virtual = [_virtual("a", "f", "b"), _virtual("b", "f", "a")]
    assert _problems(_mapped(flow_maps=flow_maps, virtual_timelines=virtual)) == [
        (
            "flow_map_chunk",
            ("flow_maps", 0, "chunks", 0),
            "'a' names no region, child timeline or virtual timeline in the tree of "
            "'score'",
        ),
        _from_itself("a", 0, "b"),
        _from_itself("b", 1, "a"),
    ]


def test_a_cycle_is_reported_at_each_of_its_members_and_nowhere_else() -> None:
    """A chain of virtual timelines ends at a timeline.

    Three name each other in a ring; a fourth comes from the ring and a
    fifth from a timeline through a chain. The ring's members are reported,
    each with the others in the order of its chain; the fourth is not (its
    own ``timeline`` names a virtual timeline that exists), and nothing of
    the FlowMap or of the length is read for any of the four.
    """
    flow_maps = [{"id": "f", "timeline": "score", "chunks": ["intro"]}]
    virtual = [
        _virtual("a", "f", "b", (99, 1)),
        _virtual("b", "f", "c"),
        _virtual("c", "f", "a"),
        _virtual("d", "f", "a", (99, 1)),
        _virtual("e", "f", "score"),
        _virtual("g", "f", "e"),
    ]
    assert _problems(_mapped(flow_maps=flow_maps, virtual_timelines=virtual)) == [
        _from_itself("a", 0, "b", "c"),
        _from_itself("b", 1, "c", "a"),
        _from_itself("c", 2, "a", "b"),
    ]
    virtual[2]["timeline"] = "verse"
    for entry in virtual:
        entry["length"] = [2, 1]
    assert _problems(_mapped(flow_maps=flow_maps, virtual_timelines=virtual)) == []


def test_a_flow_map_is_applied_within_the_tree_of_its_own_root() -> None:
    """Without ``through``, a FlowMap is applied inside its own root's tree.

    The FlowMap ``f`` of ``score`` is applied to the root, to its child and
    to a virtual timeline that comes from the child: accepted. Applied to
    the other root ``sketch``, or to a virtual timeline coming from it, it
    is refused at ``map``, and the length (99, no sum of ``f``) is not read
    there. With ``through`` stated nothing of the two is read. A conversion
    map is no FlowMap: the rule does not read it.
    """
    flow_maps = [
        {"id": "f", "timeline": "score", "chunks": ["intro"]},
        {"id": "k", "timeline": "sketch", "chunks": ["idea", "idea"]},
    ]
    within = [
        _virtual("v1", "f", "score"),
        _virtual("v2", "f", "verse"),
        _virtual("v3", "f", "v2"),
        _virtual("v4", "k", "sketch"),
    ]
    assert _problems(_mapped(flow_maps=flow_maps, virtual_timelines=within)) == []
    across = [
        _virtual("v1", "f", "sketch", (99, 1)),
        _virtual("v2", "k", "sketch"),
        _virtual("v3", "f", "v2", (99, 1)),
        _virtual("v4", "k", "verse"),
    ]
    message = (
        "'{}' is a FlowMap of '{}', and '{}' comes from the tree of '{}': without "
        "through, a virtual timeline applies a FlowMap within the tree of the "
        "FlowMap's root timeline"
    )
    assert _problems(_mapped(flow_maps=flow_maps, virtual_timelines=across)) == [
        (
            "virtual_timeline",
            ("virtual_timelines", 0, "map"),
            message.format("f", "score", "sketch", "sketch"),
        ),
        (
            "virtual_timeline",
            ("virtual_timelines", 2, "map"),
            message.format("f", "score", "v2", "sketch"),
        ),
        (
            "virtual_timeline",
            ("virtual_timelines", 3, "map"),
            message.format("k", "sketch", "verse", "score"),
        ),
    ]
    for index in (0, 2, 3):
        across[index]["through"] = "ensemble"
    value = _mapped(flow_maps=flow_maps, virtual_timelines=across)
    value["groups"] = [{"id": "ensemble", "members": ["score", "sketch"]}]
    assert _problems(value) == []
    validate(value)
    linear = {"type": "LinearMap", "id": "tempo"}
    linear |= {"source_unit": "quarters", "target_unit": "seconds"}
    value = _mapped(virtual_timelines=[_virtual("v", "tempo", "sketch", (99, 1))])
    value["timelines"][0]["conversion_maps"] = [linear]
    assert _problems(value) == []


def _not_the_sum(index: int, name: str, length: str, played: str) -> tuple:
    return (
        "virtual_timeline",
        ("virtual_timelines", index, "length"),
        f"length {length} of '{name}' is not the sum of the chunks and gaps of 'f', "
        f"{played}",
    )


def test_the_length_of_a_virtual_timeline_is_the_sum_of_chunks_and_gaps() -> None:
    """The length is the sum of the FlowMap's chunks and gaps, by exact value.

    ``f`` plays the region ``intro`` (2), a gap of 3/2, the child ``verse``
    (4), ``intro`` again and the virtual timeline ``w`` (1/2): 10. The sum
    is the same for every timeline of the tree the FlowMap is applied to,
    and a length is compared by value, however its pair is spelled.
    """
    chunks = ["intro", {"gap": [3, 2]}, "verse", "intro", "w"]
    flow_maps = [
        {"id": "f", "timeline": "score", "chunks": chunks},
        {"id": "h", "timeline": "score", "chunks": [{"gap": [1, 2]}]},
    ]
    virtual = [
        _virtual("v1", "f", "score", (10, 1)),
        _virtual("v2", "f", "verse", (20, 2)),
        _virtual("v3", "f", "v2", (10, 1)),
        _virtual("w", "h", "score", (1, 2)),
    ]
    value = _mapped(flow_maps=flow_maps, virtual_timelines=virtual)
    assert _problems(value) == []
    validate(value)
    virtual[0]["length"] = [19, 2]
    virtual[2]["length"] = [0, 1]
    virtual[3]["length"] = [1, 1]
    assert _problems(value) == [
        _not_the_sum(0, "v1", "[19, 2]", "[21, 2]"),
        _not_the_sum(1, "v2", "[20, 2]", "[21, 2]"),
        _not_the_sum(2, "v3", "[0, 1]", "[21, 2]"),
        (
            "virtual_timeline",
            ("virtual_timelines", 3, "length"),
            "length [1, 1] of 'w' is not the sum of the chunks and gaps of 'h', [1, 2]",
        ),
    ]
    flow_maps[0]["chunks"] = []
    virtual[3]["length"] = [1, 2]
    assert _problems(value) == [
        _not_the_sum(0, "v1", "[19, 2]", "[0, 1]"),
        _not_the_sum(1, "v2", "[20, 2]", "[0, 1]"),
    ]


def test_an_integer_axis_spells_the_sum_as_an_integer() -> None:
    take = timeline("take", "samples", 100)
    take["regions"] = [{"id": "a", "start": 10, "end": 40}]
    flow_maps = [{"id": "f", "timeline": "take", "chunks": ["a", {"gap": 5}, "a"]}]
    virtual = [_virtual("v", "f", "take", 60, unit="samples", number_type="int")]
    value = manifest(take, flow_maps=flow_maps, virtual_timelines=virtual)
    assert _problems(value) == [
        (
            "virtual_timeline",
            ("virtual_timelines", 0, "length"),
            "length 60 of 'v' is not the sum of the chunks and gaps of 'f', 65",
        )
    ]
    virtual[0]["length"] = 65
    validate(value)


def test_a_sum_that_cannot_be_read_on_the_axis_leaves_the_length_as_stated() -> None:
    """The length is compared only where every chunk lies on the virtual axis.

    Not read, each with a length that is no sum: a ``float`` axis (the sum
    of doubles depends on the order of its additions); a virtual timeline
    of another unit or number type than a chunk's axis; a gap on a root of
    another axis; a child of unknown length; a chunk naming nothing (its
    own problem); ``through``.
    """
    take = timeline("take", "seconds", 8.0)
    take["regions"] = [{"id": "a", "start": 0.1, "end": 0.4}]
    beats = timeline("beats", "quarters", 8.0, number_type="float")
    beats["regions"] = [{"id": "b", "start": 0.0, "end": 2.0}]
    open_child = timeline("open", "quarters", None, offset=(0, 1))
    piece = timeline("piece", children=[open_child])
    piece["regions"] = [{"id": "c", "start": [0, 1], "end": [2, 1]}]
    flow_maps = [
        {"id": "f", "timeline": "take", "chunks": ["a", {"gap": 1.5}]},
        {"id": "g", "timeline": "beats", "chunks": ["b"]},
        {"id": "h", "timeline": "piece", "chunks": ["c", "open"]},
        {"id": "i", "timeline": "piece", "chunks": ["c", "v2"]},
        {"id": "j", "timeline": "beats", "chunks": ["v5", {"gap": 1.0}]},
    ]
    virtual = [
        _virtual("v1", "f", "take", 99.0, unit="seconds", number_type="float"),
        _virtual("v2", "g", "beats", (99, 1)),
        _virtual("v3", "h", "piece", (99, 1)),
        _virtual("v4", "i", "piece", (99, 1), unit="seconds"),
        _virtual("v5", "h", "open", (99, 1), through="tempo"),
        _virtual("v6", "j", "beats", (99, 1)),
    ]
    value = manifest(take, beats, piece, flow_maps=flow_maps, virtual_timelines=virtual)
    linear = {"type": "LinearMap", "id": "tempo"}
    linear |= {"source_unit": "quarters", "target_unit": "seconds"}
    value["timelines"][2]["conversion_maps"] = [linear]
    assert _problems(value) == [
        (
            "flow_map_chunk",
            ("flow_maps", 3, "chunks", 1),
            "'v2' names no region, child timeline or virtual timeline in the tree "
            "of 'piece'",
        ),
        (
            "flow_map_chunk",
            ("flow_maps", 4, "chunks", 0),
            "'v5' names no region, child timeline or virtual timeline in the tree "
            "of 'beats'",
        ),
    ]
    flow_maps[3]["chunks"] = ["c"]
    flow_maps[4]["chunks"] = ["v2", {"gap": 1.0}]
    assert _problems(value) == []
    validate(value)


def test_a_virtual_timeline_applies_a_flow_map_or_a_conversion_map() -> None:
    value = _mapped(virtual_timelines=[_virtual("v", "tempo", "score")])
    linear = {"type": "LinearMap", "id": "tempo"}
    linear |= {"source_unit": "quarters", "target_unit": "seconds"}
    held = {"type": "ChainMap", "id": "chain", "maps": [linear]}
    held |= {"source_unit": "quarters", "target_unit": "seconds"}
    value["timelines"][0]["children"][0]["conversion_maps"] = [held]
    assert _problems(value) == []
    value["virtual_timelines"][0]["map"] = "intro"
    assert _problems(value) == [
        (
            "dangling_target",
            ("virtual_timelines", 0, "map"),
            "'intro' names no FlowMap or conversion map of this manifest",
        )
    ]


def test_one_canonical_flow_map_per_timeline() -> None:
    flow_maps = [
        {"id": "a", "timeline": "score", "chunks": [], "canonical": True},
        {"id": "b", "timeline": "sketch", "chunks": [], "canonical": True},
        {"id": "c", "timeline": "score", "chunks": [], "canonical": False},
    ]
    value = _mapped(flow_maps=flow_maps)
    assert _problems(value) == []
    flow_maps[2]["canonical"] = True
    assert _problems(value) == [
        (
            "flow_map_canonical",
            ("flow_maps", 2, "canonical"),
            "'c' is a second canonical FlowMap of 'score', after 'a'",
        )
    ]


def test_the_ids_of_flow_maps_and_virtual_timelines_are_the_manifests() -> None:
    value = _mapped(
        flow_maps=[{"id": "intro", "timeline": "score", "chunks": []}],
        virtual_timelines=[_virtual("score", "intro", "score")],
        id="score",
    )
    assert [(code, path) for code, path, _ in _problems(value)] == [
        ("duplicate_id", ("flow_maps", 0, "id")),
        ("duplicate_id", ("virtual_timelines", 0, "id")),
        ("manifest_id", ("id",)),
        ("dangling_target", ("virtual_timelines", 0, "timeline")),
    ]


# -- order and spelling ------------------------------------------------------------


def test_flow_maps_are_ordered_by_id_and_their_chunks_kept() -> None:
    value = _mapped(
        flow_maps=[
            {
                "id": "z",
                "timeline": "score",
                "chunks": ["verse", {"gap": [4, 2]}, "intro"],
            },
            {"id": "a", "timeline": "sketch", "chunks": ["idea", "idea"]},
        ],
        virtual_timelines=[_virtual("w", "z", "score"), _virtual("v", "a", "sketch")],
    )
    value["virtual_timelines"][0]["length"] = [16.0, 2]
    result = canonical_order(value)
    assert [entry["id"] for entry in result["flow_maps"]] == ["a", "z"]
    assert result["flow_maps"][1]["chunks"] == ["verse", {"gap": [2, 1]}, "intro"]
    assert [entry["id"] for entry in result["virtual_timelines"]] == ["v", "w"]
    assert result["virtual_timelines"][1]["length"] == [8, 1]
    assert complete(value)["flow_maps"][0]["chunks"][1] == {"gap": [2, 1]}


def test_distances_are_respelled_by_the_axis() -> None:
    flow = [
        {"id": "t", "role": "jump_target", "coordinate": 1},
        {
            "id": "j",
            "role": "jump",
            "coordinate": 4,
            "targets": [{"by": -2, "after": {"jump": "k", "by": 1}}],
        },
        {"id": "k", "role": "jump", "coordinate": 2, "targets": [{"by": 1}]},
        {
            "id": "b",
            "role": "break",
            "coordinate": 3,
            "ends": {"after": {"jump": "k", "by": 1}},
        },
    ]
    value = manifest(timeline("take", "seconds", 8.0, flow_control=flow))
    (root,) = complete(value)["timelines"]
    done = {entry["id"]: entry for entry in root["flow_control"]}
    assert done["j"]["targets"][0]["by"] == -2.0
    assert type(done["j"]["targets"][0]["by"]) is float
    assert type(done["j"]["targets"][0]["after"]["by"]) is float
    assert type(done["b"]["ends"]["after"]["by"]) is float
    validate(value)


# -- warnings --------------------------------------------------------------------


def test_every_word_of_the_vocabularies_is_known() -> None:
    flow = []
    for role in ("jump_target", "break", "barline"):
        for word in MANIFESTATIONS[role]:
            flow.append(element(f"{role}-{word}", role, 1, manifestation=word))
    flow.append(element("plain", "section_break", 1))
    flow.append(
        jump(
            "j",
            2,
            *({"to": f"jump_target-{word}"} for word in MANIFESTATIONS["jump_target"]),
        )
    )
    for number, word in enumerate(MANIFESTATIONS["destination"]):
        flow[-1]["targets"].append({"by": [number, 1], "manifestation": word})
    flow_maps = [
        {"id": word, "timeline": "score", "chunks": [], "convention": word}
        for word in CONVENTIONS
    ]
    flow_maps.append({"id": "hand", "timeline": "score", "chunks": []})
    root = timeline("score", length=(16, 1), flow_control=flow)
    value = with_context(manifest(root), {})
    value["flow_maps"] = flow_maps
    validate(value)
    assert manifest_warnings(value) == []


def test_a_word_of_another_role_is_unknown() -> None:
    flow = [
        element("a", "barline", 1, manifestation="fine"),
        element("b", "break", 2, manifestation="segno"),
        element("c", "jump_target", 3, manifestation="repeat_end"),
        jump("d", 4, {"manifestation": "segno"}),
    ]
    value = with_context(manifest(timeline("score", flow_control=flow)), {})
    assert [
        (warning["code"], warning["path"][4:], warning["message"])
        for warning in manifest_warnings(value)
    ] == [
        (
            "manifestation_unknown",
            ["manifestation"],
            "'fine' is no manifestation the format defines for a barline",
        ),
        (
            "manifestation_unknown",
            ["manifestation"],
            "'segno' is no manifestation the format defines for a break",
        ),
        (
            "manifestation_unknown",
            ["manifestation"],
            "'repeat_end' is no manifestation the format defines for a jump target",
        ),
        (
            "manifestation_unknown",
            ["targets", 0, "manifestation"],
            "'segno' is no manifestation the format defines for a destination",
        ),
    ]


def test_warnings_are_sorted_by_path_then_code() -> None:
    child = timeline("c", offset=(0, 1))
    child["flow_control"] = [element("x", "barline", 1, manifestation="thick")]
    root = timeline("score", children=[child])
    root["flow_control"] = [element("y", "barline", 1, manifestation="thin")]
    value = manifest(root)
    value["flow_maps"] = [
        {"id": "f", "timeline": "score", "chunks": [], "convention": "mine"}
    ]
    assert [
        (warning["code"], warning["path"]) for warning in manifest_warnings(value)
    ] == [
        ("context_absent", []),
        ("convention_unknown", ["flow_maps", 0, "convention"]),
        (
            "manifestation_unknown",
            ["timelines", 0, "children", 0, "flow_control", 0, "manifestation"],
        ),
        ("manifestation_unknown", ["timelines", 0, "flow_control", 0, "manifestation"]),
    ]


# -- provenance about an element ------------------------------------------------------


def _with_provenance(entry: dict) -> dict:
    flow = [element("b", "barline", 1, provenance=[{"method": "imported"}, entry])]
    value = with_context(manifest(timeline("score")), {})
    value["timelines"][0]["flow_control"] = flow
    value["flow_maps"] = [
        {"id": "f", "timeline": "score", "chunks": [], "provenance": [entry]}
    ]
    return value


@pytest.mark.parametrize(
    ("entry", "code", "tail", "message"),
    [
        (
            {"date": "2026-02-30"},
            "calendar_date",
            ("date",),
            "'2026-02-30' is no Gregorian calendar date written YYYY-MM-DD",
        ),
        (
            {"stated_by": ["viaf:1"]},
            "iri",
            ("stated_by", 0),
            "'viaf:1': the prefix 'viaf' is not declared in @context",
        ),
        (
            {"basis": ["#ghost"]},
            "dangling_target",
            ("basis", 0),
            "'#ghost' names no element of this manifest",
        ),
        (
            {
                "beliefs": [
                    {"actor": EDITOR, "belief": "true", "date": "2026-11-25"},
                    {"actor": EDITOR, "belief": "unlikely", "date": "2026-11-25"},
                ]
            },
            "belief_actor",
            ("beliefs", 1, "actor"),
            f"'{EDITOR}' already holds belief 0 of this entry; an actor holds one "
            "belief",
        ),
    ],
)
def test_the_provenance_of_an_element_obeys_the_entry_rules(
    entry: dict, code: str, tail: tuple, message: str
) -> None:
    value = _with_provenance(entry)
    found = [
        (problem.code, problem.path, problem.message)
        for problem in timetoshare.statement_problems(timetoshare.with_file_ids(value))
    ]
    element_path = ("timelines", 0, "flow_control", 0, "provenance", 1)
    assert found == [
        (code, (*element_path, *tail), message),
        (code, ("flow_maps", 0, "provenance", 0, *tail), message),
    ]
    with pytest.raises(timetoshare.SchemaValidationError) as caught:
        validate(value)
    assert (caught.value.code, caught.value.path) == (code, (*element_path, *tail))


def test_an_entry_about_an_element_names_no_pair_and_needs_no_context() -> None:
    entry = {"method": "manual", "stated_by": [EDITOR], "basis": ["#score"]}
    value = _with_provenance(entry)
    del value["@context"]
    validate(value)
    assert [warning["code"] for warning in manifest_warnings(value)] == [
        "context_absent"
    ]


def test_the_prefixes_of_element_provenance_are_used_prefixes() -> None:
    value = _with_provenance({"stated_by": ["viaf:1"], "method": "prov:Activity"})
    assert used_prefixes(value) == ["prov", "viaf"]
    namespaces = {"viaf": "http://viaf.org/viaf/", "prov": "http://www.w3.org/ns/prov#"}
    kept = with_context(value, namespaces)
    assert {key: kept["@context"][key] for key in namespaces} == namespaces
    validate(kept)


# -- the flow fixtures and the expected flows -------------------------------------


def _expected_flows() -> list[Path]:
    return sorted(FLOWS.glob("*.yaml"))


def test_the_expected_flows_are_stated() -> None:
    assert [path.stem for path in _expected_flows()] == [
        "da_capo_al_fine",
        "dal_segno_al_coda",
        "loop",
        "ossia",
        "repairs",
        "repeat_end_and_dal_segno",
        "sections",
        "sonata_exposition",
        "volta_passes",
    ]
    for path in _expected_flows():
        assert path.with_suffix(".md").is_file(), path.stem
        assert (FIXTURES / "flow" / f"{path.stem}.yaml").is_file()
    flows = {path.stem for path in _expected_flows()}
    fixtures = {
        path.name.split(".")[0] for path in (FIXTURES / "flow").glob("*.minimal.yaml")
    }
    assert fixtures - flows == {"flow_map_by_hand"}


def _boundaries(root: dict) -> list[Fraction]:
    """The boundaries of a timeline's atomic sections, as the schema states them."""
    read = [entry for entry in root.get("flow_control", []) if not rejected(entry)]
    starts = {root["id"]: Fraction(0)}
    starts |= {
        region["id"]: exact(region["start"]) for region in root.get("regions", [])
    }
    starts |= {
        child["id"]: exact(child["offset"]) for child in root.get("children", [])
    }
    starts |= {
        entry["id"]: exact(entry["coordinate"])
        for entry in read
        if entry["role"] == "jump_target"
    }
    sections = sorted(
        exact(entry["coordinate"]) for entry in read if entry["role"] == "section_break"
    )
    found = {Fraction(0), exact(root["length"])}
    for entry in read:
        at = exact(entry["coordinate"])
        if entry["role"] != "barline":
            found.add(at)
        for destination in entry.get("targets", []):
            if "to" in destination:
                found.add(starts[destination["to"]])
            elif "by" not in destination:
                found.add(max((s for s in sections if s < at), default=Fraction(0)))
            elif exact(destination["by"]) != 0:
                found.add(at + exact(destination["by"]))
    return sorted(found)


@pytest.mark.parametrize("path", _expected_flows(), ids=lambda path: path.stem)
def test_an_expected_flow_agrees_with_its_manifest(path: Path) -> None:
    """An expected flow is consistent with the manifest it names.

    Findings are stated for every convention: ``printed`` finds nothing,
    and a stretch ``single`` never plays that the ``default`` flow plays is
    ``never_played`` with the cause ``single_playback``, the only cause.
    """
    text = path.read_text(encoding="utf-8")
    case = loads(text)
    assert dumps(case) == text
    assert sorted(case) == ["atomic_sections", "conventions", "manifest", "timeline"]
    assert case["manifest"] == f"flow/{path.stem}"
    value = with_bare_ids(
        loads((FIXTURES / f"{case['manifest']}.yaml").read_text("utf-8"))
    )
    (root,) = [root for root in value["timelines"] if root["id"] == case["timeline"]]
    bounds = _boundaries(root)
    sections = case["atomic_sections"]
    assert [
        (exact(section["start"]), exact(section["end"])) for section in sections
    ] == list(zip(bounds, bounds[1:], strict=False))
    assert [section["name"] for section in sections] == [
        chr(ord("A") + index) for index in range(len(sections))
    ]
    spelled = {type(root["length"])}
    conventions = case["conventions"]
    assert sorted(conventions) == ["default", "printed", "single"]
    for flow in conventions.values():
        assert sorted(flow) == ["findings", "runs", "sections"]
    for flow in conventions.values():
        covered = []
        for start, end in flow["runs"]:
            assert {type(start), type(end)} == spelled
            assert Fraction(0) <= exact(start) < exact(end) <= exact(root["length"])
            inside = [
                section["name"]
                for section in sections
                if exact(start) <= exact(section["start"])
                and exact(section["end"]) <= exact(end)
            ]
            assert inside and exact(start) in bounds and exact(end) in bounds
            covered += inside
        assert covered == flow["sections"]
    assert conventions["printed"]["sections"] == [s["name"] for s in sections]
    assert [[run[0], run[1]] for run in conventions["printed"]["runs"]] == [
        [section["start"], section["end"]] for section in sections
    ]
    default = set(conventions["default"]["sections"])
    kinds = {
        "flow_ends_at_break",
        "never_played",
        "endless_loop",
        "ambiguous_targets",
        "undetermined_target",
    }
    assert conventions["printed"]["findings"] == []
    for name in ("default", "single"):
        played = set(conventions[name]["sections"])
        # One finding per stretch that no run covers: adjacent atomic sections
        # that are not played are one stretch, reported at its start. Under
        # ``single`` a stretch is divided where the ``default`` flow begins or
        # ends playing it, and a piece the ``default`` flow plays has the
        # cause ``single_playback``.
        never: list[dict] = []
        piece = None
        for section in sections:
            key = None
            if section["name"] not in played:
                key = name == "single" and section["name"] in default
            if piece is not None and (key is None or key != piece[0]):
                never.append(piece[1])
                piece = None
            if key is not None and piece is None:
                cause = {"cause": "single_playback"} if key else {}
                piece = (key, {"coordinate": section["start"], **cause})
            if piece is not None:
                piece[1]["end"] = section["end"]
        if piece is not None:
            never.append(piece[1])
        findings = conventions[name]["findings"]
        assert {finding["kind"] for finding in findings} <= kinds
        assert [
            {key: value for key, value in finding.items() if key != "kind"}
            for finding in findings
            if finding["kind"] == "never_played"
        ] == never
        for finding in findings:
            assert sorted(finding) in (
                ["coordinate", "kind"],
                ["coordinate", "end", "kind"],
                ["cause", "coordinate", "end", "kind"],
            )
            assert ("end" in finding) == (finding["kind"] == "never_played")
            assert finding.get("cause", "single_playback") == "single_playback"
            assert "cause" not in finding or finding["kind"] == "never_played"
            assert exact(finding["coordinate"]) in bounds


def test_the_sonata_expositions_flow_maps_are_its_expected_flows() -> None:
    case = loads((FLOWS / "sonata_exposition.yaml").read_text("utf-8"))
    value = with_bare_ids(
        loads((FIXTURES / "flow/sonata_exposition.yaml").read_text("utf-8"))
    )
    (root,) = value["timelines"]
    regions = {region["name"]: region for region in root["regions"]}
    assert [
        (region["name"], region["start"], region["end"]) for region in root["regions"]
    ] == [(s["name"], s["start"], s["end"]) for s in case["atomic_sections"]]
    for region in root["regions"]:
        assert region["statements"] == {"type": ["tts:AtomicSection"]}
        assert region["provenance"] == [
            {
                "method": "inferred",
                "property": "rdf:type",
                "value": {"id": "tts:AtomicSection"},
            }
        ]
    assert value["@context"]["tts"] == NAMESPACE
    assert timetoshare.expand_iri(value["@context"], "tts:AtomicSection") == (
        ATOMIC_SECTION
    )
    flow_maps = {flow_map["convention"]: flow_map for flow_map in value["flow_maps"]}
    for convention, flow in case["conventions"].items():
        assert flow_maps[convention]["chunks"] == [
            regions[name]["id"] for name in flow["sections"]
        ], convention
        assert flow_maps[convention]["timeline"] == "score"
        assert flow_maps[convention]["provenance"] == [{"method": "inferred"}]
    (virtual,) = value["virtual_timelines"]
    assert virtual["map"] == flow_maps["default"]["id"]
    played = sum(
        exact(end) - exact(start)
        for start, end in case["conventions"]["default"]["runs"]
    )
    assert exact(virtual["length"]) == played == 36
    assert (virtual["unit"], virtual["number_type"]) == ("quarters", "fraction")


def test_the_flow_fixtures_cover_what_their_names_say() -> None:
    def read(name: str) -> dict:
        return with_bare_ids(
            loads((FIXTURES / "flow" / f"{name}.minimal.yaml").read_text("utf-8"))
        )

    def flow(name: str) -> dict[str, dict]:
        (root,) = read(name)["timelines"]
        return {entry["id"]: entry for entry in root["flow_control"]}

    both = flow("repeat_end_and_dal_segno")["jump_1"]["targets"]
    assert [entry["manifestation"] for entry in both] == ["repeat_end", "dal_segno"]
    assert [entry.get("reset") for entry in both] == [None, False]
    volta = flow("volta_passes")
    assert [entry["passes"] for entry in volta["jump_1"]["targets"]] == [[1, 3], [2]]
    assert volta["jump_2"]["targets"] == [
        {"manifestation": "repeat_end", "repeat_count": 1}
    ]
    assert volta["jump_3"]["targets"] == [
        {"manifestation": "repeat_end", "repeat_count": 1, "reset": False}
    ]
    assert [
        (identifier, entry["coordinate"], entry.get("ends"))
        for identifier, entry in sorted(volta.items())
        if entry["role"] == "break"
    ] == [
        ("break_1", [12, 1], None),
        ("break_2", [12, 1], {"after": {"jump": "jump_3"}}),
    ]
    assert read("volta_passes")["timelines"][0]["length"] == [16, 1]
    ossia = flow("ossia")["jump_1"]["targets"]
    assert ossia == [
        {"by": [0, 1]},
        {"determined": False, "manifestation": "ossia", "to": "ossia"},
    ]
    assert [child["id"] for child in read("ossia")["timelines"][0]["children"]] == [
        "ossia"
    ]
    coda = flow("dal_segno_al_coda")["jump_1"]["targets"]
    assert coda[0]["after"] == {"jump": "jump_2"}
    fine = flow("da_capo_al_fine")["break_1"]
    assert (fine["manifestation"], fine["ends"]) == (
        "fine",
        {"after": {"jump": "jump_1"}},
    )
    sections = flow("sections")
    assert sections["section_break_1"] == {
        "coordinate": [16, 1],
        "id": "section_break_1",
        "role": "section_break",
    }
    assert "to" not in sections["jump_2"]["targets"][0]
    loop = read("loop")["timelines"][0]
    assert (loop["unit"], loop["length"]) == ("seconds", 10.0)
    assert loop["flow_control"][1]["targets"] == [
        {"repeat_count": 127, "to": "jump_target_1"}
    ]
    assert all("manifestation" not in entry for entry in loop["flow_control"])
    hand = read("flow_map_by_hand")
    assert hand["timelines"][0].get("flow_control") is None
    (flow_map,) = hand["flow_maps"]
    assert flow_map["chunks"] == ["second", {"gap": [4, 1]}, "first"]
    assert "convention" not in flow_map
    assert flow_map["provenance"][0]["method"] == "manual"
    computed = read("sonata_exposition")
    assert [
        (entry["convention"], entry["provenance"]) for entry in computed["flow_maps"]
    ] == [
        (convention, [{"method": "inferred"}])
        for convention in ("default", "single", "printed")
    ]
    assert [
        [(entry["method"], entry["property"]) for entry in region["provenance"]]
        for region in computed["timelines"][0]["regions"]
    ] == [[("inferred", "rdf:type")]] * 3
    repairs = flow("repairs")
    assert [
        (identifier, entry["provenance"][0]["method"], rejected(entry))
        for identifier, entry in sorted(repairs.items())
    ] == [
        ("barline_1", "imported", False),
        ("jump_1", "imported", True),
        ("jump_2", "manual", False),
        ("jump_target_1", "manual", False),
    ]
    assert repairs["jump_1"]["coordinate"] == repairs["jump_2"]["coordinate"]
    assert minimal(read("repairs")) == read("repairs")


# -- the property flow -----------------------------------------------------------


def _card(identifier: str) -> dict:
    return {"id": identifier, "part": ["card"]}


def _switched(rules: list[dict], **graphical: Any) -> dict:
    """``_mapped``'s roots with the FlowMaps ``f`` (of ``score``) and ``g`` (of
    ``sketch``), the conversion map ``tempo`` of ``score``, the virtual
    timelines ``v`` (``f`` applied to ``score``), ``w`` (``f`` applied to
    ``verse``), ``x`` (``f`` applied to ``score`` through ``grp``) and ``y``
    (``tempo`` applied to ``score``), and ``rules``."""
    flow_maps = [
        {"id": "f", "timeline": "score", "chunks": ["intro", "intro"]},
        {"id": "g", "timeline": "sketch", "chunks": ["idea"]},
    ]
    virtual = [
        _virtual("v", "f", "score", (4, 1)),
        _virtual("w", "f", "verse", (4, 1)),
        _virtual("x", "f", "score", (4, 1), through="grp"),
        _virtual("y", "tempo", "score", 4.0, unit="seconds", number_type="float"),
    ]
    value = _mapped(
        flow_maps=flow_maps,
        virtual_timelines=virtual,
        groups=[{"id": "grp", "members": ["score", "sketch"]}],
        graphical={"rules": rules, **graphical},
    )
    linear = {"type": "LinearMap", "id": "tempo"}
    value["timelines"][0]["conversion_maps"] = [
        linear | {"source_unit": "quarters", "target_unit": "seconds"}
    ]
    return value


def test_a_card_is_switched_to_a_flowmap_of_its_timeline() -> None:
    rules = [
        {"select": {"addresses": [_card("score")]}, "set": {"flow": "f"}},
        {
            "select": {"addresses": [_card("score")]},
            "set": {"flow": "v", "stroke": "#000000"},
        },
        {"select": {"addresses": [_card("sketch")]}, "set": {"stroke": "#000000"}},
    ]
    value = _switched(rules)
    assert _problems(value) == []
    validate(value)


def test_a_flow_naming_anything_else_is_refused() -> None:
    def rule(flow: str, *cards: str, **select: Any) -> dict:
        addresses = [_card(card) for card in cards] or [_card("score")]
        return {"select": select or {"addresses": addresses}, "set": {"flow": flow}}

    rules = [
        rule("intro"),
        rule("score"),
        rule("nowhere"),
        rule("f", "sketch"),
        rule("w"),
        rule("x"),
        rule("y"),
        rule("f", element="card"),
        rule("f", addresses=[_card("score")], within="score"),
        rule("f", addresses=[{"id": "score"}]),
        rule("f", addresses=[{"id": "score", "facet": "regions"}]),
        rule("f", addresses=[{"id": "score", "part": ["name"]}]),
        rule("f", "score", "sketch"),
        {"select": {"addresses": [_card("score")]}, "set": "switched"},
    ]
    styles = {"plain": {"stroke": "#000000"}, "switched": {"flow": "f"}}
    select = (
        "a rule setting flow selects the cards of timelines by their addresses alone, "
    )
    select += "each {id, part: [card]}"

    def at(index: int, *rest: str) -> tuple:
        return ("graphical", "rules", index, *rest)

    unknown = "'{}' names no FlowMap or virtual timeline of this manifest"
    applies = "'{}' does not apply a FlowMap of 'score' to 'score' without through"
    assert _problems(_switched(rules, styles=styles)) == [
        (
            "flow_rule",
            ("graphical", "styles", "switched", "flow"),
            "style 'switched' sets flow; only a rule addressed to the cards of a "
            "timeline sets it",
        ),
        ("flow_rule", at(0, "set", "flow"), unknown.format("intro")),
        ("flow_rule", at(1, "set", "flow"), unknown.format("score")),
        ("flow_rule", at(2, "set", "flow"), unknown.format("nowhere")),
        (
            "flow_rule",
            at(3, "set", "flow"),
            "'f' is a FlowMap of 'score', not of 'sketch'",
        ),
        ("flow_rule", at(4, "set", "flow"), applies.format("w")),
        ("flow_rule", at(5, "set", "flow"), applies.format("x")),
        ("flow_rule", at(6, "set", "flow"), applies.format("y")),
        ("flow_rule", at(7, "select"), select),
        ("flow_rule", at(8, "select"), select),
        ("flow_rule", at(9, "select"), select),
        ("flow_rule", at(10, "select"), select),
        ("flow_rule", at(11, "select"), select),
        (
            "flow_rule",
            at(12, "set", "flow"),
            "'f' is a FlowMap of 'score', not of 'sketch'",
        ),
    ]


def test_members_of_one_group_each_switched_are_warned_of() -> None:
    def warnings(*rules: dict, groups: list[dict]) -> list[tuple]:
        value = _switched(list(rules))
        value["groups"] = groups
        return [
            (warning["code"], warning["path"], warning["message"])
            for warning in manifest_warnings(value)
            if warning["code"] == "flow_conflict"
        ]

    score_f = {"select": {"addresses": [_card("score")]}, "set": {"flow": "f"}}
    score_v = {"select": {"addresses": [_card("score")]}, "set": {"flow": "v"}}
    sketch_g = {"select": {"addresses": [_card("sketch")]}, "set": {"flow": "g"}}
    one = [{"id": "grp", "members": ["score", "sketch"]}]
    two = [{"id": "g1", "members": ["score"]}, {"id": "g2", "members": ["sketch"]}]
    assert warnings(score_f, groups=one) == []
    assert warnings(score_f, sketch_g, groups=two) == []
    assert warnings(score_f, score_v, sketch_g, groups=one) == [
        (
            "flow_conflict",
            ["groups", 0, "members"],
            "members 'score' and 'sketch' of 'grp' state the flows 'v' and 'g': "
            "the frame is drawn as written",
        )
    ]
