"""The three serializations of a TimeToShare manifest: writing, reading, naming.

A manifest is a JSON value, exchanged as text in canonical YAML (``"yaml"``),
pretty JSON (``"json"``) or RFC 8785 JSON (``"jcs"``), each specified to the
byte by the README's "Serializations". :func:`dumps` writes all three,
:func:`loads` reads any text, and :func:`serialization_of` names the
serialization of a text without validating it.

Every writer sorts the keys of every object by Unicode code point (RFC 8785
JSON by UTF-16 code units), writes a manifest in canonical order with its
own-axis values respelled (:func:`~timetoshare.manifest.canonical_order`),
and refuses a value it cannot write: a NaN or an infinity, a string or key
holding a lone surrogate, a key whose canonical YAML form is longer than 1024
UTF-16 code units, and in RFC 8785 JSON an integer beyond ±(2^53 − 1) or an
integral float of magnitude from 2^53 up to but excluding 10^21.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from typing import Any, Literal, NoReturn

import yaml

from .manifest import canonical_order, is_manifest

__all__ = ["Serialization", "dumps", "loads", "serialization_of", "spell"]

Serialization = Literal["yaml", "json", "jcs"]
"""The name of a serialization."""

_SERIALIZATIONS = ("yaml", "json", "jcs")

_KEY_LIMIT = 1024
"""The longest canonical YAML form of a key a writer writes, in UTF-16 code units."""

_SAFE_INTEGER = 2**53 - 1
"""The largest magnitude of an integer RFC 8785 JSON writes."""

_JSON_WHITESPACE = " \t\n\r"

_BYTE_ORDER_MARK = "\ufeff"


# Numbers ------------------------------------------------------------------


def _digits(value: float) -> tuple[str, int]:
    """The shortest round-trip digits d1 … dn of a positive finite float and k.

    The decimal d1.d2…dn × 10^k reads back as ``value``; Python's ``repr``
    finds these digits (the nearest of the shortest, ties to an even digit).
    """
    text = repr(value)
    mantissa, _, exponent = text.partition("e")
    whole, _, fraction = mantissa.partition(".")
    digits = whole + fraction
    stripped = digits.lstrip("0")
    k = len(whole) - 1 - (len(digits) - len(stripped)) + int(exponent or 0)
    return stripped.rstrip("0"), k


def _finite(value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{value!r} is not a finite number and cannot be written")


def _all_finite(value: Any) -> None:
    """Refuse a value holding a NaN or an infinity at any depth."""
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, float):
            _finite(item)
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, dict):
            pending.extend(item.values())


def _float_text(value: float) -> str:
    """Spell a float as canonical YAML and pretty JSON do."""
    _finite(value)
    if value == 0:
        return "-0.0" if math.copysign(1.0, value) < 0 else "0.0"
    if value < 0:
        return "-" + _float_text(-value)
    digits, k = _digits(value)
    if -4 <= k <= 15:
        if k >= 0:
            whole = digits[: k + 1].ljust(k + 1, "0")
            return f"{whole}.{digits[k + 1 :] or '0'}"
        return "0." + "0" * (-k - 1) + digits
    sign = "+" if k >= 0 else "-"
    return f"{digits[0]}.{digits[1:] or '0'}e{sign}{abs(k):02d}"


def _ecmascript_float_text(value: float) -> str:
    """Spell a float as ECMAScript's Number::toString does, for RFC 8785 JSON."""
    _finite(value)
    if value == 0:
        return "0"
    if value < 0:
        return "-" + _ecmascript_float_text(-value)
    if value.is_integer() and 2**53 <= value < 10**21:
        raise ValueError(
            f"the integral float {_float_text(value)} cannot be written in RFC 8785 "
            "JSON, which spells it as an integer beyond 2^53 - 1"
        )
    digits, k = _digits(value)
    n = len(digits)
    if n - 1 <= k <= 20:
        return digits + "0" * (k - n + 1)
    if 0 <= k < n - 1:
        return f"{digits[: k + 1]}.{digits[k + 1 :]}"
    if -6 <= k <= -1:
        return "0." + "0" * (-k - 1) + digits
    sign = "+" if k >= 0 else "-"
    mantissa = digits[0] if n == 1 else f"{digits[0]}.{digits[1:]}"
    return f"{mantissa}e{sign}{abs(k)}"


