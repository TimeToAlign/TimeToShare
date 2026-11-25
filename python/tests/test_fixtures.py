from __future__ import annotations

import copy
import re
from collections import Counter
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

import timetoshare
from timetoshare import (
    complete,
    dumps,
    fixture_paths,
    identity_problems,
    loads,
    manifest_warnings,
    matchstamp_problems,
    minimal,
    rejection_paths,
    serialization_of,
    unknown_keys,
    validate,
    warning_paths,
    with_bare_ids,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPOSITORY_ROOT / "fixtures" / "0.2.0"


def _load(path: Path) -> dict:
    return loads(path.read_text(encoding="utf-8"))


def _read(path: Path) -> dict:
    """A fixture with its IDs bare, as the assertions below spell them."""
    return with_bare_ids(_load(path))


def test_fixture_paths_list_every_manifest_but_the_drawings() -> None:
    expected = sorted(
        path
        for path in FIXTURES.rglob("*.yaml")
        if "drawings" not in path.relative_to(FIXTURES).parts
    )
    assert fixture_paths() == expected
    assert expected


CASE_ACCESSORS = [
    "fixture_paths",
    "rejection_paths",
    "rejection_case",
    "RejectionCase",
    "warning_paths",
]


@pytest.mark.parametrize("name", CASE_ACCESSORS)
def test_a_case_accessor_lives_in_the_fixtures_module(name: str) -> None:
    fixtures = import_module("timetoshare.fixtures")
    assert getattr(timetoshare, name) is getattr(fixtures, name)
    assert name in timetoshare.__all__
    assert not hasattr(import_module("timetoshare.validate"), name)


@pytest.mark.parametrize(
    "path", fixture_paths(), ids=lambda path: str(path.relative_to(FIXTURES))
)
def test_every_fixture_is_a_manifest_without_unknown_keys(path: Path) -> None:
    value = _load(path)
    validate(value)
    assert unknown_keys(value) == []
    assert manifest_warnings(value) == []
    assert dumps(minimal(complete(value))) == dumps(minimal(value))
    assert dumps(complete(minimal(value))) == dumps(complete(value))


@pytest.mark.parametrize(
    "path",
    [*fixture_paths(), *rejection_paths(), *warning_paths()],
    ids=lambda path: f"{path.parent.name}/{path.name}",
)
def test_every_case_is_written_in_canonical_yaml(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert path.suffix == ".yaml"
    assert serialization_of(text) == "yaml"
    assert dumps(loads(text)) == text


def test_non_ascii_text_is_written_unescaped() -> None:
    text = (FIXTURES / "bundles" / "bundle_elided_layerit.yaml").read_text(
        encoding="utf-8"
    )
    assert 'name: "Prelude mm. 1–4"' in text
    assert "\\u2013" not in text


_GREY = {"stroke": "#404040", "fill": "#404040"}
_SHARED = [
    {"select": {"element": "label"}, "set": _GREY},
    {"select": {"element": "name"}, "set": _GREY},
]
_STYLED_SCORE = {
    "styles": {
        "accent": {
            "stroke": "#1D4ED8",
            "fill": "#1D4ED8",
            "stroke-width": 4,
            "opacity": 0.8,
        }
    },
    "rules": [
        *_SHARED,
        {"select": {"addresses": [{"id": "a"}]}, "set": {"display": "none"}},
        {"select": {"element": "block"}, "set": {"rx": 4}},
        {
            "select": {"class": "ContinuousLogicalTimeline", "element": "timeline"},
            "set": "accent",
        },
        {
            "select": {"class": "LinearMap"},
            "set": {"stroke": "#7C3AED", "stroke-width": 1.5},
        },
        {
            "select": {"element": "map", "modality": "discrete"},
            "set": {"stroke-dasharray": "4 2"},
        },
        {"select": {"element": "region"}, "set": {"stroke": "#800000"}},
        {"select": {"element": "region"}, "set": {"stroke": "#0F766E"}},
        {
            "select": {"element": "jump", "domain": "logical"},
            "set": {"stroke": "#DB2777", "fill": "#DB2777", "stroke-width": 2},
        },
        {
            "select": {"element": "wedge", "within": "score"},
            "set": {"stroke": "#65A30D", "fill": "#65A30D"},
        },
        {
            "select": {"addresses": [{"id": "timestamp_2"}]},
            "set": {"stroke": "#B45309", "fill": "#B45309"},
        },
        {
            "select": {"element": "child", "within": "score"},
            "set": {"display": "inline"},
        },
        {
            "select": {"element": "child", "within": "b"},
            "set": {"stroke": "#EA580C", "fill": "#EA580C"},
        },
        {
            "select": {"element": "label", "within": "score"},
            "set": {"fill": "#4D7C0F", "font-size": 10},
        },
        {
            "select": {"addresses": [{"id": "timestamp_2", "part": ["coordinate"]}]},
            "set": {"fill": "#A16207"},
        },
        {
            "select": {"addresses": [{"id": "intro", "part": ["label"]}]},
            "set": {"fill": "#0E7490"},
        },
        {
            "select": {"addresses": [{"id": "da-capo", "part": ["label"]}]},
            "set": {"fill": "#9D174D"},
        },
        {
            "select": {"addresses": [{"id": "score", "part": ["name"]}]},
            "set": {
                "fill": "#111827",
                "font-size": 12,
                "content": "Styled score",
                "max-width": 120,
            },
        },
        {"select": {"element": "name", "within": "b"}, "set": {"fill": "#0369A1"}},
    ],
    "order": {
        "score": [
            "children",
            "markers",
            "line",
            "conversion_maps",
            "regions",
            "flow_control",
        ]
    },
}


def _styled(name: str) -> dict:
    return _read(FIXTURES / name)["graphical"]


def test_the_styled_manifests_carry_their_rules() -> None:
    expected = {
        "styled__score.yaml": _STYLED_SCORE,
        "styled__performance.yaml": {
            "rules": [
                *_SHARED,
                {
                    "select": {
                        "element": "wedge",
                        "domain": "physical",
                        "within": "performance",
                    },
                    "set": {"stroke": "#7F00FF", "fill": "#7F00FF"},
                },
            ],
        },
    }
    for name, graphical in expected.items():
        styled = _styled(name)
        assert styled["rules"] == graphical["rules"]
        assert styled["styles"] == graphical.get("styles", {})
        assert styled["order"] == graphical.get("order", {})
    assert [len(value["rules"]) for value in expected.values()] == [20, 3]


# The drawn elements and texts of styled__score: (type, address, timeline it
# belongs to, class, domain, modality, parent address). The map's domain and
# modality are those of its target unit, ticks. The wedges and coordinate
# labels of the timestamps origin (timestamp_1) and length (timestamp_2) lie in
# the markers band of score, which sets nothing, so their parent is score.
_LOGICAL = ("ContinuousLogicalTimeline", "logical", "continuous")
_SCORE = {"id": "score"}
_ORIGIN = {"id": "timestamp_1"}
_LENGTH = {"id": "timestamp_2"}
_INTRO = {"id": "intro"}
_DA_CAPO = {"id": "da-capo"}
_SCORE_ELEMENTS = [
    ("timeline", _SCORE, "score", *_LOGICAL, None),
    ("child", {"id": "b"}, "b", *_LOGICAL, _SCORE),
    ("map", {"id": "ticks"}, "score", "LinearMap", "logical", "discrete", _SCORE),
    ("region", _INTRO, "score", *_LOGICAL, _SCORE),
    ("jump", _DA_CAPO, "score", *_LOGICAL, _SCORE),
    ("wedge", _ORIGIN, "score", *_LOGICAL, _SCORE),
    ("wedge", _LENGTH, "score", *_LOGICAL, _SCORE),
    ("name", {"id": "score", "part": ["name"]}, "score", *_LOGICAL, _SCORE),
    ("name", {"id": "b", "part": ["name"]}, "b", *_LOGICAL, {"id": "b"}),
    ("label", {**_ORIGIN, "part": ["coordinate"]}, "score", *_LOGICAL, _SCORE),
    ("label", {**_LENGTH, "part": ["coordinate"]}, "score", *_LOGICAL, _SCORE),
    ("label", {"id": "intro", "part": ["label"]}, "score", *_LOGICAL, _INTRO),
    ("label", {"id": "da-capo", "part": ["label"]}, "score", *_LOGICAL, _DA_CAPO),
]
_ANCESTRY = {"score": ["score"], "b": ["b", "score"]}
_DEPTH = {"score": 1, "b": 2}


def _resolve(graphical: dict, element: tuple, prop: str) -> str:
    """Return the value the manifest's own rules give ``prop``.

    Ranks follow docs/drawing.md section 2.5 within one layer: addresses, depth of
    within, class, element, the count of domain and modality, position. An
    inherited property no rule sets is taken from the parent.
    """
    kind, address, owner, cls, domain, modality, parent = element
    ranked = []
    for position, rule in enumerate(graphical["rules"]):
        select = rule["select"]
        declaration = rule["set"]
        if isinstance(declaration, str):
            declaration = graphical["styles"][declaration]
        if prop not in declaration:
            continue
        if any(
            (key == "element" and value != kind)
            or (key == "addresses" and address not in value)
            or (key == "class" and value != cls)
            or (key == "domain" and value != domain)
            or (key == "modality" and value != modality)
            or (key == "within" and value not in _ANCESTRY[owner])
            for key, value in select.items()
        ):
            continue
        rank = (
            "addresses" in select,
            _DEPTH[select["within"]] if "within" in select else 0,
            "class" in select,
            "element" in select,
            ("domain" in select) + ("modality" in select),
            position,
        )
        ranked.append((rank, declaration[prop]))
    if ranked:
        return max(ranked)[1]
    assert parent is not None, (address, prop)
    (parent_element,) = [e for e in _SCORE_ELEMENTS if e[1] == parent]
    return _resolve(graphical, parent_element, prop)


def test_every_styled_score_item_has_its_own_colour() -> None:
    graphical = _styled("styled__score.yaml")
    painted = {"name": "fill", "label": "fill", "wedge": "fill"}
    colours = [
        _resolve(graphical, element, painted.get(element[0], "stroke"))
        for element in _SCORE_ELEMENTS
    ]
    assert colours == [
        "#1D4ED8",
        "#EA580C",
        "#7C3AED",
        "#0F766E",
        "#DB2777",
        "#65A30D",
        "#B45309",
        "#111827",
        "#0369A1",
        "#4D7C0F",
        "#A16207",
        "#0E7490",
        "#9D174D",
    ]
    assert len(set(colours)) == 13
    for element, colour in zip(_SCORE_ELEMENTS, colours, strict=True):
        if element[0] in {"timeline", "child", "jump", "wedge"}:
            assert _resolve(graphical, element, "fill") == colour


def test_every_styled_score_item_is_visible() -> None:
    graphical = _styled("styled__score.yaml")
    declarations = [
        (rule["select"], rule["set"])
        for rule in graphical["rules"]
        if isinstance(rule["set"], dict)
    ] + [(None, style) for style in graphical["styles"].values()]
    for select, declaration in declarations:
        assert declaration.get("stroke-width", 1) > 0
        assert declaration.get("opacity", 1) >= 0.5
        if declaration.get("display") == "none":
            assert select == {"addresses": [{"id": "a"}]}
    content = [
        select for select, declaration in declarations if "content" in declaration
    ]
    assert content == [{"addresses": [{"id": "score", "part": ["name"]}]}]


@pytest.mark.parametrize(
    "name", ["bundle_shared_member.yaml", "bundle_shared_member.minimal.yaml"]
)
def test_a_timeline_in_two_groups_passes_every_rule(name: str) -> None:
    file = _load(FIXTURES / "bundles" / name)
    value = with_bare_ids(file)
    assert [(group["id"], group["members"]) for group in value["groups"]] == [
        ("g1", ["t", "u"]),
        ("g2", ["t", "v"]),
    ]
    validate(file)
    assert identity_problems(file) == []


@pytest.mark.parametrize(
    ("name", "downbeat", "stated"),
    [
        (
            "timestamps.yaml",
            {"display": ["wedge", "name", "cross_section"]},
            {"groupstamp": False, "matchstamp": False},
        ),
        ("timestamps.minimal.yaml", {}, {}),
    ],
)
def test_named_timestamps_pass_through_the_emitter(
    name: str, downbeat: dict[str, Any], stated: dict[str, Any]
) -> None:
    file = _load(FIXTURES / name)
    value = with_bare_ids(file)
    assert value["graphical"]["timestamps"] == [
        {
            "coordinate": [3, 2],
            "id": "timestamp_1",
            "name": "Downbeat",
            "timeline": "clt_1",
            **downbeat,
            **stated,
        },
        {
            "coordinate": [6, 1],
            "display": ["wedge", "name"],
            "id": "timestamp_2",
            "name": "Climax",
            "timeline": "clt_1",
            **stated,
        },
        {
            "coordinate": [1, 1],
            "display": ["wedge", "name", "id", "coordinate", "cross_section"],
            "id": "timestamp_3",
            "name": "Entry",
            "timeline": "clt_2",
            **stated,
        },
    ]
    assert value["graphical"].get("rules", []) == []
    validate(file)
    assert identity_problems(file) == []


def _marks(*marks: tuple[str, str, object]) -> list[dict[str, Any]]:
    """Return the origin and length timestamps, numbered from 1 in order."""
    return [
        {
            "coordinate": coordinate,
            "display": ["wedge", "coordinate"],
            "id": f"timestamp_{number}",
            "name": name,
            "timeline": timeline,
        }
        for number, (timeline, name, coordinate) in enumerate(marks, start=1)
    ]


_ORIGIN_AND_LENGTH = {
    "label_float_rounding": _marks(
        ("take", "origin", 0.0), ("take", "length", 312.48979591836735)
    ),
    "bundles/bundle_ungrouped": _marks(
        ("pages", "origin", 0),
        ("pages", "length", 5262),
        ("recording", "origin", 0),
        ("recording", "length", 441000),
        ("score", "origin", [0, 1]),
        ("score", "length", [16, 1]),
    ),
    "groups/group_unknown_length": _marks(
        ("performance", "origin", 0.0),
        ("score", "origin", [0, 1]),
        ("score", "length", [12, 1]),
    ),
}


@pytest.mark.parametrize("suffix", [".yaml", ".minimal.yaml"])
@pytest.mark.parametrize("name", list(_ORIGIN_AND_LENGTH))
def test_drawn_roots_carry_their_origin_and_length(name: str, suffix: str) -> None:
    file = _load(FIXTURES / f"{name}{suffix}")
    value = with_bare_ids(file)
    stated = {"groupstamp": False, "matchstamp": False} if suffix == ".yaml" else {}
    expected = [{**mark, **stated} for mark in _ORIGIN_AND_LENGTH[name]]
    assert value["graphical"]["timestamps"] == expected
    validate(file)
    assert identity_problems(file) == []


@pytest.mark.parametrize(
    ("name", "stated"),
    [
        ("group_groupstamp.yaml", {"groupstamp": False, "matchstamp": False}),
        ("group_groupstamp.minimal.yaml", {}),
    ],
)
def test_a_groupstamp_passes_through_the_emitter(
    name: str, stated: dict[str, Any]
) -> None:
    file = _load(FIXTURES / "groups" / name)
    value = with_bare_ids(file)
    assert value["groups"][0]["id"] == "group_1"
    assert sorted(value["groups"][0]["members"]) == ["performance", "score"]
    complete = name == "group_groupstamp.yaml"
    groupstamp = {
        "coordinate": [4, 1],
        "groupstamp": True,
        "id": "timestamp_1",
        "name": "Bar 2",
        "timeline": "score",
    }
    if complete:
        groupstamp = {
            **groupstamp,
            "display": ["wedge", "name", "cross_section"],
            "matchstamp": False,
        }
    marks = _marks(
        ("performance", "origin", 0.0),
        ("performance", "length", 4.0),
        ("score", "origin", [0, 1]),
        ("score", "length", [8, 1]),
    )
    marks = [
        {**mark, "id": f"timestamp_{number}", **stated}
        for number, mark in enumerate(marks, start=2)
    ]
    assert value["graphical"]["timestamps"] == [*marks[:3], groupstamp, marks[3]]
    assert {
        timeline["id"]: [
            (entry["source_unit"], entry["target_unit"])
            for entry in timeline["conversion_maps"]
        ]
        for timeline in value["timelines"]
    } == {"performance": [("seconds", "samples")], "score": [("quarters", "ticks")]}
    validate(file)
    assert identity_problems(file) == []


def _groupstamps(value: dict[str, Any]) -> list[dict[str, Any]]:
    """The groupstamps of a manifest with bare IDs, by their stated members."""
    return [
        {key: stamp[key] for key in ("id", "timeline", "coordinate", "name")}
        for stamp in value["graphical"]["timestamps"]
        if stamp.get("groupstamp") is True
    ]


@pytest.mark.parametrize("suffix", [".yaml", ".minimal.yaml"])
def test_a_groupstamp_on_a_member_s_child_lies_in_the_group(suffix: str) -> None:
    file = _load(FIXTURES / "groups" / f"group_groupstamp_child_member{suffix}")
    value = with_bare_ids(file)
    assert [(group["id"], sorted(group["members"])) for group in value["groups"]] == [
        ("group_1", ["performance", "score"])
    ]
    children = {
        timeline["id"]: [child["id"] for child in timeline.get("children", [])]
        for timeline in value["timelines"]
    }
    assert children == {"performance": [], "score": ["second-half"]}
    assert _groupstamps(value) == [
        {
            "id": "timestamp_1",
            "timeline": "second-half",
            "coordinate": [2, 1],
            "name": "Bar 4",
        }
    ]
    validate(file)
    assert identity_problems(file) == []


@pytest.mark.parametrize("suffix", [".yaml", ".minimal.yaml"])
def test_a_groupstamp_on_a_shared_member_lies_in_both_groups(suffix: str) -> None:
    file = _load(FIXTURES / "bundles" / f"bundle_groupstamp_shared_member{suffix}")
    value = with_bare_ids(file)
    assert [(group["id"], sorted(group["members"])) for group in value["groups"]] == [
        ("g1", ["t", "u"]),
        ("g2", ["t", "v"]),
    ]
    assert _groupstamps(value) == [
        {"id": "timestamp_1", "timeline": "t", "coordinate": [4, 1], "name": "Bar 2"}
    ]
    validate(file)
    assert identity_problems(file) == []


@pytest.mark.parametrize("suffix", [".yaml", ".minimal.yaml"])
def test_a_match_timestamp_on_a_member_of_two_groups_is_a_groupstamp(
    suffix: str,
) -> None:
    file = _load(FIXTURES / "bundles" / f"bundle_matchstamp_groupstamp{suffix}")
    cards = _load(FIXTURES / "bundles" / f"bundle_matchstamp_cards{suffix}")
    value = with_bare_ids(file)
    assert [(group["id"], sorted(group["members"])) for group in value["groups"]] == [
        ("group_1", ["performance", "score"]),
        ("group_2", ["page", "score"]),
    ]
    stamps = value["graphical"]["timestamps"]
    (stamp,) = [stamp for stamp in stamps if stamp.get("groupstamp") is True]
    assert {key: stamp[key] for key in ("id", "timeline", "coordinate")} == {
        "id": "timestamp_1",
        "timeline": "score",
        "coordinate": [4, 1],
    }
    assert stamp["matchstamp"] is True
    expected = copy.deepcopy(cards["graphical"]["timestamps"])
    for written in expected:
        if written["id"] == "#timestamp_1":
            written["groupstamp"] = True
    assert file["graphical"]["timestamps"] == expected
    assert file["graphical"]["matchstamps"] == cards["graphical"]["matchstamps"]
    validate(file)
    assert identity_problems(file) == []
    assert matchstamp_problems(file) == []


@pytest.mark.parametrize("suffix", [".yaml", ".minimal.yaml"])
def test_a_band_order_may_list_a_subset_of_the_facets(suffix: str) -> None:
    file = _load(FIXTURES / f"map_band_order_subset{suffix}")
    value = with_bare_ids(file)
    assert value["graphical"]["order"] == {"melody": ["markers", "line"]}
    assert [root["id"] for root in value["timelines"]] == ["melody"]
    assert [child["id"] for child in value["timelines"][0]["children"]] == ["phrase"]
    validate(file)
    assert identity_problems(file) == []


@pytest.mark.parametrize("suffix", [".yaml", ".minimal.yaml"])
def test_a_child_member_carries_a_timestamp_and_a_matchstamp(suffix: str) -> None:
    file = _load(FIXTURES / "groups" / f"group_child_member_stamps{suffix}")
    value = with_bare_ids(file)
    assert [(group["id"], group["members"]) for group in value["groups"]] == [
        ("group_1", ["middle", "recording"])
    ]
    (piece, recording) = value["timelines"]
    assert [piece["id"], recording["id"]] == ["piece", "recording"]
    assert [(child["id"], child["offset"]) for child in piece["children"]] == [
        ("middle", [4, 1])
    ]
    stamps = {
        stamp["id"]: stamp
        for stamp in value["graphical"]["timestamps"]
        if stamp.get("name") not in ("origin", "length")
    }
    keys = ("timeline", "coordinate", "name", "display", "matchstamp", "groupstamp")
    # The twin leaves out every member at its default: a match timestamp's display,
    # an ordinary timestamp's `matchstamp: false` and every `groupstamp: false`.
    complete = {
        "timestamp_1": ["middle", [2, 1], "Bar 2", ["cross_section"], False, False],
        "timestamp_2": ["middle", [4, 1], None, ["cross_section"], True, False],
        "timestamp_3": ["recording", 5.0, None, ["cross_section"], True, False],
    }
    minimal = {
        "timestamp_1": ["middle", [2, 1], "Bar 2", ["cross_section"], None, None],
        "timestamp_2": ["middle", [4, 1], None, None, True, None],
        "timestamp_3": ["recording", 5.0, None, None, True, None],
    }
    found = {id: [stamp.get(key) for key in keys] for id, stamp in stamps.items()}
    assert found == (minimal if suffix == ".minimal.yaml" else complete)
    assert value["graphical"]["matchstamps"] == [
        {
            "id": "matchstamp_1",
            "name": "Middle, bar 3",
            "alignment_anchors": [
                {
                    "id": "anchor_1",
                    "timestamps": ["timestamp_2", "timestamp_3"],
                    "display": ["line", "name"],
                }
            ],
            "match_claims": ["claim_1"],
        }
    ]
    validate(file)
    assert identity_problems(file) == []
    assert matchstamp_problems(file) == []


@pytest.mark.parametrize("suffix", [".yaml", ".minimal.yaml"])
def test_a_parent_of_a_member_lays_its_children_below(suffix: str) -> None:
    file = _load(FIXTURES / "groups" / f"group_grandchild_parent_on_top{suffix}")
    value = with_bare_ids(file)
    assert [(group["id"], group["members"]) for group in value["groups"]] == [
        ("group_1", ["recording", "theme"])
    ]
    (recording, score) = value["timelines"]
    assert [recording["id"], score["id"]] == ["recording", "score"]
    (movement,) = score["children"]
    assert (movement["id"], movement["offset"]) == ("movement", [16, 1])
    assert [(child["id"], child["offset"]) for child in movement["children"]] == [
        ("theme", [8, 1])
    ]
    assert value["graphical"]["order"] == {
        "group_1": ["theme", "recording"],
        "movement": [
            "line",
            "children",
            "conversion_maps",
            "markers",
            "regions",
            "flow_control",
        ],
    }
    validate(file)
    assert identity_problems(file) == []


def test_no_corpus_fixture_carries_a_named_timestamp() -> None:
    corpora = [path for path in fixture_paths() if path.name.startswith("corpus_")]
    assert len(corpora) == 24
    for path in corpora:
        assert _read(path).get("graphical", {}).get("timestamps", []) == []


@pytest.mark.parametrize(
    "name", ["bundle_free_ids.yaml", "bundle_free_ids.minimal.yaml"]
)
def test_free_ids_are_written_as_given(name: str) -> None:
    file = _load(FIXTURES / "bundles" / name)
    value = with_bare_ids(file)
    score, take = "https://example.org/piece/score", "perf/take 2"
    assert [
        (root["id"], [region["id"] for region in root.get("regions", [])])
        for root in value["timelines"]
    ] == [
        (score, ["https://example.org/piece/score#exposition"]),
        (take, ["take 2/intro"]),
    ]
    assert [sorted(group["members"]) for group in value["groups"]] == [[score, take]]
    assert [rule["select"] for rule in value["graphical"]["rules"]] == [
        {"addresses": [{"id": "take 2/intro"}]}
    ]
    validate(file)
    assert identity_problems(file) == []


def _flow_control(timeline: dict) -> list[tuple[str, str]]:
    elements = [
        (element["role"], element["id"]) for element in timeline.get("flow_control", [])
    ]
    for child in timeline.get("children", []):
        elements += _flow_control(child)
    return elements


def test_numbered_flow_control_ids_name_their_role() -> None:
    elements = [
        element
        for path in fixture_paths()
        if not path.name.endswith(".minimal.yaml")
        for root in _read(path)["timelines"]
        for element in _flow_control(root)
    ]
    numbered = Counter(
        (role, element_id)
        for role, element_id in elements
        if re.fullmatch(r"[a-z_]+_[1-9][0-9]*", element_id)
    )
    for role, element_id in numbered:
        assert element_id.rsplit("_", 1)[0] == role, element_id
    assert numbered == {
        ("barline", "barline_1"): 2,
        ("barline", "barline_2"): 1,
        ("barline", "barline_3"): 1,
        ("break", "break_1"): 9,
        ("break", "break_2"): 3,
        ("break", "break_3"): 1,
        ("break", "break_4"): 1,
        ("jump", "jump_1"): 16,
        ("jump", "jump_2"): 9,
        ("jump", "jump_3"): 3,
        ("jump", "jump_4"): 1,
        ("jump", "jump_5"): 1,
        ("jump", "jump_6"): 1,
        ("jump", "jump_7"): 1,
        ("jump", "jump_8"): 1,
        ("jump", "jump_9"): 1,
        ("jump", "jump_10"): 1,
        ("jump", "jump_11"): 1,
        ("jump_target", "jump_target_1"): 11,
        ("jump_target", "jump_target_2"): 5,
        ("jump_target", "jump_target_3"): 1,
        ("jump_target", "jump_target_4"): 1,
        ("jump_target", "jump_target_5"): 1,
        ("jump_target", "jump_target_6"): 1,
        ("jump_target", "jump_target_7"): 1,
        ("jump_target", "jump_target_8"): 1,
        ("section_break", "section_break_1"): 2,
    }
    assert {element_id for role, element_id in elements} - {
        element_id for role, element_id in numbered
    } == {"fine", "da-capo", "da_capo_al_fine", "dal_segno", "repeat", "segno"}
