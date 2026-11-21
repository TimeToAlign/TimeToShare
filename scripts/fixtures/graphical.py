"""Graphical overlays, the origin and length timestamps of drawn roots, and
builders for the band-order fixtures."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from timetoalign import Timeline

from .timelines import map_timeline, styled_score_timeline, timestamps_timeline

_GREY = {"stroke": "#404040", "fill": "#404040"}

_SHARED_RULES: list[dict[str, Any]] = [
    {"select": {"element": "label"}, "set": _GREY},
    {"select": {"element": "name"}, "set": _GREY},
]

_VIOLET = {"stroke": "#7F00FF", "fill": "#7F00FF"}

_ACCENT = {"stroke": "#1D4ED8", "fill": "#1D4ED8", "stroke-width": 4, "opacity": 0.8}

_STYLED_SCORE: dict[str, Any] = {
    "styles": {"accent": _ACCENT},
    "rules": [
        *_SHARED_RULES,
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
}

GRAPHICAL: dict[str, dict[str, dict[str, Any]]] = {
    "styled": {
        "score": {
            **_STYLED_SCORE,
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
        },
        "performance": {
            "rules": [
                *_SHARED_RULES,
                {
                    "select": {
                        "element": "wedge",
                        "domain": "physical",
                        "within": "performance",
                    },
                    "set": _VIOLET,
                },
            ]
        },
    },
    "group_styled": {
        "group_1": {
            "styles": {"frame-highlight": {"stroke": "#7F00FF"}},
            "rules": [
                {"select": {"element": "frame"}, "set": "frame-highlight"},
                {
                    "select": {
                        "element": "name",
                        "addresses": [{"id": "group_1", "part": ["name"]}],
                    },
                    "set": {"fill": "#7F00FF"},
                },
                {
                    "select": {"element": "card", "inside": "frame"},
                    "set": {"shadow": "#C4B5FD", "rx": 2},
                },
            ],
        },
    },
    "map_child_band_order": {
        "melody": {
            "order": {
                "phrase": [
                    "children",
                    "line",
                    "conversion_maps",
                    "markers",
                    "regions",
                    "flow_control",
                ]
            }
        },
    },
    "map_root_band_order": {
        "melody": {
            "order": {
                "melody": [
                    "children",
                    "line",
                    "conversion_maps",
                    "markers",
                    "regions",
                    "flow_control",
                ]
            }
        },
    },
    "styled_score_flow_inner": {
        "score": {
            **_STYLED_SCORE,
            "order": {
                "score": [
                    "children",
                    "markers",
                    "line",
                    "conversion_maps",
                    "flow_control",
                    "regions",
                ]
            },
        },
    },
    "timestamps": {
        "clt_1": {
            "timestamps": [
                {
                    "id": "timestamp_1",
                    "timeline": "clt_1",
                    "coordinate": [3, 2],
                    "name": "Downbeat",
                },
                {
                    "id": "timestamp_2",
                    "timeline": "clt_1",
                    "coordinate": [6, 1],
                    "name": "Climax",
                    "display": ["wedge", "name"],
                },
                {
                    "id": "timestamp_3",
                    "timeline": "clt_2",
                    "coordinate": [1, 1],
                    "name": "Entry",
                    "display": ["wedge", "name", "id", "coordinate", "cross_section"],
                },
            ],
        },
    },
    "bundle_free_ids": {
        "group_1": {
            "rules": [
                {
                    "select": {"addresses": [{"id": "take 2/intro"}]},
                    "set": {"stroke": "#0F766E"},
                },
            ]
        },
    },
    "bundle_matchstamps": {
        "score": {
            "timestamps": [
                {
                    "id": "timestamp_1",
                    "timeline": "score",
                    "coordinate": [4, 1],
                    "matchstamp": True,
                },
                {
                    "id": "timestamp_2",
                    "timeline": "take_1",
                    "coordinate": 88200,
                    "matchstamp": True,
                },
                {
                    "id": "timestamp_3",
                    "timeline": "take_2",
                    "coordinate": 99225,
                    "name": "Take 2, bar 2",
                    "display": ["name", "cross_section"],
                    "matchstamp": True,
                },
            ],
            "matchstamps": [
                {
                    "id": "matchstamp_1",
                    "name": "Bar 2, downbeat (take 1)",
                    "alignment_anchors": [
                        {
                            "id": "anchor_1",
                            "timestamps": ["timestamp_1", "timestamp_2"],
                            "display": ["line", "name"],
                        },
                    ],
                    "match_claims": ["claim_1", "claim_2"],
                },
                {
                    "id": "matchstamp_2",
                    "name": "Bar 2, downbeat (take 2)",
                    "alignment_anchors": [
                        {"id": "anchor_2", "timestamps": ["timestamp_1", "timestamp_3"]},
                    ],
                    "match_claims": ["claim_3"],
                },
            ],
        },
    },
    "bundle_matchstamp_cards": {
        "score": {
            "timestamps": [
                {
                    "id": "timestamp_1",
                    "timeline": "score",
                    "coordinate": [4, 1],
                    "matchstamp": True,
                },
                {
                    "id": "timestamp_2",
                    "timeline": "performance",
                    "coordinate": 1.0,
                    "matchstamp": True,
                },
                {
                    "id": "timestamp_3",
                    "timeline": "second-half",
                    "coordinate": [2, 1],
                    "matchstamp": True,
                },
            ],
            "matchstamps": [
                {
                    "id": "matchstamp_1",
                    "name": "Bar 2, performed",
                    "alignment_anchors": [
                        {
                            "id": "anchor_1",
                            "timestamps": ["timestamp_2", "timestamp_1"],
                            "display": ["line", "name"],
                        },
                    ],
                    "match_claims": ["claim_1"],
                },
                {
                    "id": "matchstamp_2",
                    "name": "Second half, bar 1",
                    "alignment_anchors": [
                        {
                            "id": "anchor_2",
                            "timestamps": ["timestamp_1", "timestamp_3"],
                            "display": ["line", "name"],
                        },
                    ],
                    "match_claims": ["claim_2"],
                },
            ],
        },
    },
}

"""The ``graphical`` object of each manifest the script styles or gives band
orders, by fixture name and the id of its root (a manifest of one root) or of
its group (a manifest of one group).

