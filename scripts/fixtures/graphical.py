"""Graphical overlays, the origin and length timestamps of drawn roots, and
builders for the band-order fixtures."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from fractions import Fraction
from typing import Any

from timetoalign import ContinuousLogicalTimeline, Timeline

from . import parts
from .timelines import styled_score_timeline, timestamps_timeline

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


def _rotated(number: int, timeline: str, quarter: int, rotation: int) -> dict[str, Any]:
    """Return the named timestamp ``timestamp_<number>`` at ``quarter`` of
    ``timeline``, named after the rotation its wedge is given."""
    return {
        "id": f"timestamp_{number}",
        "timeline": timeline,
        "coordinate": [quarter, 1],
        "name": f"{rotation}°",
    }


def _matchstamp_cards(*, groupstamp: bool) -> dict[str, Any]:
    """Return the named MatchStamps of ``bundle_matchstamp_cards``, whose match
    timestamp ``timestamp_1`` on ``score`` is a groupstamp where ``groupstamp``
    is true."""
    first: dict[str, Any] = {
        "id": "timestamp_1",
        "timeline": "score",
        "coordinate": [4, 1],
        "matchstamp": True,
    }
    if groupstamp:
        first["groupstamp"] = True
    return {
        "timestamps": [
            first,
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
    "group_groupstamp": {
        "group_1": {
            "timestamps": [
                {
                    "id": "timestamp_1",
                    "timeline": "score",
                    "coordinate": [4, 1],
                    "name": "Bar 2",
                    "groupstamp": True,
                },
            ],
        },
    },
    "group_groupstamp_child_member": {
        "group_1": {
            "timestamps": [
                {
                    "id": "timestamp_1",
                    "timeline": "second-half",
                    "coordinate": [2, 1],
                    "name": "Bar 4",
                    "groupstamp": True,
                },
            ],
        },
    },
    "bundle_groupstamp_shared_member": {
        "t": {
            "timestamps": [
                {
                    "id": "timestamp_1",
                    "timeline": "t",
                    "coordinate": [4, 1],
                    "name": "Bar 2",
                    "groupstamp": True,
                },
            ],
            "elisions": [
                {
                    "id": "elision_1",
                    "timeline": "t",
                    "start": [1, 1],
                    "end": [3, 1],
                    "width": {"canvas": 24},
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
                        {
                            "id": "anchor_2",
                            "timestamps": ["timestamp_1", "timestamp_3"],
                        },
                    ],
                    "match_claims": ["claim_3"],
                },
            ],
        },
    },
    "timestamp_wedge_rotation": {
        "melody": {
            "timestamps": [
                _rotated(1, "melody", 2, -135),
                _rotated(2, "melody", 4, -45),
                _rotated(3, "melody", 6, 0),
                _rotated(4, "melody", 8, 45),
                _rotated(5, "melody", 10, 135),
                _rotated(6, "melody", 12, 180),
                _rotated(7, "phrase", 2, -45),
                _rotated(8, "phrase", 6, 45),
                _rotated(9, "phrase", 10, 90),
            ],
            "rules": [
                {
                    "select": {"element": "wedge", "within": "phrase"},
                    "set": {"rotation": 90},
                },
                *(
                    {
                        "select": {
                            "element": "wedge",
                            "addresses": [{"id": f"timestamp_{number}"}],
                        },
                        "set": {"rotation": rotation},
                    }
                    for number, rotation in (
                        (1, -135),
                        (2, -45),
                        (3, 0),
                        (4, 45),
                        (5, 135),
                        (6, 180),
                        (7, -45),
                        (8, 45),
                    )
                ),
            ],
            "order": {
                "phrase": [
                    "children",
                    "markers",
                    "line",
                    "conversion_maps",
                    "regions",
                    "flow_control",
                ]
            },
        },
    },
    "bundle_matchstamp_cards": {"score": _matchstamp_cards(groupstamp=False)},
    "bundle_matchstamp_groupstamp": {"score": _matchstamp_cards(groupstamp=True)},
    "map_band_order_subset": {"melody": {"order": {"melody": ["markers", "line"]}}},
    "group_child_member_stamps": {
        "group_1": {
            "timestamps": [
                {
                    "id": "timestamp_1",
                    "timeline": "middle",
                    "coordinate": [2, 1],
                    "name": "Bar 2",
                    "display": ["cross_section"],
                },
                {
                    "id": "timestamp_2",
                    "timeline": "middle",
                    "coordinate": [4, 1],
                    "matchstamp": True,
                },
                {
                    "id": "timestamp_3",
                    "timeline": "recording",
                    "coordinate": 5.0,
                    "matchstamp": True,
                },
            ],
            "matchstamps": [
                {
                    "id": "matchstamp_1",
                    "name": "Middle, bar 3",
                    "alignment_anchors": [
                        {
                            "id": "anchor_1",
                            "timestamps": ["timestamp_2", "timestamp_3"],
                            "display": ["line", "name"],
                        },
                    ],
                    "match_claims": ["claim_1"],
                },
            ],
        },
    },
    "group_grandchild_parent_on_top": {
        "group_1": {
            "order": {
                "group_1": ["theme", "recording"],
                "movement": [
                    "line",
                    "children",
                    "conversion_maps",
                    "markers",
                    "regions",
                    "flow_control",
                ],
            },
        },
    },
    "bundle_elisions_stored": {
        "group_1": {
            "rules": [
                {"select": {"addresses": [{"id": "coda"}]}, "set": {"display": "none"}},
                {
                    "select": {"element": "elision", "within": "session"},
                    "set": {"display": "none"},
                },
                {
                    "select": {"addresses": [{"id": "session", "part": ["card"]}]},
                    "set": {"elision-mode": "full"},
                },
            ],
            "elisions": [
                {"id": "elision_1", "timeline": "coda", "start": [0, 1], "end": [8, 1]},
                {
                    "id": "elision_2",
                    "timeline": "page",
                    "start": 600,
                    "end": 1754,
                    "name": "Appendix",
                    "display": ["ellipsis", "name", "coordinate"],
                },
                {
                    "id": "elision_3",
                    "timeline": "recording",
                    "start": 0.0,
                    "end": 2.0,
                    "display": ["ellipsis", "coordinate"],
                },
                {
                    "id": "elision_4",
                    "timeline": "score",
                    "start": [0, 1],
                    "end": [20, 1],
                    "width": {"ratio": 0.5},
                    "display": ["ellipsis", "id", "continuation"],
                },
                {
                    "id": "elision_5",
                    "timeline": "score",
                    "start": [32, 1],
                    "end": [48, 1],
                    "name": "Development",
                    "width": {"span": [4, 1]},
                    "display": ["name"],
                },
                {
                    "id": "elision_6",
                    "timeline": "score",
                    "start": [40, 1],
                    "end": [56, 1],
                    "width": {"canvas": 30},
                    "display": [],
                },
                {"id": "elision_7", "timeline": "session", "start": 0.0, "end": 30.0},
            ],
        },
    },
    "group_elided_members": {
        "group_1": {
            "timestamps": [
                {
                    "id": "timestamp_1",
                    "timeline": "voice",
                    "coordinate": [15, 1],
                    "name": "Climax",
                    "groupstamp": True,
                },
                {
                    "id": "timestamp_2",
                    "timeline": "voice",
                    "coordinate": [21, 1],
                    "name": "Return",
                    "groupstamp": True,
                },
            ],
            "elisions": [
                {
                    "id": "elision_1",
                    "timeline": "excerpt",
                    "start": [2, 1],
                    "end": [8, 1],
                    "name": "Development",
                    "display": ["ellipsis", "name", "coordinate"],
                },
                {
                    "id": "elision_2",
                    "timeline": "phrase",
                    "start": [2, 1],
                    "end": [6, 1],
                    "width": {"ratio": 0.5},
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
"regions"}``). A band order lists ``line`` and any of the five facets.

``group_styled`` gives every frame the named style ``frame-highlight`` (a
violet stroke), fills the group's title, ``{"id": "group_1", "part":
["name"]}``, violet, and gives every card held by a frame a light violet
shadow and a corner radius of 2.

``group_groupstamp`` names the timestamp "Bar 2" at quarter 4 of the
member ``score`` a groupstamp, so its line extends across both members of
``group_1``. ``group_groupstamp_child_member`` names the timestamp "Bar 4"
at quarter 2 of ``second-half``, the child of the member ``score``, a
groupstamp: the child lies in ``group_1`` through its parent.
``bundle_groupstamp_shared_member`` names the timestamp "Bar 2" at quarter
4 of ``t``, a member of ``g1`` and of ``g2``, a groupstamp, so its line
extends across both frames. ``bundle_matchstamp_groupstamp`` makes the
match timestamp ``timestamp_1`` of ``bundle_matchstamp_cards``, at quarter 4
of ``score``, a member of ``group_1`` and of ``group_2``, a groupstamp.
``group_child_member_stamps`` puts both kinds of line on the child member
``middle`` of ``group_parent_both``: the timestamp "Bar 2" at its quarter 2,
drawing its cross-section line alone, and the match timestamp at its quarter
4 that the anchor of the MatchStamp "Middle, bar 3" joins to second 5.0 of
the member ``recording``.

``group_grandchild_parent_on_top`` gives the parent ``movement`` of the
member ``theme`` of ``group_grandchild`` the band order ``line``,
``children``, ``conversion_maps``, ``markers``, ``regions``,
``flow_control``, which lays its children below its line, while the root
``score`` keeps the default, its children above its line. In the card of
``theme`` the faded line of ``movement`` therefore lies above the member's
line and that of ``score`` below it: each on the side opposite to where its
own band order puts its children. Its ``order`` also states the display
order ``group_grandchild`` has, ``theme`` before ``recording``, which the
entry replaces.

``bundle_elisions_stored`` stores one elision of each kind the drawing
treats apart, in canonical order: ``elision_1`` from 0 to 8 of the child
``coda``, whose line a rule hides; ``elision_2`` "Appendix" from 600 to
1754 of the ungrouped ``page``, drawing its ellipsis, its name and its
coordinates; ``elision_3`` from 0.0 to 2.0 of the member ``recording``,
which lies in the group and so is drawn across its frame, with its
ellipsis and its coordinates; on the root ``score``, behind the frame of
its child member ``theme`` (16 to 24), ``elision_4`` from 0 to 20 with
the width ``{"ratio": 0.5}``, which overlaps the member and draws its
ellipsis, its ID and the continuations of its rows, ``elision_5``
"Development" from 32 to 48 with ``{"span": [4, 1]}``, drawing its name
alone, and ``elision_6`` from 40 to 56 with ``{"canvas": 30}``, which
overlaps ``elision_5`` and draws a bare gap; and ``elision_7`` from 0.0
to 30.0 of the root ``session``, behind the frame of its child member
``take``, whose cards the rule ``elision-mode: full`` draws whole, so
``elision_7`` is kept and not drawn. Beside it the rule
``{"element": "elision", "within": "session"}`` hides every elision
within the session: it hides ``elision_7`` a second time and leaves
``elision_3`` drawn where the frame carries it into the session's
ancestor card, since a carried gap follows the frame's display and not the
card's cascade, while the mode rule shows that it is drawn in every mode.

``group_elided_members`` stores two elisions on timelines lying in the
group "Theme", each drawn across its frame: ``elision_1`` "Development"
from 2 to 8 of the member ``excerpt``, without ``width``, drawing its
ellipsis, its name and its coordinates, and ``elision_2`` from 2 to 6 of
``phrase``, the child of the member ``voice``, with ``{"ratio": 0.5}``.
The groupstamps "Climax" at 15 and "Return" at 21 of ``voice`` lie in
the gap of ``elision_2`` and after it.

``bundle_groupstamp_shared_member`` also stores the elision ``elision_1``
from 1 to 3 of ``t`` with ``{"canvas": 24}``, drawn across both frames.

``timestamp_wedge_rotation`` turns the wedges of named timestamps, each
named after its rotation. On the root ``melody`` they lie at quarters 2,
4, 6, 8, 10 and 12, turned -135, -45, 0, 45, 135 and 180 by a rule naming
the wedge's address; 0 is written, the others are the stops of a slider
between -180 and 180 (-180 draws the wedge 180 draws). On the child
``phrase``, whose band order lays its markers band against its line above
it, the wedges at its quarters 2 and 6 are turned -45 and 45 by addressed
rules, so they mirror those below the root's line; the wedge at its
quarter 10 is reached only by the rule ``{"element": "wedge", "within":
"phrase"}``, which turns every wedge of ``phrase`` 90 and is outranked by
the addressed rules. The root's ``origin`` and ``length`` keep the
unturned wedge.

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
that the maps of both lie below their lines. ``map_band_order_subset``
gives ``melody`` the band order ``markers``, ``line`` alone: the facets it
leaves out keep their side of the default order, so ``melody`` draws
``children``, ``conversion_maps``, ``markers``, ``line``, ``regions``,
``flow_control``, and ``phrase`` follows that completed order.
"""


