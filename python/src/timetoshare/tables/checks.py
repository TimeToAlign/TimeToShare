"""The checks of the MatchClaim table and the Projections table.

Each ``*_problems`` function lists every problem it finds, the table's own
first, then row by row; each ``check_*`` function raises the first as a
``TableError``. A table may hold columns its type does not declare; they are
kept and never checked.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from functools import cache
from typing import Any, Literal

import pyarrow as pa
from jsonschema import Draft202012Validator

from ..ids import with_bare_ids
from ..manifest import UNIT_NUMBER_TYPES
from ..statements import calendar_date
from ..validate import PROVENANCE_DEFINITION, _select, load_schema
from ..validation.diagnostics import json_pointer, number_type_of, timelines_by_id
from .columns import (
    BELIEF_KEYS,
    COORDINATE_KEYS,
    MATCH_CLAIM_SCHEMA,
    PROJECTION_SCHEMA,
    PROVENANCE_KEYS,
    PROVENANCE_METADATA_KEY,
    SCOPE_FIELD,
    coordinate_value,
)

__all__ = [
    "TableCode",
    "TableError",
    "TableProblem",
    "check_match_claims",
    "check_projections",
    "check_succession",
    "match_claim_problems",
    "projection_problems",
    "row_provenance",
    "succession_problems",
]

TableCode = Literal[
    "schema_violation",
    "invalid_id",
    "duplicate_id",
    "invalid_coordinate",
    "claim_events",
    "claim_timelines",
    "claim_anchors",
    "invalid_certainty",
    "invalid_provenance",
    "axis_mismatch",
    "unknown_timeline",
    "invalid_projection_of",
    "invalid_duration",
    "succession_missing",
    "succession_changed",
]

Column = tuple[str, ...]


@dataclass(frozen=True)
class TableProblem:
    """One problem of a table: its code, its row (``None`` for the whole
    table), the path of its column and its message."""

    code: TableCode
    row: int | None
    column: Column
    message: str


class TableError(ValueError):
    """A table breaks a rule; ``problem`` is the first problem found."""

    def __init__(self, problem: TableProblem) -> None:
        super().__init__(problem.message)
        self.problem = problem


_CONTROL = re.compile("[\u0000-\u001f]")
_NUMBER_TYPES = ("int", "float", "fraction")
_REQUIRED_CLAIM = ("timeline_a_id", "timeline_b_id", "is_synchronous", "id")
_REQUIRED_PROJECTION = ("id", "timeline_id", "start")


def _shape(data_type: pa.DataType) -> Any:
    """A type's shape, blind to nullability and to the name of list items."""
    if pa.types.is_struct(data_type):
        return ("struct", tuple((f.name, _shape(f.type)) for f in data_type))
    if pa.types.is_list(data_type):
        return ("list", _shape(data_type.value_type))
    return str(data_type)


def _schema_problems(table: pa.Table, schema: pa.Schema) -> list[TableProblem]:
    problems = []
    for field in schema:
        if field.name not in table.column_names:
            problems.append(
                TableProblem(
                    "schema_violation",
                    None,
                    (field.name,),
                    f"the table has no column '{field.name}'",
                )
            )
        elif _shape(table.schema.field(field.name).type) != _shape(field.type):
            problems.append(
                TableProblem(
                    "schema_violation",
                    None,
                    (field.name,),
                    f"the column '{field.name}' is "
                    f"{table.schema.field(field.name).type}, not {field.type}",
                )
            )
    return problems


def _id_problem(value: Any, what: str) -> str | None:
    if value == "":
        return f"{what} is empty"
    if _CONTROL.search(value):
        return f"{what} {value!r} holds a control character"
    return None


def _coordinate_problem(cell: Mapping[str, Any]) -> str | None:
    """Why a non-null coordinate cell is malformed, or ``None``."""
    missing = [key for key in COORDINATE_KEYS if cell[key] is None]
    if missing:
        return f"the coordinate has no {', '.join(missing)}"
    if cell["unit"] not in UNIT_NUMBER_TYPES:
        return f"'{cell['unit']}' is no unit"
    if cell["number_type"] not in _NUMBER_TYPES:
        return f"'{cell['number_type']}' is no number type"
    if not math.isfinite(cell["value"]):
        return f"the coordinate's value {cell['value']} is not finite"
    if cell["denominator"] < 1:
        return f"the coordinate's denominator {cell['denominator']} is below 1"
    if cell["number_type"] == "int" and cell["denominator"] != 1:
        return f"an int coordinate has the denominator {cell['denominator']}"
    return None


