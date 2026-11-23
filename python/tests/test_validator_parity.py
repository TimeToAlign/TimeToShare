"""The schema gate changes no outcome of the validator.

The strategy is the README's section "The schema gate": four facts, each
asserted on every input, from which every outcome follows.
"""

from __future__ import annotations

import copy
import math
import random
from collections import OrderedDict, defaultdict
from collections.abc import Callable, Iterator
from decimal import Decimal
from fractions import Fraction
from functools import cache
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

from tests.large_manifests import long_tables, many_timestamps
from timetoshare import loads, with_bare_ids, with_file_ids
from timetoshare.fixtures import (
    fixture_paths,
    rejection_case,
    rejection_paths,
    warning_paths,
)
from timetoshare.ids import _copied, leniently_bare_ids
from timetoshare.validation.representation import (
    finite_number_problems,
    plainly_finite,
)

current = import_module("timetoshare.validate")

SEED = 20261123
MUTATIONS = 60
"""Mutations of each kind."""
SEARCH = 3000
"""How far the mutations of a kind are enumerated for an answer they must reach."""
DEFINITION_CASES = 600
"""Mutated sub-values checked against one definition each."""


def _read(path: Path) -> Any:
    return loads(path.read_text(encoding="utf-8"))


# The four facts.

_PLAIN_ATOMS = frozenset({str, int, float, bool, type(None)})


def _plain(value: Any) -> bool:
    """Whether ``value`` is plain JSON data: exact types, string keys."""
    kind = type(value)
    if kind in _PLAIN_ATOMS:
        return True
    if kind is list:
        return all(_plain(item) for item in value)
    if kind is dict:
        return all(type(key) is str and _plain(item) for key, item in value.items())
    return False


def _assert_gate_answers_as_the_walk(schema: Any, value: Any) -> bool | None:
    """Fact 1: on plain finite data the gate answers "valid" exactly where
    the one path rule finds nothing among the walk's errors, with the walk's
    keys; ``None`` where the gate is not asked."""
    if not (_plain(value) and plainly_finite(value)):
        return None
    keys = schema.gated(value)
    errors = list(schema.walk.iter_errors(value))
    clean = current.select(errors) is None
    assert (keys is not None) is clean
    if keys is not None:
        assert keys == set(current._keys(errors))
    return clean


def _result(call: Callable[[], Any]) -> Any:
    """What ``call`` returns, problems as tuples, or what it raises."""
    try:
        returned = call()
    except Exception as error:
        return (
            type(error).__name__,
            getattr(error, "code", None),
            tuple(getattr(error, "path", ())),
            str(error),
        )
    if isinstance(returned, list):
        return [
            (problem.code, tuple(problem.path), problem.message) for problem in returned
        ]
    return ("valid", *returned)


def _outcome(value: Any) -> tuple[Any, ...]:
    """What ``validate``, ``statement_problems`` and ``matchstamp_problems``
    give for ``value``: a raised error by type, code, path and message, else
    the unknown keys and the warnings, and the two lists of problems."""
    return (
        _result(lambda: current._check(value)),
        _result(lambda: current.statement_problems(value)),
        _result(lambda: current.matchstamp_problems(value)),
    )


def _assert_outcome_is_the_walks(value: Any) -> tuple[Any, ...]:
    """Fact 2: the outcome is the one with the gate removed."""
    gated = _outcome(value)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(current._Schema, "gated", lambda self, value: None)
        walked = _outcome(value)
    assert gated == walked
    return gated


def _assert_finite_rule_skipped_soundly(value: Any) -> None:
    """Fact 3: ``plainly_finite`` implies the finite rule finds nothing."""
    if plainly_finite(value):
        assert next(finite_number_problems(leniently_bare_ids(value)), None) is None


