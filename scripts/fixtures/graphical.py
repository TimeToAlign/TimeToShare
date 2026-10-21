"""Graphical overlays and builders for the band-order fixtures."""

from __future__ import annotations

from typing import Any

from timetoalign import Timeline

from .timelines import map_timeline, styled_score_timeline

_GREY = {"stroke": "#404040", "fill": "#404040"}

_SHARED_STATEMENTS: list[dict[str, Any]] = [
    {"select": {"element": "label"}, "set": _GREY},
    {"select": {"element": "name"}, "set": _GREY},
]

_VIOLET = {"stroke": "#7F00FF", "fill": "#7F00FF"}

_ACCENT = {"stroke": "#1D4ED8", "fill": "#1D4ED8", "stroke-width": 4, "opacity": 0.8}

_STYLED_SCORE: dict[str, Any] = {
    "styles": {"accent": _ACCENT},
    "statements": [
        *_SHARED_STATEMENTS,
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
            "select": {"addresses": [{"id": "score", "part": ["end"]}]},
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
            "select": {"addresses": [{"id": "score", "part": ["end", "label"]}]},
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
            "statements": [
                *_SHARED_STATEMENTS,
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
            "statements": [
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
    "bundle_free_ids": {
        "group_1": {
            "statements": [
                {
                    "select": {"addresses": [{"id": "take 2/intro"}]},
                    "set": {"stroke": "#0F766E"},
                },
            ]
        },
    },
}

"""The ``graphical`` object of each manifest the script styles or gives band
orders, by fixture name and the id of its root (a manifest of one root) or of
its group (a manifest of one group).

The script adds an entry to the manifest's ``graphical``. The library reads
its ``styles`` and ``statements`` back as styling it keeps unread, and each
entry of its ``order``, a band order keyed by a timeline's id, as an order
it keeps unchecked; it writes both back, the band orders beside the display
orders of its own groups. A statement selects elements by their address
objects: an element by its own id (``{"id": "intro"}``), a part of it by its
id and the part words (``{"id": "score", "part": ["end", "label"]}``), and a
band by its timeline's id and its facet (``{"id": "score", "facet":
"regions"}``). A band order lists ``line`` and the five facets.

``group_styled`` gives every frame the named style ``frame-highlight`` (a
violet stroke), fills the group's title, ``{"id": "group_1", "part":
["name"]}``, violet, and gives every card held by a frame a light violet
shadow and a corner radius of 2.

``bundle_free_ids`` strokes the region ``take 2/intro``, selected by its
address ``{"id": "take 2/intro"}``, teal.

In ``styled__score`` every drawn element and every text takes its own colour
under the cascade of ``docs/drawing.md`` (statements numbered from 0 in the
list, the two shared ones first):

==========================  =========  =============================================
Item                        Colour     Set by
==========================  =========  =============================================
root line ``score``         #1D4ED8    4, the style ``accent`` (class and element)
child line ``b``            #EA580C    13 (element ``child`` within ``b``)
map ``ticks``               #7C3AED    5 (class ``LinearMap``)
brace ``intro``             #0F766E    8, which outranks 7 by its position
jump ``da-capo``            #DB2777    9 (element ``jump_from``, domain ``logical``)
start wedge of ``score``    #65A30D    10 (element ``wedge`` within ``score``)
end wedge of ``score``      #B45309    11 (``addresses``)
name of ``score``           #111827    18 (``addresses``; also ``content``)
name of ``b``               #0369A1    19 (element ``name`` within ``b``)
label of the start wedge    #4D7C0F    14 (element ``label`` within ``score``)
label of the end wedge      #A16207    15 (``addresses``)
label of ``intro``          #0E7490    16 (``addresses``)
label of ``da-capo``        #9D174D    17 (``addresses``)
==========================  =========  =============================================

A stroke and the fill of one element share its colour. Statement 12 displays
every child of ``score``; statement 2, which names ``addresses``, outranks it
and hides the child ``a``. The band order of ``score`` lays its start and end wedges
against its line above it and its children beyond them, and its map against
its line below it, then its region and its jump.

``styled_score_flow_inner`` holds the same root with the same styles and
statements, so every colour above, and a band order that differs only in its
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


def map_child_band_order() -> Timeline:
    """Build ``map`` with a band order on the child ``phrase`` alone."""
    return map_timeline()


def map_root_band_order() -> Timeline:
    """Build ``map`` with a band order on the root ``melody`` alone."""
    return map_timeline()


def styled_score_flow_inner() -> Timeline:
    """Build ``styled__score`` with flow control nearer its line than regions."""
    return styled_score_timeline()
