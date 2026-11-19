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
    """Build ``op106_work``, Beethoven's Piano Sonata No. 29, Op. 106.

    The bundle ``op106`` ("Beethoven, Piano Sonata No. 29, Op. 106") holds
    five roots side by side, none nesting another: the work ``clt_1``
    ("Op. 106") of unknown length and its four movements ``clt_2`` ("I.
    Allegro", 1645 quarters), ``clt_3`` ("II. Scherzo. Assai vivace", 510),
    ``clt_4`` ("III. Adagio sostenuto", 561) and ``clt_5`` ("IV.
    Introduzione. Largo – Allegro risoluto", 9911/8). The statements say
    what the work is, who composed it, its catalogue number and the parts
    MusicBrainz lists; how the movements lie in time is not stated.
    """
    bundle = AlignmentBundle(id="op106", name="Beethoven, Piano Sonata No. 29, Op. 106")
    bundle.add_timeline(
        ContinuousLogicalTimeline(
            length=None, unit="quarters", uid="clt_1", name="Op. 106"
        )
    )
    for uid, name, length in (
        ("clt_2", "I. Allegro", Fraction(1645)),
        ("clt_3", "II. Scherzo. Assai vivace", Fraction(510)),
        ("clt_4", "III. Adagio sostenuto", Fraction(561)),
        ("clt_5", "IV. Introduzione. Largo – Allegro risoluto", Fraction(9911, 8)),
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
    """Build ``djset_segment``, a DJ set and one segment of it.

    The bundle ``moriero_halloween_xxl_2025`` ("Samuel Moriero, Impact
    Halloween XXL 2025 (full set)") holds the set ``cpt_1`` ("the set",
    5277.0 seconds) with the segment ``cpt_2`` ("HUMBLE. (Skrillex Remix /
    Samuel Moriero Remix)", 91.0 seconds) at 437.0.
    """
    the_set = parts.named(ContinuousPhysicalTimeline, "cpt_1", "the set", 5277.0)
    the_set.add_child(
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
    return bundle.add_timeline(the_set)


def nielsen_record() -> AlignmentBundle:
    """Build ``nielsen_record``, a catalogue record of a song and its sources.

    The bundle ``cnw0133`` ("Carl Nielsen, Hr. Olufs Sang (CNW 133)") holds
    the version ``clt_1`` (quarters, of unknown length) and the two sources
    ``cgt_1`` ("Score, print (Wilhelm Hansen, 1906)") and ``cgt_2`` ("Score,
    autograph, printer's manuscript"), millimeters of unknown length, which
    no scan gives a length yet. No timeline nests another: work, version and
    sources are related by statements alone.
    """
    bundle = AlignmentBundle(
        id="cnw0133", name="Carl Nielsen, Hr. Olufs Sang (CNW 133)"
    )
    bundle.add_timeline(
        ContinuousLogicalTimeline(length=None, unit="quarters", uid="clt_1")
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
