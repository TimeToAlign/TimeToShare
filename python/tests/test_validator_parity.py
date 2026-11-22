"""The compiled schema check changes no diagnostic of the validator."""

from __future__ import annotations

import copy
import random
from collections.abc import Callable, Iterator
from functools import cache
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from tests.large_manifests import long_tables, many_timestamps
from tests.reference import ids as reference_ids
from tests.reference import validate as reference
from timetoshare import loads, with_bare_ids, with_file_ids
from timetoshare.fixtures import (
    fixture_paths,
    rejection_case,
    rejection_paths,
    warning_paths,
)
from timetoshare.validation.diagnostics import SchemaValidationError
from timetoshare.validation.schema_check import compiled_check

current = import_module("timetoshare.validate")

SEED = 20261122
MUTATIONS = 100
"""Mutations of each kind."""


def _problem(problem: Any) -> Any:
    if isinstance(problem, SchemaValidationError):
        return (problem.code, tuple(problem.path), problem.message)
    return problem


def _outcome(call: Callable[[Any], Any], value: Any) -> Any:
    """The error ``call`` raises, or what it returns, as comparable data."""
    try:
        result = call(value)
    except SchemaValidationError as error:
        return ("SchemaValidationError", error.code, tuple(error.path), error.message)
    except Exception as error:  # every other error is compared by class and text
        return (type(error).__name__, str(error))
    if isinstance(result, tuple):
        return tuple([_problem(item) for item in part] for part in result)
    if isinstance(result, list):
        return [_problem(item) for item in result]
    return result


def _outcomes(module: Any, value: Any) -> dict[str, Any]:
    """The outcomes of one implementation; ``value`` is copied for each call.

    ``validate``, ``unknown_keys`` and ``manifest_warnings`` are the one
    check ``_check`` (the first discarding its lists, the others returning
    one), so its outcome stands for all three.
    """
    return {
        name: _outcome(getattr(module, name), copy.deepcopy(value))
        for name in (
            "_check",
            "identity_problems",
            "statement_problems",
            "matchstamp_problems",
        )
    }


@cache
def _closed_walk() -> Any:
    return Draft202012Validator(reference._closed_document())


def _assert_same(value: Any) -> None:
    assert _outcomes(current, value) == _outcomes(reference, value)
    walked = next(_closed_walk().iter_errors(value), None) is None
    assert current._marking_check()(copy.deepcopy(value)) is walked


def _read(path: Path) -> Any:
    return loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", fixture_paths(), ids=lambda path: path.name)
def test_a_fixture_has_the_reference_outcome(path: Path) -> None:
    _assert_same(_read(path))


@pytest.mark.parametrize("path", rejection_paths(), ids=lambda path: path.name)
def test_a_rejection_case_has_the_reference_outcome(path: Path) -> None:
    _assert_same(rejection_case(path).manifest)


@pytest.mark.parametrize("path", warning_paths(), ids=lambda path: path.name)
def test_a_warning_case_has_the_reference_outcome(path: Path) -> None:
    _assert_same(_read(path)["manifest"])


@pytest.mark.parametrize("build", [many_timestamps, long_tables])
def test_a_large_manifest_has_the_reference_outcome(
    build: Callable[[], Any],
) -> None:
    _assert_same(build())


# Mutations of the valid fixtures.

_REPLACEMENTS: tuple[Any, ...] = ("text", 7, 2.5, True, None, [], {})


