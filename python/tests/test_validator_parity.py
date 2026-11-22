"""The compiled schema check changes no diagnostic of the validator.

The strategy is the README's section "The compiled schema check": three
facts, each asserted on every input, from which every outcome follows.
"""

from __future__ import annotations

import copy
import math
import random
from collections import OrderedDict, defaultdict
from collections.abc import Callable, Iterator, Mapping
from decimal import Decimal
from fractions import Fraction
from functools import cache
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

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
from timetoshare.validation.schema_check import Check, SchemaCompiler, Unanswered

current = import_module("timetoshare.validate")

SEED = 20261122
MUTATIONS = 60
"""Mutations of each kind."""
DEFINITION_CASES = 600
"""Mutated sub-values checked against one definition each."""


def compiled_check(document: Mapping[str, Any], node: Any) -> Check:
    """The check of ``node``, its references read in ``document``."""
    return SchemaCompiler(document).check(node)


def _read(path: Path) -> Any:
    return loads(path.read_text(encoding="utf-8"))


# The three facts.

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


def _answer(check: Check, value: Any) -> bool | None:
    """The check's answer, ``None`` where it declines (raises)."""
    try:
        answer = check(value)
    except Exception:
        return None
    assert answer is True or answer is False
    return answer


def _walks_clean(walk: Any, value: Any) -> bool:
    """Whether the walk yields no error (a walk that raises yields none)."""
    try:
        return next(walk.iter_errors(value), None) is None
    except Exception:
        return False


def _assert_answers_as_the_walk(check: Check, walk: Any, value: Any) -> bool | None:
    """Fact 1: the check answers ``True`` exactly where the walk yields nothing."""
    answer = _answer(check, value)
    if answer is None:
        assert not _plain(value)
    else:
        assert answer is _walks_clean(walk, value)
    return answer


def _assert_finite_rule_skipped_soundly(value: Any) -> None:
    """Fact 2: ``plainly_finite`` implies the finite rule finds nothing."""
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
    """Fact 3: the conversions' copy is ``copy.deepcopy``'s, sharing nothing."""
    copied = _copied(value)
    expected = copy.deepcopy(value)
    assert copied == expected
    assert [type(node) for node in _nodes(copied)] == [
        type(node) for node in _nodes(expected)
    ]
    assert not _containers(value) & _containers(copied)


@cache
def _walk() -> Any:
    return Draft202012Validator(current._closed_document())


def _assert_facts(value: Any) -> bool | None:
    answer = _assert_answers_as_the_walk(current._checks().manifest, _walk(), value)
    _assert_finite_rule_skipped_soundly(value)
    _assert_copied(value)
    return answer


@pytest.mark.parametrize("path", fixture_paths(), ids=lambda path: path.name)
def test_a_fixture_holds_the_facts(path: Path) -> None:
    assert _assert_facts(_read(path)) is True


@pytest.mark.parametrize("path", rejection_paths(), ids=lambda path: path.name)
def test_a_rejection_case_holds_the_facts(path: Path) -> None:
    _assert_facts(rejection_case(path).manifest)


@pytest.mark.parametrize("path", warning_paths(), ids=lambda path: path.name)
def test_a_warning_case_holds_the_facts(path: Path) -> None:
    _assert_facts(_read(path)["manifest"])


@pytest.mark.parametrize("build", [many_timestamps, long_tables])
def test_a_large_manifest_holds_the_facts(build: Callable[[], Any]) -> None:
    assert _assert_facts(build()) is True


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
def _valid() -> tuple[Any, ...]:
    return tuple(_read(path) for path in fixture_paths())


def _mutated(kind: str, number: int) -> Any:
    """The ``number``-th mutation of ``kind``, drawn from its own seeded stream."""
    draw = random.Random(f"{SEED}-{kind}-{number}")
    while True:
        value = copy.deepcopy(draw.choice(_valid()))
        if _mutate(kind, value, draw):
            return value


@pytest.mark.parametrize("number", range(MUTATIONS))
@pytest.mark.parametrize("kind", KINDS)
def test_a_mutated_fixture_holds_the_facts(kind: str, number: int) -> None:
    _assert_facts(_mutated(kind, number))


