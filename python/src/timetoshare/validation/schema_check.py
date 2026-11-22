"""A compiled validity check of the schema, the fast path of the schema walk.

``jsonschema`` walks the schema node by node for every value, building an
evolved validator and resolving every ``$ref`` on the way; on a manifest of a
few hundred kilobytes that walk takes seconds. A manifest that passes it is
the common case, and the walk's answer then is only "no error". This module
turns the schema, once, into nested Python closures that answer the same
question, whether ``Draft202012Validator(schema).iter_errors(value)`` yields
nothing, without building a single error.

Each keyword is checked with the semantics ``jsonschema`` gives it under JSON
Schema 2020-12 (its type checker, its equality, which tells ``True`` from
``1``, its uniqueness, ``re.search`` for patterns, and for
``unevaluatedProperties`` the keys its ``find_evaluated_property_keys_by_schema``
counts). A schema node is valid when every keyword is, so the order the
closures test them in changes no answer. A keyword ``jsonschema`` validates
and this module does not know refuses to compile, so the schema can never
quietly outgrow the check.

The check is used one way only: where it answers ``True`` the walk is
skipped, since it would yield nothing; where it answers ``False`` or raises,
the caller runs the walk, which builds the diagnostics as before.
"""

from __future__ import annotations

import itertools
import numbers
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from jsonschema import Draft202012Validator

Check = Callable[[Any], bool]
"""A compiled schema node: whether a value is valid under it."""

Keys = Callable[[Any], set[str]]
"""The keys of an object that a schema node evaluates."""

Node = Mapping[str, Any]
"""A schema node that is an object, not a boolean."""

Kind = str | None
"""The one type a node declares, which its other keywords may then assume."""

_ORDER = (
    "type",
    "const",
    "enum",
    "required",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "minProperties",
    "maxProperties",
    "dependentRequired",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "pattern",
    "format",
    "uniqueItems",
    "$ref",
    "properties",
    "additionalProperties",
    "propertyNames",
    "prefixItems",
    "items",
    "allOf",
    "anyOf",
    "oneOf",
    "not",
    "if",
    "unevaluatedProperties",
)
"""The compiled keywords, ``type`` first and the cheap ones before the deep."""

_NOT_COMPILED = frozenset(Draft202012Validator.VALIDATORS).difference(_ORDER)
"""The keywords ``jsonschema`` validates that this module does not compile."""

_DEFINITIONS = "#/$defs/"


def _is_object(value: Any) -> bool:
    return isinstance(value, dict)


def _is_array(value: Any) -> bool:
    return isinstance(value, list)


def _is_string(value: Any) -> bool:
    return isinstance(value, str)


def _is_null(value: Any) -> bool:
    return value is None


def _is_boolean(value: Any) -> bool:
    return isinstance(value, bool)


def _is_integer(value: Any) -> bool:
    kind = type(value)
    if kind is int:
        return True
    if kind is float:
        return value.is_integer()
    if isinstance(value, bool):
        return False
    return isinstance(value, int) or (isinstance(value, float) and value.is_integer())


def _is_number(value: Any) -> bool:
    kind = type(value)
    if kind is int or kind is float:
        return True
    return not isinstance(value, bool) and isinstance(value, numbers.Number)


_TYPES: dict[str, Check] = {
    "object": _is_object,
    "array": _is_array,
    "string": _is_string,
    "null": _is_null,
    "boolean": _is_boolean,
    "integer": _is_integer,
    "number": _is_number,
}


class _Unbooled:
    """``True`` and ``False`` told apart from ``1`` and ``0``, as in uniqueness."""


_TRUE = _Unbooled()
_FALSE = _Unbooled()


def _unbool(value: Any) -> Any:
    if value is True:
        return _TRUE
    if value is False:
        return _FALSE
    return value


