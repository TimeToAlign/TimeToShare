"""Named-timestamp rules: the timeline a timestamp names and its coordinate."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from ..manifest import _exact, spell
from .diagnostics import SchemaValidationError, timelines_by_id, timestamps_of


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