@pytest.mark.parametrize("kind", KINDS)
def test_the_mutations_of_a_kind_reach_both_answers(kind: str) -> None:
    """The mutations exercise valid and invalid manifests, not only one."""
    check = current._checks().manifest
    answers = {_answer(check, _mutated(kind, number)) for number in range(MUTATIONS)}
    assert {True, False} <= answers


# Per definition.


@cache
def _definition_compiler() -> SchemaCompiler:
    return SchemaCompiler(current._closed_document())


def _containers_of(value: Any) -> list[Any]:
    return [node for node in _nodes(value) if type(node) in (dict, list)]


def _definition_case(number: int) -> tuple[str, Any]:
    """A definition and a mutated sub-value of a fixture it accepts."""
    draw = random.Random(f"{SEED}-definition-{number}")
    definitions = current._closed_document()["$defs"]
    compiler = _definition_compiler()
    while True:
        sub = copy.deepcopy(draw.choice(_containers_of(draw.choice(_valid()))))
        accepting = [
            name
            for name in sorted(definitions)
            if _answer(compiler.check(definitions[name]), sub) is True
        ]
        if not accepting:
            continue
        name = draw.choice(accepting)
        if _mutate(draw.choice(KINDS), sub, draw):
            return name, sub


@pytest.mark.parametrize("number", range(DEFINITION_CASES))
def test_a_definition_answers_as_its_walk(number: int) -> None:
    name, value = _definition_case(number)
    definitions = current._closed_document()["$defs"]
    check = _definition_compiler().check(definitions[name])
    _assert_answers_as_the_walk(check, current._definition_validator(name), value)


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


# Compilation ends before any check runs.


def _messages(errors: Any) -> list[str]:
    return [error.message for error in errors]


class _Capturing(SchemaCompiler):
    """A compiler keeping what a definition's cells hold while it compiles."""

    def __init__(self, document: Mapping[str, Any], name: str) -> None:
        super().__init__(document)
        self.name = name
        self.cells: dict[str, Any] = {}

    def check(self, node: Any) -> Check:
        if node is self._definitions.get(self.name) and self.name in self._checks:
            self.cells["check"] = self._checks[self.name][0]
        return super().check(node)

    def keys(self, node: Any) -> Any:
        if node is self._definitions.get(self.name) and self.name in self._keys:
            self.cells["keys"] = self._keys[self.name][0]
        return super().keys(node)


def _while_compiling(schema: Mapping[str, Any], name: str, cell: str) -> Check:
    """``schema``'s check as a second thread finds it while ``name`` compiles.

    The cell of ``name`` holds what the compiler put there before compiling
    the definition, as another thread reusing the compiler would see it.
    """
    capturing = _Capturing(schema, name)
    capturing.check(schema)
    compiler = SchemaCompiler(schema)
    cells = compiler._checks if cell == "check" else compiler._keys
    cells[name] = [capturing.cells[cell]]
    return compiler.check(schema)