def equal(one: Any, two: Any) -> bool:
    """Equality as JSON Schema reads it: ``True`` is not ``1``, at any depth."""
    if one is two:
        return True
    if isinstance(one, str) or isinstance(two, str):
        return one == two
    if isinstance(one, Sequence) and isinstance(two, Sequence):
        return len(one) == len(two) and all(
            equal(i, j) for i, j in zip(one, two, strict=False)
        )
    if isinstance(one, Mapping) and isinstance(two, Mapping):
        return len(one) == len(two) and all(
            key in two and equal(item, two[key]) for key, item in one.items()
        )
    return _unbool(one) == _unbool(two)


def unique(container: Any) -> bool:
    """Whether every item is distinct under :func:`equal`."""
    try:
        ordered = sorted(_unbool(item) for item in container)
        for i, j in zip(ordered, itertools.islice(ordered, 1, None), strict=False):
            if equal(i, j):
                return False
    except (NotImplementedError, TypeError):
        seen: list[Any] = []
        for item in container:
            item = _unbool(item)
            for other in seen:
                if equal(other, item):
                    return False
            seen.append(item)
    return True


def _always(value: Any) -> bool:
    return True


def _never(value: Any) -> bool:
    return False


_ASSUMED = {
    "object": ("object",),
    "array": ("array",),
    "string": ("string",),
    "number": ("number", "integer"),
}
"""The declared types under which a keyword of each kind needs no guard."""


def _guarded(kind: str, known: Kind, check: Check) -> Check | None:
    """``check``, a keyword of values of ``kind``, run where it applies.

    A keyword of JSON Schema passes every value not of its kind. Where the
    node declares that kind (or, for numbers, integers) the value has it by
    the time the keyword runs; where it declares another, the keyword never
    runs on a valid value and is left out.
    """
    if known is None:
        is_kind = _TYPES[kind]

        def guarded(value: Any) -> bool:
            return not is_kind(value) or check(value)

        return guarded
    if known in _ASSUMED[kind]:
        return check
    return None


def _no_keys(value: Any) -> set[str]:
    return set()


def _all(checks: list[Check]) -> Check:
    if not checks:
        return _always
    if len(checks) == 1:
        return checks[0]
    if len(checks) == 2:
        first, second = checks

        def both(value: Any) -> bool:
            return first(value) and second(value)

        return both
    frozen = tuple(checks)

    def every(value: Any) -> bool:
        for check in frozen:
            if not check(value):
                return False
        return True

    return every


