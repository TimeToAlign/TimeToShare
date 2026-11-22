"""The table checks read columns and find what the reading row by row found
(see "The table checks read columns, not rows" in README.md)."""

from __future__ import annotations

import copy
import json
import math
import random
from collections import Counter
from collections.abc import Callable, Iterator
from typing import Any

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from timetoshare import loads  # noqa: E402
from timetoshare.tables import (  # noqa: E402
    MATCH_CLAIM_SCHEMA,
    PROJECTION_SCHEMA,
    PROVENANCE_METADATA_KEY,
    fixture_path,
    match_claim_problems,
    projection_problems,
    succession_problems,
)

from . import table_checks_reference as reference  # noqa: E402
from .large_tables import large_manifest, many_claims  # noqa: E402
from .test_tables import (  # noqa: E402
    ACTOR,
    CLAIM_CASES,
    CLAIMS,
    MANIFEST,
    PROJECTION_CASES,
    PROJECTIONS,
    PROVENANCE,
    PROVENANCE_CASES,
    anchor,
    changed,
    claims_table,
    number,
    projections_table,
    q,
    sec,
    smp,
)

COMPACT_ACTOR = "orcid:0000-0002-1825-0097"
FIXTURE_MANIFEST = loads(fixture_path("manifest.yaml").read_text(encoding="utf-8"))
CONTEXT_MANIFEST = {**MANIFEST, "@context": FIXTURE_MANIFEST["@context"]}
"""The inline tables' manifest with the fixture's context, which declares
``orcid``, so a compact and an absolute actor are one actor."""


def _fixture_rows(name: str) -> list[dict[str, Any]]:
    return pq.read_table(fixture_path(name)).to_pylist()


def _outcome(check: Callable[..., Any], *arguments: Any) -> Any:
    try:
        return ("problems", check(*arguments))
    except Exception as error:  # the comparison holds for raising, too
        return ("raises", type(error).__name__, str(error))


def assert_same_claim_problems(table: Any, manifest: Any) -> list:
    expected = _outcome(reference.match_claim_problems, table, manifest)
    assert _outcome(match_claim_problems, table, manifest) == expected
    return expected[1] if expected[0] == "problems" else ["raised"]


def assert_same_projection_problems(table: Any, manifest: Any) -> list:
    expected = _outcome(reference.projection_problems, table, manifest)
    assert _outcome(projection_problems, table, manifest) == expected
    return expected[1] if expected[0] == "problems" else ["raised"]


# The fixture tables and the inline cases


@pytest.mark.parametrize(
    "manifest", [None, FIXTURE_MANIFEST], ids=["alone", "manifest"]
)
def test_the_fixture_tables(manifest: Any) -> None:
    claims = pq.read_table(fixture_path("match_claims.parquet"))
    projections = pq.read_table(fixture_path("projections.parquet"))
    assert assert_same_claim_problems(claims, manifest) == []
    assert assert_same_projection_problems(projections, manifest) == []
    assert succession_problems(claims, claims) == []


@pytest.mark.parametrize(
    "case", CLAIM_CASES + PROVENANCE_CASES, ids=lambda case: case[0]
)
@pytest.mark.parametrize("manifest", [None, MANIFEST], ids=["alone", "manifest"])
def test_each_claim_case(case: tuple, manifest: Any) -> None:
    table = claims_table(changed(CLAIMS, case[1]))
    assert assert_same_claim_problems(table, manifest) != []


@pytest.mark.parametrize("case", PROJECTION_CASES, ids=lambda case: case[0])
@pytest.mark.parametrize("manifest", [None, MANIFEST], ids=["alone", "manifest"])
def test_each_projection_case(case: tuple, manifest: Any) -> None:
    table = projections_table(changed(PROJECTIONS, case[1]))
    assert assert_same_projection_problems(table, manifest) != []


# The values a change puts in, by the key they go to