The script adds an entry to the manifest's ``graphical``. The library reads
its ``styles``, ``rules`` and ``timestamps`` back as styling it keeps
unread, and each
entry of its ``order``, a band order keyed by a timeline's id, as an order
it keeps unchecked; it writes both back, the band orders beside the display
orders of its own groups. A rule selects elements by their address
objects: an element by its own id (``{"id": "intro"}``), a part of it by its
id and the part words (``{"id": "intro", "part": ["label"]}``), and a
band by its timeline's id and its facet (``{"id": "score", "facet":
"regions"}``). A band order lists ``line`` and the five facets.

``group_styled`` gives every frame the named style ``frame-highlight`` (a
violet stroke), fills the group's title, ``{"id": "group_1", "part":
["name"]}``, violet, and gives every card held by a frame a light violet
shadow and a corner radius of 2.

``bundle_free_ids`` strokes the region ``take 2/intro``, selected by its
address ``{"id": "take 2/intro"}``, teal.

In ``styled__score`` every drawn element and every text takes its own colour
under the cascade of ``docs/drawing.md`` (rules numbered from 0 in the
list, the two shared ones first):

==========================  =========  =============================================
Item                        Colour     Set by
==========================  =========  =============================================
root line ``score``         #1D4ED8    4, the style ``accent`` (class and element)
child line ``b``            #EA580C    13 (element ``child`` within ``b``)
map ``ticks``               #7C3AED    5 (class ``LinearMap``)
brace ``intro``             #0F766E    8, which outranks 7 by its position
jump ``da-capo``            #DB2777    9 (element ``jump_from``, domain ``logical``)
wedge of ``origin``         #65A30D    10 (element ``wedge`` within ``score``)
wedge of ``length``         #B45309    11 (``addresses``)
name of ``score``           #111827    18 (``addresses``; also ``content``)
name of ``b``               #0369A1    19 (element ``name`` within ``b``)
coordinate of ``origin``    #4D7C0F    14 (element ``label`` within ``score``)
coordinate of ``length``    #A16207    15 (``addresses``)
label of ``intro``          #0E7490    16 (``addresses``)
label of ``da-capo``        #9D174D    17 (``addresses``)
==========================  =========  =============================================

A stroke and the fill of one element share its colour. Rule 12 displays
every child of ``score``; rule 2, which names ``addresses``, outranks it
and hides the child ``a``. ``origin`` (``timestamp_1``) and ``length``
(``timestamp_2``) are the root's two timestamps of ``origin_and_length``,
rules 11 and 15 address the wedge and the coordinate label of
``length``. The band order of ``score`` lays the timestamps' wedges against
its line above it and its children beyond them, and its map against
its line below it, then its region and its jump.

``styled_score_flow_inner`` holds the same root with the same styles and
rules, so every colour above, and a band order that differs only in its
last two bands: below the line, the jump lies nearer the line than the
region.

