"""Named-timestamp, MatchStamp and resource rules.

The timeline a timestamp names and its coordinate; the alignment anchors of
the named MatchStamps and their match timestamps; the timelines and types of
the resources.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from ..manifest import _exact
from ..serialization import spell
from .diagnostics import (
    SchemaValidationError,
    _entries,
    connected_sets,
    matchstamps_of,
    timelines_by_id,
    timestamps_of,
)


def timestamp_problems(
    manifest: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """Yield timestamps off the manifest's timelines or outside their extent.

    A timestamp names a timeline of the manifest, at any depth, and its
    coordinate lies between 0 and that timeline's length, or at or after 0
    where the length is not known.
    """
    timelines = timelines_by_id(manifest)
    for index, timestamp in enumerate(timestamps_of(manifest)):
        path = ("graphical", "timestamps", index)
        identifier = timestamp["timeline"]
        timeline = timelines.get(identifier)
        if timeline is None:
            yield SchemaValidationError(
                "timestamp_timeline",
                (*path, "timeline"),
                f"'{identifier}' names no timeline of this manifest",
            )
            continue
        coordinate = timestamp["coordinate"]
        length = timeline.get("length")
        where = f"coordinate {spell(coordinate)} of '{timestamp['id']}'"
        if _exact(coordinate) < 0:
            yield SchemaValidationError(
                "timestamp_coordinate",
                (*path, "coordinate"),
                f"{where} lies before the start of its timeline '{identifier}'",
            )
        elif length is not None and _exact(coordinate) > _exact(length):
            yield SchemaValidationError(
                "timestamp_coordinate",
                (*path, "coordinate"),
                f"{where} is beyond the length {spell(length)} of its timeline "
                f"'{identifier}'",
            )


def matchstamp_problems(
    manifest: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """Yield the problems of the named MatchStamps and their match timestamps.

    MatchStamp by MatchStamp, each alignment anchor names two match
    timestamps of the manifest (``matchstamp: true``) lying on two timelines,
    and the anchors are one connected set; then, timestamp by timestamp, a
    match timestamp shares its coordinate with no earlier match timestamp
    and some MatchStamp names it.
    """
    timestamps: dict[str, Mapping[str, Any]] = {}
    for timestamp in timestamps_of(manifest):
        timestamps.setdefault(timestamp["id"], timestamp)
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
        if timestamp.get("matchstamp") is not True:
            continue
        path = ("graphical", "timestamps", index)
        identifier = timestamp["id"]
        key = (timestamp["timeline"], _exact(timestamp["coordinate"]))
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


ONE_RESOURCE_TYPES = ("MatchClaim", "Projection")
"""The resource types a manifest names at most once."""


def resource_problems(
    manifest: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """Yield the problems of the resources.

    Resource by resource, each ID of its ``timelines`` names a timeline of
    the manifest, at any depth, and no earlier resource has its type where
    that type is ``MatchClaim`` or ``Projection``.
    """
    timelines = timelines_by_id(manifest)
    first: dict[str, str] = {}
    for index, resource in enumerate(_entries(manifest, "resources")):
        path = ("resources", index)
        for number, identifier in enumerate(resource["timelines"]):
            if identifier not in timelines:
                yield SchemaValidationError(
                    "resource_timeline",
                    (*path, "timelines", number),
                    f"'{identifier}' names no timeline of this manifest",
                )
        kind = resource["type"]
        if kind in ONE_RESOURCE_TYPES:
            if kind in first:
                yield SchemaValidationError(
                    "resource_type",
                    (*path, "type"),
                    f"a manifest names at most one resource of the type {kind}; "
                    f"'{first[kind]}' is one",
                )
            else:
                first[kind] = resource["id"]
