"""The fixtures of flow control, FlowMaps and virtual timelines (``flow/``).

Each builder returns a named manifest of one root. The expected flows under
``fixtures/flows/<version>/`` and their traces name the flow-control
elements by ID, so every builder states those IDs; the atomic sections and
FlowMaps of ``sonata_exposition`` are computed by the library, which mints
theirs.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from timetoalign import (
    AlignmentBundle,
    ContinuousLogicalTimeline,
    ContinuousPhysicalTimeline,
    Timeline,
)
from timetoalign.core import Gap
from timetoalign.core.provenance import Belief, Provenance
from timetoalign.timelines.flowcontrol import (
    Barline,
    Break,
    DestinationReference,
    FlowCondition,
    Jump,
    JumpDestination,
    JumpTarget,
    SectionBreak,
)

from . import parts

EDITOR = "https://example.org/people/editor"
"""The actor who writes by hand and holds the beliefs of these fixtures."""
DAY = "2026-11-25"
"""The day of every dated entry and belief of these fixtures."""


def _manifest(name: str, root: Timeline) -> AlignmentBundle:
    """Return the manifest ``name`` of the one root ``root``, given no id."""
    bundle = AlignmentBundle(name=name)
    bundle.add_timeline(root)
    return bundle


def _score(length: int) -> Timeline:
    """Return the root ``score`` ("Score") of ``length`` quarters."""
    return parts.named(ContinuousLogicalTimeline, "score", "Score", Fraction(length))


def _after(jump: str) -> FlowCondition:
    """Return the condition that holds once the one destination of ``jump``
    has been taken.
    """
    return FlowCondition(after=DestinationReference(jump=jump))


def _leap(manifestation: str, **members: Any) -> JumpDestination:
    """Return a da capo or dal segno, taken once without restoring repeats."""
    return JumpDestination(
        repeat_count=1, reset=False, manifestation=manifestation, **members
    )


def _by_hand() -> Provenance:
    """Return the entry of what the editor wrote by hand and believes."""
    return Provenance(
        method="manual",
        stated_by=(EDITOR,),
        date=DAY,
        beliefs=(Belief(actor=EDITOR, belief="true", date=DAY),),
    )


def sonata_exposition() -> AlignmentBundle:
    """Build ``sonata_exposition``: two volta brackets and their computed flows.

    The score (24 quarters) holds the jump ``jump_1`` at 12, before the
    brackets, with the destinations ``by`` 0 on pass 1 and to
    ``jump_target_1`` on pass 2, and at 16, between the brackets, the break
    ``break_1``, the first bracket's repeat sign ``jump_2`` (a repeat end
    taken once, without a place) and the second bracket's start
    ``jump_target_1``. The library computes the rest from them: the three
    atomic sections as regions "A", "B" and "C" typed ``tts:AtomicSection``,
    and the FlowMaps of the conventions ``default``, ``single`` and
    ``printed``, each with a provenance entry of the method ``inferred``.
    The virtual timeline ``virtual_1`` ("Score, as played") states that the
    ``default`` FlowMap was applied, 36 quarters.
    """
    score = _score(24)
    flow, at = score.flow_control, score.make_coordinate
    second = flow.add(JumpTarget(at(16), manifestation="volta", id="jump_target_1"))
    flow.add(
        Jump(
            at(12),
            [
                JumpDestination(by=0, passes=[1], manifestation="volta"),
                JumpDestination(to=second.id, passes=[2], manifestation="volta"),
            ],
            id="jump_1",
        )
    )
    flow.add(Break(at(16), manifestation="volta", id="break_1"))
    flow.add(
        Jump(
            at(16),
            [JumpDestination(repeat_count=1, manifestation="repeat_end")],
            id="jump_2",
        )
    )
    computed = score.create_flow_maps_from_flow_control()
    if computed is None or computed.findings:
        raise SystemExit(f"sonata_exposition: the flows computed are {computed!r}")
    played = next(
        flow_map for flow_map in computed.flow_maps if flow_map.convention == "default"
    )
    score.create_virtual_timeline(played, id="virtual_1", name="Score, as played")
    return _manifest("Sonata exposition", score)


def dal_segno_al_coda() -> AlignmentBundle:
    """Build ``dal_segno_al_coda``: a To Coda that waits for the dal segno.

    The score (32 quarters) holds the segno ``jump_target_1`` at 4, the jump
    ``jump_1`` ("To Coda") at 12, whose destination to the coda
    ``jump_target_2`` at 24 holds ``after`` the dal segno al coda, and the
    jump ``jump_2`` ("D.S. al Coda") at 24 back to the segno.
    """
    score = _score(32)
    flow, at = score.flow_control, score.make_coordinate
    segno = flow.add(JumpTarget(at(4), manifestation="segno", id="jump_target_1"))
    coda = flow.add(JumpTarget(at(24), manifestation="coda", id="jump_target_2"))
    dal_segno = flow.add(
        Jump(
            at(24),
            [_leap("dal_segno_al_coda", to=segno.id)],
            label="D.S. al Coda",
            id="jump_2",
        )
    )
    flow.add(
        Jump(
            at(12),
            [
                JumpDestination(
                    to=coda.id,
                    after=DestinationReference(jump=dal_segno.id),
                    manifestation="to_coda",
                )
            ],
            label="To Coda",
            id="jump_1",
        )
    )
    return _manifest("Dal segno al coda", score)


def da_capo_al_fine() -> AlignmentBundle:
    """Build ``da_capo_al_fine``: a Fine that ends the flow after the da capo.

    The score (16 quarters) holds the jump ``jump_1`` ("D.C. al Fine") at
    16, a da capo al fine without a place, and the break ``break_1``
    ("Fine") at 8, whose ``ends.after`` names it.
    """
    score = _score(16)
    flow, at = score.flow_control, score.make_coordinate
    da_capo = flow.add(
        Jump(at(16), [_leap("da_capo_al_fine")], label="D.C. al Fine", id="jump_1")
    )
    flow.add(
        Break(
            at(8),
            manifestation="fine",
            ends=_after(da_capo.id),
            label="Fine",
            id="break_1",
        )
    )
    return _manifest("Da capo al fine", score)


def repeat_end_and_dal_segno() -> AlignmentBundle:
    """Build ``repeat_end_and_dal_segno``: two signs on one barline.

    The score (24 quarters) holds the repeat start ``jump_target_1`` at 4,
    the segno ``jump_target_2`` at 8 and one jump, ``jump_1`` at 16, with
    two destinations: a repeat end to the repeat start, and a dal segno
    labelled "D.S." to the segno.
    """
    score = _score(24)
    flow, at = score.flow_control, score.make_coordinate
    start = flow.add(
        JumpTarget(at(4), manifestation="repeat_start", id="jump_target_1")
    )
    segno = flow.add(JumpTarget(at(8), manifestation="segno", id="jump_target_2"))
    flow.add(
        Jump(
            at(16),
            [
                JumpDestination(
                    to=start.id, repeat_count=1, manifestation="repeat_end"
                ),
                _leap("dal_segno", to=segno.id, label="D.S."),
            ],
            id="jump_1",
        )
    )
    return _manifest("Repeat end and dal segno on one barline", score)


def volta_passes() -> AlignmentBundle:
    """Build ``volta_passes``: brackets for the passes 1 and 3, and 2.

    The score (16 quarters) holds the jump ``jump_1`` at 8, before the
    brackets, with the destinations ``by`` 0 on the passes 1 and 3 and to
    ``jump_target_1`` on pass 2; at 12, between the brackets, the break
    ``break_1``, the first bracket's repeat sign ``jump_2``, the second
    bracket's start ``jump_target_1`` and the Fine ``break_2``, whose
    ``ends.after`` names the repeat sign ``jump_3`` at 16, which closes the
    second bracket and does not restore (``reset`` false).
    """
    score = _score(16)
    flow, at = score.flow_control, score.make_coordinate
    second = flow.add(JumpTarget(at(12), manifestation="volta", id="jump_target_1"))
    flow.add(
        Jump(
            at(8),
            [
                JumpDestination(by=0, passes=[1, 3], manifestation="volta"),
                JumpDestination(to=second.id, passes=[2], manifestation="volta"),
            ],
            id="jump_1",
        )
    )
    flow.add(Break(at(12), manifestation="volta", id="break_1"))
    flow.add(
        Jump(
            at(12),
            [JumpDestination(repeat_count=1, manifestation="repeat_end")],
            id="jump_2",
        )
    )
    closing = flow.add(
        Jump(
            at(16),
            [JumpDestination(repeat_count=1, reset=False, manifestation="repeat_end")],
            id="jump_3",
        )
    )
    flow.add(Break(at(12), manifestation="fine", ends=_after(closing.id), id="break_2"))
    return _manifest("Volta brackets 1, 3 and 2", score)


def ossia() -> AlignmentBundle:
    """Build ``ossia``: a choice nobody can check, laid out after the main text.

    The score (24 quarters) holds the child ``ossia`` ("Ossia", 8 quarters)
    at 16. The jump ``jump_1`` at 4 goes on (``by`` 0) or, ``determined``
    false, to the child; the break ``break_1`` at 16 ends the main text; the
    jump ``jump_2`` at 24 leads back to the jump target ``jump_target_1`` at
    12.
    """
    score = _score(24)
    child = parts.holding(
        score,
        parts.named(ContinuousLogicalTimeline, "ossia", "Ossia", Fraction(8)),
        Fraction(16),
    )
    flow, at = score.flow_control, score.make_coordinate
    flow.add(
        Jump(
            at(4),
            [
                JumpDestination(by=0),
                JumpDestination(to=child.id, determined=False, manifestation="ossia"),
            ],
            id="jump_1",
        )
    )
    back = flow.add(JumpTarget(at(12), manifestation="ossia", id="jump_target_1"))
    flow.add(Break(at(16), id="break_1"))
    flow.add(
        Jump(
            at(24),
            [JumpDestination(to=back.id, manifestation="ossia")],
            id="jump_2",
        )
    )
    return _manifest("Ossia", score)


def sections() -> AlignmentBundle:
    """Build ``sections``: two sections, each with a da capo of its own.

    The score (32 quarters) holds the section break ``section_break_1``,
    without a manifestation, at 16. The first section has a da capo al fine,
    the jump ``jump_1`` ("D.C. al Fine") at 16 and the break ``break_1``
    ("Fine") at 8 whose ``ends.after`` names it; the second a da capo, the
    jump ``jump_2`` ("D.C.") at 32. Neither da capo has a place, so the
    second goes back to the section break.
    """
    score = _score(32)
    flow, at = score.flow_control, score.make_coordinate
    first = flow.add(
        Jump(at(16), [_leap("da_capo_al_fine")], label="D.C. al Fine", id="jump_1")
    )
    flow.add(
        Break(
            at(8),
            manifestation="fine",
            ends=_after(first.id),
            label="Fine",
            id="break_1",
        )
    )
    flow.add(SectionBreak(at(16), id="section_break_1"))
    flow.add(Jump(at(32), [_leap("da_capo")], label="D.C.", id="jump_2"))
    return _manifest("Two sections", score)


def loop() -> AlignmentBundle:
    """Build ``loop``: a loop on a seconds axis, without a manifestation.

    The take ``take`` ("Take", 10.0 seconds) holds the jump target
    ``jump_target_1`` at 2.0 and the jump ``jump_1`` at 6.0 back to it,
    taken 127 times.
    """
    take = parts.named(ContinuousPhysicalTimeline, "take", "Take", 10.0)
    flow, at = take.flow_control, take.make_coordinate
    start = flow.add(JumpTarget(at(2.0), id="jump_target_1"))
    flow.add(
        Jump(at(6.0), [JumpDestination(to=start.id, repeat_count=127)], id="jump_1")
    )
    return _manifest("Loop", take)


def flow_map_by_hand() -> AlignmentBundle:
    """Build ``flow_map_by_hand``: a FlowMap written by hand, no flow control.

    The set ``set`` ("Set", 20 quarters) holds the children ``first``
    ("First piece", 8 quarters at 0) and ``second`` ("Second piece", 12
    quarters at 8). The FlowMap ``flow_map_1`` ("Encore order") plays
    ``second``, a gap of 4 quarters and ``first``; it states no convention,
    and its provenance entry is the editor's, by hand and believed true.
    """
    whole = parts.named(ContinuousLogicalTimeline, "set", "Set", Fraction(20))
    first = parts.holding(
        whole,
        parts.named(ContinuousLogicalTimeline, "first", "First piece", Fraction(8)),
        Fraction(0),
    )
    second = parts.holding(
        whole,
        parts.named(ContinuousLogicalTimeline, "second", "Second piece", Fraction(12)),
        Fraction(8),
    )
    whole.create_flow_map(
        [second, Gap(Fraction(4)), first],
        id="flow_map_1",
        name="Encore order",
        provenance=[_by_hand()],
    )
    return _manifest("Set list", whole)


def repairs() -> AlignmentBundle:
    """Build ``repairs``: a rejected jump and its replacement at one coordinate.

    The score (16 quarters) is read from an import that gave the double
    barline ``barline_1`` at 8 and the repeat end ``jump_1`` at 16 back to
    the start, each with a provenance entry of the method ``imported``. The
    editor rejects the jump (the belief ``false``, with a note) and adds by
    hand the repeat start ``jump_target_1`` at 8 and the repeat end
    ``jump_2`` at 16 to it.
    """
    score = _score(16)
    flow, at = score.flow_control, score.make_coordinate
    imported = Provenance(method="imported")
    flow.add(
        Barline(
            at(8), manifestation="double_barline", provenance=imported, id="barline_1"
        )
    )
    wrong = flow.add(
        Jump(
            at(16),
            [JumpDestination(repeat_count=1, manifestation="repeat_end")],
            provenance=imported,
            id="jump_1",
        )
    )
    flow.with_belief(
        wrong.id,
        EDITOR,
        "false",
        date=DAY,
        note="The repeat begins at the double barline.",
    )
    start = flow.add(
        JumpTarget(
            at(8),
            manifestation="repeat_start",
            provenance=_by_hand(),
            id="jump_target_1",
        )
    )
    flow.add(
        Jump(
            at(16),
            [JumpDestination(to=start.id, repeat_count=1, manifestation="repeat_end")],
            provenance=_by_hand(),
            id="jump_2",
        )
    )
    return _manifest("Repairs", score)