_PROVENANCE_POOL = [
    PROVENANCE,
    {**PROVENANCE, "stated_by": []},
    {**PROVENANCE, "date": "2026-02-30"},
    {**PROVENANCE, "date": "20.11.2026"},
    {**PROVENANCE, "method": "by ear"},
    {**PROVENANCE, "match": "same"},
    {**PROVENANCE, "basis": ["https://example.org/a", "https://example.org/a"]},
    {
        **PROVENANCE,
        "beliefs": [
            {"actor": ACTOR, "belief": "true", "date": "2026-11-20", "note": None},
            {
                "actor": COMPACT_ACTOR,
                "belief": "false",
                "date": "2026-11-21",
                "note": None,
            },
        ],
    },
    {**PROVENANCE, "beliefs": [None]},
    {**PROVENANCE, "beliefs": []},
    {**dict.fromkeys(PROVENANCE), "beliefs": None},
]

_POOLS: dict[str, list[Any]] = {
    "id": ["", "x\x01y", "claim_1", "projection_1", "note_1", None],
    "event": ["", "x\x1fy", "note_1", "note_2", "é", None],
    "name": ["C4", "", None],
    "timeline": ["clt_1", "dpt_1", "cpt_1", "clt_2", "tl_unknown", "", None],
    "unit": ["quarters", "samples", "seconds", "ticks", "whole_notes", "parsecs", None],
    "number_type": ["int", "fraction", "float", "decimal", None],
    "numerator": [0, 1, -1, 3, 2**62, None],
    "denominator": [1, 2, 4, 0, -2, None],
    "value": [0.0, -0.0, 0.5, -2.5, 1e300, math.nan, math.inf, -math.inf, None],
    "certainty": [0.0, 1.0, 0.5, 1.5, -0.0, -0.1, math.nan, None],
    "is_synchronous": [True, False, None],
    "anchor": [None, anchor(q(1, 2), smp(22050)), anchor(q(3), sec(0.5))],
    "coordinate": [None, q(1), q(2, 4), smp(3), sec(0.5), q(-1, 2)],
    "provenance": [None, *_PROVENANCE_POOL],
    "projection_of": [
        None,
        {"timeline_id": "clt_1", "event_id": "note_1"},
        {"timeline_id": None, "event_id": ""},
        {"timeline_id": "dpt_1", "event_id": "note_1"},
    ],
    "number": [
        None,
        number(smp(0)),
        number(smp(-5)),
        number(q(7, 2)),
        number(q(-1, 4)),
        number(sec(0.75)),
        number(sec(-0.0)),
    ],
    "stated_by": [[], [ACTOR], [ACTOR, ACTOR], [COMPACT_ACTOR], None],
    "date": ["2026-11-20", "2026-02-30", "20.11.2026", None],
    "method": ["manual", "by ear", "https://example.org/methods/listening", None],
    "iri": ["https://example.org/a", "not an iri", "", None],
    "match": ["exact", "close", "same", None],
    "beliefs": [
        None,
        [],
        [None],
        [{"actor": ACTOR, "belief": "true", "date": "2026-11-20", "note": None}],
    ],
    "actor": [ACTOR, COMPACT_ACTOR, "not an iri", None],
    "belief_entry": [
        None,
        {"actor": ACTOR, "belief": "unlikely", "date": "2026-11-22", "note": "n"},
        {"actor": COMPACT_ACTOR, "belief": "true", "date": "2026-11-20", "note": None},
    ],
    "belief": ["true", "false", "unlikely", "maybe", None],
    "string": ["", "x", ACTOR, None],
}

_KEY_POOLS = {
    "id": "id",
    "event_a_id": "event",
    "event_b_id": "event",
    "event_id": "event",
    "event_a_name": "name",
    "event_b_name": "name",
    "timeline_a_id": "timeline",
    "timeline_b_id": "timeline",
    "timeline_id": "timeline",
    "start_anchor": "anchor",
    "end_anchor": "anchor",
    "coordinate_a": "coordinate",
    "coordinate_b": "coordinate",
    "start": "number",
    "duration": "number",
    "service": "iri",
    "basis": "stated_by",
    "note": "string",
}


def _pool(path: tuple) -> list[Any]:
    """The values a change may put at ``path`` (row index first)."""
    key = next((part for part in reversed(path) if isinstance(part, str)), "")
    if isinstance(path[-1], int):
        return _POOLS["belief_entry" if key == "beliefs" else "actor"]
    return _POOLS[_KEY_POOLS.get(key, key if key in _POOLS else "string")]


