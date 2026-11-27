"""Named-timestamp, elision, MatchStamp and resource rules.

The timeline a timestamp names, its coordinate and whether it may be a
groupstamp; the timeline an elision names and its stretch; the alignment
anchors of the named MatchStamps and their match timestamps; the timelines,
types and folders of the resources.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from fractions import Fraction
from typing import Any

from ..manifest import exact
from ..serialization import spell
from .diagnostics import (
    SchemaValidationError,
    axes_by_id,
    connected_sets,
    elisions_of,
    entries_of,
    matchstamps_of,
    string_id,
    timestamps_of,
)


def _grouped_timelines(manifest: Mapping[str, Any]) -> set[str]:
    """Return the IDs of the timelines lying in a group, at any depth.

    A timeline lies in a group when it or one of its ancestors is listed in
    the group's ``members``: a member's descendants are drawn inside the
    member's card in the group's frame. An ancestor of a member lies in no
    group through it. A virtual timeline lies in the groups it is a member
    of.
    """
    members = {
        member
        for group in entries_of(manifest, "groups")
        for member in group.get("members", [])
    }
    grouped: set[str] = set()

    def visit(timeline: Mapping[str, Any], inside: bool) -> None:
        """Add a timeline if it or an ancestor is a member, then its children."""
        inside = inside or timeline["id"] in members
        if inside:
            grouped.add(timeline["id"])
        for child in entries_of(timeline, "children"):
            visit(child, inside)

    for root in entries_of(manifest, "timelines"):
        visit(root, False)
    grouped.update(
        entry["id"]
        for entry in entries_of(manifest, "virtual_timelines")
        if entry["id"] in members
    )
    return grouped


def timestamp_problems(
    manifest: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """Yield timestamps off the manifest's timelines, outside their extent or groupless.

    A timestamp names a timeline of the manifest, at any depth, or a virtual
    timeline, and its coordinate lies between 0 and that timeline's length,
    or at or after 0 where the length is not known. A groupstamp
    (``groupstamp: true``), a match timestamp included, lies in a group: its
    timeline or one of that timeline's ancestors is a member of a group.
    """
    timelines = axes_by_id(manifest)
    grouped = _grouped_timelines(manifest)
    ends: dict[str, Fraction] = {}
    for index, timestamp in enumerate(timestamps_of(manifest)):
        path = ("graphical", "timestamps", index)
        identifier = timestamp["timeline"]
        timeline = timelines.get(identifier)
        if timeline is None:
            yield SchemaValidationError(
                "timestamp_timeline",
                (*path, "timeline"),
                f"'{identifier}' names no timeline or virtual timeline of this "
                "manifest",
            )
            continue
        coordinate = timestamp["coordinate"]
        length = timeline.get("length")
        value = exact(coordinate)
        if value < 0:
            yield SchemaValidationError(
                "timestamp_coordinate",
                (*path, "coordinate"),
                f"coordinate {spell(coordinate)} of '{timestamp['id']}' lies "
                f"before the start of its timeline '{identifier}'",
            )
        elif length is not None:
            end = ends.get(identifier)
            if end is None:
                end = ends[identifier] = exact(length)
            if value > end:
                yield SchemaValidationError(
                    "timestamp_coordinate",
                    (*path, "coordinate"),
                    f"coordinate {spell(coordinate)} of '{timestamp['id']}' is "
                    f"beyond the length {spell(length)} of its timeline "
                    f"'{identifier}'",
                )
        if timestamp.get("groupstamp") is True and identifier not in grouped:
            yield SchemaValidationError(
                "groupstamp",
                (*path, "groupstamp"),
                f"'{timestamp['id']}' is a groupstamp, but its timeline "
                f"'{identifier}' is a member of no group and lies in none",
            )


def elision_problems(
    manifest: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """Yield elisions off the manifest's timelines or outside their extent.

    An elision names a timeline of the manifest, at any depth, or a virtual
    timeline, and its ``start`` lies before its ``end``, both between 0 and
    that timeline's length, or at or after 0 where the length is not known.
    Elisions may overlap; no overlap is a problem.
    """
    timelines = axes_by_id(manifest)
    ends: dict[str, Fraction] = {}
    for index, elision in enumerate(elisions_of(manifest)):
        path = ("graphical", "elisions", index)
        identifier = elision["timeline"]
        timeline = timelines.get(identifier)
        if timeline is None:
            yield SchemaValidationError(
                "elision_timeline",
                (*path, "timeline"),
                f"'{identifier}' names no timeline or virtual timeline of this "
                "manifest",
            )
            continue
        start, end = elision["start"], elision["end"]
        if exact(start) < 0:
            yield SchemaValidationError(
                "elision_stretch",
                (*path, "start"),
                f"start {spell(start)} of '{elision['id']}' lies before the start "
                f"of its timeline '{identifier}'",
            )
        length = timeline.get("length")
        if length is not None:
            known = ends.get(identifier)
            if known is None:
                known = ends[identifier] = exact(length)
            if exact(end) > known:
                yield SchemaValidationError(
                    "elision_stretch",
                    (*path, "end"),
                    f"end {spell(end)} of '{elision['id']}' is beyond the length "
                    f"{spell(length)} of its timeline '{identifier}'",
                )
        if exact(start) >= exact(end):
            yield SchemaValidationError(
                "elision_stretch",
                (*path, "end"),
                f"end {spell(end)} of '{elision['id']}' does not lie after its "
                f"start {spell(start)}",
            )


def matchstamp_problems(
    manifest: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """Yield the problems of the named MatchStamps and their match timestamps.

    MatchStamp by MatchStamp, each alignment anchor names two match
    timestamps of the manifest (``matchstamp: true``) lying on two timelines,
    and the anchors are one connected set; then, timestamp by timestamp, a
    match timestamp shares its coordinate with no earlier match timestamp and
    some MatchStamp names it.
    """
    timestamps: dict[str, Mapping[str, Any]] = {}
    for timestamp in timestamps_of(manifest):
        identifier = string_id(timestamp)
        if identifier is not None:
            timestamps.setdefault(identifier, timestamp)
    named: set[str] = set()
    for index, matchstamp in enumerate(matchstamps_of(manifest)):
        path = ("graphical", "matchstamps", index, "alignment_anchors")
        pairs: list[tuple[str, str]] = []
        for number, anchor in enumerate(matchstamp["alignment_anchors"]):
            at = (*path, number, "timestamps")
            ends = anchor["timestamps"]
            named.update(ends)
            pairs.append((ends[0], ends[1]))
            found = []
            for position, identifier in enumerate(ends):
                timestamp = timestamps.get(identifier)
                if timestamp is None:
                    yield SchemaValidationError(
                        "alignment_anchor",
                        (*at, position),
                        f"'{identifier}' names no timestamp of this manifest",
                    )
                elif timestamp.get("matchstamp") is not True:
                    yield SchemaValidationError(
                        "alignment_anchor",
                        (*at, position),
                        f"'{identifier}' is no match timestamp",
                    )
                else:
                    found.append(timestamp)
            if len(found) == 2 and found[0]["timeline"] == found[1]["timeline"]:
                yield SchemaValidationError(
                    "alignment_anchor",
                    (*at, 1),
                    f"the timestamps of '{anchor['id']}' both lie on the timeline "
                    f"'{found[0]['timeline']}'",
                )
        if len(set(connected_sets(pairs).values())) > 1:
            yield SchemaValidationError(
                "matchstamp",
                path,
                f"the alignment anchors of '{matchstamp['id']}' are not one "
                "connected set",
            )
    first: dict[tuple[str, Any], str] = {}
    for index, timestamp in enumerate(timestamps_of(manifest)):
        if (
            not isinstance(timestamp, Mapping)
            or timestamp.get("matchstamp") is not True
        ):
            continue
        path = ("graphical", "timestamps", index)
        identifier = timestamp["id"]
        key = (timestamp["timeline"], exact(timestamp["coordinate"]))
        if key in first:
            yield SchemaValidationError(
                "match_timestamp",
                path,
                f"'{identifier}' lies on the coordinate of the match timestamp "
                f"'{first[key]}'",
            )
        else:
            first[key] = identifier
        if identifier not in named:
            yield SchemaValidationError(
                "match_timestamp",
                path,
                f"the match timestamp '{identifier}' belongs to no MatchStamp",
            )


FOLDER_FILE_KEYS = ("size", "integrity")
"""The members of a descriptor that state a file's bytes, which a folder has not."""


