"""The row-by-row checks of the two tables, kept as the reference.

The package's checks (``timetoshare.tables``) find their problems column by
column; this module is the implementation they replaced, one row at a time,
kept unchanged but for its imports so that ``test_table_checks.py`` can
compare the two on every table it builds. It is no part of the package.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterator, Mapping
from functools import cache
from typing import Any

import pyarrow as pa
from jsonschema import Draft202012Validator

from timetoshare.ids import with_bare_ids
from timetoshare.manifest import UNITS
from timetoshare.statements import calendar_date, expand_iri
from timetoshare.tables import TableProblem
from timetoshare.tables.columns import (
    BELIEF_KEYS,
    COORDINATE_KEYS,
    MATCH_CLAIM_REQUIRED,
    MATCH_CLAIM_SCHEMA,
    NUMBER_KEYS,
    NUMBER_MEMBERS,
    PROJECTION_REQUIRED,
    PROJECTION_SCHEMA,
    PROVENANCE_KEYS,
    PROVENANCE_METADATA_KEY,
    coordinate_value,
)
from timetoshare.validate import PROVENANCE_DEFINITION, load_schema, select, worded
from timetoshare.validation.diagnostics import (
    json_pointer,
    number_type_of,
    timelines_by_id,
)

__all__ = ["match_claim_problems", "projection_problems", "succession_problems"]

Column = tuple[str, ...]


_CONTROL = re.compile("[\u0000-\u001f]")


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


def _axis_problem(unit: str, number_type: str) -> str | None:
    """Why a unit and a number type, both stated, are no axis, or ``None``.

    The unit is one of :data:`~timetoshare.UNITS`, the number type one of the
    three, and one the unit admits."""
    if unit not in UNITS:
        return f"'{unit}' is no unit"
    if number_type not in NUMBER_MEMBERS:
        return f"'{number_type}' is no number type"
    if number_type not in UNITS[unit].number_types:
        return f"'{unit}' admits no number type '{number_type}'"
    return None


def _number_problem(
    number: Mapping[str, Any], number_type: str, what: str
) -> str | None:
    """Why a non-null number is no number of ``number_type``, or ``None``.

    A number fills the members of its number type and leaves the others
    null (:data:`~timetoshare.tables.NUMBER_MEMBERS`); a float is finite, a
    fraction's denominator at least 1.
    """
    held = NUMBER_MEMBERS[number_type]
    kind = f"{'an' if number_type == 'int' else 'a'} {number_type} {what}"
    for key in held:
        if number[key] is None:
            return f"{kind} has no {key}"
    for key in NUMBER_KEYS:
        if key not in held and number[key] is not None:
            return f"{kind} holds its {' and '.join(held)} alone, not a {key}"
    if number_type == "float" and not math.isfinite(number["value"]):
        return f"the {what}'s value {number['value']} is not finite"
    if number_type == "fraction" and number["denominator"] < 1:
        return f"the {what}'s denominator {number['denominator']} is below 1"
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


def _provenance_problem(
    entry: Any, what: str, context: Mapping[str, Any] | None
) -> str | None:
    """Why a provenance entry is no entry of the provenance schema, or ``None``.

    The schema first, its problem chosen by the validators' one path rule;
    then a key the schema does not declare, of the entry or of a belief;
    then a date that is no day of the Gregorian calendar; then an actor
    holding a second belief, actors compared as the IRIs they stand for
    under ``context`` (the manifest's ``@context``), else as written.
    ``what`` names the entry in the message, and the member at fault follows
    as a JSON pointer into it.
    """
    error = select(_provenance_validator().iter_errors(entry))
    if error is not None:
        return f"{what} {json_pointer(error.absolute_path)}: {worded(error)}"
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
        actor = expand_iri(context, belief["actor"]) or belief["actor"]
        if actor in held:
            return (
                f"{what} {json_pointer(('beliefs', index, 'actor'))}: "
                f"'{belief['actor']}' already holds belief {held[actor]} of this "
                "entry; an actor holds one belief"
            )
        held[actor] = index
    return None


def _shared_provenance(
    table: pa.Table, context: Mapping[str, Any] | None = None
) -> tuple[dict[str, Any] | None, str | None]:
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
    problem = _provenance_problem(entry, "the file's provenance", context)
    if problem:
        return None, problem
    cell = {key: entry.get(key) for key in PROVENANCE_KEYS}
    if cell["beliefs"] is not None:
        cell["beliefs"] = [
            {key: belief.get(key) for key in BELIEF_KEYS} for belief in cell["beliefs"]
        ]
    return cell, None


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
            return (timeline["unit"], number_type_of(timeline))
        return self.seen.get(timeline_id)

    def axis(
        self, row: int, column: Column, timeline_id: str, axis: tuple[str, str]
    ) -> TableProblem | None:
        """The problem of a unit and a number type on the timeline, or ``None``."""
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


def projection_problems(
    table: pa.Table, manifest: Mapping[str, Any] | None = None
) -> list[TableProblem]:
    """Every problem of a Projections table, checked against a manifest (as
    read from its file, IDs written ``#``) where one is given.

    A Projection's ID is unique in the package, as every event's: two
    timelines never both hold ``projection_1``."""
    problems = _schema_problems(table, PROJECTION_SCHEMA)
    if problems:
        return problems
    rows = table.select(list(PROJECTION_SCHEMA.names)).to_pylist()
    problems = [*_nulls(rows, PROJECTION_REQUIRED)]
    if problems:
        return problems
    problems.extend(_ids(rows))
    axes = _Axes(manifest)
    for index, row in enumerate(rows):
        timeline_id = row["timeline_id"]
        problem = axes.timeline(index, ("timeline_id",), timeline_id)
        if problem:
            problems.append(problem)
        problems.extend(_projection_numbers(index, row, axes))
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


def _projection_numbers(
    index: int, row: Mapping[str, Any], axes: _Axes
) -> Iterator[TableProblem]:
    """The problems of a Projection's axis, ``start`` and ``duration``: its
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
