"""The row-by-row checks of the tables, kept as the reference.

The package's checks (``timetoshare.tables``) find their problems column by
column; this module is the implementation they replaced, one row at a time,
kept so that ``test_table_checks.py`` can compare the two on every table it
builds. It changes where the format's rules change, and only there: its
rules of a MatchClaim's sides and anchors read the sentinels' reserved
strings in the event ID columns (``CHUNK_SENTINEL`` on a synchronous row,
``NOMATCH_SENTINEL`` on one that is not), an ID that is a sentinel's
string is refused by the package's message of an ID, and so is a projected
event's ID, by a message written here. The registry is read one row at a
time: an event row's axis, positions, nulls, scoped ID and locator, and a
``projection_of``, set on a Projection's row alone, naming its event by both
members, no sentinel, on another timeline than the Projection's own and on
one the manifest (or the package) holds. The helpers the change left as
they were (the shape check, the messages, the check of a provenance entry)
are the package's own, imported; the row loops are this module's. It is no part of the
package.
"""

from __future__ import annotations

from collections.abc import Collection, Iterator, Mapping
from typing import Any

import pyarrow as pa

from timetoshare.ids import with_bare_ids
from timetoshare.manifest import UNITS
from timetoshare.tables import CHUNK_SENTINEL, NOMATCH_SENTINEL, TableProblem
from timetoshare.tables.checks import (
    _axis_problem,
    _id_problem,
    _number_problem,
    _present,
    _provenance_problem,
    _schema_problems,
    _shared_provenance,
)
from timetoshare.tables.columns import (
    COORDINATE_KEYS,
    MATCH_CLAIM_REQUIRED,
    MATCH_CLAIM_SCHEMA,
    NON_EVENT_KINDS,
    PROVENANCE_METADATA_KEY,
    REGISTRY_EVENT_REQUIRED,
    REGISTRY_REQUIRED,
    REGISTRY_SCHEMA,
    coordinate_value,
)
from timetoshare.validation.diagnostics import number_type_of, timelines_by_id

__all__ = [
    "match_claim_problems",
    "registry_problems",
    "succession_problems",
]

Column = tuple[str, ...]


class _Axes:
    """Collects the axis of each timeline a table's cells lie on."""

    def __init__(self, manifest: Mapping[str, Any] | None) -> None:
        self.seen: dict[str, tuple[str, str]] = {}
        self.timelines = (
            None if manifest is None else timelines_by_id(with_bare_ids(manifest))
        )

    def timeline(
        self, row: int, column: Column, timeline_id: Any
    ) -> TableProblem | None:
        if self.timelines is not None and timeline_id not in self.timelines:
            return TableProblem(
                "unknown_timeline",
                row,
                column,
                f"the manifest has no timeline '{timeline_id}'",
            )
        return None

    def expected(self, timeline_id: str) -> tuple[str, str] | None:
        """The axis a timeline's cells must have: the manifest's timeline's,
        else that of the first cell seen on it, else ``None``."""
        timeline = (self.timelines or {}).get(timeline_id)
        if timeline is not None:
            return self.own(timeline)
        return self.seen.get(timeline_id)

    @staticmethod
    def own(timeline: dict[str, Any]) -> tuple[Any, Any]:
        """A manifest timeline's unit and number type; the number type is
        ``None`` where the unit is missing or unknown and none is stated."""
        unit = timeline.get("unit")
        try:
            return (unit, number_type_of(timeline))
        except (KeyError, TypeError):
            return (unit, None)

    def axis(
        self, row: int, column: Column, timeline_id: str, axis: tuple[str, str]
    ) -> TableProblem | None:
        """The problem of a unit and a number type on the timeline, or ``None``."""
        if self.timelines is not None:
            timeline = self.timelines.get(timeline_id)
            if timeline is None:
                return None
            own = self.own(timeline)
            if axis != own:
                if own[1] is None:
                    reason = (
                        "which has no unit"
                        if own[0] is None
                        else f"whose unit {own[0]!r} is unknown"
                    )
                    message = (
                        f"a coordinate in {axis[0]} ({axis[1]}) on the timeline "
                        f"'{timeline_id}', {reason}"
                    )
                else:
                    message = (
                        f"a coordinate in {axis[0]} ({axis[1]}) on the timeline "
                        f"'{timeline_id}' in {own[0]} ({own[1]})"
                    )
                return TableProblem("axis_mismatch", row, column, message)
        first = self.seen.setdefault(timeline_id, axis)
        if first != axis:
            return TableProblem(
                "axis_mismatch",
                row,
                column,
                f"the timeline '{timeline_id}' has coordinates in {first[0]} "
                f"({first[1]}) and in {axis[0]} ({axis[1]})",
            )
        return None