def _nodes(value: Any) -> Iterator[Any]:
    """Every node of ``value``, keys included, depth first."""
    yield value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _nodes(key)
            yield from _nodes(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _nodes(item)


def _containers(value: Any) -> set[int]:
    return {id(node) for node in _nodes(value) if isinstance(node, dict | list)}


def _assert_copied(value: Any) -> None:
    """Fact 4: the conversions' copy is ``copy.deepcopy``'s, sharing nothing."""
    copied = _copied(value)
    expected = copy.deepcopy(value)
    assert copied == expected
    assert [type(node) for node in _nodes(copied)] == [
        type(node) for node in _nodes(expected)
    ]
    assert not _containers(value) & _containers(copied)


def _assert_facts(value: Any) -> tuple[Any, ...]:
    """The four facts on ``value``; its outcome."""
    _assert_gate_answers_as_the_walk(current._manifest_schema(), value)
    outcome = _assert_outcome_is_the_walks(value)
    _assert_finite_rule_skipped_soundly(value)
    _assert_copied(value)
    return outcome


def _valid(outcome: tuple[Any, ...]) -> bool:
    return outcome[0][0] == "valid"


@pytest.mark.parametrize("path", fixture_paths(), ids=lambda path: path.name)
def test_a_fixture_holds_the_facts(path: Path) -> None:
    assert _valid(_assert_facts(_read(path)))


@pytest.mark.parametrize("path", rejection_paths(), ids=lambda path: path.name)
def test_a_rejection_case_holds_the_facts(path: Path) -> None:
    _assert_facts(rejection_case(path).manifest)


@pytest.mark.parametrize("path", warning_paths(), ids=lambda path: path.name)
def test_a_warning_case_holds_the_facts(path: Path) -> None:
    assert _valid(_assert_facts(_read(path)["manifest"]))


@pytest.mark.parametrize("build", [many_timestamps, long_tables])
def test_a_large_manifest_holds_the_facts(build: Callable[[], Any]) -> None:
    assert _valid(_assert_facts(build()))


@pytest.mark.parametrize("path", fixture_paths(), ids=lambda path: path.name)
def test_the_id_conversions_give_the_fixture_back_sharing_nothing(path: Path) -> None:
    value = _read(path)
    bare = with_bare_ids(value)
    filed = with_file_ids(bare)
    assert filed == value
    assert not _containers(value) & _containers(bare)
    assert not _containers(bare) & _containers(filed)


# Mutations.


def _schema_strings() -> list[str]:
    """Every ``const`` and ``enum`` string of the closed document."""
    found: set[str] = set()
    for node in _nodes(current._closed_document()):
        if isinstance(node, dict):
            if isinstance(node.get("const"), str):
                found.add(node["const"])
            if isinstance(node.get("enum"), list):
                found.update(each for each in node["enum"] if isinstance(each, str))
    return sorted(found)


_STRINGS = _schema_strings()

_REPLACEMENTS: tuple[Any, ...] = ("text", 7, 2.5, True, None, [], {})

_PAIRS: tuple[tuple[Any, Any], ...] = (
    (1, True),
    (0, False),
    (1, 1.0),
    ([1, 2], [1.0, 2]),
    ({"a": 1}, {"a": 1.0}),
)

_EXTREMES: tuple[Any, ...] = (
    math.nan,
    math.inf,
    -math.inf,
    2**53 + 1,
    2**64,
    10**400,
    -(2**53) - 1,
)


class _DictSub(dict):
    pass


class _ListSub(list):
    pass


class _StrSub(str):
    pass


class _IntSub(int):
    pass


class _FloatSub(float):
    pass


class _Lying(dict):
    """A dictionary whose ``keys()`` disagrees with its iteration."""

    def keys(self) -> Any:
        return set()


_FOREIGN: tuple[Any, ...] = (
    Fraction(1, 3),
    Decimal("1.5"),
    (1, 2),
    b"x",
    complex(1, 1),
)


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
    return [node for node in _nodes(value) if type(node) is dict]


def _arrays(value: Any) -> list[list[Any]]:
    return [node for node in _nodes(value) if type(node) is list]


def _foreign(value: Any, draw: random.Random) -> Any:
    """A Python value that is no JSON, in place of ``value``."""
    options = list(_FOREIGN)
    if type(value) is dict:
        options += [
            OrderedDict(value),
            defaultdict(list, value),
            _DictSub(value),
            _Lying(value),
        ]
    elif type(value) is list:
        options += [_ListSub(value), tuple(value)]
    elif type(value) is str:
        options.append(_StrSub(value))
    elif type(value) is int:
        options.append(_IntSub(value))
    elif type(value) is float:
        options.append(_FloatSub(value))
    return draw.choice(options)


def _mutate(kind: str, value: Any, draw: random.Random) -> bool:
    """Mutate ``value`` in place by one operator; ``False`` where none applies."""
    places = list(_places(value))
    objects = _objects(value)
    if kind == "delete":
        filled = [each for each in objects if each]
        if not filled:
            return False
        target = draw.choice(filled)
        del target[draw.choice(sorted(target))]
    elif kind == "retype":
        if not places:
            return False
        container, key = draw.choice(places)
        kinds = [each for each in _REPLACEMENTS if _kind(each) != _kind(container[key])]
        container[key] = copy.deepcopy(draw.choice(kinds))
    elif kind == "unknown":
        if not objects:
            return False
        draw.choice(objects)["undeclared_key"] = 1
    elif kind == "duplicate":
        holders = [each for each in objects if isinstance(each.get("id"), str)]
        if len(holders) < 2:
            return False
        first, second = draw.sample(holders, 2)
        second["id"] = first["id"]
    elif kind == "string":
        texts = [(c, k) for c, k in places if isinstance(c[k], str)]
        if not texts:
            return False
        container, key = draw.choice(texts)
        container[key] = draw.choice(_STRINGS)
    elif kind == "copy_key":
        filled = [each for each in objects if each]
        if not filled or len(objects) < 2:
            return False
        source = draw.choice(filled)
        target = draw.choice([each for each in objects if each is not source])
        key = draw.choice(sorted(source))
        target[key] = copy.deepcopy(source[key])
    elif kind == "pair":
        arrays = _arrays(value)
        if not arrays:
            return False
        array = draw.choice(arrays)
        if array and draw.random() < 0.5:
            array.append(copy.deepcopy(draw.choice(array)))
        else:
            array.extend(copy.deepcopy(draw.choice(_PAIRS)))
    elif kind == "extreme":
        if not places:
            return False
        container, key = draw.choice(places)
        container[key] = draw.choice(_EXTREMES)
    elif kind == "python":
        if objects and draw.random() < 0.2:
            draw.choice(objects)[draw.choice([1, None, (1, 2)])] = "x"
        elif places:
            container, key = draw.choice(places)
            container[key] = _foreign(container[key], draw)
        else:
            return False
    else:
        raise ValueError(kind)
    return True


KINDS = (
    "delete",
    "retype",
    "unknown",
    "duplicate",
    "string",
    "copy_key",
    "pair",
    "extreme",
    "python",
)


@cache
def _valid_fixtures() -> tuple[Any, ...]:
    return tuple(_read(path) for path in fixture_paths())


def _mutated(kind: str, number: int) -> Any:
    """The ``number``-th mutation of ``kind``, drawn from its own seeded stream."""
    draw = random.Random(f"{SEED}-{kind}-{number}")
    while True:
        value = copy.deepcopy(draw.choice(_valid_fixtures()))
        if _mutate(kind, value, draw):
            return value


@pytest.mark.parametrize("number", range(MUTATIONS))
@pytest.mark.parametrize("kind", KINDS)
def test_a_mutated_fixture_holds_the_facts(kind: str, number: int) -> None:
    _assert_facts(_mutated(kind, number))


def _first_mutation(kind: str, sought: Callable[[tuple[Any, ...]], bool]) -> int:
    """The number of the first mutation of ``kind`` whose outcome is sought,
    the facts asserted on it; ``SEARCH`` where none of the first is."""
    for number in range(SEARCH):
        value = _mutated(kind, number)
        if sought(_outcome(value)):
            assert sought(_assert_facts(value))
            return number
    return SEARCH


@pytest.mark.parametrize("valid", [True, False])
@pytest.mark.parametrize("kind", KINDS)
def test_the_mutations_of_a_kind_reach_both_answers(kind: str, valid: bool) -> None:
    """The mutations exercise valid and invalid manifests, not only one."""
    number = _first_mutation(kind, lambda outcome: _valid(outcome) is valid)
    assert number < SEARCH


def test_an_undeclared_key_reaches_valid_manifests_with_listed_keys() -> None:
    number = _first_mutation(
        "unknown", lambda outcome: _valid(outcome) and bool(outcome[0][1])
    )
    assert number < SEARCH


# Per definition.


def _containers_of(value: Any) -> list[Any]:
    return [node for node in _nodes(value) if type(node) in (dict, list)]


def _definition_case(number: int) -> tuple[str, Any]:
    """A definition and a mutated sub-value of a fixture its gate accepts."""
    draw = random.Random(f"{SEED}-definition-{number}")
    definitions = sorted(current._closed_document()["$defs"])
    while True:
        sub = copy.deepcopy(draw.choice(_containers_of(draw.choice(_valid_fixtures()))))
        accepting = [
            name
            for name in definitions
            if current._definition_schema(name).gate.is_valid(sub)
        ]
        if not accepting:
            continue
        name = draw.choice(accepting)
        if _mutate(draw.choice(KINDS), sub, draw):
            return name, sub


@pytest.mark.parametrize("number", range(DEFINITION_CASES))
def test_a_definition_answers_as_its_walk(number: int) -> None:
    name, value = _definition_case(number)
    _assert_gate_answers_as_the_walk(current._definition_schema(name), value)


def test_the_definition_cases_reach_both_answers() -> None:
    answers = {
        _assert_gate_answers_as_the_walk(current._definition_schema(name), value)
        for name, value in map(_definition_case, range(DEFINITION_CASES))
    }
    assert {True, False} <= answers


# Every entry point has its gate.


def test_every_entry_point_has_its_gate() -> None:
    members = {("Manifest", "@context"), ("Graphical", "matchstamps")} | {
        (definition, member)
        for definition in current._SUBJECT_DEFINITIONS.values()
        for member in current._STATEMENT_MEMBERS
    }
    assert len(members) == 8
    # Every member ``statement_problems`` checks alone is one of them.
    for member in members:
        current._member_schema(*member)
    current._definition_schema("Timestamp")
    # Every member ``statement_problems`` checks alone is one of them, and on
    # the fixtures each gate answers as its walk.
    for value in _valid_fixtures():
        found = current._statement_members(value, leniently_bare_ids(value))
        for definition, member, content, *_ in found:
            assert (definition, member) in members
            schema = current._member_schema(definition, member)
            assert _assert_gate_answers_as_the_walk(schema, content) is True
        graphical = value.get("graphical", {})
        if "matchstamps" in graphical:
            schema = current._member_schema("Graphical", "matchstamps")
            content = graphical["matchstamps"]
            assert _assert_gate_answers_as_the_walk(schema, content) is True
        for timestamp in graphical.get("timestamps", []):
            schema = current._definition_schema("Timestamp")
            assert _assert_gate_answers_as_the_walk(schema, timestamp) is True


# The walk is skipped where the gate finds nothing.


class _CountingWalk:
    def __init__(self, walk: Any) -> None:
        self.calls = 0
        self.walk = walk

    @property
    def schema(self) -> Any:
        return self.walk.schema

    def iter_errors(self, value: Any) -> Any:
        self.calls += 1
        return self.walk.iter_errors(value)


def _counted(monkeypatch: pytest.MonkeyPatch) -> _CountingWalk:
    schema = current._manifest_schema()
    walk = _CountingWalk(schema.walk)
    counted = current._Schema(walk=walk, gate=schema.gate)
    monkeypatch.setattr(current, "_manifest_schema", lambda: counted)
    return walk


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
    walk = _counted(monkeypatch)
    current.validate(build())
    assert walk.calls == 0


def test_an_undeclared_key_is_listed_without_the_walk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    walk = _counted(monkeypatch)
    value = _read(fixture_paths()[0])
    value["undeclared_key"] = 1
    value["timelines"][0]["undeclared_key"] = 1
    assert current.unknown_keys(value) == [
        {"path": [], "key": "undeclared_key"},
        {"path": ["timelines", 0], "key": "undeclared_key"},
    ]
    assert walk.calls == 0


def test_an_invalid_manifest_takes_the_walk_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    walk = _counted(monkeypatch)
    value = _read(fixture_paths()[0])
    value["timelines"][0]["unit"] = "furlongs"
    with pytest.raises(ValueError):
        current.validate(value)
    assert walk.calls == 1


# The gate shares the walk's keyword semantics where the package relies on it.

_SEMANTICS: list[tuple[dict[str, Any], list[Any]]] = [
    ({"const": 1}, [1, 1.0, True, "1", [1]]),
    ({"const": True}, [True, 1, False]),
    (
        {"const": [1, {"a": True}]},
        [[1, {"a": True}], [1, {"a": 1}], [True, {"a": True}]],
    ),
    ({"enum": [1, "x"]}, [1, True, "x", 1.0, None]),
    ({"uniqueItems": True}, [[1, True], [1, 1.0], [[1], [True]], [{"a": 1}, {"a": 1}]]),
    ({"type": "integer"}, [1, 1.0, 1.5, True, "1", None, 2**64, 10**400]),
    ({"type": "number"}, [1, 1.5, True, None, "1"]),
    ({"minLength": 2, "maxLength": 3}, ["a", "ab", "abcd", "𝅝𝅝", 5]),
    ({"minimum": 1, "exclusiveMaximum": 3}, [0, 1, 2.5, 3, True, "2"]),
    (
        {"prefixItems": [{"type": "integer"}], "items": False},
        [[1], [1, 2], ["x"], [], {}],
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
]


@pytest.mark.parametrize(("schema", "values"), _SEMANTICS)
def test_the_gate_answers_as_the_walk_on_each_keyword(
    schema: Any, values: list[Any]
) -> None:
    checked = current._Schema.of(schema)
    assert [checked.gate.is_valid(value) for value in values] == [
        checked.walk.is_valid(value) for value in values
    ]


_BELIEF_BASE = {
    "$defs": {
        "Record": {
            "properties": {
                "date": {},
                "beliefs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"actor": {}},
                        "unevaluatedProperties": False,
                    },
                },
            }
        }
    },
    "type": "object",
    "allOf": [{"$ref": "#/$defs/Record"}],
    "properties": {"property": {}},
    "unevaluatedProperties": False,
}