def _paths(value: Any, path: tuple = ()) -> Iterator[tuple]:
    """Every path into a row's members, nested ones included."""
    if isinstance(value, dict):
        for key, member in value.items():
            yield (*path, key)
            yield from _paths(member, (*path, key))
    elif isinstance(value, list):
        for index, member in enumerate(value):
            yield (*path, index)
            yield from _paths(member, (*path, index))


def _put(rows: list[dict], path: tuple, value: Any) -> None:
    holder: Any = rows
    for key in path[:-1]:
        holder = holder[key]
    holder[path[-1]] = copy.deepcopy(value)


def _cell_paths(rows: list[dict], *keys: str) -> list[tuple]:
    return [
        (index, *path)
        for index, row in enumerate(rows)
        for path in _paths(row)
        if path[-1] in keys
    ]


# The kinds of change, each a function of a stream and the rows


def _null(rng: random.Random, rows: list[dict]) -> None:
    paths = [(index, *path) for index, row in enumerate(rows) for path in _paths(row)]
    if paths:
        _put(rows, rng.choice(paths), None)


def _value(rng: random.Random, rows: list[dict]) -> None:
    paths = [(index, *path) for index, row in enumerate(rows) for path in _paths(row)]
    if paths:
        path = rng.choice(paths)
        _put(rows, path, rng.choice(_pool(path)))


def _duplicate(rng: random.Random, rows: list[dict]) -> None:
    if not rows:
        return
    source = rng.choice(rows)
    if rng.random() < 0.5 or len(rows) == 1:
        rows.insert(rng.randrange(len(rows) + 1), copy.deepcopy(source))
    else:
        rng.choice(rows)["id"] = source["id"]


def _timeline(rng: random.Random, rows: list[dict]) -> None:
    paths = _cell_paths(rows, "timeline_a_id", "timeline_b_id", "timeline_id")
    if paths:
        _put(rows, rng.choice(paths), rng.choice(_POOLS["timeline"][:-1]))


def _axis(rng: random.Random, rows: list[dict]) -> None:
    """A cell or a row stating another axis, kept well-formed for it in half
    the cases, so the first cell read on a timeline moves."""
    paths = _cell_paths(rows, "coordinate_a", "coordinate_b") or _cell_paths(
        rows, "unit"
    )
    if not paths:
        return
    path = rng.choice(paths)
    if path[-1] == "unit":
        row = rows[path[0]]
        cell = rng.choice([smp(1), q(1, 2), sec(0.5), {**sec(0.5), "unit": "samples"}])
        row.update(unit=cell["unit"], number_type=cell["number_type"])
        if rng.random() < 0.5:
            row["start"] = number(cell)
        return
    cell = rng.choice(
        [
            smp(7),
            q(5, 2),
            sec(2.5),
            {**q(1, 3), "unit": "beats"},
            {**sec(1.0), "unit": "quarters"},
            {**smp(1), "unit": "parsecs"},
            {**smp(1), "number_type": "decimal"},
            {**q(1), "unit": "seconds"},
        ]
    )
    holder: Any = rows
    for key in path[:-1]:
        holder = holder[key]
    if holder is not None:
        holder[path[-1]] = cell


def _number(rng: random.Random, rows: list[dict]) -> None:
    paths = _cell_paths(rows, "numerator", "denominator", "value")
    if paths:
        path = rng.choice(paths)
        _put(rows, path, rng.choice(_pool(path)))


def _provenance(rng: random.Random, rows: list[dict]) -> None:
    """One provenance cell put in several rows, so one distinct cell stands
    for many."""
    if not rows:
        return
    cell = rng.choice(_POOLS["provenance"])
    for row in rng.sample(rows, rng.randint(1, len(rows))):
        if "provenance" in row:
            row["provenance"] = copy.deepcopy(cell)


def _rows(rng: random.Random, rows: list[dict]) -> None:
    choice = rng.randrange(4)
    if choice == 0:
        rng.shuffle(rows)
    elif choice == 1:
        del rows[rng.randint(0, 1) :]
    elif choice == 2 and rows:
        rows.append(copy.deepcopy(rng.choice(rows)))
    else:
        rows.reverse()


_ROW_CHANGES: dict[str, Callable[[random.Random, list[dict]], None]] = {
    "null": _null,
    "value": _value,
    "duplicate": _duplicate,
    "timeline": _timeline,
    "axis": _axis,
    "number": _number,
    "provenance": _provenance,
    "rows": _rows,
}

