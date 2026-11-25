"""Flow rules: flow control, FlowMaps and virtual timelines.

The schema checks the shape of every flow-control element, FlowMap and
virtual timeline; the rules here reach beyond it.

Before the schema, an element written in the earlier form of flow control
(the key ``type`` with ``jump_from``, ``jump_to`` or ``flow_marker``, or the
key ``target``) is refused with the name of the converter
(``flow_control_form``).

After the schema, timeline by timeline, the rules read the elements that are
not rejected. An element is rejected when an entry of its ``provenance``
holds a belief ``false``: a repair rejects an element and adds another, so a
rejected jump and its replacement may share a coordinate. In document
order: a coordinate lies from 0 to the timeline's known length
(``flow_coordinate``); a timeline has one jump at a coordinate
(``jump_repeated``); the destinations of a jump are distinct places
(``jump_destination``); a ``to`` names a jump target or a region of the
timeline, a child of it or the timeline itself (``dangling_target``); a place
reached by ``by`` lies from 0 to the known length (``flow_coordinate``); an
``after`` names exactly one destination of another jump of the timeline
(``dangling_target``).

Then the FlowMaps: ``timeline`` names a root (``flow_map_timeline``), every
chunk ID a region or a child timeline inside that root's tree, or a virtual
timeline of a timeline of it (``flow_map_chunk``), and at most one FlowMap of
a timeline is canonical (``flow_map_canonical``); and the virtual timelines:
``map`` names a FlowMap or a conversion map, ``timeline`` a timeline or
another virtual timeline (``dangling_target``).

A manifestation or a convention outside the format's vocabulary is valid:
:func:`flow_warnings` reports it.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from fractions import Fraction
from typing import Any

from ..manifest import exact
from ..serialization import spell
from .diagnostics import (
    InstancePath,
    SchemaValidationError,
    entries_of,
    json_pointer,
    number_type_of,
    string_id,
    tree_ids,
)

CONVERTER = "scripts/convert_flow_control.py"
"""The script that converts the earlier form of flow control, by its path in
the TimeToShare repository."""

EARLIER_ROLES = ("jump_from", "jump_to", "flow_marker")
"""The values of ``type`` in the earlier form of flow control."""

MANIFESTATIONS: Mapping[str, tuple[str, ...]] = {
    "destination": (
        "repeat_end",
        "da_capo",
        "da_capo_al_fine",
        "da_capo_al_coda",
        "dal_segno",
        "dal_segno_al_fine",
        "dal_segno_al_coda",
        "to_coda",
        "volta",
        "ossia",
    ),
    "jump_target": ("repeat_start", "segno", "coda", "volta", "ossia"),
    "break": ("fine", "volta"),
    "section_break": (),
    "barline": ("double_barline", "final_barline"),
}
"""The manifestations the format defines: of a jump's destination, and of an
element by its role. The vocabulary is open; any other word is reported as
unknown and never refused."""

CONVENTIONS = ("default", "single", "printed")
"""The conventions the format defines for a FlowMap; the vocabulary is open."""

_NAMED = {
    "destination": "a destination",
    "jump_target": "a jump target",
    "break": "a break",
    "section_break": "a section break",
    "barline": "a barline",
}


def _bare(text: str) -> str:
    return text[1:] if text.startswith("#") and len(text) > 1 else text


def _earlier(element: Any) -> bool:
    if not isinstance(element, Mapping):
        return False
    kind, role = element.get("type"), element.get("role")
    return (
        (isinstance(kind, str) and kind in EARLIER_ROLES)
        or (isinstance(role, str) and role in EARLIER_ROLES)
        or ("target" in element and "role" not in element)
    )


def _earlier_form(timeline: Any, path: InstancePath) -> Iterator[SchemaValidationError]:
    for index, element in enumerate(entries_of(timeline, "flow_control")):
        if _earlier(element):
            at = (*path, "flow_control", index)
            identifier = string_id(element)
            named = (
                f"flow-control element '{_bare(identifier)}'"
                if identifier is not None
                else f"the flow-control element at {json_pointer(at)}"
            )
            yield SchemaValidationError(
                "flow_control_form",
                at,
                f"{named} is written in the earlier form of flow control (type, "
                f"target): convert the manifest with {CONVERTER}",
            )
    for index, child in enumerate(entries_of(timeline, "children")):
        yield from _earlier_form(child, (*path, "children", index))


def earlier_form_problems(manifest: Any) -> Iterator[SchemaValidationError]:
    """Yield every flow-control element written in the earlier form.

    Root by root, each timeline's elements before its children's. The walk
    reads any value and either form of an ID.
    """
    for index, root in enumerate(entries_of(manifest, "timelines")):
        yield from _earlier_form(root, ("timelines", index))


def rejected(element: Any) -> bool:
    """Whether an entry of an element's provenance holds a belief ``false``."""
    return any(
        isinstance(belief, Mapping) and belief.get("belief") == "false"
        for entry in entries_of(element, "provenance")
        for belief in entries_of(entry, "beliefs")
    )


