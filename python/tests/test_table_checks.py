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
    CHUNK_SENTINEL,
    MATCH_CLAIM_SCHEMA,
    NOMATCH_SENTINEL,
    PROVENANCE_METADATA_KEY,
    REGISTRY_SCHEMA,
    checks,
    fixture_path,
    match_claim_problems,
    registry_problems,
    succession_problems,
)

from . import table_checks_reference as reference  # noqa: E402
from .large_tables import BAD_TIMELINES, large_manifest, many_claims  # noqa: E402
from .test_tables import (  # noqa: E402
    ACTOR,
    ADMITTED_CASES,
    CLAIM_CASES,
    CLAIMS,
    MANIFEST,
    PROJECTION_CASES,
    PROVENANCE,
    PROVENANCE_CASES,
    REGISTRY,
    REGISTRY_CASES,
    anchor,
    changed,
    claims_table,
    number,
    q,
    registry_table,
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


FORMER_MESSAGES = {
    "the MatchClaim names no event",
    "a NOMATCH MatchClaim is not synchronous",
    "a sentinel side has no name",
}
"""The messages of the reading that took a null event ID for NOMATCH, and
of the rule that refused a name on a CHUNK side: no table yields them any
more."""


def assert_same_claim_problems(table: Any, manifest: Any) -> list:
    expected = _outcome(reference.match_claim_problems, table, manifest)
    assert _outcome(match_claim_problems, table, manifest) == expected
    if expected[0] == "problems":
        assert not FORMER_MESSAGES & {problem.message for problem in expected[1]}
    return expected[1] if expected[0] == "problems" else ["raised"]


def assert_same_registry_problems(table: Any, manifest: Any) -> list:
    expected = _outcome(reference.registry_problems, table, manifest)
    assert _outcome(registry_problems, table, manifest) == expected
    return expected[1] if expected[0] == "problems" else ["raised"]


# The fixture tables and the inline cases


@pytest.mark.parametrize(
    "manifest", [None, FIXTURE_MANIFEST], ids=["alone", "manifest"]
)
def test_the_fixture_tables(manifest: Any) -> None:
    claims = pq.read_table(fixture_path("match_claims.parquet"))
    registry = pq.read_table(fixture_path("registry.parquet"))
    assert assert_same_claim_problems(claims, manifest) == []
    assert assert_same_registry_problems(registry, manifest) == []
    assert succession_problems(claims, claims) == []


@pytest.mark.parametrize(
    "case", CLAIM_CASES + PROVENANCE_CASES, ids=lambda case: case[0]
)
@pytest.mark.parametrize("manifest", [None, MANIFEST], ids=["alone", "manifest"])
def test_each_claim_case(case: tuple, manifest: Any) -> None:
    table = claims_table(changed(CLAIMS, case[1]))
    assert assert_same_claim_problems(table, manifest) != []


@pytest.mark.parametrize("case", ADMITTED_CASES, ids=lambda case: case[0])
@pytest.mark.parametrize("manifest", [None, MANIFEST], ids=["alone", "manifest"])
def test_each_admitted_row(case: tuple, manifest: Any) -> None:
    table = claims_table(changed(CLAIMS, case[1]))
    assert assert_same_claim_problems(table, manifest) == []


@pytest.mark.parametrize("case", PROJECTION_CASES, ids=lambda case: case[0])
@pytest.mark.parametrize("manifest", [None, MANIFEST], ids=["alone", "manifest"])
def test_each_projection_case(case: tuple, manifest: Any) -> None:
    table = registry_table(changed(REGISTRY, case[1]))
    assert assert_same_registry_problems(table, manifest) != []


@pytest.mark.parametrize("case", REGISTRY_CASES, ids=lambda case: case[0])
@pytest.mark.parametrize("manifest", [None, MANIFEST], ids=["alone", "manifest"])
def test_each_registry_case(case: tuple, manifest: Any) -> None:
    table = registry_table(changed(REGISTRY, case[1]))
    assert assert_same_registry_problems(table, manifest) != []


# A manifest's timelines, read where a row reaches them

_BAD_NAMES = [
    "furlongs",
    "no-unit",
    "unit-5",
    "number-type-7",
    "null-unit",
    "list-unit",
]
_NAMED_OUTCOMES = {
    "furlongs": ", whose unit 'furlongs' is unknown",
    "no-unit": ", which has no unit",
    "unit-5": " in 5 (int)",
    "number-type-7": " in samples (7)",
    "null-unit": " in None (int)",
    "list-unit": " in ['samples'] (int)",
}
"""What the inline tables meet against a manifest whose ``dpt_1`` is the bad
timeline: an ``axis_mismatch`` at every cell or row on ``dpt_1``, whose
message ends as worded here."""


def _with_bad_timeline(manifest: dict, bad: dict, named: bool) -> dict:
    """The manifest with the bad timeline added as ``x``, which no row names,
    or put in place of ``dpt_1``, which the rows name."""
    manifest = copy.deepcopy(manifest)
    if not named:
        manifest["timelines"].append({**bad, "id": "#x"})
        return manifest
    manifest["timelines"] = [
        {**bad, "id": "#dpt_1"} if timeline["id"] == "#dpt_1" else timeline
        for timeline in manifest["timelines"]
    ]
    return manifest


@pytest.mark.parametrize("named", [False, True], ids=["unnamed", "named"])
@pytest.mark.parametrize("bad", BAD_TIMELINES, ids=_BAD_NAMES)
def test_a_bad_timeline_is_read_where_a_row_reaches_it(bad: dict, named: bool) -> None:
    manifest = _with_bad_timeline(MANIFEST, bad, named)
    for compared, table in (
        (assert_same_claim_problems, claims_table(CLAIMS)),
        (assert_same_registry_problems, registry_table(REGISTRY)),
    ):
        problems = compared(table, manifest)
        if not named:
            assert problems == []
            continue
        outcome = _NAMED_OUTCOMES[_BAD_NAMES[BAD_TIMELINES.index(bad)]]
        assert {problem.code for problem in problems} == {"axis_mismatch"}
        assert problems[0].message == (
            f"a coordinate in samples (int) on the timeline 'dpt_1'{outcome}"
        )


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
    "id": ["", "x\x01y", "claim_1", "projection_1", "note_1", CHUNK_SENTINEL, None],
    "event": [
        "",
        "x\x1fy",
        "note_1",
        "note_2",
        "é",
        NOMATCH_SENTINEL,
        CHUNK_SENTINEL,
        None,
    ],
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
    "kind": ["Projection", "MidiNote", "Timeline", "MatchClaim", "", None],
    "location": ["tables/Note/", "manifest.yaml", "", None],
    "parse_id": ["parse_1", "parse_2", None],
    "locator": ["track 0, message 4", "track 0, message 9", None],
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
    "vanished_in": "parse_id",
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
KINDS = (*_ROW_CHANGES, *_TABLE_KINDS, "manifest")


def _manifest_timelines(manifest: dict) -> list[dict]:
    """Every timeline of a manifest, children included."""
    found = []

    def visit(timeline: dict) -> None:
        found.append(timeline)
        for child in timeline.get("children", []):
            visit(child)

    for root in manifest["timelines"]:
        visit(root)
    return found


def _bad_manifest(rng: random.Random, manifest: dict) -> dict:
    """The manifest with a bad timeline added unnamed, or put in place of
    one of its timelines (its ID and children kept)."""
    manifest = copy.deepcopy(manifest)
    bad = rng.choice(BAD_TIMELINES)
    if rng.random() < 0.5:
        manifest["timelines"].append({**bad, "id": "#x"})
        return manifest
    timeline = rng.choice(_manifest_timelines(manifest))
    kept = {key: timeline[key] for key in ("id", "children") if key in timeline}
    timeline.clear()
    timeline.update({**bad, **kept})
    return manifest


_CLAIM_BASES = [
    (_fixture_rows("match_claims.parquet"), FIXTURE_MANIFEST),
    (CLAIMS, MANIFEST),
    ([{**row, "provenance": PROVENANCE} for row in CLAIMS], CONTEXT_MANIFEST),
]
_REGISTRY_BASES = [
    (_fixture_rows("registry.parquet"), FIXTURE_MANIFEST),
    (REGISTRY, MANIFEST),
]


def mutated(
    kind: str, n: int, bases: list[tuple[list[dict], Any]], schema: Any
) -> tuple[Any, list[dict], Any]:
    """The ``n``-th table of a kind: a base changed once by the kind and up
    to twice by any row change, its rows, and the manifest it is checked
    against (``None`` in about a third of the tables, never for the kind
    ``manifest``, which gives the manifest a bad timeline)."""
    rng = random.Random(f"20261122-tables-{kind}-{n}")
    base, manifest = rng.choice(bases)
    rows = copy.deepcopy(base)
    changes = [_ROW_CHANGES[kind]] if kind in _ROW_CHANGES else []
    changes += rng.choices(list(_ROW_CHANGES.values()), k=rng.randint(0, 2))
    for change in changes:
        change(rng, rows)
    table = _built(rng, rows, schema, kind)
    if kind == "manifest":
        return table, rows, _bad_manifest(rng, manifest)
    return table, rows, None if rng.random() < 0.34 else manifest


def test_mutated_match_claim_tables() -> None:
    outcomes: dict[str, Counter] = {kind: Counter() for kind in KINDS}
    for kind in KINDS:
        for n in range(160):
            table, _, manifest = mutated(kind, n, _CLAIM_BASES, MATCH_CLAIM_SCHEMA)
            problems = assert_same_claim_problems(table, manifest)
            outcomes[kind]["problems" if problems else "none"] += 1
    assert sum(sum(counts.values()) for counts in outcomes.values()) == 1_920
    for kind, counts in outcomes.items():
        assert counts["problems"] > 0 and counts["none"] > 0, (kind, counts)


def test_mutated_registries() -> None:
    outcomes: dict[str, Counter] = {kind: Counter() for kind in KINDS}
    for kind in KINDS:
        if kind in ("provenance", "shared"):
            continue
        for n in range(100):
            table, _, manifest = mutated(kind, n, _REGISTRY_BASES, REGISTRY_SCHEMA)
            problems = assert_same_registry_problems(table, manifest)
            outcomes[kind]["problems" if problems else "none"] += 1
    assert sum(sum(counts.values()) for counts in outcomes.values()) == 1_000
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


def _one_sided(rng: random.Random, old_rows: list[dict], new_rows: list[dict]) -> None:
    """A coordinate stated on one side alone: in one table the cell is null,
    in the other it keeps its number but loses its unit, its number type or
    both."""
    paths = [
        path
        for path in _cell_paths(old_rows, "coordinate_a", "coordinate_b")
        if _get(old_rows, path) is not None
    ]
    if not paths:
        return
    path = rng.choice(paths)
    stripped, nulled = (
        (old_rows, new_rows) if rng.random() < 0.5 else (new_rows, old_rows)
    )
    for key in rng.choice([("unit", "number_type"), ("unit",), ("number_type",)]):
        _get(stripped, path)[key] = None
    _put(nulled, path, None)


def test_the_succession_rule_on_pairs() -> None:
    outcomes = Counter()
    for kind in (*_SUCCESSIONS, "one_sided"):
        for n in range(70):
            rng = random.Random(f"20261122-succession-{kind}-{n}")
            base, _ = rng.choice(_CLAIM_BASES)
            old_rows = copy.deepcopy(base)
            if rng.random() < 0.3:
                _rows(rng, old_rows)
            new_rows = copy.deepcopy(old_rows)
            if kind == "one_sided":
                _one_sided(rng, old_rows, new_rows)
                steps = rng.choices(list(_SUCCESSIONS.values()), k=rng.randint(0, 1))
            else:
                steps = [
                    _SUCCESSIONS[kind],
                    *rng.choices(list(_SUCCESSIONS.values()), k=rng.randint(0, 1)),
                ]
            for step in steps:
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
            outcomes[(kind, "compared")] += 1
    assert outcomes[("checked", True)] > 0 and outcomes[("checked", False)] > 0
    assert sum(count for key, count in outcomes.items() if key[0] == "checked") >= 250
    assert outcomes[("one_sided", "compared")] > 0


def test_a_coordinate_stated_on_one_side() -> None:
    old_rows, new_rows = copy.deepcopy(CLAIMS), copy.deepcopy(CLAIMS)
    old_rows[0]["start_anchor"]["coordinate_a"] = {
        "numerator": 1,
        "denominator": 2,
        "value": None,
        "unit": None,
        "number_type": None,
    }
    new_rows[0]["start_anchor"]["coordinate_a"] = None
    old, new = claims_table(old_rows), claims_table(new_rows)
    expected = [
        (
            "succession_changed",
            0,
            ("start_anchor",),
            "the MatchClaim 'claim_1' changed its 'start_anchor'",
        )
    ]
    for check in (reference.succession_problems, succession_problems):
        assert [
            (problem.code, problem.row, problem.column, problem.message)
            for problem in check(old, new)
        ] == expected


# Text that is no UTF-8

_HOLE = "QQQ"
"""A placeholder written into a string cell and replaced, in the table's
Arrow IPC bytes, by three bytes that are no UTF-8."""


def _broken(table: Any) -> Any:
    """The table with every placeholder's bytes replaced by ``ff fe fd``."""
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    data = sink.getvalue().to_pybytes()
    assert _HOLE.encode() in data
    return pa.ipc.open_stream(data.replace(_HOLE.encode(), b"\xff\xfe\xfd")).read_all()


def _undecodable(position: int) -> tuple:
    return (
        "raises",
        "UnicodeDecodeError",
        f"'utf-8' codec can't decode byte 0xff in position {position}: "
        "invalid start byte",
    )


def _claims_with(change: Callable[[list[dict]], None]) -> Any:
    return _broken(claims_table(changed(CLAIMS, change)))


_UNDECODABLE_CLAIMS = {
    "id": (lambda rows: rows[1].update(id=_HOLE), 0),
    "unit": (
        lambda rows: rows[0]["start_anchor"]["coordinate_a"].update(unit=_HOLE),
        0,
    ),
    "actor": (
        lambda rows: rows[0]["provenance"]["beliefs"][0].update(actor="a" + _HOLE),
        1,
    ),
    "first-column-first": (
        lambda rows: (
            rows[0].update(id=_HOLE),
            rows[3].update(timeline_a_id="clt_" + _HOLE),
        ),
        4,
    ),
}


@pytest.mark.parametrize("case", _UNDECODABLE_CLAIMS, ids=list(_UNDECODABLE_CLAIMS))
@pytest.mark.parametrize("manifest", [None, MANIFEST], ids=["alone", "manifest"])
def test_text_that_is_no_utf8_raises_as_reading_it_does(
    case: str, manifest: Any
) -> None:
    change, position = _UNDECODABLE_CLAIMS[case]
    table = _claims_with(change)
    assert assert_same_claim_problems(table, manifest) == ["raised"]
    assert _outcome(match_claim_problems, table, manifest) == _undecodable(position)
    valid = claims_table(CLAIMS)
    for old, new in ((table, valid), (valid, table)):
        expected = _outcome(reference.succession_problems, old, new)
        assert _outcome(succession_problems, old, new) == expected
        assert expected == _undecodable(position)


@pytest.mark.parametrize("manifest", [None, MANIFEST], ids=["alone", "manifest"])
def test_a_projection_that_is_no_utf8(manifest: Any) -> None:
    rows = changed(
        REGISTRY, lambda rows: rows[0]["projection_of"].update(event_id=_HOLE)
    )
    table = _broken(registry_table(rows))
    assert assert_same_registry_problems(table, manifest) == ["raised"]
    assert _outcome(registry_problems, table, manifest) == _undecodable(0)


@pytest.mark.parametrize("manifest", [None, MANIFEST], ids=["alone", "manifest"])
def test_a_registry_location_that_is_no_utf8(manifest: Any) -> None:
    rows = changed(REGISTRY, lambda rows: rows[4].update(location=_HOLE))
    table = _broken(registry_table(rows))
    assert assert_same_registry_problems(table, manifest) == ["raised"]
    assert _outcome(registry_problems, table, manifest) == _undecodable(0)


def test_bytes_that_are_never_read() -> None:
    """Bytes that are no UTF-8 in a null slot of a string column and in a
    member of a null struct are no problem."""
    table = claims_table(CLAIMS)
    offsets = pa.array([0, 0, 3, 3, 3], pa.int32()).buffers()[1]
    validity = pa.array([True, False, True, True]).buffers()[1]
    names = pa.Array.from_buffers(
        pa.string(), 4, [validity, offsets, pa.py_buffer(b"\xff\xfe\xfd")]
    )
    assert names.to_pylist() == ["", None, "", ""]
    table = table.set_column(
        table.column_names.index("event_a_name"), "event_a_name", names
    )
    for manifest in (None, MANIFEST):
        assert assert_same_claim_problems(table, manifest) == []
    registry = registry_table(REGISTRY)
    source = registry.column("projection_of").combine_chunks()
    rows = len(registry)
    events = pa.Array.from_buffers(
        pa.string(),
        rows,
        [
            None,
            pa.array([0, 6, *[9] * (rows - 1)], pa.int32()).buffers()[1],
            pa.py_buffer(b"note_1\xff\xfe\xfd"),
        ],
    )
    source = pa.StructArray.from_arrays(
        [source.field("timeline_id"), events],
        names=["timeline_id", "event_id"],
        mask=pa.array([False, *[True] * (rows - 1)]),
    )
    assert source.to_pylist() == [
        {"timeline_id": "clt_1", "event_id": "note_1"},
        *[None] * (rows - 1),
    ]
    registry = registry.set_column(
        registry.column_names.index("projection_of"), "projection_of", source
    )
    for manifest in (None, MANIFEST):
        assert assert_same_registry_problems(registry, manifest) == []


# Every flagged cell has its message


def test_a_flagged_cell_without_a_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks, "_id_problem", lambda value, what: None)
    table = claims_table(changed(CLAIMS, lambda rows: rows[0].update(id="")))
    with pytest.raises(AssertionError, match="^no message for 'invalid_id' at row 0$"):
        match_claim_problems(table)


# A larger table


@pytest.mark.parametrize("provenance", [False, True], ids=["plain", "provenance"])
def test_a_larger_table(provenance: bool) -> None:
    rows = 2_000
    table = many_claims(rows, provenance)
    manifest = large_manifest(rows)
    for against in (None, manifest, large_manifest(rows, BAD_TIMELINES)):
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