def _integer_text(value: int) -> str:
    return str(int(value))


def _safe_integer_text(value: int) -> str:
    if abs(value) > _SAFE_INTEGER:
        raise ValueError(
            f"the integer {_integer_text(value)} cannot be written in RFC 8785 JSON, "
            "whose numbers are doubles"
        )
    return _integer_text(value)


# Strings ------------------------------------------------------------------

_SHORT_ESCAPES = {
    ord('"'): '\\"',
    ord("\\"): "\\\\",
    0x08: "\\b",
    0x09: "\\t",
    0x0A: "\\n",
    0x0C: "\\f",
    0x0D: "\\r",
}


def _escapes(*code_points: int) -> dict[int, str]:
    table = {code_point: f"\\u{code_point:04x}" for code_point in code_points}
    return table | _SHORT_ESCAPES


_JSON_ESCAPES = _escapes(*range(0x20))
_YAML_ESCAPES = _escapes(
    *range(0x20), *range(0x7F, 0xA0), 0x2028, 0x2029, 0xFEFF, 0xFFFE, 0xFFFF
)

_PLAIN = re.compile(r"[A-Za-z_][A-Za-z0-9_./-]*")
_YAML_WORDS = frozenset(("null", "true", "false", "yes", "no", "on", "off", "y", "n"))
"""Strings that match the plain pattern but are quoted, as YAML 1.2 or 1.1 reads
them as something else."""


def _json_string(value: str) -> str:
    return '"' + value.translate(_JSON_ESCAPES) + '"'


def _yaml_string(value: str) -> str:
    if _PLAIN.fullmatch(value) and value.lower() not in _YAML_WORDS:
        return value
    return '"' + value.translate(_YAML_ESCAPES) + '"'


def _yaml_key(key: Any) -> str:
    """The canonical YAML form of a key, refused when it is too long.

    Raises:
        TypeError: If the key is not a string.
        ValueError: If its form exceeds 1024 UTF-16 code units, in every
            serialization, so that every value written can be written in
            canonical YAML and read by every YAML parser.
    """
    if not isinstance(key, str):
        raise TypeError(f"a key must be a string, not {key!r}")
    form = _yaml_string(key)
    units = len(form) + sum(1 for character in form if ord(character) > 0xFFFF)
    if units > _KEY_LIMIT:
        raise ValueError(
            f"a key whose canonical YAML form is {units} UTF-16 code units long, "
            f"more than {_KEY_LIMIT}, cannot be written"
        )
    return form


def _json_key(key: Any) -> str:
    _yaml_key(key)
    return _json_string(key)


# Values -------------------------------------------------------------------


