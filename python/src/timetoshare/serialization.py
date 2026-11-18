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
UTF-16 code units, a value nested deeper than 256 levels, and in RFC 8785
JSON an integer beyond ±(2^53 − 1) or an integral float of magnitude from
2^53 up to but excluding 10^21.

The depth of a value is 0 for a scalar and, for an object or an array, 1 more
than the greatest depth of its members (1 for an empty one). The readers
refuse a text whose value would be deeper than 256, at the first character
of the first collection at depth 257, so that every value written can be read
and the place of the refusal depends on the text alone. A text holding several
faults is refused for the first in document order, where its token stands.
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

_DEPTH_LIMIT = 256
"""The greatest depth of a value a writer writes and a reader reads."""

_TOO_DEEP = f"collections nest deeper than {_DEPTH_LIMIT} levels"
"""The reason the readers give for a text nested deeper than the limit."""

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


def _within_depth(value: Any) -> None:
    """Refuse a value nested deeper than the limit, walking no deeper than it.

    A list or a dict that holds itself is refused the same way.
    """
    pending = [(value, 1)]
    while pending:
        item, depth = pending.pop()
        if isinstance(item, list | dict):
            if depth > _DEPTH_LIMIT:
                raise ValueError(
                    f"a value nested deeper than {_DEPTH_LIMIT} levels "
                    "cannot be written"
                )
            members = item.values() if isinstance(item, dict) else item
            pending.extend((member, depth + 1) for member in members)


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
        ValueError: If the serialization refuses the value (a value nested
            deeper than 256 levels, checked first, a NaN or an infinity, a
            string or key holding a lone surrogate, a key whose canonical
            YAML form is longer than 1024 UTF-16 code units, and in
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
    _within_depth(value)
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
    """The line and column of an index, counted from one, the column in code points."""
    line = text.count("\n", 0, index) + 1
    column = index - (text.rfind("\n", 0, index) + 1) + 1
    return f"line {line}, column {column}"


_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(\.[0-9]+)?([eE][-+]?[0-9]+)?")
_LITERALS = (("true", True), ("false", False), ("null", None))
_STRING_RUN = re.compile(r'[^"\\\x00-\x1f\ud800-\udfff]+')
_STRING_ESCAPES = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}
_HEX4 = re.compile(r"[0-9A-Fa-f]{4}")
_JSON_SCALAR = re.compile(
    r'[ \t\n\r]*(?:"(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9A-Fa-f]{4}))*"'
    r"|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?|true|false|null)[ \t\n\r]*"
)
"""One JSON scalar under the grammar of RFC 8259, with white space around it."""


def _skip(text: str, index: int) -> int:
    while index < len(text) and text[index] in _JSON_WHITESPACE:
        index += 1
    return index