def test_a_check_reaching_a_reference_still_compiling_declines() -> None:
    # Under ``oneOf`` an answer of ``False`` for ``B`` would accept ``1``.
    schema = {
        "$defs": {"A": {"type": "integer"}, "B": {"minimum": 0}},
        "oneOf": [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/B"}],
    }
    check = _while_compiling(schema, "B", "check")
    with pytest.raises(Unanswered):
        check(1)
    walk = Draft202012Validator(schema)
    errors = current._walk_errors(walk, check, 1)
    assert errors
    assert _messages(errors) == _messages(walk.iter_errors(1))


def test_the_keys_of_a_reference_still_compiling_decline() -> None:
    schema = {
        "$defs": {"A": {"properties": {"a": {}}}},
        "allOf": [{"$ref": "#/$defs/A"}],
        "unevaluatedProperties": False,
    }
    check = _while_compiling(schema, "A", "keys")
    with pytest.raises(Unanswered):
        check({"a": 1, "b": 1})
    walk = Draft202012Validator(schema)
    errors = current._walk_errors(walk, check, {"a": 1, "b": 1})
    assert errors
    assert _messages(errors) == _messages(walk.iter_errors({"a": 1, "b": 1}))


def _fixture_with(*members: str) -> Any:
    for value in _valid():
        held = {
            member for node in _nodes(value) if type(node) is dict for member in node
        }
        if set(members) <= held:
            return value
    raise AssertionError(members)


def test_every_entry_point_is_compiled_before_the_first_check() -> None:
    fresh = current._compiled_checks.__wrapped__()
    document = current._closed_document()
    definitions = document["$defs"]
    entries = [document, definitions["Timestamp"]] + [
        definitions[definition]["properties"][member]
        for definition, member in current._CHECKED_MEMBERS
    ]
    assert all(id(entry) in fresh.compiler._compiled for entry in entries)
    # Every member ``statement_problems`` checks alone is one of them: those
    # the fixtures reach, and every subject's by its definition.
    found = {
        (definition, member)
        for value in _valid()
        for definition, member, *_ in current._statement_members(
            value, leniently_bare_ids(value)
        )
    }
    assert found <= set(fresh.members)
    assert {
        (definition, member)
        for definition in current._SUBJECT_DEFINITIONS.values()
        for member in current._STATEMENT_MEMBERS
    } <= set(fresh.members)
    assert len(fresh.members) == 8


def test_no_node_is_compiled_after_the_first_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fresh = current._compiled_checks.__wrapped__()
    monkeypatch.setattr(current, "_compiled_checks", lambda: fresh)
    compiled = len(fresh.compiler._compiled)
    current.validate(_valid()[0])
    assert len(fresh.compiler._compiled) == compiled
    stamped = _fixture_with("matchstamps")
    assert current.matchstamp_problems(stamped) == []
    assert len(fresh.compiler._compiled) == compiled
    stated = _fixture_with("statements", "provenance", "@context")
    assert current.statement_problems(stated) == []
    assert len(fresh.compiler._compiled) == compiled


# Containers the check does not answer for.


def test_a_mapping_whose_keys_disagree_declines() -> None:
    schema = {"properties": {"a": {}}, "unevaluatedProperties": False}
    check = compiled_check(schema, schema)
    walk = Draft202012Validator(schema)
    for value in (_Lying(a=1), OrderedDict(a=1), OrderedDict(b=1), _ListSub()):
        with pytest.raises(Unanswered) if isinstance(value, dict) else _no_raise():
            check(value)
        assert _messages(current._walk_errors(walk, check, value)) == _messages(
            walk.iter_errors(value)
        )
    assert _messages(current._walk_errors(walk, check, _Lying(a=1))) == [
        "Unevaluated properties are not allowed ('a' was unexpected)"
    ]


class _no_raise:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *exception: Any) -> bool:
        return False


def test_an_ordered_manifest_has_the_outcome_of_the_walk() -> None:
    value = _read(fixture_paths()[0])
    ordered = OrderedDict(value)
    with pytest.raises(Unanswered):
        current._checks().manifest(ordered)
    assert current._check(ordered) == current._check(value)
    ordered["undeclared_key"] = 1
    assert current.unknown_keys(ordered) == [{"path": [], "key": "undeclared_key"}]


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
    (
        {
            "$id": "https://example.org/s",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "integer",
        },
        [1, "1"],
    ),
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
        {"format": "email"},
        {"$ref": "other.json#/$defs/A"},
        {
            "$defs": {"A": {"type": "string"}},
            "properties": {
                "x": {
                    "$id": "http://example.org/x",
                    "$defs": {"A": {"type": "integer"}},
                    "$ref": "#/$defs/A",
                }
            },
        },
        {
            "properties": {
                "x": {"$schema": "https://json-schema.org/draft/2020-12/schema"}
            }
        },
        {"properties": {"x": {"$anchor": "x"}}},
        {"properties": {"x": {"$dynamicAnchor": "x"}}},
        {"$vocabulary": {"https://json-schema.org/draft/2020-12/vocab/core": True}},
    ],
    ids=[
        "patternProperties",
        "dependentSchemas",
        "contains",
        "format",
        "foreign reference",
        "nested $id",
        "nested $schema",
        "$anchor",
        "$dynamicAnchor",
        "$vocabulary",
    ],
)
def test_a_schema_the_check_does_not_know_refuses_to_compile(schema: Any) -> None:
    with pytest.raises(NotImplementedError):
        compiled_check(schema, schema)