_SHARED = [
    json.dumps({"stated_by": [ACTOR], "method": "manual"}),
    json.dumps({"date": "2026-02-30"}),
    json.dumps({"beliefs": "x"}),
    json.dumps({"date": 5}),
    "{",
    "[1]",
]


def _built(rng: random.Random, rows: list[dict], schema: Any, kind: str) -> Any:
    """The table of the rows, in the form the kind asks for."""
    table = pa.Table.from_pylist(rows, schema=schema)
    if kind == "shared":
        if rng.random() < 0.5:
            for row in rows:
                row["provenance"] = None
            table = pa.Table.from_pylist(rows, schema=schema)
        table = table.replace_schema_metadata(
            {PROVENANCE_METADATA_KEY: rng.choice(_SHARED)}
        )
    if kind == "chunks" and table.num_rows > 1:
        cuts = sorted(
            rng.sample(
                range(1, table.num_rows), rng.randint(1, 3) if table.num_rows > 3 else 1
            )
        )
        bounds = [0, *cuts, table.num_rows]
        pieces = [
            table.slice(a, b - a) for a, b in zip(bounds, bounds[1:], strict=False)
        ]
        table = pa.concat_tables(pieces)
        assert table.column(0).num_chunks == len(pieces)
    if kind == "dictionary":
        if rng.random() < 0.5:
            scope = pa.array(
                [rng.choice(["take_1", "take_2", None]) for _ in range(table.num_rows)],
                pa.string(),
            ).dictionary_encode()
            table = table.append_column("scope", scope)
        else:
            names = [f.name for f in schema if pa.types.is_string(f.type)]
            name = rng.choice(names)
            index = table.column_names.index(name)
            table = table.set_column(
                index, name, table.column(name).dictionary_encode()
            )
    return table


_TABLE_KINDS = ("shared", "chunks", "dictionary")
KINDS = (*_ROW_CHANGES, *_TABLE_KINDS)

_CLAIM_BASES = [
    (_fixture_rows("match_claims.parquet"), FIXTURE_MANIFEST),
    (CLAIMS, MANIFEST),
    ([{**row, "provenance": PROVENANCE} for row in CLAIMS], CONTEXT_MANIFEST),
]
_PROJECTION_BASES = [
    (_fixture_rows("projections.parquet"), FIXTURE_MANIFEST),
    (PROJECTIONS, MANIFEST),
]


def mutated(
    kind: str, n: int, bases: list[tuple[list[dict], Any]], schema: Any
) -> tuple[Any, list[dict], Any]:
    """The ``n``-th table of a kind: a base changed once by the kind and up
    to twice by any row change, its rows, and the manifest it is checked
    against (``None`` in about a third of the tables)."""
    rng = random.Random(f"20261122-tables-{kind}-{n}")
    base, manifest = rng.choice(bases)
    rows = copy.deepcopy(base)
    changes = [_ROW_CHANGES[kind]] if kind in _ROW_CHANGES else []
    changes += rng.choices(list(_ROW_CHANGES.values()), k=rng.randint(0, 2))
    for change in changes:
        change(rng, rows)
    table = _built(rng, rows, schema, kind)
    return table, rows, None if rng.random() < 0.34 else manifest


def test_mutated_match_claim_tables() -> None:
    outcomes: dict[str, Counter] = {kind: Counter() for kind in KINDS}
    for kind in KINDS:
        for n in range(160):
            table, _, manifest = mutated(kind, n, _CLAIM_BASES, MATCH_CLAIM_SCHEMA)
            problems = assert_same_claim_problems(table, manifest)
            outcomes[kind]["problems" if problems else "none"] += 1
    assert sum(sum(counts.values()) for counts in outcomes.values()) >= 1_760
    for kind, counts in outcomes.items():
        assert counts["problems"] > 0 and counts["none"] > 0, (kind, counts)


def test_mutated_projection_tables() -> None:
    outcomes: dict[str, Counter] = {kind: Counter() for kind in KINDS}
    for kind in KINDS:
        if kind in ("provenance", "shared"):
            continue
        for n in range(100):
            table, _, manifest = mutated(kind, n, _PROJECTION_BASES, PROJECTION_SCHEMA)
            problems = assert_same_projection_problems(table, manifest)
            outcomes[kind]["problems" if problems else "none"] += 1
    assert sum(sum(counts.values()) for counts in outcomes.values()) >= 900
    for kind, counts in outcomes.items():
        if counts:
            assert counts["problems"] > 0 and counts["none"] > 0, (kind, counts)