def _place(timeline: Mapping[str, Any], coordinate: Any, by: Any) -> Fraction:
    """Where a distance ``by`` from ``coordinate`` lands on the timeline's axis.

    On a ``float`` axis the two JSON numbers are added as doubles, as a
    reader adds them; on every other axis the sum is exact.
    """
    if number_type_of(timeline) == "float":
        try:
            return Fraction(float(coordinate) + float(by))
        except (TypeError, ValueError, OverflowError):
            pass
    return exact(coordinate) + exact(by)


def _place_key(destination: Mapping[str, Any]) -> tuple[str, Any]:
    if "to" in destination:
        return ("to", destination["to"])
    if "by" in destination:
        return ("by", exact(destination["by"]))
    return ("", None)


def _place_words(destination: Mapping[str, Any]) -> str:
    if "to" in destination:
        return f"to '{destination['to']}'"
    if "by" in destination:
        return f"by {spell(destination['by'])}"
    return "without a place"


def _after_problems(
    after: Mapping[str, Any],
    path: InstancePath,
    holder: str | None,
    jumps: Mapping[str, Mapping[str, Any]],
) -> Iterator[SchemaValidationError]:
    """The problem of one ``after``: it names one destination of another jump."""
    name = after["jump"]
    if name == holder:
        yield SchemaValidationError(
            "dangling_target",
            (*path, "jump"),
            f"'{name}' is the jump holding this destination; after names a "
            "destination of another jump",
        )
        return
    jump = jumps.get(name)
    if jump is None:
        yield SchemaValidationError(
            "dangling_target",
            (*path, "jump"),
            f"'{name}' names no jump of this timeline",
        )
        return
    destinations = jump["targets"]
    for key in ("to", "by"):
        if key in after:
            wanted = _place_key({key: after[key]})
            found = sum(_place_key(entry) == wanted for entry in destinations)
            if found != 1:
                yield SchemaValidationError(
                    "dangling_target",
                    (*path, key),
                    f"jump '{name}' has no destination "
                    f"{_place_words({key: after[key]})}",
                )
            return
    placeless = sum(_place_key(entry) == ("", None) for entry in destinations)
    if placeless != 1 and len(destinations) != 1:
        yield SchemaValidationError(
            "dangling_target",
            path,
            f"jump '{name}' has {len(destinations)} destinations and none without "
            "a place; after names one by its to or by",
        )