def _ids(rows: list[dict[str, Any]]) -> Iterator[TableProblem]:
    """Each ID valid, and given once in the table.

    A MatchClaim is addressed by its ID alone; a Projection's ID is unique
    in the package, as every event's, so two timelines never share one.
    """
    seen: set[str] = set()
    for index, row in enumerate(rows):
        value = row["id"]
        if value is None:
            continue
        problem = _id_problem(value, "the ID")
        if problem:
            yield TableProblem("invalid_id", index, ("id",), problem)
        elif value in seen:
            yield TableProblem(
                "duplicate_id", index, ("id",), f"the ID '{value}' is given twice"
            )
        seen.add(value)


def _claim_rows(table: pa.Table) -> list[dict[str, Any]]:
    """The rows of a MatchClaim table, its declared columns alone."""
    return table.select(list(MATCH_CLAIM_SCHEMA.names)).to_pylist()


def _nulls(
    rows: list[dict[str, Any]], required: tuple[str, ...]
) -> Iterator[TableProblem]:
    for index, row in enumerate(rows):
        for key in required:
            if row[key] is None:
                yield TableProblem(
                    "schema_violation", index, (key,), f"'{key}' is null"
                )


def _claim_problems(
    index: int, row: dict[str, Any], axes: _Axes
) -> Iterator[TableProblem]:
    a, b = row["timeline_a_id"], row["timeline_b_id"]
    for key in ("timeline_a_id", "timeline_b_id"):
        problem = axes.timeline(index, (key,), row[key])
        if problem:
            yield problem
    if a == b:
        yield TableProblem(
            "claim_timelines", index, ("timeline_b_id",), f"both sides are '{a}'"
        )
    for key in ("event_a_id", "event_b_id"):
        if row[key] not in (CHUNK_SENTINEL, NOMATCH_SENTINEL):
            problem = _id_problem(row[key], "the event ID")
            if problem:
                yield TableProblem("invalid_id", index, (key,), problem)
    synchronous = row["is_synchronous"]
    start, end = row["start_anchor"], row["end_anchor"]
    sides = ("a", "b")
    for side in sides:
        if not synchronous and row[f"event_{side}_id"] == CHUNK_SENTINEL:
            yield TableProblem(
                "claim_events",
                index,
                (f"event_{side}_id",),
                "CHUNK_SENTINEL stands only on a synchronous MatchClaim",
            )
    for side in sides:
        if synchronous and row[f"event_{side}_id"] == NOMATCH_SENTINEL:
            yield TableProblem(
                "claim_events",
                index,
                (f"event_{side}_id",),
                "NOMATCH_SENTINEL stands only on a MatchClaim that is not synchronous",
            )
    nomatch = [row[f"event_{side}_id"] == NOMATCH_SENTINEL for side in sides]
    if all(nomatch):
        yield TableProblem(
            "claim_events",
            index,
            ("event_b_id",),
            "a NOMATCH MatchClaim names an event on its other side",
        )
    for side, is_nomatch in zip(sides, nomatch, strict=True):
        if is_nomatch and row[f"event_{side}_name"] is not None:
            yield TableProblem(
                "claim_events",
                index,
                (f"event_{side}_name",),
                "a NOMATCH side has no name",
            )
    if synchronous:
        if start is None:
            yield TableProblem(
                "claim_anchors",
                index,
                ("start_anchor",),
                "a synchronous MatchClaim has a start anchor",
            )
    elif start is not None or end is not None:
        yield TableProblem(
            "claim_anchors",
            index,
            ("start_anchor" if start is not None else "end_anchor",),
            "a NOMATCH MatchClaim has no anchors"
            if any(nomatch)
            else "a conceptual MatchClaim has no anchors",
        )
    if end is not None and start is None:
        yield TableProblem(
            "claim_anchors",
            index,
            ("end_anchor",),
            "an end anchor needs a start anchor",
        )
    for name, anchor in (("start_anchor", start), ("end_anchor", end)):
        if anchor is None:
            continue
        for side, timeline_id in (("a", a), ("b", b)):
            yield from _cell_problems(
                index,
                (name, f"coordinate_{side}"),
                timeline_id,
                anchor[f"coordinate_{side}"],
                axes,
            )
    certainty = row["certainty"]
    if certainty is not None and not 0 <= certainty <= 1:
        yield TableProblem(
            "invalid_certainty",
            index,
            ("certainty",),
            f"the certainty {certainty} lies outside [0, 1]",
        )


