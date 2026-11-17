"""The construction helpers the timeline, group and bundle builders share."""

from __future__ import annotations

import datetime
from fractions import Fraction
from typing import Any

from timetoalign import (
    Assertion,
    ContinuousLogicalTimeline,
    ContinuousPhysicalTimeline,
    DiscreteGraphicalTimeline,
    DiscreteLogicalTimeline,
    DiscretePhysicalTimeline,
    Link,
    PartSlot,
    Timeline,
)
from timetoalign.core import FlowControlElement
from timetoalign.maps import (
    QuartersToTicks,
    SamplesToSeconds,
    ScalarMap,
    SecondsToSamples,
)
from timetoalign.timelines.flowcontrol import Jump

TILIA = "bruckner5_scherzo/harnoncourt/Bruckner5_Scherzo.json"

"""The TiLiA export, in the ``score`` corpus, whose group and bundle are emitted."""

OP_106_WORK = "https://musicbrainz.org/work/4a622b0d-b0c0-405e-b49e-05b70c108284"
"""The MusicBrainz page of Beethoven's Piano Sonata No. 29, Op. 106."""

OP_106_LABEL = "Piano Sonata No. 29 in B♭ major, Op. 106"
"""The label of the links to Op. 106."""

OP_106_MOVEMENTS = (
    ("80cbaf7b-a1da-3fc5-b650-6eb72a803980", "I. Allegro"),
    ("7813c9cf-6054-3ef3-b9ed-8ae4690581c9", "II. Scherzo. Assai vivace"),
    ("7d110747-f011-41d4-9ce5-a1fad9abed2f", "III. Adagio sostenuto"),
    (
        "cfa82cd6-bcb5-39dd-9beb-c98e275c7c84",
        "IV. Introduzione. Largo – Allegro risoluto",
    ),
)
"""The MusicBrainz work IDs and labels of the four movements of Op. 106."""

EDITOR = Assertion(
    asserted_by=("https://example.org/people/editor",),
    asserted_on=datetime.date(2026, 11, 17),
    method="manual",
    status="confirmed",
)
"""The editor's assertion of the links of the description fixtures."""


def movement(index: int) -> str:
    """Return the URL of the MusicBrainz page of movement ``index`` of Op. 106."""
    return f"https://musicbrainz.org/work/{OP_106_MOVEMENTS[index][0]}"


def op_106(
    *urls: str,
    slots: list[PartSlot],
    assertion: Assertion | None = EDITOR,
    **options: Any,
) -> Link:
    """Return a link to Op. 106 from ``urls``, its four movements as ``slots``.

    The link is labelled with ``OP_106_LABEL``, its reading has the parts
    ``slots`` (``has_part``), and the ``options`` are those of
    ``Link.from_urls``.
    """
    return Link.from_urls(
        *urls, label=OP_106_LABEL, assertion=assertion, **options
    ).with_parts("has_part", slots)


def ticks(uid: str | None = None) -> QuartersToTicks:
    """Return a map of quarters to ticks, 480 per quarter, its id ``uid`` or
    minted.
    """
    return QuartersToTicks(ppq=480, uid=uid)


def tempo(uid: str | None = None) -> ScalarMap:
    """Return a tempo map of quarters to seconds, half a second per quarter, its
    id ``uid`` or minted.
    """
    return ScalarMap(
        Fraction(1, 2), source_unit="quarters", target_unit="seconds", uid=uid
    )


def to_samples() -> SecondsToSamples:
    """Return a map of seconds to samples, 44100 per second, its id minted."""
    return SecondsToSamples(sample_rate=44100)


def to_seconds() -> SamplesToSeconds:
    """Return a map of samples to seconds, 44100 per second, its id minted."""
    return SamplesToSeconds(sample_rate=44100)


def to_points() -> ScalarMap:
    """Return a map of pixels to points, 3/4 of a point each, its id minted."""
    return ScalarMap(Fraction(3, 4), source_unit="pixels", target_unit="points")


def with_maps(timeline: Timeline, *maps: Any) -> Timeline:
    """Attach ``maps`` to ``timeline`` in order and return the timeline."""
    for conversion_map in maps:
        timeline.add_conversion_map(conversion_map)
    return timeline


def with_repeat(timeline: Timeline, source: Any, destination: Any) -> Timeline:
    """Give ``timeline`` a jump from ``source`` back to ``destination``.

    The jump is a repeat end taken once (``repeat_count`` 1), labelled
    "Repeat", its id minted.
    """
    timeline.flow_control.add_jump(
        Jump(
            from_coordinate=timeline.make_coordinate(source),
            to_coordinate=timeline.make_coordinate(destination),
            control_type=FlowControlElement.repeat_end,
            repeat_count=1,
            label="Repeat",
        )
    )
    return timeline


def with_region(timeline: Timeline, start: Any, end: Any, uid: str) -> Timeline:
    """Give ``timeline`` the region ``uid`` from ``start`` to ``end``."""
    timeline.create_region(start, end, id=uid)
    return timeline


def named(cls: type[Timeline], uid: str, name: str, length: Any) -> Timeline:
    """Build an unlocked timeline of ``cls`` in its domain's usual unit."""
    unit = {
        ContinuousLogicalTimeline: "quarters",
        ContinuousPhysicalTimeline: "seconds",
        DiscreteLogicalTimeline: "ticks",
        DiscretePhysicalTimeline: "samples",
        DiscreteGraphicalTimeline: "pixels",
    }[cls]
    return cls(length=length, unit=unit, uid=uid, name=name)


def quarters(uid: str, length: Any, **keywords: Any) -> Timeline:
    """Build an unnamed timeline of quarters; a length of None is unknown."""
    return ContinuousLogicalTimeline(
        length=length, unit="quarters", uid=uid, **keywords
    )


def holding(parent: Timeline, child: Timeline, offset: Any) -> Timeline:
    """Add ``child`` to ``parent`` at ``offset`` and return the child."""
    parent.add_child(child, offset)
    return child