def timeline_flow_problems(
    timeline: Mapping[str, Any], path: InstancePath
) -> Iterator[SchemaValidationError]:
    """Yield the problems of one timeline's flow control, in document order.

    The timeline's own elements only; its children are the caller's.
    """
    flow = entries_of(timeline, "flow_control")
    read = [(index, entry) for index, entry in enumerate(flow) if not rejected(entry)]
    if not read:
        return
    length = timeline.get("length")
    end = None if length is None else exact(length)
    owner = timeline["id"]
    jumps = {entry["id"]: entry for _, entry in read if entry["role"] == "jump"}
    places = {entry["id"] for _, entry in read if entry["role"] == "jump_target"}
    places.update(region["id"] for region in entries_of(timeline, "regions"))
    places.update(child["id"] for child in entries_of(timeline, "children"))
    places.add(owner)
    first_jump: dict[Fraction, str] = {}

    def outside(value: Fraction) -> bool:
        return value < 0 or (end is not None and value > end)

    def beyond() -> str:
        return (
            "it lies before 0"
            if end is None
            else f"it lies outside 0 to the length {spell(length)}"
        )

    for index, entry in read:
        at = (*path, "flow_control", index)
        coordinate = exact(entry["coordinate"])
        if outside(coordinate):
            yield SchemaValidationError(
                "flow_coordinate",
                (*at, "coordinate"),
                f"coordinate {spell(entry['coordinate'])} of '{entry['id']}' is not "
                f"on '{owner}': {beyond()}",
            )
        if entry["role"] == "break" and "after" in entry.get("ends", {}):
            yield from _after_problems(
                entry["ends"]["after"], (*at, "ends", "after"), None, jumps
            )
        if entry["role"] != "jump":
            continue
        if coordinate in first_jump:
            yield SchemaValidationError(
                "jump_repeated",
                at,
                f"'{entry['id']}' is a second jump at coordinate "
                f"{spell(entry['coordinate'])} of '{owner}', after "
                f"'{first_jump[coordinate]}': several signs at one place are "
                "destinations of one jump",
            )
        else:
            first_jump[coordinate] = entry["id"]
        seen: dict[tuple[str, Any], int] = {}
        for number, destination in enumerate(entry["targets"]):
            here = (*at, "targets", number)
            key = _place_key(destination)
            if key in seen:
                yield SchemaValidationError(
                    "jump_destination",
                    here,
                    f"destination {number} of '{entry['id']}' has the place of "
                    f"destination {seen[key]}, {_place_words(destination)}",
                )
            else:
                seen[key] = number
            if "to" in destination and destination["to"] not in places:
                yield SchemaValidationError(
                    "dangling_target",
                    (*here, "to"),
                    f"'{destination['to']}' names no jump target, region or child "
                    "of this timeline, nor the timeline itself",
                )
            if "by" in destination:
                place = _place(timeline, entry["coordinate"], destination["by"])
                if outside(place):
                    yield SchemaValidationError(
                        "flow_coordinate",
                        (*here, "by"),
                        f"by {spell(destination['by'])} from coordinate "
                        f"{spell(entry['coordinate'])} of '{entry['id']}' is not on "
                        f"'{owner}': {beyond()}",
                    )
            if "after" in destination:
                yield from _after_problems(
                    destination["after"], (*here, "after"), entry["id"], jumps
                )


def _tree(
    root: Mapping[str, Any],
) -> tuple[set[str], set[str]]:
    """The IDs of a root's timelines and of what gives an interval inside its tree.

    The first set holds the root and every descendant; the second every
    descendant and every region of the root or a descendant.
    """
    timelines: set[str] = set()
    intervals: set[str] = set()

    def visit(timeline: Mapping[str, Any], child: bool) -> None:
        timelines.add(timeline["id"])
        if child:
            intervals.add(timeline["id"])
        intervals.update(region["id"] for region in entries_of(timeline, "regions"))
        for entry in entries_of(timeline, "children"):
            visit(entry, True)

    visit(root, False)
    return timelines, intervals


def _map_ids(manifest: Mapping[str, Any]) -> set[str]:
    """The IDs of every conversion map of a manifest, at any depth."""
    found: set[str] = set()
    for index, root in enumerate(entries_of(manifest, "timelines")):
        for identifier, path in tree_ids(root, ("timelines", index)):
            if "conversion_maps" in path:
                found.add(identifier)
    return found