def _cell_problems(
    index: int,
    column: Column,
    timeline_id: str,
    cell: Mapping[str, Any] | None,
    axes: _Axes,
) -> Iterator[TableProblem]:
    """The problems of an anchor's coordinate cell, which states its own axis."""
    if cell is None:
        yield TableProblem(
            "invalid_coordinate", index, column, "the coordinate is null"
        )
        return
    for key in ("unit", "number_type"):
        if cell[key] is None:
            yield TableProblem(
                "invalid_coordinate", index, column, f"the coordinate has no {key}"
            )
            return
    problem = _axis_problem(cell["unit"], cell["number_type"]) or _number_problem(
        cell, cell["number_type"], "coordinate"
    )
    if problem:
        yield TableProblem("invalid_coordinate", index, column, problem)
        return
    axis = axes.axis(index, column, timeline_id, (cell["unit"], cell["number_type"]))
    if axis:
        yield axis


def match_claim_problems(
    table: pa.Table, manifest: Mapping[str, Any] | None = None
) -> list[TableProblem]:
    """Every problem of a MatchClaim table, checked against a manifest (as
    read from its file, IDs written ``#``) where one is given.

    A MatchClaim's ID is unique in the table, which belongs to one manifest. An
    actor holds one belief in a row; against a manifest, actors are compared
    as the IRIs they stand for under its ``@context``, so a compact and an
    absolute IRI of one actor are one actor, else as written."""
    problems = _schema_problems(table, MATCH_CLAIM_SCHEMA)
    if problems:
        return problems
    rows = _claim_rows(table)
    problems = [*_nulls(rows, MATCH_CLAIM_REQUIRED)]
    if problems:
        return problems
    problems.extend(_ids(rows))
    shared = PROVENANCE_METADATA_KEY.encode() in (table.schema.metadata or {})
    context = None if manifest is None else manifest.get("@context")
    _, problem = _shared_provenance(table, context)
    if problem:
        problems.append(
            TableProblem("invalid_provenance", None, ("provenance",), problem)
        )
    axes = _Axes(manifest)
    for index, row in enumerate(rows):
        problems.extend(_claim_problems(index, row, axes))
        cell = row["provenance"]
        if cell is not None:
            problem = (
                "the provenance is stated in the file's metadata and in the row"
                if shared
                else _provenance_problem(_present(cell), "the provenance", context)
            )
            if problem:
                problems.append(
                    TableProblem("invalid_provenance", index, ("provenance",), problem)
                )
    return sorted(problems, key=_order)