# The succession rule


def _respelled(rng: random.Random, rows: list[dict]) -> None:
    """A fraction written in other terms, the same coordinate."""
    paths = [
        path
        for path in _cell_paths(rows, "coordinate_a", "coordinate_b")
        if (cell := rows[path[0]][path[1]][path[2]]) is not None
        and cell["number_type"] == "fraction"
    ]
    if paths:
        index, *rest = rng.choice(paths)
        cell = rows[index][rest[0]][rest[1]]
        factor = rng.choice([2, 3, -1])
        if factor > 0:
            cell.update(
                numerator=cell["numerator"] * factor,
                denominator=cell["denominator"] * factor,
            )


def _nudged(rng: random.Random, rows: list[dict]) -> None:
    """A float or an integer one step away."""
    paths = [
        path
        for path in _cell_paths(rows, "numerator", "value", "certainty")
        if _get(rows, path) is not None
    ]
    if paths:
        path = rng.choice(paths)
        value = _get(rows, path)
        _put(
            rows,
            path,
            math.nextafter(value, math.inf) if isinstance(value, float) else value + 1,
        )


def _get(rows: list[dict], path: tuple) -> Any:
    holder: Any = rows
    for key in path:
        holder = holder[key]
    return holder


def _removed(rng: random.Random, rows: list[dict]) -> None:
    if rows:
        del rows[rng.randrange(len(rows))]


_SUCCESSIONS = {
    "removed": _removed,
    "respelled": _respelled,
    "nudged": _nudged,
    "provenance": _provenance,
    "rows": _rows,
    "value": _value,
    "duplicate": _duplicate,
    "timeline": _timeline,
    "axis": _axis,
}


def test_the_succession_rule_on_pairs() -> None:
    outcomes = Counter()
    for kind, change in _SUCCESSIONS.items():
        for n in range(60):
            rng = random.Random(f"20261122-succession-{kind}-{n}")
            base, _ = rng.choice(_CLAIM_BASES)
            old_rows = copy.deepcopy(base)
            if rng.random() < 0.3:
                _rows(rng, old_rows)
            new_rows = copy.deepcopy(old_rows)
            for step in [
                change,
                *rng.choices(list(_SUCCESSIONS.values()), k=rng.randint(0, 1)),
            ]:
                step(rng, new_rows)
            old = claims_table(old_rows)
            new = _built(
                rng, new_rows, MATCH_CLAIM_SCHEMA, rng.choice(["chunks", "plain"])
            )
            checked = (
                reference.match_claim_problems(old) == []
                and reference.match_claim_problems(new) == []
            )
            expected = _outcome(reference.succession_problems, old, new)
            if expected[0] == "raises":
                assert not checked
                outcomes[("outside", False)] += 1
                continue
            assert _outcome(succession_problems, old, new) == expected
            outcomes[("checked" if checked else "unchecked", bool(expected[1]))] += 1
    assert outcomes[("checked", True)] > 0 and outcomes[("checked", False)] > 0
    assert sum(count for key, count in outcomes.items() if key[0] == "checked") >= 250


# A larger table


@pytest.mark.parametrize("provenance", [False, True], ids=["plain", "provenance"])
def test_a_larger_table(provenance: bool) -> None:
    rows = 2_000
    table = many_claims(rows, provenance)
    manifest = large_manifest(rows)
    for against in (None, manifest):
        assert assert_same_claim_problems(table, against) == []
    rng = random.Random(f"20261122-tables-larger-{provenance}")
    rows_changed = table.to_pylist()
    for change in (_axis, _duplicate, _provenance, _timeline, _number) * 6:
        change(rng, rows_changed)
    changed = _built(rng, rows_changed, MATCH_CLAIM_SCHEMA, "chunks")
    for against in (None, manifest):
        assert assert_same_claim_problems(changed, against) != []
    expected = _outcome(reference.succession_problems, table, changed)
    if expected[0] == "problems":
        assert succession_problems(table, changed) == expected[1] != []
