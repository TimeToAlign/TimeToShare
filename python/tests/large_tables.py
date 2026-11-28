"""Large valid tables, built for the comparison and the timing of the table checks."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pyarrow as pa

from timetoshare import with_file_ids
from timetoshare.tables import (
    CHUNK_SENTINEL,
    MATCH_CLAIM_SCHEMA,
    NOMATCH_SENTINEL,
)

ACTOR = "https://orcid.org/0000-0002-1825-0097"
BELIEF_WORDS = ("true", "unlikely", "false")


BAD_TIMELINES: tuple[dict[str, Any], ...] = (
    {"unit": "furlongs", "length": 1},
    {"length": 1},
    {"unit": 5, "number_type": "int", "length": 1},
    {"unit": "samples", "number_type": 7, "length": 1},
    {"unit": None, "number_type": "int", "length": 1},
    {"unit": ["samples"], "number_type": "int", "length": 1},
)
"""Timelines a manifest that was never validated may hold, without ``id``:
a unit that is none, no unit, a unit or number type that is no string, a
null unit."""


def large_manifest(rows: int, unused: Sequence[dict[str, Any]] = ()) -> dict[str, Any]:
    """The two timelines of :func:`many_claims`, in the file form, followed
    by the ``unused`` timelines, which no row names, as ``unused_1``, … ."""
    return with_file_ids(
        {
            "timetoshare": "0.2.0",
            "timelines": [
                {"id": "clt_1", "unit": "quarters", "length": [rows, 1]},
                {"id": "dpt_1", "unit": "samples", "length": rows * 22050},
                *(
                    {**timeline, "id": f"unused_{index}"}
                    for index, timeline in enumerate(unused, 1)
                ),
            ],
        }
    )


def _quarter(numerator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": 2,
        "value": None,
        "unit": "quarters",
        "number_type": "fraction",
    }


def _sample(numerator: int) -> dict[str, Any]:
    return {
        "numerator": numerator * 22050,
        "denominator": None,
        "value": None,
        "unit": "samples",
        "number_type": "int",
    }


def _anchor(k: int) -> dict[str, Any]:
    return {"coordinate_a": _quarter(k), "coordinate_b": _sample(k)}


def _provenance(k: int) -> dict[str, Any]:
    """One of 84 entries: three belief words by 28 days."""
    return {
        "stated_by": [ACTOR],
        "date": "2026-11-20",
        "method": "manual",
        "service": None,
        "basis": None,
        "match": None,
        "note": None,
        "beliefs": [
            {
                "actor": ACTOR,
                "belief": BELIEF_WORDS[k % 3],
                "date": f"2026-11-{1 + k % 28:02d}",
                "note": None,
            }
        ],
    }


def many_claims(rows: int = 250_000, provenance: bool = False) -> pa.Table:
    """A valid MatchClaim table of ``rows`` rows over ``clt_1`` and ``dpt_1``.

    Row ``k`` (from 0) claims ``note_<k+1>`` and ``projection_<k+1>``: every
    50th row (``k % 50 == 49``) is a NOMATCH, every 100th (``k % 100 == 98``)
    a conceptual MatchClaim, every other row synchronous with its start
    anchor at the quarter ``k/2`` and the sample ``22050 k``, and every tenth
    (``k % 10 == 0``) an interval ending one step later. Among the
    synchronous rows, every 50th (``k % 50 == 20``, an interval) is CHUNK on
    its sample side, every 100th (``k % 100 == 37``) CHUNK on its quarter
    side and every 100th (``k % 100 == 73``) CHUNK on both sides. With
    ``provenance``, every row holds one of 84 provenance entries.
    """
    data: dict[str, list[Any]] = {name: [] for name in MATCH_CLAIM_SCHEMA.names}
    for k in range(rows):
        nomatch = k % 50 == 49
        conceptual = k % 100 == 98
        synchronous = not (nomatch or conceptual)
        data["timeline_a_id"].append("clt_1")
        data["timeline_b_id"].append("dpt_1")
        data["start_anchor"].append(_anchor(k) if synchronous else None)
        data["end_anchor"].append(
            _anchor(k + 1) if synchronous and k % 10 == 0 else None
        )
        data["is_synchronous"].append(synchronous)
        data["provenance"].append(_provenance(k) if provenance else None)
        data["certainty"].append(1.0)
        chunk_a = k % 100 in (37, 73)
        chunk_b = k % 50 == 20 or k % 100 == 73
        data["event_a_id"].append(CHUNK_SENTINEL if chunk_a else f"note_{k + 1}")
        data["event_a_name"].append(None)
        data["event_b_id"].append(
            NOMATCH_SENTINEL
            if nomatch
            else CHUNK_SENTINEL
            if chunk_b
            else f"projection_{k + 1}"
        )
        data["event_b_name"].append(None)
        data["id"].append(f"claim_{k + 1}")
    return pa.table(
        [pa.array(data[field.name], type=field.type) for field in MATCH_CLAIM_SCHEMA],
        schema=MATCH_CLAIM_SCHEMA,
    )
