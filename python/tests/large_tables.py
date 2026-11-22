"""Large valid tables, built for the comparison and the timing of the table checks."""

from __future__ import annotations

from typing import Any

import pyarrow as pa

from timetoshare import with_file_ids
from timetoshare.tables import MATCH_CLAIM_SCHEMA, PROJECTION_SCHEMA

ACTOR = "https://orcid.org/0000-0002-1825-0097"
BELIEF_WORDS = ("true", "unlikely", "false")


def large_manifest(rows: int) -> dict[str, Any]:
    """The two timelines of :func:`many_claims`, in the file form."""
    return with_file_ids(
        {
            "timetoshare": "0.2.0",
            "timelines": [
                {"id": "clt_1", "unit": "quarters", "length": [rows, 1]},
                {"id": "dpt_1", "unit": "samples", "length": rows * 22050},
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
    (``k % 10 == 0``) an interval ending one step later. With
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
        data["event_a_id"].append(f"note_{k + 1}")
        data["event_a_name"].append(None)
        data["event_b_id"].append(None if nomatch else f"projection_{k + 1}")
        data["event_b_name"].append(None)
        data["id"].append(f"claim_{k + 1}")
    return pa.table(
        [pa.array(data[field.name], type=field.type) for field in MATCH_CLAIM_SCHEMA],
        schema=MATCH_CLAIM_SCHEMA,
    )


def many_projections(rows: int = 250_000) -> pa.Table:
    """A valid Projections table of ``rows`` rows: Projection ``k`` (from 0)
    stands on ``dpt_1`` at the sample ``22050 k`` for ``note_<k+1>`` of
    ``clt_1``, every tenth lasting 22050 samples."""
    data: dict[str, list[Any]] = {name: [] for name in PROJECTION_SCHEMA.names}
    for k in range(rows):
        data["id"].append(f"projection_{k + 1}")
        data["timeline_id"].append("dpt_1")
        data["unit"].append("samples")
        data["number_type"].append("int")
        data["start"].append(
            {"numerator": k * 22050, "denominator": None, "value": None}
        )
        data["duration"].append(
            {"numerator": 22050, "denominator": None, "value": None}
            if k % 10 == 0
            else None
        )
        data["projection_of"].append(
            {"timeline_id": "clt_1", "event_id": f"note_{k + 1}"}
        )
    return pa.table(
        [pa.array(data[field.name], type=field.type) for field in PROJECTION_SCHEMA],
        schema=PROJECTION_SCHEMA,
    )