def flow_map_problems(manifest: Mapping[str, Any]) -> Iterator[SchemaValidationError]:
    """Yield the problems of the FlowMaps, then of the virtual timelines.

    FlowMap by FlowMap: its timeline, its chunks in their order (none where
    the timeline is no root), then a second canonical FlowMap of its
    timeline. Virtual timeline by virtual timeline: its map, then its
    timeline.
    """
    roots = {root["id"]: root for root in entries_of(manifest, "timelines")}
    trees = {identifier: _tree(root) for identifier, root in roots.items()}
    every = set().union(*(timelines for timelines, _ in trees.values()))
    flow_maps = entries_of(manifest, "flow_maps")
    virtual = entries_of(manifest, "virtual_timelines")
    comes_from: dict[str, str] = {}
    for entry in virtual:
        comes_from.setdefault(entry["id"], entry["timeline"])

    def lies_in(identifier: str, timelines: set[str]) -> bool:
        """Whether a virtual timeline comes, map by map, from one of ``timelines``."""
        visited: set[str] = set()
        while identifier in comes_from and identifier not in visited:
            visited.add(identifier)
            identifier = comes_from[identifier]
        return identifier in timelines

    canonical: dict[str, str] = {}
    for index, flow_map in enumerate(flow_maps):
        at = ("flow_maps", index)
        name = flow_map["timeline"]
        if name not in roots:
            yield SchemaValidationError(
                "flow_map_timeline",
                (*at, "timeline"),
                f"'{name}' is a child timeline; a FlowMap names a root timeline"
                if name in every
                else f"'{name}' names no root timeline of this manifest",
            )
        else:
            timelines, intervals = trees[name]
            for number, chunk in enumerate(flow_map["chunks"]):
                if not isinstance(chunk, str):
                    continue
                if chunk not in intervals and not (
                    chunk in comes_from and lies_in(chunk, timelines)
                ):
                    yield SchemaValidationError(
                        "flow_map_chunk",
                        (*at, "chunks", number),
                        f"'{chunk}' names no region, child timeline or virtual "
                        f"timeline in the tree of '{name}'",
                    )
        if flow_map.get("canonical") is True:
            if name in canonical:
                yield SchemaValidationError(
                    "flow_map_canonical",
                    (*at, "canonical"),
                    f"'{flow_map['id']}' is a second canonical FlowMap of '{name}', "
                    f"after '{canonical[name]}'",
                )
            else:
                canonical[name] = flow_map["id"]

    maps = {flow_map["id"] for flow_map in flow_maps} | _map_ids(manifest)
    for index, entry in enumerate(virtual):
        at = ("virtual_timelines", index)
        if entry["map"] not in maps:
            yield SchemaValidationError(
                "dangling_target",
                (*at, "map"),
                f"'{entry['map']}' names no FlowMap or conversion map of this manifest",
            )
        name = entry["timeline"]
        if name == entry["id"] or (name not in every and name not in comes_from):
            yield SchemaValidationError(
                "dangling_target",
                (*at, "timeline"),
                f"'{name}' names no timeline and no other virtual timeline of "
                "this manifest",
            )


def _timeline_warnings(
    timeline: Mapping[str, Any], path: InstancePath
) -> Iterator[dict[str, Any]]:
    for index, entry in enumerate(entries_of(timeline, "flow_control")):
        at = (*path, "flow_control", index)
        checked = [(entry["role"], entry, at)]
        checked += [
            ("destination", destination, (*at, "targets", number))
            for number, destination in enumerate(entries_of(entry, "targets"))
        ]
        for kind, holder, here in checked:
            word = holder.get("manifestation")
            if isinstance(word, str) and word not in MANIFESTATIONS.get(kind, ()):
                yield {
                    "code": "manifestation_unknown",
                    "path": [*here, "manifestation"],
                    "message": f"'{word}' is no manifestation the format defines "
                    f"for {_NAMED[kind]}",
                }
    for index, child in enumerate(entries_of(timeline, "children")):
        yield from _timeline_warnings(child, (*path, "children", index))


def flow_warnings(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the flow warnings of a valid manifest, in document order.

    ``manifestation_unknown`` at the ``manifestation`` of a flow-control
    element or of a jump's destination that the format does not define for
    it, and ``convention_unknown`` at the ``convention`` of a FlowMap that is
    none of the format's.
    """
    found: list[dict[str, Any]] = []
    for index, root in enumerate(entries_of(manifest, "timelines")):
        found.extend(_timeline_warnings(root, ("timelines", index)))
    for index, flow_map in enumerate(entries_of(manifest, "flow_maps")):
        word = flow_map.get("convention")
        if isinstance(word, str) and word not in CONVENTIONS:
            found.append(
                {
                    "code": "convention_unknown",
                    "path": ["flow_maps", index, "convention"],
                    "message": f"'{word}' is no convention the format defines",
                }
            )
    return found