_ZERO: dict[str, Any] = {"int": 0, "float": 0.0, "fraction": [0, 1]}
"""The zero of each number type as a manifest stores a coordinate."""

_ORIGIN_AND_LENGTH_DISPLAY = ["wedge", "coordinate"]

_MEMBER_ORIGIN_AND_LENGTH_DISPLAY = ["wedge", "coordinate", "cross_section"]


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
    and its coordinate label (``display`` ``["wedge", "coordinate"]``). On a
    member that is a child timeline both are groupstamps that also draw
    their cross-section lines (``["wedge", "coordinate", "cross_section"]``),
    as an editor gives them to a child joining a group, so that their lines
    cross the frame and the member's ancestor lines. The
    timestamps are returned in canonical order (by timeline, then coordinate),
    each with the smallest ``timestamp_N`` the manifest's ids leave free,
    minted in that order. ``manifest`` is the library's complete form, which
    names every timeline's ``number_type``.
    """
    used = set(_ids({key: v for key, v in manifest.items() if key != "graphical"}))
    used.update(
        stamp["id"] for stamp in manifest.get("graphical", {}).get("timestamps", [])
    )
    children = {
        timeline["id"]
        for timeline, ancestors in _tree(manifest["timelines"])
        if ancestors
    }
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
        stamp: dict[str, Any] = {
            "id": f"timestamp_{number}",
            "timeline": timeline_id,
            "coordinate": coordinate,
            "name": name,
            "display": list(_ORIGIN_AND_LENGTH_DISPLAY),
        }
        if timeline_id in children:
            stamp["display"] = list(_MEMBER_ORIGIN_AND_LENGTH_DISPLAY)
            stamp["groupstamp"] = True
        timestamps.append(stamp)
    return timestamps


def timestamps() -> Timeline:
    """Build the timelines of three named timestamps, each drawing other parts.

    ``Downbeat`` at 3/2 and ``Climax`` at 6 lie on the root ``clt_1``,
    ``Entry`` at 1 on its child ``clt_2``. ``Downbeat`` draws the default
    parts (its wedge, name and cross-section line), ``Climax`` its wedge and
    name only, ``Entry`` all five: wedge, name, ID, coordinate and
    cross-section line.
    """
    return timestamps_timeline()


def timestamp_wedge_rotation() -> Timeline:
    """Build the timelines of the turned wedges.

    The root ``melody`` ("Melody", 16 quarters) holds the child ``phrase``
    ("Phrase", 12 quarters) at 1, so no timestamp of the child lies at a
    quarter of the root that holds one; the named timestamps lie on both
    (``GRAPHICAL["timestamp_wedge_rotation"]``).
    """
    melody = parts.named(ContinuousLogicalTimeline, "melody", "Melody", Fraction(16))
    parts.holding(
        melody,
        parts.named(ContinuousLogicalTimeline, "phrase", "Phrase", Fraction(12)),
        Fraction(1),
    )
    return melody


def styled_score_flow_inner() -> Timeline:
    """Build ``styled__score`` with flow control nearer its line than regions."""
    return styled_score_timeline()