``map_child_band_order`` and ``map_root_band_order`` hold the timelines of
``map`` and one band order each, which lays a line's conversion maps against
it below it, its markers below them and its children above it. The first
gives it to the child ``phrase`` alone, so that the map of ``phrase`` lies
below its line and that of ``melody`` above; the second to the root
``melody`` and none to ``phrase``, which follows the order of ``melody``, so
that the maps of both lie below their lines.
"""


_ZERO: dict[str, Any] = {"int": 0, "float": 0.0, "fraction": [0, 1]}
"""The zero of each number type as a manifest stores a coordinate."""

_ORIGIN_AND_LENGTH_DISPLAY = ["wedge", "coordinate"]


def _ids(value: Any) -> Iterator[str]:
    """Yield every ``id`` held at any depth of a manifest written by the library."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "id" and isinstance(item, str):
                yield item
            else:
                yield from _ids(item)
    elif isinstance(value, list):
        for item in value:
            yield from _ids(item)


def _tree(
    timelines: list[Mapping[str, Any]], ancestors: tuple[str, ...] = ()
) -> Iterator[tuple[Mapping[str, Any], tuple[str, ...]]]:
    """Yield every timeline of a tree with the ids of its ancestors, root first."""
    for timeline in timelines:
        yield timeline, ancestors
        yield from _tree(timeline.get("children", []), (*ancestors, timeline["id"]))


def drawn_roots(manifest: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return the timelines a manifest draws as roots of member drawings.

    These are every group's members and every ungrouped root, a root of
    ``timelines`` that no group names as a member and that contains no member
    (``docs/drawing.md``, section 8.1), in the traversal order of
    ``timelines``.
    """
    members = {
        member for group in manifest.get("groups", []) for member in group["members"]
    }
    holding = {
        ancestor
        for timeline, ancestors in _tree(manifest["timelines"])
        if timeline["id"] in members
        for ancestor in ancestors
    }
    return [
        timeline
        for timeline, ancestors in _tree(manifest["timelines"])
        if timeline["id"] in members
        or (not ancestors and timeline["id"] not in holding)
    ]


def origin_and_length(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the timestamps ``origin`` and ``length`` of each drawn root.

    An editor names the zero of every root of a member drawing ``origin`` and,
    when its length is known, its length ``length``, each drawing its wedge
    and its coordinate label (``display`` ``["wedge", "coordinate"]``). The
    timestamps are returned in canonical order (by timeline, then coordinate),
    each with the smallest ``timestamp_N`` the manifest's ids leave free,
    minted in that order. ``manifest`` is the library's complete form, which
    names every timeline's ``number_type``.
    """
    used = set(_ids({key: v for key, v in manifest.items() if key != "graphical"}))
    used.update(
        stamp["id"] for stamp in manifest.get("graphical", {}).get("timestamps", [])
    )
    marks: list[tuple[str, Any, str]] = []
    for timeline in sorted(drawn_roots(manifest), key=lambda timeline: timeline["id"]):
        marks.append((timeline["id"], _ZERO[timeline["number_type"]], "origin"))
        if timeline.get("length") is not None:
            marks.append((timeline["id"], timeline["length"], "length"))
    timestamps: list[dict[str, Any]] = []
    number = 0
    for timeline_id, coordinate, name in marks:
        number += 1
        while f"timestamp_{number}" in used:
            number += 1
        timestamps.append(
            {
                "id": f"timestamp_{number}",
                "timeline": timeline_id,
                "coordinate": coordinate,
                "name": name,
                "display": list(_ORIGIN_AND_LENGTH_DISPLAY),
            }
        )
    return timestamps


def map_child_band_order() -> Timeline:
    """Build ``map`` with a band order on the child ``phrase`` alone."""
    return map_timeline()


def map_root_band_order() -> Timeline:
    """Build ``map`` with a band order on the root ``melody`` alone."""
    return map_timeline()


def timestamps() -> Timeline:
    """Build the timelines of three named timestamps, each drawing other parts.

    ``Downbeat`` at 3/2 and ``Climax`` at 6 lie on the root ``clt_1``,
    ``Entry`` at 1 on its child ``clt_2``. ``Downbeat`` draws the default
    parts (its wedge, name and cross-section line), ``Climax`` its wedge and
    name only, ``Entry`` all five: wedge, name, ID, coordinate and
    cross-section line.
    """
    return timestamps_timeline()


def styled_score_flow_inner() -> Timeline:
    """Build ``styled__score`` with flow control nearer its line than regions."""
    return styled_score_timeline()