@cache
def _provenance_validator() -> Draft202012Validator:
    """The validator of one provenance entry: the provenance schema's root."""
    definitions = load_schema()["$defs"]
    return Draft202012Validator(
        {"$defs": definitions, "$ref": f"#/$defs/{PROVENANCE_DEFINITION}"}
    )


def _present(cell: Mapping[str, Any]) -> dict[str, Any]:
    """A row's provenance cell as the entry it holds: a null member is absent."""
    entry = {key: value for key, value in cell.items() if value is not None}
    if "beliefs" in entry:
        entry["beliefs"] = [
            {key: value for key, value in belief.items() if value is not None}
            if isinstance(belief, Mapping)
            else belief
            for belief in entry["beliefs"]
        ]
    return entry


def _provenance_problem(entry: Any, what: str) -> str | None:
    """Why a provenance entry is no entry of the provenance schema, or ``None``.

    The schema first, its problem chosen by the validators' one path rule;
    then a key the schema does not declare, of the entry or of a belief;
    then a date that is no day of the Gregorian calendar; then an actor
    holding a second belief. ``what`` names the entry in the message, and
    the member at fault follows as a JSON pointer into it.
    """
    error = _select(_provenance_validator().iter_errors(entry))
    if error is not None:
        return f"{what} {json_pointer(error.absolute_path)}: {error.message}"
    beliefs = entry.get("beliefs", [])
    for keys, known, path, kind in (
        (entry, PROVENANCE_KEYS, (), "a provenance entry"),
        *(
            (belief, BELIEF_KEYS, ("beliefs", index), "a belief")
            for index, belief in enumerate(beliefs)
        ),
    ):
        unknown = sorted(set(keys) - set(known))
        if unknown:
            return f"{what} {json_pointer(path)}: '{unknown[0]}' is no key of {kind}"
    dates = [(("date",), entry["date"])] if "date" in entry else []
    dates.extend(
        (("beliefs", index, "date"), belief["date"])
        for index, belief in enumerate(beliefs)
    )
    for path, date in dates:
        try:
            calendar_date(date)
        except ValueError as problem:
            return f"{what} {json_pointer(path)}: {problem}"
    held: dict[str, int] = {}
    for index, belief in enumerate(beliefs):
        actor = belief["actor"]
        if actor in held:
            return (
                f"{what} {json_pointer(('beliefs', index, 'actor'))}: '{actor}' "
                f"already holds belief {held[actor]} of this entry; an actor holds "
                "one belief"
            )
        held[actor] = index
    return None


def _shared_provenance(table: pa.Table) -> tuple[dict[str, Any] | None, str | None]:
    """The provenance the file's metadata states for every row, and a problem.

    The entry is checked as a row's is, and returned with every member,
    an absent one ``None``, as a row's cell holds it.
    """
    metadata = table.schema.metadata or {}
    text = metadata.get(PROVENANCE_METADATA_KEY.encode())
    if text is None:
        return None, None
    try:
        entry = json.loads(text)
    except ValueError:
        return None, "the file's provenance is no JSON text"
    if not isinstance(entry, dict):
        return None, "the file's provenance is no object"
    problem = _provenance_problem(entry, "the file's provenance")
    if problem:
        return None, problem
    cell = {key: entry.get(key) for key in PROVENANCE_KEYS}
    if cell["beliefs"] is not None:
        cell["beliefs"] = [
            {key: belief.get(key) for key in BELIEF_KEYS} for belief in cell["beliefs"]
        ]
    return cell, None


def row_provenance(table: pa.Table) -> list[dict[str, Any] | None]:
    """The provenance of every row of a checked MatchClaim table: its own, or
    the file's where the row states none."""
    shared, _ = _shared_provenance(table)
    return [
        cell if cell is not None else shared
        for cell in table.column("provenance").to_pylist()
    ]


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

    def cell(
        self, row: int, column: Column, timeline_id: str, cell: Mapping[str, Any]
    ) -> TableProblem | None:
        axis = (cell["unit"], cell["number_type"])
        if self.timelines is not None:
            timeline = self.timelines.get(timeline_id)
            if timeline is None:
                return None
            own = (timeline["unit"], number_type_of(timeline))
            if axis != own:
                return TableProblem(
                    "axis_mismatch",
                    row,
                    column,
                    f"a coordinate in {axis[0]} ({axis[1]}) on the timeline "
                    f"'{timeline_id}' in {own[0]} ({own[1]})",
                )
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


