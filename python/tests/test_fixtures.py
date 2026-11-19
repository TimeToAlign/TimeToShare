from __future__ import annotations

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
    text = (FIXTURES / "corpus_score_ms3.yaml").read_text(encoding="utf-8")
    assert 'label: "MC 15 → start (MC 1)"' in text
    assert "\\u2192" not in text


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
            "select": {"element": "jump_from", "domain": "logical"},
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
    ("jump_from", _DA_CAPO, "score", *_LOGICAL, _SCORE),
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
        if element[0] in {"timeline", "child", "jump_from", "wedge"}:
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
    ("name", "downbeat"),
    [
        ("timestamps.yaml", {"display": ["wedge", "name", "cross_section"]}),
        ("timestamps.minimal.yaml", {}),
    ],
)
def test_named_timestamps_pass_through_the_emitter(
    name: str, downbeat: dict[str, Any]
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
        },
        {
            "coordinate": [6, 1],
            "display": ["wedge", "name"],
            "id": "timestamp_2",
            "name": "Climax",
            "timeline": "clt_1",
        },
        {
            "coordinate": [1, 1],
            "display": ["wedge", "name", "id", "coordinate", "cross_section"],
            "id": "timestamp_3",
            "name": "Entry",
            "timeline": "clt_2",
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
    assert value["graphical"]["timestamps"] == _ORIGIN_AND_LENGTH[name]
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
        (element["type"], element["id"]) for element in timeline.get("flow_control", [])
    ]
    for child in timeline.get("children", []):
        elements += _flow_control(child)
    return elements


def test_generated_flow_control_ids_carry_their_type() -> None:
    elements = [
        element
        for path in fixture_paths()
        if not path.name.endswith(".minimal.yaml")
        for root in _read(path)["timelines"]
        for element in _flow_control(root)
    ]
    generated = Counter(
        (kind, element_id)
        for kind, element_id in elements
        if re.fullmatch(r"[a-z_]+_[1-9][0-9]*", element_id)
    )
    assert all(element_id.startswith(f"{kind}_") for kind, element_id in generated)
    assert generated == {
        ("flow_marker", "flow_marker_1"): 3,
        ("jump_from", "jump_from_1"): 6,
        ("jump_from", "jump_from_2"): 2,
        ("jump_from", "jump_from_3"): 1,
        ("jump_from", "jump_from_4"): 1,
        ("jump_to", "jump_to_1"): 3,
        ("jump_to", "jump_to_2"): 2,
        ("jump_to", "jump_to_3"): 1,
    }
    assert {element_id for kind, element_id in elements} - {
        element_id for kind, element_id in generated
    } == {"fine", "da-capo", "da_capo_al_fine", "dal_segno", "repeat", "segno"}
