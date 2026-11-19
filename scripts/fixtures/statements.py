"""Builders for the fixtures that carry statements: the structure of each bundle.

Each builder builds only the timelines, groups and conversion maps of its
bundle; the statements and the provenance of the bundle and of its elements
come from ``descriptions/<name>.yaml`` and are attached when the manifest is
composed (``plan._compose``).
"""

from __future__ import annotations

from fractions import Fraction

from timetoalign import (
    AlignmentBundle,
    ContinuousGraphicalTimeline,
    ContinuousLogicalTimeline,
    ContinuousPhysicalTimeline,
    DiscretePhysicalTimeline,
)
from timetoalign.maps import SamplesToSeconds

from . import parts


def op106_work() -> AlignmentBundle:
    """Build ``op106_work``, sources of Beethoven's Piano Sonata No. 29, Op. 106.

    The bundle ``op106`` ("Beethoven, Piano Sonata No. 29, Op. 106") holds
    five roots side by side, none nesting another: the first edition
    ``clt_1`` ("Op. 106, first edition (Vienna: Artaria, 1819)") of unknown
    length and the Humdrum encodings of the four movements, whose written
    lengths (both endings counted) give the lengths: ``clt_2`` ("I. Allegro
    (sonata29-1.krn)", 1645 quarters), ``clt_3`` ("II. Scherzo. Assai vivace
    (sonata29-2.krn)", 510), ``clt_4`` ("III. Adagio sostenuto
    (sonata29-3.krn)", 561) and ``clt_5`` ("IV. Introduzione. Largo –
    Allegro risoluto (sonata29-4.krn)", 9911/8). The statements name the
    sonata as what the bundle is about, the edition as an example of it and
    each encoding as an example of its movement; how the timelines lie in
    time is not stated.
    """
    bundle = AlignmentBundle(id="op106", name="Beethoven, Piano Sonata No. 29, Op. 106")
    bundle.add_timeline(
        ContinuousLogicalTimeline(
            length=None,
            unit="quarters",
            uid="clt_1",
            name="Op. 106, first edition (Vienna: Artaria, 1819)",
        )
    )
    for uid, name, length in (
        ("clt_2", "I. Allegro (sonata29-1.krn)", Fraction(1645)),
        ("clt_3", "II. Scherzo. Assai vivace (sonata29-2.krn)", Fraction(510)),
        ("clt_4", "III. Adagio sostenuto (sonata29-3.krn)", Fraction(561)),
        (
            "clt_5",
            "IV. Introduzione. Largo – Allegro risoluto (sonata29-4.krn)",
            Fraction(9911, 8),
        ),
    ):
        bundle.add_timeline(parts.named(ContinuousLogicalTimeline, uid, name, length))
    return bundle


def layerit_recording() -> AlignmentBundle:
    """Build ``layerit_recording``, a score encoding and a filmed performance.

    The bundle ``layerit_clair_de_lune`` ("LayerIt, Clair de lune mm. 1–6
    (Pires)") holds the MEI encoding ``clt_6`` ("Clair de lune, mm. 1–6
    (MEI)", 27 quarters); the video ``cpt_1`` ("C.Debussy - Clair de Lune,
    Maria João Pires live at Jardin Musical", seconds, of unknown length)
    with the stretch ``cpt_2`` (33.353016 seconds) at 0.0; and the audio file
    ``dpt_1`` ("ClairDeLune_MariaJoaoPires_untilM6.wav", 1470868 samples)
    with the map ``cmap_1`` of samples to seconds at 44100 per second. The
    group ``group_1`` ("recording") aligns ``cpt_2`` with ``dpt_1``.
    """
    encoding = parts.named(
        ContinuousLogicalTimeline, "clt_6", "Clair de lune, mm. 1–6 (MEI)", Fraction(27)
    )
    video = ContinuousPhysicalTimeline(
        length=None,
        unit="seconds",
        uid="cpt_1",
        name="C.Debussy - Clair de Lune, Maria João Pires live at Jardin Musical",
    )
    stretch = ContinuousPhysicalTimeline(length=33.353016, unit="seconds", uid="cpt_2")
    video.add_child(stretch, 0.0)
    audio = parts.with_maps(
        parts.named(
            DiscretePhysicalTimeline,
            "dpt_1",
            "ClairDeLune_MariaJoaoPires_untilM6.wav",
            Fraction(1470868),
        ),
        SamplesToSeconds(sample_rate=44100, uid="cmap_1"),
    )
    bundle = AlignmentBundle(
        id="layerit_clair_de_lune", name="LayerIt, Clair de lune mm. 1–6 (Pires)"
    )
    bundle.add_timeline(encoding)
    bundle.add_timeline(stretch, as_group="recording")
    bundle.add_timeline(audio, grouped_with=stretch.id)
    return bundle


def djset_segment() -> AlignmentBundle:
    """Build ``djset_segment``, the recording of a DJ set and one segment of it.

    The bundle ``moriero_halloween_xxl_2025`` ("Samuel Moriero, Impact
    Halloween XXL 2025 (full set)") holds the recording of the set ``cpt_1``
    ("the set's recording", 5277.0 seconds) with the segment ``cpt_2``
    ("HUMBLE. (Skrillex Remix / Samuel Moriero Remix)", 91.0 seconds) at
    437.0. The set itself, a work of its own, has no time axis apart from its
    recording and is named by the statements alone.
    """
    recording = parts.named(
        ContinuousPhysicalTimeline, "cpt_1", "the set's recording", 5277.0
    )
    recording.add_child(
        parts.named(
            ContinuousPhysicalTimeline,
            "cpt_2",
            "HUMBLE. (Skrillex Remix / Samuel Moriero Remix)",
            91.0,
        ),
        437.0,
    )
    bundle = AlignmentBundle(
        id="moriero_halloween_xxl_2025",
        name="Samuel Moriero, Impact Halloween XXL 2025 (full set)",
    )
    return bundle.add_timeline(recording)


def nielsen_record() -> AlignmentBundle:
    """Build ``nielsen_record``, a catalogue record of a song and its sources.

    The bundle ``cnw0133`` ("Carl Nielsen, Hr. Olufs Sang (CNW 133)") holds
    the two sources ``cgt_1`` ("Score, print (Wilhelm Hansen, 1906)") and
    ``cgt_2`` ("Score, autograph, printer's manuscript"), millimeters of
    unknown length, which no scan gives a length yet. No timeline nests
    another; the work and its version have no time axis of their own and are
    named by the statements alone.
    """
    bundle = AlignmentBundle(
        id="cnw0133", name="Carl Nielsen, Hr. Olufs Sang (CNW 133)"
    )
    for uid, name in (
        ("cgt_1", "Score, print (Wilhelm Hansen, 1906)"),
        ("cgt_2", "Score, autograph, printer's manuscript"),
    ):
        bundle.add_timeline(
            ContinuousGraphicalTimeline(
                length=None, unit="millimeters", uid=uid, name=name
            )
        )
    return bundle