def _ids(rows: list[dict[str, Any]], within: str) -> Iterator[TableProblem]:
    """Each ID valid, and given once within the value of the column ``within``.

    A MatchClaim's ID is unique in its scope (``scope``, null for the
    package's own), a Projection's on its timeline (``timeline_id``).
    """
    where = {"scope": "in the scope", "timeline_id": "on the timeline"}[within]
    seen: set[tuple[Any, str]] = set()
    for index, row in enumerate(rows):
        value = row["id"]
        if value is None:
            continue
        problem = _id_problem(value, "the ID")
        key = (row[within], value)
        if problem:
            yield TableProblem("invalid_id", index, ("id",), problem)
        elif key in seen:
            message = f"the ID '{value}' is given twice"
            if key[0] is not None:
                message += f" {where} '{key[0]}'"
            yield TableProblem("duplicate_id", index, ("id",), message)
        seen.add(key)


def _scope_problems(table: pa.Table) -> list[TableProblem]:
    """The problems of the optional ``scope`` column: its type."""
    name = SCOPE_FIELD.name
    if name in table.column_names and _shape(table.schema.field(name).type) != _shape(
        SCOPE_FIELD.type
    ):
        return [
            TableProblem(
                "schema_violation",
                None,
                (name,),
                f"the column '{name}' is {table.schema.field(name).type}, "
                f"not {SCOPE_FIELD.type}",
            )
        ]
    return []


def _claim_rows(table: pa.Table) -> list[dict[str, Any]]:
    """The rows of a MatchClaim table, each with its ``scope``, null where the
    table has no such column."""
    names = list(MATCH_CLAIM_SCHEMA.names)
    if SCOPE_FIELD.name in table.column_names:
        return table.select([*names, SCOPE_FIELD.name]).to_pylist()
    return [{**row, SCOPE_FIELD.name: None} for row in table.select(names).to_pylist()]


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
        if row[key] is not None:
            problem = _id_problem(row[key], "the event ID")
            if problem:
                yield TableProblem("invalid_id", index, (key,), problem)
    event_a, event_b = row["event_a_id"], row["event_b_id"]
    start, end = row["start_anchor"], row["end_anchor"]
    if event_a is None and event_b is None:
        yield TableProblem(
            "claim_events", index, ("event_a_id",), "the MatchClaim names no event"
        )
    elif event_a is None or event_b is None:
        if row["is_synchronous"]:
            yield TableProblem(
                "claim_anchors",
                index,
                ("is_synchronous",),
                "a NOMATCH MatchClaim is not synchronous",
            )
        elif start is not None or end is not None:
            yield TableProblem(
                "claim_anchors",
                index,
                ("start_anchor" if start is not None else "end_anchor",),
                "a NOMATCH MatchClaim has no anchors",
            )
    elif row["is_synchronous"]:
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
            "a conceptual MatchClaim has no anchors",
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
    if cell is None:
        yield TableProblem(
            "invalid_coordinate", index, column, "the coordinate is null"
        )
        return
    problem = _coordinate_problem(cell)
    if problem:
        yield TableProblem("invalid_coordinate", index, column, problem)
        return
    axis = axes.cell(index, column, timeline_id, cell)
    if axis:
        yield axis


def match_claim_problems(
    table: pa.Table, manifest: Mapping[str, Any] | None = None
) -> list[TableProblem]:
    """Every problem of a MatchClaim table, checked against a manifest (as
    read from its file, IDs written ``#``) where one is given.

    A MatchClaim's ID is unique in its scope: the package's own, where the
    table has no ``scope`` column or the row's is null, else the scope it
    names (:data:`~timetoshare.tables.SCOPE_FIELD`)."""
    problems = [
        *_schema_problems(table, MATCH_CLAIM_SCHEMA),
        *_scope_problems(table),
    ]
    if problems:
        return problems
    rows = _claim_rows(table)
    problems = [*_nulls(rows, _REQUIRED_CLAIM)]
    if problems:
        return problems
    for index, row in enumerate(rows):
        if row["scope"] is not None:
            problem = _id_problem(row["scope"], "the scope")
            if problem:
                problems.append(TableProblem("invalid_id", index, ("scope",), problem))
    problems.extend(_ids(rows, "scope"))
    shared = PROVENANCE_METADATA_KEY.encode() in (table.schema.metadata or {})
    _, problem = _shared_provenance(table)
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
                else _provenance_problem(_present(cell), "the provenance")
            )
            if problem:
                problems.append(
                    TableProblem("invalid_provenance", index, ("provenance",), problem)
                )
    return sorted(problems, key=_order)