def _read_json(text: str) -> Any:
    """Read a JSON text losslessly.

    Integers stay exact at any size and floats stay floats; a float is the
    double nearest to the decimal written. The text is read from its first
    character and refused at its first fault, at the token that offends: a
    string at the escape or the character that ends it wrongly, a lone
    surrogate where it is written, a number that rounds to an infinity, a
    repeated key, and a collection opening at depth 257 where they stand.

    Raises:
        ValueError: If the text is not one JSON value, repeats a key in an
            object, holds a lone surrogate in a string or a key, or a number
            that rounds to an infinity, or nests collections deeper than 256
            levels.
    """

    def fail(index: int, problem: str) -> NoReturn:
        raise ValueError(f"{problem} at {_position(text, index)}")

    def string(index: int) -> tuple[str, int]:
        """The string whose opening quote is at ``index``, and the index after it.

        A high-surrogate escape pairs only with the low-surrogate escape right
        after it; one that does not is lone where it is written, whatever
        follows it. A surrogate standing as itself is lone.
        """
        parts: list[str] = []
        high = -1
        index += 1
        while True:
            run = _STRING_RUN.match(text, index)
            if run is not None and high < 0:
                parts.append(run.group())
                index = run.end()
            at = index
            if text.startswith("\\u", index) and _HEX4.match(text, index + 2):
                unit = int(text[index + 2 : index + 6], 16)
                index += 6
                if high >= 0:
                    if not 0xDC00 <= unit <= 0xDFFF:
                        fail(high, "a string holds a lone surrogate")
                    first = int(text[high + 2 : high + 6], 16)
                    parts.append(
                        chr(0x10000 + ((first - 0xD800) << 10) + unit - 0xDC00)
                    )
                    high = -1
                elif 0xD800 <= unit <= 0xDBFF:
                    high = at
                elif 0xDC00 <= unit <= 0xDFFF:
                    fail(at, "a string holds a lone surrogate")
                else:
                    parts.append(chr(unit))
                continue
            if high >= 0:
                fail(high, "a string holds a lone surrogate")
            character = text[index : index + 1]
            if character == '"':
                return "".join(parts), index + 1
            if character == "\\":
                escaped = text[index + 1 : index + 2]
                if escaped not in _STRING_ESCAPES:
                    fail(at, "an invalid escape")
                parts.append(_STRING_ESCAPES[escaped])
                index += 2
            elif not character:
                fail(at, "an unterminated string")
            elif character < " ":
                fail(at, "a control character in a string")
            else:
                fail(at, "a string holds a lone surrogate")

    # Each open container: [value, closing bracket, pending key].
    stack: list[list[Any]] = []

    def key(index: int, container: dict[str, Any]) -> tuple[str, int]:
        if text[index : index + 1] != '"':
            fail(index, "expected a key")
        name, after = string(index)
        if name in container:
            fail(index, f"the key {json.dumps(name)} repeats")
        after = _skip(text, after)
        if text[after : after + 1] != ":":
            fail(after, "expected ':'")
        return name, after + 1

    index = 0
    while True:
        index = _skip(text, index)
        character = text[index : index + 1]
        if character in ("{", "["):
            if len(stack) == _DEPTH_LIMIT:
                fail(index, _TOO_DEEP)
            closing = "}" if character == "{" else "]"
            index = _skip(text, index + 1)
            if text[index : index + 1] == closing:
                value: Any = {} if character == "{" else []
                index += 1
            else:
                frame: list[Any] = [{} if character == "{" else [], closing, None]
                if character == "{":
                    frame[2], index = key(index, frame[0])
                stack.append(frame)
                continue
        elif character == '"':
            value, index = string(index)
        elif character and character in "-0123456789":
            match = _NUMBER.match(text, index)
            if match is None:
                fail(index, "invalid number")
            if match.group(1) is None and match.group(2) is None:
                value = int(match.group())
            else:
                value = float(match.group())
                if not math.isfinite(value):
                    fail(index, f"{match.group()} rounds to an infinity")
            index = match.end()
        else:
            for word, literal in _LITERALS:
                if text.startswith(word, index):
                    value, index = literal, index + len(word)
                    break
            else:
                fail(
                    index,
                    "unexpected end of text" if not character else "expected a value",
                )
        while True:
            if not stack:
                index = _skip(text, index)
                if index != len(text):
                    fail(index, "extra data after the value")
                return value
            frame = stack[-1]
            container, closing = frame[0], frame[1]
            if closing == "}":
                container[frame[2]] = value
            else:
                container.append(value)
            index = _skip(text, index)
            character = text[index : index + 1]
            if character == ",":
                index = _skip(text, index + 1)
                if closing == "}":
                    frame[2], index = key(index, container)
                break
            if character != closing:
                fail(index, f"expected ',' or '{closing}'")
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
    model is read: a tag outside it, such as ``!!timestamp``, ``!!binary``,
    ``!!set`` or ``!!omap``, is refused, and so are anchors and aliases, a
    repeated key, a key that is not a string, a non-finite float, a string
    holding an unpaired surrogate and a collection opening at depth 257.

    The value is built in one pass over the parser's events, every
    collection on a stack rather than by recursion, and each node is checked
    as its event arrives, a key before its value: its anchor, its tag, a key
    being a string and not repeating, its depth, then its value. So the
    refusal raised is the first in document order, and a parser error is
    raised where the parser meets it.
    """

    yaml_implicit_resolvers: dict[Any, Any] = {}
    yaml_constructors: dict[Any, Any] = {}

    def get_single_data(self) -> Any:
        """Read the one document of the stream; ``None`` for an empty stream."""
        self.get_event()
        value = None
        if not self.check_event(yaml.StreamEndEvent):
            self.get_event()
            value = self._read_value()
            self.get_event()
        if not self.check_event(yaml.StreamEndEvent):
            event = self.get_event()
            raise yaml.composer.ComposerError(
                "expected a single document in the stream",
                None,
                "but found another document",
                event.start_mark,
            )
        self.get_event()
        return value

    def _read_value(self) -> Any:
        """Read the value beginning at the next event, and every value in it."""
        # The collections being read, the innermost last: [the value being
        # built, the key whose value is pending, or _NO_KEY].
        frames: list[list[Any]] = []
        while True:
            event = self.get_event()
            if isinstance(event, yaml.SequenceEndEvent | yaml.MappingEndEvent):
                value = frames.pop()[0]
            else:
                if isinstance(event, yaml.AliasEvent):
                    _refuse(event, "an alias is not read")
                if event.anchor is not None:
                    _refuse(event, "an anchor is not read")
                holder = frames[-1] if frames else None
                is_key = (
                    holder is not None
                    and isinstance(holder[0], dict)
                    and holder[1] is _NO_KEY
                )
                if isinstance(event, yaml.ScalarEvent):
                    value = self._scalar(event)
                    if is_key:
                        if not isinstance(value, str):
                            _refuse(event, "a key that is not a string is not read")
                        if value in holder[0]:
                            _refuse(event, f"the key {json.dumps(value)} repeats")
                        holder[1] = value
                        continue
                else:
                    is_sequence = isinstance(event, yaml.SequenceStartEvent)
                    _collection_tag(event, is_sequence, self.resolve)
                    if is_key:
                        _refuse(event, "a key that is not a string is not read")
                    if len(frames) == _DEPTH_LIMIT:
                        _refuse(event, _TOO_DEEP)
                    frames.append([[] if is_sequence else {}, _NO_KEY])
                    continue
            if not frames:
                return value
            holder = frames[-1]
            if isinstance(holder[0], list):
                holder[0].append(value)
            else:
                holder[0][holder[1]] = value
                holder[1] = _NO_KEY

    def _scalar(self, event: Any) -> Any:
        """The value of a scalar, built by the constructor of its tag."""
        tag = event.tag
        if tag is None or tag == "!":
            tag = self.resolve(yaml.ScalarNode, event.value, event.implicit)
        node = yaml.ScalarNode(
            tag, event.value, event.start_mark, event.end_mark, event.style
        )
        constructor = self.yaml_constructors.get(tag, self.yaml_constructors[None])
        return constructor(self, node)


_NO_KEY = object()
"""The key of a mapping whose next node is a key."""


def _collection_tag(event: Any, is_sequence: bool, resolve: Callable[..., str]) -> None:
    """Refuse a collection under a tag other than the plain one of its kind."""
    kind = yaml.SequenceNode if is_sequence else yaml.MappingNode
    tag = event.tag
    if tag is None or tag == "!":
        tag = resolve(kind, None, event.implicit)
    if tag == _TAG + ("seq" if is_sequence else "map"):
        return
    if tag in (_TAG + "seq", _TAG + "map"):
        _refuse(event, f"the tag {tag} does not fit the node it is given")
    _refuse(event, f"the tag {tag} names no value of the JSON data model")


def _refuse(node: Any, problem: str) -> NoReturn:
    """Refuse a node, or the event that begins it, at its start."""
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


def _construct_mismatched(loader: _YamlLoader, node: Any) -> None:
    """Refuse a node under ``!!seq`` or ``!!map`` that is not of that kind."""
    _refuse(node, f"the tag {node.tag} does not fit the node it is given")


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
    ("seq", _construct_mismatched),
    ("map", _construct_mismatched),
):
    _YamlLoader.add_constructor(_TAG + _name, _constructor)
_YamlLoader.add_constructor(None, _construct_other)


def _read_yaml(text: str) -> Any:
    """Read a YAML text under the YAML 1.2 core schema.

    An empty text, or one of comments only, reads as null. The text is
    refused at its first fault in document order.

    Raises:
        ValueError: With the line and column, both counted from one, the
            column in code points, for every error of the parser (more than
            one document, a character YAML does not allow, an unknown tag
            among them), collections nested deeper than 256 levels, at the
            start of the first collection at depth 257, and every value
            :class:`_YamlLoader` refuses.
    """
    try:
        return _load_yaml(text)
    except yaml.reader.ReaderError as error:
        # PyYAML checks every character before it parses any, so a fault
        # before the character it refuses is found in the text before it.
        try:
            _load_yaml(text[: error.position])
        except yaml.MarkedYAMLError as earlier:
            mark = earlier.problem_mark or earlier.context_mark
            if mark is not None and mark.index < error.position:
                raise _marked(earlier) from None
        where = _position(text, error.position)
        raise ValueError(f"{error.reason} #x{error.character:04x} at {where}") from None
    except yaml.MarkedYAMLError as error:
        raise _marked(error) from None


def _load_yaml(text: str) -> Any:
    loader = _YamlLoader(text)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def _marked(error: yaml.MarkedYAMLError) -> ValueError:
    """The refusal of a parser error or a refused node, with its line and column."""
    mark = error.problem_mark or error.context_mark
    problem = ", ".join(part for part in (error.context, error.problem) if part)
    if mark is None:
        return ValueError(problem)
    return ValueError(f"{problem} at line {mark.line + 1}, column {mark.column + 1}")


def _without_byte_order_mark(text: str) -> str:
    return text[1:] if text.startswith(_BYTE_ORDER_MARK) else text


def _reads_as_json(text: str) -> bool:
    """Whether a text is read as JSON: it opens with ``{`` or ``[`` after white
    space, or it is one JSON scalar."""
    opening = text.lstrip(_JSON_WHITESPACE)[:1]
    return opening in ("{", "[") or _JSON_SCALAR.fullmatch(text) is not None


def loads(text: str) -> Any:
    """Read a text in any serialization, JSON or YAML.

    One U+FEFF at position 0 is removed first. The text is read as JSON when
    its first character other than a space, a tab, a line feed or a carriage
    return is ``{`` or ``[``, or when it is a JSON text; every other text is
    read as YAML. Integers stay exact at any size and floats stay floats. It
    does not validate.

    Raises:
        ValueError: With the line and column of the first fault in document
            order, both counted from one, the column in code points (in the
            text after a leading U+FEFF is removed), for a text the reading
            rules refuse: a JSON text that is not one JSON value, an error of
            the YAML parser (more than one document, an unknown tag), a key
            that repeats in its object, a key that is not a string, an
            anchor or an alias, a value outside the JSON data model, a
            non-finite number (``NaN``, ``Infinity``, ``.inf``, ``.nan`` and
            a number that rounds to an infinity), a lone surrogate in a
            string or a key, written as itself or through an escape, and
            collections nested deeper than 256 levels, placed at the first
            collection at depth 257.
        TypeError: If ``text`` is not a ``str``.
    """
    if not isinstance(text, str):
        raise TypeError(f"loads reads a str, not {type(text).__name__}")
    text = _without_byte_order_mark(text)
    return _read_json(text) if _reads_as_json(text) else _read_yaml(text)


def serialization_of(text: str) -> Serialization:
    """Name the serialization of a text without validating it; never raises.

    ``"jcs"`` for a text read as JSON that is byte for byte the RFC 8785
    JSON of its value; ``"json"`` for every other text read as JSON (one
    that cannot be read, one whose value the RFC 8785 writer refuses, and
    one that begins with a byte order mark included); ``"yaml"`` for every
    other text.
    """
    body = _without_byte_order_mark(text)
    if not _reads_as_json(body):
        return "yaml"
    if body is not text:
        return "json"
    try:
        return "jcs" if dumps(_read_json(body), serialization="jcs") == body else "json"
    except (ValueError, TypeError):
        return "json"
