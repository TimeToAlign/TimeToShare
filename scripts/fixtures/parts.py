"""The construction helpers the timeline, group and bundle builders share."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from timetoalign import (
    ContinuousLogicalTimeline,
    ContinuousPhysicalTimeline,
    DiscreteGraphicalTimeline,
    DiscreteLogicalTimeline,
    DiscretePhysicalTimeline,
    Timeline,
)
from timetoalign.maps import (
    QuartersToTicks,
    SamplesToSeconds,
    ScalarMap,
    SecondsToSamples,
)
from timetoalign.timelines.flowcontrol import Jump, JumpDestination

TILIA = "bruckner5_scherzo/harnoncourt/Bruckner5_Scherzo.json"

"""The TiLiA export, in the ``score`` corpus, whose group and bundle are emitted."""


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


def leap(
    timeline: Timeline,
    manifestation: str,
    *,
    to: str | None = None,
    label: str | None = None,
) -> JumpDestination:
    """Return the destination of a da capo or dal segno of ``timeline``.

    A leap is taken once and does not restore the repeats it goes back over
    (``repeat_count`` 1, ``reset`` false). It goes back to the jump target
    ``to``, or to the start of ``timeline``, which it then names itself.
    """
    return JumpDestination(
        to=timeline.id if to is None else to,
        repeat_count=1,
        reset=False,
        manifestation=manifestation,
        label=label,
    )


def repeat_end(
    timeline: Timeline, *, to: str | None = None, count: int = 1
) -> JumpDestination:
    """Return a repeat end labelled "Repeat", taken ``count`` times.

    It goes back to the jump target ``to``, or to the start of ``timeline``,
    which it then names itself.
    """
    return JumpDestination(
        to=timeline.id if to is None else to,
        repeat_count=count,
        manifestation="repeat_end",
        label="Repeat",
    )


def with_repeat(timeline: Timeline, source: Any) -> Timeline:
    """Give ``timeline`` a jump at ``source`` back to its start.

    The jump, its id minted, holds one destination: a repeat end taken once
    (``repeat_count`` 1), labelled "Repeat", naming the timeline itself.
    """
    timeline.flow_control.add(
        Jump(timeline.make_coordinate(source), [repeat_end(timeline)])
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


def score_with_second_half() -> Timeline:
    """Build the score ``score`` ("Score", 8 quarters) holding the child
    ``second-half`` ("Second half", 4 quarters at 4)."""
    score = named(ContinuousLogicalTimeline, "score", "Score", Fraction(8))
    holding(
        score,
        named(ContinuousLogicalTimeline, "second-half", "Second half", Fraction(4)),
        Fraction(4),
    )
    return score