def projection_problems(
    table: pa.Table, manifest: Mapping[str, Any] | None = None
) -> list[TableProblem]:
    """Every problem of a Projections table, checked against a manifest (as
    read from its file, IDs written ``#``) where one is given.

    A Projection's ID is unique on its timeline, as every event's: two
    timelines may each hold ``projection_1``."""
    problems = _schema_problems(table, PROJECTION_SCHEMA)
    if problems:
        return problems
    rows = table.select(list(PROJECTION_SCHEMA.names)).to_pylist()
    problems = [*_nulls(rows, _REQUIRED_PROJECTION)]
    if problems:
        return problems
    problems.extend(_ids(rows, "timeline_id"))
    axes = _Axes(manifest)
    for index, row in enumerate(rows):
        timeline_id = row["timeline_id"]
        problem = axes.timeline(index, ("timeline_id",), timeline_id)
        if problem:
            problems.append(problem)
        problems.extend(
            _cell_problems(index, ("start",), timeline_id, row["start"], axes)
        )
        duration = row["duration"]
        if duration is not None:
            found = list(
                _cell_problems(index, ("duration",), timeline_id, duration, axes)
            )
            problems.extend(found)
            if not found and coordinate_value(duration) < 0:
                problems.append(
                    TableProblem(
                        "invalid_duration",
                        index,
                        ("duration",),
                        "the duration is negative",
                    )
                )
        source = row["projection_of"]
        if source is None:
            continue
        for key in ("timeline_id", "event_id"):
            if not source[key]:
                problems.append(
                    TableProblem(
                        "invalid_projection_of",
                        index,
                        ("projection_of", key),
                        f"the projected event has no {key}",
                    )
                )
        if source["timeline_id"] == timeline_id:
            problems.append(
                TableProblem(
                    "invalid_projection_of",
                    index,
                    ("projection_of", "timeline_id"),
                    f"a Projection stands for an event of another timeline than "
                    f"'{timeline_id}'",
                )
            )
        elif source["timeline_id"]:
            problem = axes.timeline(
                index, ("projection_of", "timeline_id"), source["timeline_id"]
            )
            if problem:
                problems.append(problem)
    return sorted(problems, key=_order)


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

    Both are checked MatchClaim tables. A MatchClaim is its scope and its
    ID (a table without a ``scope`` column holds the package's own alone).
    Every MatchClaim of ``old`` is in ``new``, and its row has the same
    value in every column but ``provenance``; a coordinate is the same when
    its unit, number type and exact value are. The rows of ``new`` are
    reported by their index in ``new``.
    """
    columns = [name for name in MATCH_CLAIM_SCHEMA.names if name != "provenance"]
    later = {
        (row["scope"], row["id"]): (index, row)
        for index, row in reversed(list(enumerate(_claim_rows(new))))
    }
    problems = []
    for row in _claim_rows(old):
        name = f"the MatchClaim '{row['id']}'"
        if row["scope"] is not None:
            name += f" of the scope '{row['scope']}'"
        found = later.get((row["scope"], row["id"]))
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


def _first(problems: list[TableProblem]) -> None:
    if problems:
        raise TableError(problems[0])


def check_match_claims(
    table: pa.Table, manifest: Mapping[str, Any] | None = None
) -> None:
    """Raise ``TableError`` for the first problem of a MatchClaim table."""
    _first(match_claim_problems(table, manifest))


def check_projections(
    table: pa.Table, manifest: Mapping[str, Any] | None = None
) -> None:
    """Raise ``TableError`` for the first problem of a Projections table."""
    _first(projection_problems(table, manifest))


def check_succession(old: pa.Table, new: pa.Table) -> None:
    """Raise ``TableError`` for the first breach of the succession rule."""
    _first(succession_problems(old, new))