def folder_problems(
    descriptor: Mapping[str, Any], path: tuple[str | int, ...]
) -> Iterator[SchemaValidationError]:
    """Yield the problem of a descriptor naming a folder (a ``url`` ending in
    ``/``) with a ``size`` or an ``integrity``: the first of the two it
    states, at that member."""
    url = descriptor.get("url")
    if not (isinstance(url, str) and url.endswith("/")):
        return
    for key in FOLDER_FILE_KEYS:
        if key in descriptor:
            yield SchemaValidationError(
                "folder_descriptor",
                (*path, key),
                f"'{url}' names a folder, which has no {key}",
            )
            return


def resource_problems(
    manifest: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """Yield the problems of the resources.

    Resource by resource, each ID of its ``timelines`` names a timeline of
    the manifest, at any depth, or a virtual timeline, and no earlier
    resource of its type lists it; then a folder has no ``size`` and no
    ``integrity``.
    """
    timelines = axes_by_id(manifest)
    first: dict[tuple[str, str], str] = {}
    for index, resource in enumerate(entries_of(manifest, "resources")):
        path = ("resources", index)
        kind = resource["type"]
        for number, identifier in enumerate(resource["timelines"]):
            at = (*path, "timelines", number)
            if identifier not in timelines:
                yield SchemaValidationError(
                    "resource_timeline",
                    at,
                    f"'{identifier}' names no timeline or virtual timeline of "
                    "this manifest",
                )
            earlier = first.setdefault((kind, identifier), resource["id"])
            if earlier != resource["id"]:
                yield SchemaValidationError(
                    "resource_type",
                    at,
                    f"'{identifier}' is listed by the resource '{earlier}' of the "
                    f"type {kind} already",
                )
        yield from folder_problems(resource, path)