def _kind(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return repr(value)
    if isinstance(value, int | float):
        return "number"
    return type(value).__name__


def _places(value: Any) -> Iterator[tuple[Any, Any]]:
    """Every member position ``(container, key or index)``, depth first."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield value, key
            yield from _places(item)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield value, index
            yield from _places(item)


def _objects(value: Any) -> list[dict[str, Any]]:
    found = [value] if isinstance(value, dict) else []
    return found + [
        item
        for container, key in _places(value)
        if isinstance(container[key], dict)
        for item in [container[key]]
    ]


@cache
def _valid() -> tuple[Any, ...]:
    return tuple(_read(path) for path in fixture_paths())


def _mutated(kind: str, number: int) -> Any:
    """The ``number``-th mutation of ``kind``, drawn from its own seeded stream."""
    draw = random.Random(f"{SEED}-{kind}-{number}")
    while True:
        value = copy.deepcopy(draw.choice(_valid()))
        if kind == "delete":
            target = draw.choice([item for item in _objects(value) if item])
            del target[draw.choice(sorted(target))]
            return value
        if kind == "retype":
            container, key = draw.choice(list(_places(value)))
            kinds = [
                each for each in _REPLACEMENTS if _kind(each) != _kind(container[key])
            ]
            container[key] = copy.deepcopy(draw.choice(kinds))
            return value
        if kind == "unknown":
            draw.choice(_objects(value))["undeclared_key"] = 1
            return value
        holders = [item for item in _objects(value) if isinstance(item.get("id"), str)]
        if len(holders) >= 2:
            first, second = draw.sample(holders, 2)
            second["id"] = first["id"]
            return value


@pytest.mark.parametrize("number", range(MUTATIONS))
@pytest.mark.parametrize("kind", ["delete", "retype", "unknown", "duplicate"])
def test_a_mutated_fixture_has_the_reference_outcome(kind: str, number: int) -> None:
    _assert_same(_mutated(kind, number))


def test_the_mutations_reach_refusals_and_unknown_keys() -> None:
    """The mutations exercise the walk's diagnostics, not only valid manifests."""
    outcomes = {
        kind: [_outcome(current._check, _mutated(kind, n)) for n in range(MUTATIONS)]
        for kind in ("delete", "retype", "unknown", "duplicate")
    }
    for kind, found in outcomes.items():
        refused = [each for each in found if each[0] == "SchemaValidationError"]
        assert refused, kind
    accepted = [each for each in outcomes["unknown"] if isinstance(each[0], list)]
    assert any(keys for keys, _ in accepted)


# The walk is skipped where the check finds nothing.


class _CountingWalk:
    def __init__(self) -> None:
        self.calls = 0
        self.walk = current._marking_validator()

    def iter_errors(self, value: Any) -> Any:
        self.calls += 1
        return self.walk.iter_errors(value)


@pytest.mark.parametrize(
    "build",
    [
        many_timestamps,
        long_tables,
        lambda: _read(fixture_paths()[0]),
    ],
    ids=["many_timestamps", "long_tables", "first_fixture"],
)
def test_a_valid_manifest_validates_without_the_walk(
    build: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    walk = _CountingWalk()
    monkeypatch.setattr(current, "_marking_validator", lambda: walk)
    current.validate(build())
    assert walk.calls == 0


def test_an_undeclared_key_takes_the_walk_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    walk = _CountingWalk()
    monkeypatch.setattr(current, "_marking_validator", lambda: walk)
    value = _read(fixture_paths()[0])
    value["undeclared_key"] = 1
    assert current.unknown_keys(value) == [{"path": [], "key": "undeclared_key"}]
    assert walk.calls == 1


# The compiled check shares the walk's keyword semantics.

_SEMANTICS: list[tuple[dict[str, Any], list[Any]]] = [
    ({"const": 1}, [1, 1.0, True, "1", [1]]),
    ({"const": True}, [True, 1, False]),
    (
        {"const": [1, {"a": True}]},
        [[1, {"a": True}], [1, {"a": 1}], [True, {"a": True}]],
    ),
    ({"enum": [1, "x"]}, [1, True, "x", 1.0, None]),
    ({"enum": ["a", "b"]}, ["a", "c", 1, None]),
    ({"uniqueItems": True}, [[1, True], [1, 1.0], [[1], [True]], [{"a": 1}, {"a": 1}]]),
    ({"type": "integer"}, [1, 1.0, 1.5, True, "1", None]),
    ({"type": "number"}, [1, 1.5, True, None, "1"]),
    ({"type": ["string", "null"]}, ["a", None, 1]),
    ({"pattern": "^[a-z]"}, ["abc", "Abc", "1", 1, "xyz\n"]),
    ({"minLength": 2, "maxLength": 3}, ["a", "ab", "abcd", "𝅝𝅝", 5]),
    ({"minimum": 1, "exclusiveMaximum": 3}, [0, 1, 2.5, 3, True, "2"]),
    ({"minItems": 1, "maxItems": 2}, [[], [1], [1, 2, 3], "ab"]),
    (
        {"required": ["a"], "minProperties": 2},
        [{"a": 1}, {"a": 1, "b": 2}, {"b": 1}, []],
    ),
    ({"dependentRequired": {"a": ["b"]}}, [{"a": 1}, {"a": 1, "b": 1}, {"b": 1}]),
    (
        {"prefixItems": [{"type": "integer"}], "items": False},
        [[1], [1, 2], ["x"], [], {}],
    ),
    ({"propertyNames": {"pattern": "^x"}}, [{"xa": 1}, {"ya": 1}, {}]),
    (
        {"properties": {"a": {"type": "string"}}, "additionalProperties": False},
        [{"a": "x"}, {"a": 1}, {"b": 1}, "s"],
    ),
    (
        {"properties": {"a": {}}, "additionalProperties": {"type": "integer"}},
        [{"a": "x", "b": 1}, {"b": "x"}],
    ),
    ({"oneOf": [{"type": "integer"}, {"minimum": 0}]}, [1, -1, 0.5, -0.5, "x"]),
    ({"anyOf": [{"type": "string"}, {"type": "null"}]}, ["a", None, 1]),
    ({"not": {"type": "string"}}, ["a", 1]),
    (
        {"if": {"properties": {"a": {"const": 1}}}, "then": {"required": ["b"]}},
        [{"a": 1}, {"a": 1, "b": 0}, {"a": 2}],
    ),
    (
        {
            "type": "object",
            "properties": {"kind": {}},
            "oneOf": [
                {"properties": {"kind": {"const": "a"}, "x": {}}},
                {"properties": {"kind": {"const": "b"}, "y": {}}},
            ],
            "unevaluatedProperties": False,
        },
        [
            {"kind": "a", "x": 1},
            {"kind": "a", "y": 1},
            {"kind": "b", "y": 1},
            {"kind": "c"},
        ],
    ),
    (
        {
            "$defs": {"Base": {"properties": {"id": {"type": "string"}}}},
            "allOf": [{"$ref": "#/$defs/Base"}],
            "properties": {"name": {}},
            "unevaluatedProperties": False,
        },
        [{"id": "x", "name": 1}, {"id": 1}, {"other": 1}],
    ),
    (
        {
            "if": {"required": ["a"]},
            "then": {"properties": {"b": {}}},
            "else": {"properties": {"c": {}}},
            "properties": {"a": {}},
            "unevaluatedProperties": False,
        },
        [{"a": 1, "b": 1}, {"a": 1, "c": 1}, {"c": 1}, {"b": 1}],
    ),
    ({"items": True, "additionalProperties": True}, [[1], {"a": 1}]),
    (True, [1, None]),
    (False, [1, None]),
]


@pytest.mark.parametrize(("schema", "values"), _SEMANTICS)
def test_the_check_answers_as_the_walk_on_each_keyword(
    schema: Any, values: list[Any]
) -> None:
    check = compiled_check(schema if isinstance(schema, dict) else {}, schema)
    walk = Draft202012Validator(schema)
    assert [check(value) for value in values] == [
        walk.is_valid(value) for value in values
    ]


@pytest.mark.parametrize(
    "schema",
    [
        {"patternProperties": {"^x": {}}},
        {"dependentSchemas": {"a": {}}},
        {"contains": {}},
        {"$ref": "other.json#/$defs/A"},
    ],
    ids=["patternProperties", "dependentSchemas", "contains", "foreign reference"],
)
def test_a_schema_the_check_does_not_know_refuses_to_compile(schema: Any) -> None:
    with pytest.raises(NotImplementedError):
        compiled_check(schema, schema)


# The faster copies stay copies.


def _containers(value: Any) -> Iterator[Any]:
    if isinstance(value, dict | list):
        yield value
        for item in value.values() if isinstance(value, dict) else value:
            yield from _containers(item)


@pytest.mark.parametrize("path", fixture_paths(), ids=lambda path: path.name)
def test_the_id_conversions_give_the_reference_copies(path: Path) -> None:
    value = _read(path)
    bare = with_bare_ids(value)
    assert bare == reference_ids.with_bare_ids(value)
    filed = with_file_ids(bare)
    assert filed == reference_ids.with_file_ids(bare)
    assert filed == value
    held = {id(each) for each in _containers(value)}
    assert not held & {id(each) for each in _containers(bare)}
    assert not {id(each) for each in _containers(bare)} & {
        id(each) for each in _containers(filed)
    }