def _scalar(
    value: Any, number: Callable[[Any], str], string: Callable[[str], str]
) -> str:
    """Spell a scalar; raise ``TypeError`` for a value that is not a JSON scalar."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return string(value)
    if isinstance(value, int | float):
        return number(value)
    raise TypeError(f"{type(value).__name__} is not a JSON value: {value!r}")


def _number_text(value: int | float) -> str:
    return _float_text(value) if isinstance(value, float) else _integer_text(value)


def _rfc8785_number_text(value: int | float) -> str:
    if isinstance(value, float):
        return _ecmascript_float_text(value)
    return _safe_integer_text(value)


def _yaml_scalar(value: Any) -> str:
    return _scalar(value, _number_text, _yaml_string)


def _json_scalar(value: Any) -> str:
    return _scalar(value, _number_text, _json_string)


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, bool | int | float | str)


def _inline(value: Any, scalar: Callable[[Any], str]) -> str | None:
    """The one-line text of a scalar, ``{}``, ``[]`` a scalar sequence, or ``None``."""
    if isinstance(value, dict):
        return None if value else "{}"
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(_is_scalar(item) for item in value):
            return "[" + ", ".join(scalar(item) for item in value) + "]"
        return None
    return scalar(value)


def _sorted_keys(
    value: dict[Any, Any], key: Callable[[str], Any] | None = None
) -> list[str]:
    for name in value:
        if not isinstance(name, str):
            raise TypeError(f"a key must be a string, not {name!r}")
    return sorted(value, key=key)


def _yaml_block(value: Any, column: int, lines: list[str]) -> None:
    """Write an object with members or a block sequence at ``column``."""
    pad = " " * column
    if isinstance(value, dict):
        for key in _sorted_keys(value):
            head = f"{pad}{_yaml_key(key)}:"
            inline = _inline(value[key], _yaml_scalar)
            if inline is None:
                lines.append(head)
                _yaml_block(value[key], column + 2, lines)
            else:
                lines.append(f"{head} {inline}")
        return
    for item in value:
        inline = _inline(item, _yaml_scalar)
        if inline is None:
            lines.append(f"{pad}-")
            _yaml_block(item, column + 2, lines)
        else:
            lines.append(f"{pad}- {inline}")


def _yaml_text(value: Any) -> str:
    lines: list[str] = []
    if isinstance(value, dict | list) and value:
        _yaml_block(value, 0, lines)
    else:
        lines.append(_inline(value, _yaml_scalar) or "")
    return "\n".join(lines) + "\n"


def _json_lines(value: Any, column: int) -> list[str]:
    """The lines of a value; the first continues the line of its key or item."""
    inline = _inline(value, _json_scalar)
    if inline is not None:
        return [inline]
    if isinstance(value, dict):
        entries = [(_json_key(key) + ": ", value[key]) for key in _sorted_keys(value)]
        opening, closing = "{", "}"
    else:
        entries = [("", item) for item in value]
        opening, closing = "[", "]"
    pad = " " * (column + 2)
    lines = [opening]
    for index, (prefix, item) in enumerate(entries):
        nested = _json_lines(item, column + 2)
        nested[0] = pad + prefix + nested[0]
        if index < len(entries) - 1:
            nested[-1] += ","
        lines.extend(nested)
    lines.append(" " * column + closing)
    return lines


def _json_text(value: Any) -> str:
    return "\n".join(_json_lines(value, 0)) + "\n"


def _utf16(key: str) -> bytes:
    return key.encode("utf-16-be", "surrogatepass")


def _rfc8785_text(value: Any) -> str:
    if isinstance(value, dict):
        members = (
            f"{_json_key(key)}:{_rfc8785_text(value[key])}"
            for key in _sorted_keys(value, _utf16)
        )
        return "{" + ",".join(members) + "}"
    if isinstance(value, list):
        return "[" + ",".join(_rfc8785_text(item) for item in value) + "]"
    return _scalar(value, _rfc8785_number_text, _json_string)


_WRITERS: dict[str, Callable[[Any], str]] = {
    "yaml": _yaml_text,
    "json": _json_text,
    "jcs": _rfc8785_text,
}


def dumps(value: Any, serialization: Serialization = "yaml") -> str:
    """Return the text of a manifest, or of any JSON value, in one serialization.

    ``"yaml"`` writes canonical YAML, ``"json"`` pretty JSON and ``"jcs"``
    RFC 8785 JSON. A value that is an object whose ``timelines`` member is
    an array is a manifest: it is put in canonical order and its own-axis
    values respelled first (:func:`~timetoshare.manifest.canonical_order`).
    Every other value keeps the order of its arrays and the kind of its
    numbers. The form, complete or minimal, is the one given.

    Raises:
        ValueError: If the serialization refuses the value (a NaN or an
            infinity, a string or key holding a lone surrogate, a key whose
            canonical YAML form is longer than 1024 UTF-16 code units, and in
            ``"jcs"`` an integer beyond ±(2^53 − 1) or an integral float of
            magnitude from 2^53 up to but excluding 10^21), if a manifest
            cannot be put in canonical order, or if ``serialization`` names
            no serialization.
        TypeError: If the value is not JSON, whose kinds are ``dict`` with
            string keys, ``list``, ``str``, ``int``, ``float``, ``bool`` and
            ``None``.
    """
    if serialization not in _SERIALIZATIONS:
        raise ValueError(f"unknown serialization {serialization!r}")
    _all_finite(value)
    if is_manifest(value):
        value = canonical_order(value)
    text = _WRITERS[serialization](value)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError(
            "a string or key holding a lone surrogate cannot be written in UTF-8"
        ) from error
    return text


def spell(value: Any) -> str:
    """Spell a value as a message quotes it.

    A finite number is spelled as canonical YAML and pretty JSON spell it, an
    array as its items separated by ``, `` within brackets (``[32, 1]``), and
    anything else as compact JSON. The JavaScript package spells values the
    same way.
    """
    if isinstance(value, list):
        return "[" + ", ".join(spell(item) for item in value) + "]"
    if isinstance(value, float):
        return _float_text(value) if math.isfinite(value) else repr(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return _integer_text(value)
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


# Reading ------------------------------------------------------------------


def _position(text: str, index: int) -> str:
    line = text.count("\n", 0, index) + 1
    column = index - (text.rfind("\n", 0, index) + 1) + 1
    return f"line {line}, column {column}"


class _JsonSyntaxError(ValueError):
    """A text that is not one JSON value under the grammar of RFC 8259."""

    def __init__(self, text: str, index: int, problem: str) -> None:
        super().__init__(f"{problem} at {_position(text, index)}")


_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(\.[0-9]+)?([eE][-+]?[0-9]+)?")
_LITERALS = (("true", True), ("false", False), ("null", None))


def _skip(text: str, index: int) -> int:
    while index < len(text) and text[index] in _JSON_WHITESPACE:
        index += 1
    return index


def _read_json(text: str) -> Any:
    """Read a JSON text losslessly.

    Integers stay exact at any size and floats stay floats; a float is the
    double nearest to the decimal written. The whole text is checked against
    the grammar first, so a text that is not JSON raises
    :class:`_JsonSyntaxError` even where it also holds a refused value.

    Raises:
        _JsonSyntaxError: If the text is not one JSON value.
        ValueError: If it is, but repeats a key in an object, holds a lone
            surrogate in a string or a key, or a number that rounds to an
            infinity.
    """
    refusal: ValueError | None = None

    def refuse(index: int, problem: str) -> None:
        nonlocal refusal
        if refusal is None:
            refusal = ValueError(f"{problem} at {_position(text, index)}")

    def string(index: int) -> tuple[str, int]:
        try:
            value, end = json.decoder.scanstring(text, index + 1, True)
        except json.JSONDecodeError as error:
            problem = error.msg.removesuffix(" at")
            raise _JsonSyntaxError(text, error.pos, problem) from None
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            refuse(index, "a string holds a lone surrogate")
        return value, end

    def key(index: int) -> tuple[str, int]:
        if text[index : index + 1] != '"':
            raise _JsonSyntaxError(text, index, "expected a key")
        name, index = string(index)
        index = _skip(text, index)
        if text[index : index + 1] != ":":
            raise _JsonSyntaxError(text, index, "expected ':'")
        return name, index + 1

    # Each open container: [value, closing bracket, pending key, key position].
    stack: list[list[Any]] = []
    index = 0
    while True:
        index = _skip(text, index)
        character = text[index : index + 1]
        if character in ("{", "["):
            closing = "}" if character == "{" else "]"
            index = _skip(text, index + 1)
            if text[index : index + 1] == closing:
                value: Any = {} if character == "{" else []
                index += 1
            else:
                frame: list[Any] = [{} if character == "{" else [], closing, None, 0]
                if character == "{":
                    frame[3] = index
                    frame[2], index = key(index)
                stack.append(frame)
                continue
        elif character == '"':
            value, index = string(index)
        elif character and character in "-0123456789":
            match = _NUMBER.match(text, index)
            if match is None:
                raise _JsonSyntaxError(text, index, "invalid number")
            if match.group(1) is None and match.group(2) is None:
                value = int(match.group())
            else:
                value = float(match.group())
                if not math.isfinite(value):
                    refuse(index, f"{match.group()} rounds to an infinity")
            index = match.end()
        else:
            for word, literal in _LITERALS:
                if text.startswith(word, index):
                    value, index = literal, index + len(word)
                    break
            else:
                problem = (
                    "unexpected end of text" if not character else "expected a value"
                )
                raise _JsonSyntaxError(text, index, problem)
        while True:
            if not stack:
                index = _skip(text, index)
                if index != len(text):
                    raise _JsonSyntaxError(text, index, "extra data after the value")
                if refusal is not None:
                    raise refusal
                return value
            frame = stack[-1]
            container, closing = frame[0], frame[1]
            if closing == "}":
                if frame[2] in container:
                    refuse(frame[3], f"the key {json.dumps(frame[2])} repeats")
                container[frame[2]] = value
            else:
                container.append(value)
            index = _skip(text, index)
            character = text[index : index + 1]
            if character == ",":
                index = _skip(text, index + 1)
                if closing == "}":
                    frame[3] = index
                    frame[2], index = key(index)
                break
            if character != closing:
                raise _JsonSyntaxError(text, index, f"expected ',' or '{closing}'")
            stack.pop()
            value, index = container, index + 1


_CORE_NULL = re.compile(r"(?:~|null|Null|NULL|)\Z")
_CORE_BOOL = re.compile(r"(?:true|True|TRUE|false|False|FALSE)\Z")
_CORE_INT = re.compile(r"(?:[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)\Z")
_CORE_FLOAT = re.compile(
    r"(?:[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?"
    r"|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))\Z"
)
_CORE_FINITE_FLOAT = re.compile(
    r"[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?\Z"
)
_TAG = "tag:yaml.org,2002:"


class _YamlLoader(yaml.SafeLoader):
    """PyYAML's safe loader reading under the YAML 1.2 core schema.

    The implicit resolvers are the core schema's (null, booleans, integers in
    base 10, ``0o`` and ``0x``, floats), replacing YAML 1.1's, so ``no`` and
    ``2026-11-17`` are strings and ``1e-05`` is a float. Only the JSON data
    model is constructed: a tag outside it, such as ``!!timestamp``,
    ``!!binary``, ``!!set`` or ``!!omap``, is refused, and so are anchors and
    aliases, a repeated key, a key that is not a string, a non-finite float
    and a string holding an unpaired surrogate.
    """

    yaml_implicit_resolvers: dict[Any, Any] = {}
    yaml_constructors: dict[Any, Any] = {}

    def compose_node(self, parent: Any, index: Any) -> Any:
        event = self.peek_event()
        if isinstance(event, yaml.AliasEvent):
            raise yaml.composer.ComposerError(
                None, None, "an alias is not read", event.start_mark
            )
        if getattr(event, "anchor", None) is not None:
            raise yaml.composer.ComposerError(
                None, None, "an anchor is not read", event.start_mark
            )
        return super().compose_node(parent, index)

    def construct_mapping(self, node: Any, deep: bool = False) -> dict[str, Any]:
        mapping: dict[str, Any] = {}
        for key_node, value_node in node.value:
            key = (
                self.construct_object(key_node, deep=True)
                if isinstance(key_node, yaml.ScalarNode)
                else None
            )
            if not isinstance(key, str):
                _refuse(key_node, "a key that is not a string is not read")
            if key in mapping:
                _refuse(key_node, f"the key {json.dumps(key)} repeats")
            mapping[key] = self.construct_object(value_node, deep=True)
        return mapping


def _refuse(node: Any, problem: str) -> NoReturn:
    raise yaml.constructor.ConstructorError(None, None, problem, node.start_mark)


def _construct_null(loader: _YamlLoader, node: Any) -> None:
    if not _CORE_NULL.match(loader.construct_scalar(node)):
        _refuse(node, "not a null")


def _construct_bool(loader: _YamlLoader, node: Any) -> bool:
    text = loader.construct_scalar(node)
    if not _CORE_BOOL.match(text):
        _refuse(node, "not a boolean")
    return text in ("true", "True", "TRUE")


def _construct_int(loader: _YamlLoader, node: Any) -> int:
    text = loader.construct_scalar(node)
    if not _CORE_INT.match(text):
        _refuse(node, f"{text!r} is not an integer")
    if text.startswith(("0o", "0x")):
        return int(text[2:], 8 if text[1] == "o" else 16)
    return int(text)


def _construct_float(loader: _YamlLoader, node: Any) -> float:
    text = loader.construct_scalar(node)
    if not _CORE_FINITE_FLOAT.match(text):
        _refuse(node, f"{text!r} is not a finite float")
    value = float(text)
    if not math.isfinite(value):
        _refuse(node, f"{text} rounds to an infinity")
    return value


def _construct_str(loader: _YamlLoader, node: Any) -> str:
    text = loader.construct_scalar(node)
    try:
        # Join a high surrogate and a low one, written as two escapes, into
        # one character; an unpaired surrogate cannot be decoded.
        return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le")
    except UnicodeDecodeError:
        _refuse(node, "a string holds a lone surrogate")


def _construct_seq(loader: _YamlLoader, node: Any) -> list[Any]:
    return loader.construct_sequence(node, deep=True)


def _construct_map(loader: _YamlLoader, node: Any) -> dict[str, Any]:
    return loader.construct_mapping(node, deep=True)


def _construct_other(loader: _YamlLoader, node: Any) -> None:
    _refuse(node, f"the tag {node.tag} names no value of the JSON data model")


for _name, _pattern, _first in (
    ("null", _CORE_NULL, ["~", "n", "N", ""]),
    ("bool", _CORE_BOOL, list("tTfF")),
    ("int", _CORE_INT, list("-+0123456789")),
    ("float", _CORE_FLOAT, list("-+.0123456789")),
):
    _YamlLoader.add_implicit_resolver(_TAG + _name, _pattern, _first)
for _name, _constructor in (
    ("null", _construct_null),
    ("bool", _construct_bool),
    ("int", _construct_int),
    ("float", _construct_float),
    ("str", _construct_str),
    ("seq", _construct_seq),
    ("map", _construct_map),
):
    _YamlLoader.add_constructor(_TAG + _name, _constructor)
_YamlLoader.add_constructor(None, _construct_other)


def _read_yaml(text: str) -> Any:
    """Read a YAML text under the YAML 1.2 core schema.

    An empty text, or one of comments only, reads as null.

    Raises:
        ValueError: With the line and column, for every error of the parser
            (more than one document and an unknown tag among them) and every
            value :class:`_YamlLoader` refuses.
    """
    try:
        loader = _YamlLoader(text)
        try:
            return loader.get_single_data()
        finally:
            loader.dispose()
    except yaml.MarkedYAMLError as error:
        mark = error.problem_mark or error.context_mark
        problem = ", ".join(part for part in (error.context, error.problem) if part)
        if mark is None:
            raise ValueError(problem) from None
        raise ValueError(
            f"{problem} at line {mark.line + 1}, column {mark.column + 1}"
        ) from None
    except yaml.reader.ReaderError as error:
        where = _position(text, error.position)
        raise ValueError(f"{error.reason} #x{error.character:04x} at {where}") from None


def _without_byte_order_mark(text: str) -> str:
    return text[1:] if text.startswith(_BYTE_ORDER_MARK) else text


def _opens_json(text: str) -> bool:
    return text.lstrip(_JSON_WHITESPACE)[:1] in ("{", "[")


def loads(text: str) -> Any:
    """Read a text in any serialization, JSON or YAML.

    One U+FEFF at position 0 is removed first. The text is read as JSON when
    its first character other than a space, a tab, a line feed or a carriage
    return is ``{`` or ``[``, or when it is a JSON text; every other text is
    read as YAML. Integers stay exact at any size and floats stay floats. It
    does not validate.

    Raises:
        ValueError: With the line and column of the fault, for a text the
            reading rules refuse: a JSON text that is not one JSON value, an
            error of the YAML parser (more than one document, an unknown tag),
            a key that repeats in its object, a key that is not a string, an
            anchor or an alias, a value outside the JSON data model, a
            non-finite number (``NaN``, ``Infinity``, ``.inf``, ``.nan`` and
            a number that rounds to an infinity) and a lone surrogate in a
            string or a key, written as itself or through an escape.
        TypeError: If ``text`` is not a ``str``.
    """
    if not isinstance(text, str):
        raise TypeError(f"loads reads a str, not {type(text).__name__}")
    text = _without_byte_order_mark(text)
    try:
        return _read_json(text)
    except _JsonSyntaxError:
        if _opens_json(text):
            raise
    return _read_yaml(text)


def serialization_of(text: str) -> Serialization:
    """Name the serialization of a text without validating it; never raises.

    ``"jcs"`` for a text read as JSON that is byte for byte the RFC 8785
    JSON of its value; ``"json"`` for every other text read as JSON (one
    that cannot be read, one whose value the RFC 8785 writer refuses, and
    one that begins with a byte order mark included); ``"yaml"`` for every
    other text.
    """
    body = _without_byte_order_mark(text)
    try:
        value = _read_json(body)
    except _JsonSyntaxError:
        return "json" if _opens_json(body) else "yaml"
    except (ValueError, RecursionError):
        return "json"
    if body is not text:
        return "json"
    try:
        return "jcs" if dumps(value, serialization="jcs") == body else "json"
    except (ValueError, TypeError, RecursionError):
        return "json"