def _projection_of(
    index: int, row: Mapping[str, Any], projected: tuple[Collection[str], str] | None
) -> Iterator[TableProblem]:
    """The problems of a row's ``projection_of``: set on a Projection's row
    alone; there both members given, the event no sentinel, on another
    timeline than the Projection's and, where ``projected`` gives the
    timelines it may lie on, on one of them (worded by its message)."""
    source = row["projection_of"]
    if source is None:
        return
    if row["kind"] != "Projection":
        yield TableProblem(
            "invalid_projection_of",
            index,
            ("projection_of",),
            f"'projection_of' is set on a row of the kind '{row['kind']}'",
        )
        return
    for key in ("timeline_id", "event_id"):
        if not source[key]:
            yield TableProblem(
                "invalid_projection_of",
                index,
                ("projection_of", key),
                f"the projected event has no {key}",
            )
    if source["event_id"] in (CHUNK_SENTINEL, NOMATCH_SENTINEL):
        yield TableProblem(
            "invalid_projection_of",
            index,
            ("projection_of", "event_id"),
            f"'{source['event_id']}' is reserved for a sentinel",
        )
    own = source["timeline_id"]
    if own is not None and own == row["timeline_id"]:
        yield TableProblem(
            "invalid_projection_of",
            index,
            ("projection_of", "timeline_id"),
            "a Projection stands for an event of another timeline than "
            f"'{row['timeline_id']}'",
        )
    if projected is not None and own and own not in projected[0]:
        yield TableProblem(
            "unknown_timeline",
            index,
            ("projection_of", "timeline_id"),
            projected[1].format(own),
        )


_ELEMENTS = tuple(
    kind for kind in NON_EVENT_KINDS if kind not in ("MatchClaim", "Parse")
)
_NON_EVENT_EMPTY = (
    "unit",
    "number_type",
    "start",
    "duration",
    "parse_id",
    "locator",
    "vanished_in",
)


def _registry_nulls(rows: list[dict[str, Any]]) -> Iterator[TableProblem]:
    for index, row in enumerate(rows):
        kind = row["kind"]
        is_non_event = kind in NON_EVENT_KINDS
        for key in REGISTRY_SCHEMA.names:
            value = row[key]
            if key in REGISTRY_REQUIRED:
                missing = value is None
            elif key in REGISTRY_EVENT_REQUIRED:
                missing = kind is not None and not is_non_event and value is None
            elif key == "location":
                missing = is_non_event and value is None
            else:
                missing = False
            if missing:
                yield TableProblem(
                    "schema_violation", index, (key,), f"'{key}' is null"
                )
            if is_non_event and key in _NON_EVENT_EMPTY and value is not None:
                yield TableProblem(
                    "schema_violation", index, (key,), f"a non-event row has no '{key}'"
                )


def registry_problems(
    table: pa.Table,
    manifest: Mapping[str, Any] | None = None,
    *,
    projected_timelines: Collection[str] | None = None,
) -> list[TableProblem]:
    """Every problem of a registry, checked against a manifest where one is
    given, one row at a time; a Projection's projected timeline checked
    against ``projected_timelines`` where given, else the manifest's."""
    problems = _schema_problems(table, REGISTRY_SCHEMA)
    if problems:
        return problems
    rows = table.select(list(REGISTRY_SCHEMA.names)).to_pylist()
    problems = [*_registry_nulls(rows)]
    if problems:
        return problems
    seen: set[Any] = set()
    axes = _Axes(manifest)
    projected = None
    if projected_timelines is not None:
        projected = (
            set(projected_timelines),
            "no manifest of the package has the timeline '{}'",
        )
    elif axes.timelines is not None:
        projected = (set(axes.timelines), "the manifest has no timeline '{}'")
    locators: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        value = row["id"]
        problem = _id_problem(value, "the ID")
        if problem:
            problems.append(TableProblem("invalid_id", index, ("id",), problem))
        else:
            element = row["kind"] in _ELEMENTS
            key = (row["location"], value) if element else value
            if key in seen:
                at = f" at '{row['location']}'" if element else ""
                problems.append(
                    TableProblem(
                        "duplicate_id",
                        index,
                        ("id",),
                        f"the ID '{value}' is given twice{at}",
                    )
                )
            seen.add(key)
        if row["kind"] in NON_EVENT_KINDS:
            problems.extend(_projection_of(index, row, projected))
            continue
        problem = axes.timeline(index, ("timeline_id",), row["timeline_id"])
        if problem:
            problems.append(problem)
        problems.extend(_projection_numbers(index, row, axes))
        if row["locator"] is not None:
            located = (row["parse_id"], row["locator"])
            if located in locators:
                problems.append(
                    TableProblem(
                        "duplicate_locator",
                        index,
                        ("locator",),
                        f"the locator '{row['locator']}' is given twice in the "
                        f"parse '{row['parse_id']}'",
                    )
                )
            locators.add(located)
        problems.extend(_projection_of(index, row, projected))
    return sorted(problems, key=_order)