def test_a_failing_allof_base_leaves_its_keys_unevaluated_in_both() -> None:
    checked = current._Schema.of(_BELIEF_BASE)
    value = {"property": 1, "date": 1, "beliefs": [{"actor": 1, "x": 1}]}
    walked = {
        (tuple(error.absolute_path), tuple(sorted(error.instance)))
        for error in checked.walk.iter_errors(value)
        if error.validator == "unevaluatedProperties"
    }
    gated = {
        (tuple(error.instance_path), tuple(sorted(error.kind.unexpected)))
        for error in checked.gate.iter_errors(value)
    }
    assert gated == {(("beliefs", 0), ("x",)), ((), ("beliefs", "date"))}
    assert {path for path, _ in walked} == {path for path, _ in gated}


def _belief_with_undeclared_key() -> Any:
    value = _read(next(p for p in fixture_paths() if p.name == "bare.minimal.yaml"))
    value["provenance"] = [
        {
            "property": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "value": {"id": "http://example.org/work"},
            "beliefs": [
                {
                    "actor": "http://example.org/editor",
                    "belief": "true",
                    "date": "2026-11-18",
                    "x": 1,
                }
            ],
        }
    ]
    return value


def test_an_undeclared_key_below_an_allof_base_is_listed_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = _belief_with_undeclared_key()
    listed = {(("provenance", 0, "beliefs", 0), "x")}
    assert current._manifest_schema().gated(value) == listed
    assert _assert_gate_answers_as_the_walk(current._manifest_schema(), value) is True
    walk = _counted(monkeypatch)
    assert current.unknown_keys(value) == [
        {"path": ["provenance", 0, "beliefs", 0], "key": "x"}
    ]
    assert walk.calls == 0
    _assert_facts(value)


def test_a_final_line_feed_is_left_to_the_walk() -> None:
    checked = current._Schema.of({"pattern": "^[a-z]+$"})
    assert checked.walk.is_valid("abc\n")
    assert not checked.gate.is_valid("abc\n")
    assert checked.read("abc\n", True) == ([], set())