class SchemaCompiler:
    """Compiles nodes of one schema document whose references are all local."""

    def __init__(self, document: Mapping[str, Any]) -> None:
        self._definitions: Mapping[str, Any] = document.get("$defs", {})
        self._checks: dict[str, list[Check]] = {}
        self._keys: dict[str, list[Keys]] = {}
        # Each node compiled once, by identity; the node is kept beside its
        # result so that no identity is reused while the compiler lives.
        self._compiled: dict[int, tuple[Any, Check]] = {}
        self._evaluated: dict[int, tuple[Any, Keys]] = {}

    def check(self, node: Any) -> Check:
        """Return the validity check of ``node``, a schema or a boolean."""
        known = self._compiled.get(id(node))
        if known is not None:
            return known[1]
        compiled = self._check(node)
        self._compiled[id(node)] = (node, compiled)
        return compiled

    def keys(self, node: Any) -> Keys:
        """Return the keys an object has evaluated by ``node``.

        The keys ``jsonschema``'s ``find_evaluated_property_keys_by_schema``
        counts: those ``properties`` names, those an
        ``additionalProperties`` or ``unevaluatedProperties`` schema accepts,
        and those of every ``allOf``/``anyOf``/``oneOf`` branch the value is
        valid under, of the ``$ref`` target and of the ``if`` arm taken.
        """
        known = self._evaluated.get(id(node))
        if known is not None:
            return known[1]
        compiled = self._keys_of(node)
        self._evaluated[id(node)] = (node, compiled)
        return compiled

    def _check(self, node: Any) -> Check:
        if node is True:
            return _always
        if node is False:
            return _never
        if not isinstance(node, Mapping):
            raise NotImplementedError(f"not a schema: {node!r}")
        unknown = _NOT_COMPILED.intersection(node)
        if unknown:
            raise NotImplementedError(f"keywords not compiled: {sorted(unknown)}")
        # A node of one type checks the type first, and every other keyword
        # then runs on a value of that type: one of another type's keywords
        # is left out, one of its own drops its guard. Validity is the
        # conjunction of the keywords, so neither the order nor what a
        # failed type leaves unchecked changes an answer.
        types = node.get("type")
        known = types if isinstance(types, str) else None
        checks: list[Check] = []
        for keyword in _ORDER:
            if keyword in node:
                compile_keyword = getattr(self, "_" + keyword.lstrip("$"))
                compiled = compile_keyword(node[keyword], node, known)
                if compiled is not None:
                    checks.append(compiled)
        return _all(checks)

    def _keys_of(self, node: Any) -> Keys:
        if not isinstance(node, Mapping):
            return _no_keys
        parts: list[Keys] = []
        reference = node.get("$ref")
        if reference is not None:
            parts.append(self._reference_keys(reference))
        properties = node.get("properties")
        if isinstance(properties, dict):
            names = frozenset(properties)

            def declared(value: Any) -> set[str]:
                return names.intersection(value)

            parts.append(declared)
        for keyword in ("additionalProperties", "unevaluatedProperties"):
            if keyword in node:
                accepts = self.check(node[keyword])

                def accepted(value: Any, accepts: Check = accepts) -> set[str]:
                    return {key for key, item in value.items() if accepts(item)}

                parts.append(accepted)
        for keyword in ("allOf", "oneOf", "anyOf"):
            for branch in node.get(keyword, ()):
                valid, held = self.check(branch), self.keys(branch)

                def taken(
                    value: Any, valid: Check = valid, held: Keys = held
                ) -> set[str]:
                    return held(value) if valid(value) else set()

                parts.append(taken)
        if "if" in node:
            condition, condition_keys = self.check(node["if"]), self.keys(node["if"])
            then_keys = self.keys(node["then"]) if "then" in node else _no_keys
            else_keys = self.keys(node["else"]) if "else" in node else _no_keys

            def arm(value: Any) -> set[str]:
                if condition(value):
                    return condition_keys(value) | then_keys(value)
                return else_keys(value)

            parts.append(arm)
        if not parts:
            return _no_keys

        def evaluated(value: Any) -> set[str]:
            found: set[str] = set()
            for part in parts:
                found |= part(value)
            return found

        return evaluated

    def _definition(self, reference: str) -> str:
        if not reference.startswith(_DEFINITIONS):
            raise NotImplementedError(f"reference not local: {reference}")
        name = reference.removeprefix(_DEFINITIONS)
        if name not in self._definitions:
            raise NotImplementedError(f"no definition: {reference}")
        return name

    def _ref(self, reference: str, node: Node, known: Kind) -> Check:
        name = self._definition(reference)
        cell = self._checks.get(name)
        if cell is None:
            cell = self._checks[name] = [_never]
            cell[0] = self.check(self._definitions[name])

        def referred(value: Any) -> bool:
            return cell[0](value)

        return referred

    def _reference_keys(self, reference: str) -> Keys:
        name = self._definition(reference)
        cell = self._keys.get(name)
        if cell is None:
            cell = self._keys[name] = [_no_keys]
            cell[0] = self.keys(self._definitions[name])

        def referred(value: Any) -> set[str]:
            return cell[0](value)

        return referred

    def _type(self, types: Any, node: Node, known: Kind) -> Check:
        names = [types] if isinstance(types, str) else list(types)
        checks = tuple(_TYPES[name] for name in names)
        if len(checks) == 1:
            return checks[0]

        def any_type(value: Any) -> bool:
            return any(check(value) for check in checks)

        return any_type

    def _const(self, expected: Any, node: Node, known: Kind) -> Check:
        if isinstance(expected, str):
            # ``equal`` compares with ``==`` where either side is a string.
            def text(value: Any) -> bool:
                return value is expected or value == expected

            return text

        def constant(value: Any) -> bool:
            return equal(value, expected)

        return constant

    def _enum(self, members: Any, node: Node, known: Kind) -> Check:
        members = list(members)
        if all(isinstance(member, str) for member in members):
            texts = frozenset(members)

            def text(value: Any) -> bool:
                # A string equals a member exactly when it is one; any other
                # value is compared as ``equal`` compares it.
                if type(value) is str:
                    return value in texts
                return any(member == value for member in members)

            return text

        def among(value: Any) -> bool:
            return any(equal(member, value) for member in members)

        return among

    def _required(self, names: Any, node: Node, known: Kind) -> Check | None:
        names = tuple(names)

        def present(value: Any) -> bool:
            for name in names:
                if name not in value:
                    return False
            return True

        return _guarded("object", known, present)

    def _size(self, kind: str, known: Kind, bound: int, at_least: bool) -> Check | None:
        if at_least:

            def long_enough(value: Any) -> bool:
                return len(value) >= bound

            return _guarded(kind, known, long_enough)

        def short_enough(value: Any) -> bool:
            return len(value) <= bound

        return _guarded(kind, known, short_enough)

    def _minItems(self, bound: int, node: Node, known: Kind) -> Check | None:
        return self._size("array", known, bound, True)

    def _maxItems(self, bound: int, node: Node, known: Kind) -> Check | None:
        return self._size("array", known, bound, False)

    def _minLength(self, bound: int, node: Node, known: Kind) -> Check | None:
        return self._size("string", known, bound, True)

    def _maxLength(self, bound: int, node: Node, known: Kind) -> Check | None:
        return self._size("string", known, bound, False)

    def _minProperties(self, bound: int, node: Node, known: Kind) -> Check | None:
        return self._size("object", known, bound, True)

    def _maxProperties(self, bound: int, node: Node, known: Kind) -> Check | None:
        return self._size("object", known, bound, False)

    def _dependentRequired(
        self, dependencies: Mapping[str, Any], node: Node, known: Kind
    ) -> Check | None:
        pairs = tuple((name, tuple(needed)) for name, needed in dependencies.items())

        def dependent(value: Any) -> bool:
            for name, needed in pairs:
                if name in value and any(each not in value for each in needed):
                    return False
            return True

        return _guarded("object", known, dependent)

    def _minimum(self, bound: Any, node: Node, known: Kind) -> Check | None:
        def at_least(value: Any) -> bool:
            return not value < bound

        return _guarded("number", known, at_least)

    def _maximum(self, bound: Any, node: Node, known: Kind) -> Check | None:
        def at_most(value: Any) -> bool:
            return not value > bound

        return _guarded("number", known, at_most)

    def _exclusiveMinimum(self, bound: Any, node: Node, known: Kind) -> Check | None:
        def above(value: Any) -> bool:
            return not value <= bound

        return _guarded("number", known, above)

    def _exclusiveMaximum(self, bound: Any, node: Node, known: Kind) -> Check | None:
        def below(value: Any) -> bool:
            return not value >= bound

        return _guarded("number", known, below)

    def _format(self, name: Any, node: Node, known: Kind) -> None:
        # The walk's validator has no format checker: ``format`` annotates.
        return None

    def _pattern(self, pattern: str, node: Node, known: Kind) -> Check | None:
        search = re.compile(pattern).search

        def matches(value: Any) -> bool:
            return search(value) is not None

        return _guarded("string", known, matches)

    def _uniqueItems(self, required: Any, node: Node, known: Kind) -> Check | None:
        if not required:
            return None
        return _guarded("array", known, unique)

    def _properties(
        self, properties: Mapping[str, Any], node: Node, known: Kind
    ) -> Check | None:
        members = tuple(
            (name, self.check(member)) for name, member in properties.items()
        )

        def each(value: Any) -> bool:
            for name, check in members:
                if name in value and not check(value[name]):
                    return False
            return True

        return _guarded("object", known, each)

    def _additionalProperties(
        self, additional: Any, node: Node, known: Kind
    ) -> Check | None:
        if "patternProperties" in node:
            raise NotImplementedError("patternProperties is not compiled")
        declared = frozenset(node.get("properties", {}))
        if additional is True:
            return None
        if additional is False:

            def closed(value: Any) -> bool:
                return declared.issuperset(value)

            return _guarded("object", known, closed)
        accepts = self.check(additional)

        def extras(value: Any) -> bool:
            for key, item in value.items():
                if key not in declared and not accepts(item):
                    return False
            return True

        return _guarded("object", known, extras)

    def _propertyNames(self, names: Any, node: Node, known: Kind) -> Check | None:
        accepts = self.check(names)

        def named(value: Any) -> bool:
            for key in value:
                if not accepts(key):
                    return False
            return True

        return _guarded("object", known, named)

    def _prefixItems(self, prefix: Any, node: Node, known: Kind) -> Check | None:
        checks = tuple(self.check(item) for item in prefix)

        def leading(value: Any) -> bool:
            for item, check in zip(value, checks, strict=False):
                if not check(item):
                    return False
            return True

        return _guarded("array", known, leading)

    def _items(self, items: Any, node: Node, known: Kind) -> Check | None:
        start = len(node.get("prefixItems", ()))
        if items is True:
            return None
        if items is False:

            def nothing_more(value: Any) -> bool:
                return len(value) <= start

            return _guarded("array", known, nothing_more)
        check = self.check(items)
        if start == 0:

            def every(value: Any) -> bool:
                for item in value:
                    if not check(item):
                        return False
                return True

            return _guarded("array", known, every)

        def rest(value: Any) -> bool:
            for item in itertools.islice(value, start, None):
                if not check(item):
                    return False
            return True

        return _guarded("array", known, rest)

    def _allOf(self, branches: Any, node: Node, known: Kind) -> Check:
        return _all([self.check(branch) for branch in branches])

    def _anyOf(self, branches: Any, node: Node, known: Kind) -> Check:
        checks = tuple(self.check(branch) for branch in branches)

        def some(value: Any) -> bool:
            for check in checks:
                if check(value):
                    return True
            return False

        return some

    def _oneOf(self, branches: Any, node: Node, known: Kind) -> Check:
        checks = tuple(self.check(branch) for branch in branches)

        def exactly_one(value: Any) -> bool:
            found = False
            for check in checks:
                if check(value):
                    if found:
                        return False
                    found = True
            return found

        return exactly_one

    def _not(self, negated: Any, node: Node, known: Kind) -> Check:
        check = self.check(negated)

        def refused(value: Any) -> bool:
            return not check(value)

        return refused

    def _if(self, condition: Any, node: Node, known: Kind) -> Check:
        then = self.check(node["then"]) if "then" in node else _always
        otherwise = self.check(node["else"]) if "else" in node else _always
        test = self.check(condition)

        def arm(value: Any) -> bool:
            return then(value) if test(value) else otherwise(value)

        return arm

    def _unevaluatedProperties(
        self, unevaluated: Any, node: Node, known: Kind
    ) -> Check | None:
        declared = frozenset(node.get("properties", {}))
        accepts = self.check(unevaluated)
        evaluated_keys = self.keys(node)

        def evaluated_only(value: Any) -> bool:
            # ``properties`` evaluates its names whatever their values, and
            # the evaluated keys only grow beyond them.
            if declared.issuperset(value):
                return True
            evaluated = evaluated_keys(value)
            for key, item in value.items():
                if key not in evaluated and not accepts(item):
                    return False
            return True

        return _guarded("object", known, evaluated_only)


def compiled_check(document: Mapping[str, Any], node: Any) -> Check:
    """Return the validity check of ``node``, its references read in ``document``.

    The check answers whether ``jsonschema``'s 2020-12 walk of ``node`` would
    yield no error; an exception it raises (a value no keyword can compare,
    a nesting beyond the recursion limit) means only that it cannot answer.

    Raises:
        NotImplementedError: If the schema holds a keyword or a reference
            this module does not compile.
    """
    return SchemaCompiler(document).check(node)