def _projection_numbers(
    index: int, row: Mapping[str, Any], axes: _Axes
) -> Iterator[TableProblem]:
    """The problems of an event row's axis, ``start`` and ``duration``: its
    row states the unit and the number type of both, never null here."""
    unit, number_type = row["unit"], row["number_type"]
    problem = _axis_problem(unit, number_type)
    if problem:
        column = "unit" if unit not in UNITS else "number_type"
        yield TableProblem("invalid_coordinate", index, (column,), problem)
        return
    expected = axes.expected(row["timeline_id"])
    column = ("unit",) if expected and expected[0] != unit else ("number_type",)
    axis = axes.axis(index, column, row["timeline_id"], (unit, number_type))
    if axis:
        yield axis
    for key, what in (("start", "coordinate"), ("duration", "duration")):
        number = row[key]
        if number is None:
            continue
        problem = _number_problem(number, number_type, what)
        if problem:
            yield TableProblem("invalid_coordinate", index, (key,), problem)
        elif key == "duration" and coordinate_value(number, number_type) < 0:
            yield TableProblem(
                "invalid_duration", index, (key,), "the duration is negative"
            )


def _order(problem: TableProblem) -> int:
    return -1 if problem.row is None else problem.row


def _comparable(value: Any) -> Any:
    """A value with every coordinate cell read as (unit, number type, exact value)."""
    if isinstance(value, dict):
        if set(value) == set(COORDINATE_KEYS):
            return (value["unit"], value["number_type"], coordinate_value(value))
        return {key: _comparable(member) for key, member in value.items()}
    if isinstance(value, list):
        return [_comparable(member) for member in value]
    return value


def succession_problems(old: pa.Table, new: pa.Table) -> list[TableProblem]:
    """Every breach of the succession rule by ``new`` written over ``old``.

    Both are checked MatchClaim tables. A MatchClaim is its ID alone; a column
    the type does not declare takes no part. Every MatchClaim of ``old`` is
    in ``new``, and its row has the same value in every column but
    ``provenance``; a coordinate is the same when its unit, number type and
    exact value are, so ``2/4`` and ``1/2`` are one coordinate. The rows of
    ``new`` are reported by their index in ``new``.
    """
    columns = [name for name in MATCH_CLAIM_SCHEMA.names if name != "provenance"]
    later = {
        row["id"]: (index, row)
        for index, row in reversed(list(enumerate(_claim_rows(new))))
    }
    problems = []
    for row in _claim_rows(old):
        name = f"the MatchClaim '{row['id']}'"
        found = later.get(row["id"])
        if found is None:
            problems.append(
                TableProblem("succession_missing", None, ("id",), f"{name} is missing")
            )
            continue
        index, successor = found
        for column in columns:
            if _comparable(row[column]) != _comparable(successor[column]):
                problems.append(
                    TableProblem(
                        "succession_changed",
                        index,
                        (column,),
                        f"{name} changed its '{column}'",
                    )
                )
    return problems
