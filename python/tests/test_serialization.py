from __future__ import annotations

import json
import math
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from timetoshare import canonical_order, dumps, loads, serialization_of

from .conftest import manifest, timeline

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SERIALIZATIONS = REPOSITORY_ROOT / "fixtures" / "serializations"
FILES = {"yaml": "canonical.yaml", "json": "pretty.json", "jcs": "rfc8785.json"}
ALL = ("yaml", "json", "jcs")

MANIFEST_CASES = {
    "readme_manifest",
    "manifest_canonical_order",
    "manifest_order_by_value",
    "manifest_ties_kept",
    "manifest_display_order",
}
JSON_TEXT_CASES = {
    "top_level_empty_object",
    "top_level_empty_array",
    "top_level_integer",
    "top_level_float",
    "top_level_null",
    "top_level_true",
    "top_level_quoted_string",
    "top_level_string_yaml_escapes",
}
"""The cases whose canonical YAML is a JSON text too, which a reader reads as JSON."""

YAML_READ_AS_JSON = {
    "flow_mapping_unquoted_key.yaml",
    "flow_sequence_plain.yaml",
    "flow_sequence_then_comment.yaml",
}
"""Refusals meant as YAML that open with ``{`` or ``[`` and are read as JSON."""

WRITER_REFUSALS = {
    "key_1025_plain.json": set(ALL),
    "key_1025_quoted.json": set(ALL),
    "key_1025_utf16_units.json": set(ALL),
    "key_1025_nested.yaml": set(ALL),
    "integer_2_53.json": {"jcs"},
    "integer_minus_2_53.yaml": {"jcs"},
    "integer_2_64.yaml": {"jcs"},
    "float_2_53.yaml": {"jcs"},
    "float_minus_1e16.yaml": {"jcs"},
    "float_1e20.json": {"jcs"},
    "float_below_1e21.yaml": {"jcs"},
    "order_entry_not_object.yaml": set(ALL),
    "order_entries_not_objects_without_version.json": set(ALL),
    "order_member_missing.yaml": set(ALL),
    "order_member_wrong_type.yaml": set(ALL),
    "order_id_wrong_type.yaml": set(ALL),
    "order_timestamp_timeline_not_string.yaml": set(ALL),
    "order_group_member_not_string.yaml": set(ALL),
    "order_coordinate_zero_denominator.yaml": set(ALL),
    "order_coordinate_three_members.yaml": set(ALL),
    "order_coordinate_boolean.yaml": set(ALL),
}
"""The writer refusals and the serializations that refuse each, as the cases' README
states them; every file of ``refusals-writing/`` is one of them."""


def _text(path: Path) -> str:
    """The text of a file, a leading byte order mark kept."""
    return path.read_bytes().decode("utf-8")


def _kind(value: Any) -> Any:
    """A form of a JSON value whose equality is kind for kind.

    An integer equals only an integer, a float only a float, and ``-0.0``
    differs from ``0.0``.
    """
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return (type(value).__name__, value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, float):
        return ("float", value, math.copysign(1.0, value))
    if isinstance(value, list):
        return ("list", [_kind(item) for item in value])
    assert isinstance(value, dict)
    return ("dict", {key: _kind(item) for key, item in value.items()})


def _is_json_text(text: str) -> bool:
    """Whether a text is one JSON value, by the standard library's reader."""

    def refuse(constant: str) -> None:
        raise ValueError(constant)

    try:
        json.loads(text, parse_constant=refuse)
    except ValueError:
        return False
    return True


def _integral_floats_as_integers(value: Any) -> Any:
    """The value RFC 8785 JSON reads back: integral floats below 2^53 as integers."""
    if isinstance(value, float) and value.is_integer() and abs(value) < 2**53:
        return int(value)
    if isinstance(value, list):
        return [_integral_floats_as_integers(item) for item in value]
    if isinstance(value, dict):
        return {key: _integral_floats_as_integers(item) for key, item in value.items()}
    return value


# -- the shared cases ----------------------------------------------------------------

CASES = sorted(path for path in (SERIALIZATIONS / "cases").iterdir() if path.is_dir())


def _case(case: Path) -> tuple[Any, dict[str, str]]:
    texts = {
        serialization: _text(case / name)
        for serialization, name in FILES.items()
        if (case / name).exists()
    }
    return loads(texts["json"]), texts


def test_the_cases_are_listed() -> None:
    assert len(CASES) == 35
    assert all((case / "canonical.yaml").exists() for case in CASES)
    assert {case.name for case in CASES if not (case / "rfc8785.json").exists()} == {
        "integers_beyond_double",
        "floats_integral_large",
    }


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_a_case_is_written_byte_for_byte(case: Path) -> None:
    value, texts = _case(case)
    for serialization in ALL:
        if serialization in texts:
            assert dumps(value, serialization=serialization) == texts[serialization]
        else:
            with pytest.raises(ValueError):
                dumps(value, serialization=serialization)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_the_json_texts_of_a_case_read_and_write_back(case: Path) -> None:
    value, texts = _case(case)
    assert dumps(loads(texts["json"]), serialization="json") == texts["json"]
    if "jcs" in texts:
        read = loads(texts["jcs"])
        assert _kind(read) == _kind(_integral_floats_as_integers(value))
        assert dumps(read, serialization="jcs") == texts["jcs"]
        if case.name in MANIFEST_CASES:
            assert dumps(read) == texts["yaml"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_the_canonical_yaml_of_a_case_reads_to_its_value(case: Path) -> None:
    value, texts = _case(case)
    read = loads(texts["yaml"])
    assert _kind(read) == _kind(value)
    assert dumps(read) == texts["yaml"]


# -- readings ------------------------------------------------------------------------


def _is_expected(path: Path) -> bool:
    return path.name.endswith((".expected.yaml", ".expected.rfc8785.json"))


READINGS = sorted(
    path for path in (SERIALIZATIONS / "readings").iterdir() if not _is_expected(path)
)


def _expected(path: Path, suffix: str) -> Path:
    return path.with_name(path.name.rsplit(".", 1)[0] + suffix)


def test_every_reading_has_its_expected_text() -> None:
    assert READINGS
    for path in READINGS:
        assert _expected(path, ".expected.yaml").exists(), path.name


@pytest.mark.parametrize("path", READINGS, ids=lambda path: path.name)
def test_a_reading_reads_to_its_expected_value(path: Path) -> None:
    value = loads(_text(path))
    assert dumps(value) == _text(_expected(path, ".expected.yaml"))
    rfc8785 = _expected(path, ".expected.rfc8785.json")
    if rfc8785.exists():
        assert dumps(value, serialization="jcs") == _text(rfc8785)


@pytest.mark.parametrize("path", READINGS, ids=lambda path: path.name)
def test_an_expected_text_reads_and_writes_back(path: Path) -> None:
    expected = _text(_expected(path, ".expected.yaml"))
    value = loads(expected)
    assert dumps(value) == expected
    rfc8785 = _expected(path, ".expected.rfc8785.json")
    if rfc8785.exists():
        assert dumps(value, serialization="jcs") == _text(rfc8785)


# -- refusals ------------------------------------------------------------------------

REFUSALS = sorted((SERIALIZATIONS / "refusals").iterdir())


@pytest.mark.parametrize("path", REFUSALS, ids=lambda path: path.name)
def test_a_refused_text_raises(path: Path) -> None:
    with pytest.raises(ValueError):
        loads(_text(path))


WRITING = sorted(path.name for path in (SERIALIZATIONS / "refusals-writing").iterdir())


def test_every_writer_refusal_is_stated() -> None:
    assert WRITING
    assert set(WRITING) == set(WRITER_REFUSALS)


def test_the_tables_name_exactly_their_files() -> None:
    values = {case.name: _case(case)[0] for case in CASES}
    texts = {case.name: _text(case / "canonical.yaml") for case in CASES}
    assert MANIFEST_CASES == {
        name
        for name, value in values.items()
        if isinstance(value, dict) and isinstance(value.get("timelines"), list)
    }
    assert JSON_TEXT_CASES == {
        name for name, text in texts.items() if _is_json_text(text)
    }
    assert YAML_READ_AS_JSON == {
        path.name
        for path in REFUSALS
        if path.suffix == ".yaml" and _text(path).lstrip(" \t\n\r")[:1] in ("{", "[")
    }


@pytest.mark.parametrize("name", WRITING)
def test_a_writer_refuses_a_value_in_the_serializations_named(name: str) -> None:
    value = loads(_text(SERIALIZATIONS / "refusals-writing" / name))
    for serialization in ALL:
        if serialization in WRITER_REFUSALS[name]:
            with pytest.raises(ValueError):
                dumps(value, serialization=serialization)
        else:
            dumps(value, serialization=serialization)


# -- serialization_of ----------------------------------------------------------------


def _named_serialization(path: Path) -> str:
    """The serialization the cases' README names for one of its files."""
    relative = path.relative_to(SERIALIZATIONS)
    directory, name = relative.parts[0], relative.parts[-1]
    if directory == "cases":
        if name == "canonical.yaml":
            return "json" if relative.parts[1] in JSON_TEXT_CASES else "yaml"
        return "json" if name == "pretty.json" else "jcs"
    if name.endswith(".expected.rfc8785.json"):
        return "jcs"
    if name.endswith(".expected.yaml"):
        return "json" if _is_json_text(_text(path)) else "yaml"
    if name.endswith(".json") or name in YAML_READ_AS_JSON:
        return "json"
    return "yaml"


ALL_FILES = sorted(
    path
    for path in SERIALIZATIONS.rglob("*")
    if path.is_file() and path.suffix != ".md"
)


@pytest.mark.parametrize(
    "path", ALL_FILES, ids=lambda path: path.relative_to(SERIALIZATIONS).as_posix()
)
def test_serialization_of_names_every_file(path: Path) -> None:
    assert serialization_of(_text(path)) == _named_serialization(path)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("{}", "jcs"),
        ("\ufeff{}", "json"),
        ("{}\n", "json"),
        ("a: 1\n", "yaml"),
        ("", "yaml"),
        ("[1,", "json"),
        ('{"a": "\\ud800"}', "json"),
        ('{"a": "\ud800"}', "json"),
        ('a: "\ud800"\n', "yaml"),
        ('{"b":1,"a":2}', "json"),
        ("[9007199254740992]", "json"),
        ("480", "jcs"),
    ],
    ids=repr,
)
def test_serialization_of_never_raises(text: str, expected: str) -> None:
    assert serialization_of(text) == expected


# -- the float spelling --------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "canonical", "rfc8785"),
    [
        (2.0, "2.0", "2"),
        (123.25, "123.25", "123.25"),
        (0.1, "0.1", "0.1"),
        (0.0001, "0.0001", "0.0001"),
        (0.00001, "1.0e-05", "0.00001"),
        (0.00005, "5.0e-05", "0.00005"),
        (-2.5e-07, "-2.5e-07", "-2.5e-7"),
        (1.5e-10, "1.5e-10", "1.5e-10"),
        (1e-7, "1.0e-07", "1e-7"),
        (1e15, "1000000000000000.0", "1000000000000000"),
        (1700000000.0, "1700000000.0", "1700000000"),
        (1503.25, "1503.25", "1503.25"),
        (1e21, "1.0e+21", "1e+21"),
        (5e-324, "5.0e-324", "5e-324"),
        (1.7976931348623157e308, "1.7976931348623157e+308", "1.7976931348623157e+308"),
        (0.0, "0.0", "0"),
        (-0.0, "-0.0", "0"),
    ],
    ids=repr,
)
def test_floats_are_spelled_by_the_algorithm(
    value: float, canonical: str, rfc8785: str
) -> None:
    assert dumps(value) == canonical + "\n"
    assert dumps(value, serialization="json") == canonical + "\n"
    assert dumps(value, serialization="jcs") == rfc8785


@pytest.mark.parametrize(
    ("value", "canonical"),
    [(1e16, "1.0e+16"), (1.5e16, "1.5e+16"), (2.0**53, "9007199254740992.0")],
    ids=repr,
)
def test_integral_floats_rfc8785_refuses(value: float, canonical: str) -> None:
    assert dumps([value]) == f"- {canonical}\n"
    with pytest.raises(ValueError, match="RFC 8785"):
        dumps([value], serialization="jcs")


# -- the writers' refusals -----------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [math.nan, math.inf, -math.inf, "a\ud800", {"\udfff": 1}, {"k": ["x\udc00"]}],
    ids=repr,
)
@pytest.mark.parametrize("serialization", ALL)
def test_values_every_writer_refuses(value: Any, serialization: str) -> None:
    with pytest.raises(ValueError):
        dumps(value, serialization=serialization)


WRITTEN_KEYS = {
    "1024 letters": "a" * 1024,
    "1021 letters and a space": "a" * 1021 + " ",
    "511 tabs": "\t" * 511,
    "511 characters above U+FFFF": "\U0001f600" * 511,
}
REFUSED_KEYS = {
    "1025 letters": "a" * 1025,
    "1022 letters and a space": "a" * 1022 + " ",
    "511 tabs and a letter": "\t" * 511 + "a",
    "511 characters above U+FFFF and a letter": "\U0001f600" * 511 + "a",
}


@pytest.mark.parametrize("key", WRITTEN_KEYS.values(), ids=WRITTEN_KEYS)
@pytest.mark.parametrize("serialization", ALL)
def test_a_key_of_1024_code_units_is_written(key: str, serialization: str) -> None:
    dumps({key: 1}, serialization=serialization)
    dumps({"outer": [{key: 1}]}, serialization=serialization)


@pytest.mark.parametrize("key", REFUSED_KEYS.values(), ids=REFUSED_KEYS)
@pytest.mark.parametrize("serialization", ALL)
def test_a_key_of_1025_code_units_is_refused(key: str, serialization: str) -> None:
    with pytest.raises(ValueError, match="1025 UTF-16 code units"):
        dumps({key: 1}, serialization=serialization)
    with pytest.raises(ValueError, match="1025 UTF-16 code units"):
        dumps({"outer": [{key: 1}]}, serialization=serialization)


@pytest.mark.parametrize(
    "value",
    [2**53, -(2**53), 2**64, 2.0**53, -1e16, 1e20, 1e21 - 2**17],
    ids=repr,
)
def test_rfc8785_refuses_numbers_beyond_a_double(value: int | float) -> None:
    with pytest.raises(ValueError, match="RFC 8785"):
        dumps({"n": value}, serialization="jcs")
    dumps({"n": value})
    dumps({"n": value}, serialization="json")


def test_rfc8785_writes_the_safe_integers() -> None:
    value = [2**53 - 1, -(2**53 - 1), float(2**53 - 1), 1e21]
    assert dumps(value, serialization="jcs") == (
        "[9007199254740991,-9007199254740991,9007199254740991,1e+21]"
    )


@pytest.mark.parametrize(
    "value",
    [(1, 2), {1, 2}, Fraction(1, 2), {1: "a"}, [object()]],
    ids=["tuple", "set", "Fraction", "integer key", "object"],
)
@pytest.mark.parametrize("serialization", ALL)
def test_a_value_that_is_not_json_is_a_type_error(
    value: Any, serialization: str
) -> None:
    with pytest.raises(TypeError):
        dumps(value, serialization=serialization)


def test_a_non_finite_number_is_refused_before_ordering() -> None:
    child = timeline("c", "seconds", 1.0, offset=math.nan)
    value = manifest(timeline("a", "seconds", 1.0, children=[child]))
    for serialization in ALL:
        with pytest.raises(ValueError, match="nan is not a finite number"):
            dumps(value, serialization=serialization)


def test_an_unknown_serialization_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown serialization 'toml'"):
        dumps({}, serialization="toml")  # type: ignore[arg-type]


# -- canonical order and respelling ---------------------------------------------------


def _order_refusals() -> dict[str, Any]:
    def region(start: Any) -> dict[str, Any]:
        return {"id": "r", "start": start, "end": [1, 1]}

    return {
        "entry not an object": {"timelines": [timeline("a"), "b"]},
        "child without offset": manifest(timeline("a", children=[timeline("c")])),
        "start a string": manifest(timeline("a", regions=[region("0")])),
        "id an integer": manifest(timeline("a"), {**timeline("b"), "id": 2}),
        "timestamp timeline an integer": manifest(
            timeline("a"),
            graphical={
                "timestamps": [{"id": "t", "timeline": 1, "coordinate": 0, "name": "x"}]
            },
        ),
        "member an integer": manifest(
            timeline("a"), groups=[{"id": "g", "members": [1]}]
        ),
        "denominator zero": manifest(timeline("a", regions=[region([1, 0])])),
        "three members": manifest(timeline("a", regions=[region([1, 2, 3])])),
        "coordinate true": manifest(timeline("a", regions=[region(True)])),
        "timelines not objects": {"timelines": ["b", "a"]},
    }


@pytest.mark.parametrize("value", _order_refusals().values(), ids=_order_refusals())
@pytest.mark.parametrize("serialization", ALL)
def test_a_manifest_out_of_canonical_order_is_refused(
    value: Any, serialization: str
) -> None:
    with pytest.raises(ValueError, match="cannot put .* in canonical order"):
        dumps(value, serialization=serialization)


def test_a_member_that_holds_no_array_is_written_as_given() -> None:
    value = manifest(
        timeline("a", children="x", regions=7, flow_control={}), groups="g"
    )
    assert canonical_order(value) == value


def test_entries_that_tie_keep_their_given_order() -> None:
    value = manifest(timeline("t", name="second"), timeline("t", name="first"))
    assert [root["name"] for root in canonical_order(value)["timelines"]] == [
        "second",
        "first",
    ]


def _respelled(root: dict[str, Any]) -> Any:
    return _kind(canonical_order(manifest(root))["timelines"][0])


def _axis_values(**members: Any) -> dict[str, Any]:
    return {
        "length": 2.0,
        "offset": 2,
        "regions": [{"id": "r", "start": [4, 8], "end": 3}],
        "flow_control": [
            {
                "id": "f",
                "type": "flow_marker",
                "manifestation": "fine",
                "coordinate": 1.0,
            }
        ],
        **members,
    }


@pytest.mark.parametrize(
    "axis",
    [
        {"unit": "furlongs"},
        {},
        {"unit": ["seconds"], "number_type": "float"},
        {"unit": "quarters", "number_type": "decimal"},
        {"unit": "ticks", "number_type": None},
        {"unit": "seconds", "number_type": 1},
    ],
    ids=[
        "unit unknown",
        "unit missing",
        "unit not a string",
        "type unknown",
        "type null",
        "type not a string",
    ],
)
def test_values_on_an_unknown_axis_are_written_as_given(axis: dict[str, Any]) -> None:
    root = {"id": "t", **axis, **_axis_values()}
    assert _respelled(root) == _kind(root)


def test_a_missing_number_type_is_the_units_default() -> None:
    root = {"id": "t", "unit": "ticks", **_axis_values(regions=[])}
    assert _respelled(root) == _kind(
        {
            **root,
            "length": 2,
            "flow_control": [{**root["flow_control"][0], "coordinate": 1}],
        }
    )


def test_a_child_under_an_unknown_axis_keeps_its_offset() -> None:
    child = timeline("c", length=[4, 8], offset=[4, 8])
    root = {"id": "t", "unit": "furlongs", "length": 2.0, "children": [child]}
    written = canonical_order(manifest(root))["timelines"][0]["children"][0]
    assert _kind(written) == _kind({**child, "length": [1, 2]})


def test_a_childs_offset_follows_its_parents_number_type() -> None:
    child = timeline("c", "ticks", 4.0, offset=2)
    root = timeline("t", "seconds", 10, children=[child])
    written = canonical_order(manifest(root))["timelines"][0]
    assert _kind(written["length"]) == _kind(10.0)
    assert _kind(written["children"][0]) == _kind({**child, "length": 4, "offset": 2.0})


@pytest.mark.parametrize(
    ("timelines", "name"),
    [
        ([timeline("t", "seconds", 4.0), timeline("t", "seconds", 4.0)], "t"),
        ([timeline("t", "seconds", 4.0)], "ghost"),
    ],
    ids=["named twice", "named nowhere"],
)
def test_a_timestamp_off_one_timeline_keeps_its_coordinate(
    timelines: list[dict[str, Any]], name: str
) -> None:
    stamp = {"id": "s", "timeline": name, "coordinate": 2, "name": "x"}
    value = manifest(*timelines, graphical={"timestamps": [stamp]})
    (written,) = canonical_order(value)["graphical"]["timestamps"]
    assert _kind(written["coordinate"]) == _kind(2)


# -- the JSON reader -----------------------------------------------------------------


def test_loads_keeps_integers_exact_and_floats_floats() -> None:
    half, two, big, minus_zero_integer, minus_zero, exponent = loads(
        "[0.5, 2.0, 123456789012345678, -0, -0.0, 1E5]"
    )
    assert (half, two, big, exponent) == (0.5, 2.0, 123456789012345678, 100000.0)
    assert [type(value) for value in (two, big, exponent)] == [float, int, float]
    assert type(minus_zero_integer) is int and minus_zero_integer == 0
    assert math.copysign(1.0, minus_zero) == -1.0
    assert loads(str(2**64)) == 2**64


@pytest.mark.parametrize(
    "text", ["[1,]", "{1: 2}", "[1] 2", '{"a": NaN}', "[-Infinity]", "1e400"]
)
def test_loads_refuses_a_json_text_that_is_no_json_value(text: str) -> None:
    with pytest.raises(ValueError):
        loads(text)


@pytest.mark.parametrize(
    ("text", "value"),
    [("", None), ("01", 1), ("nul", "nul"), ("NaN", "NaN"), ("-Infinity", "-Infinity")],
    ids=repr,
)
def test_a_text_that_is_no_json_text_is_read_as_yaml(text: str, value: Any) -> None:
    assert _kind(loads(text)) == _kind(value)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('{\n  "a": 1,\n  "a": 2\n}', 'the key "a" repeats at line 3, column 3'),
        ('[\n  "\\ud800"\n]', "a string holds a lone surrogate at line 2, column 3"),
        ('["x", "\ud800"]', "a string holds a lone surrogate at line 1, column 7"),
        ('{"\\udc00": 1}', "a string holds a lone surrogate at line 1, column 2"),
    ],
    ids=["duplicate key", "escaped surrogate", "surrogate as itself", "key"],
)
def test_loads_refuses_with_the_position(text: str, message: str) -> None:
    with pytest.raises(ValueError) as caught:
        loads(text)
    assert str(caught.value) == message


def test_loads_reads_a_surrogate_pair_as_one_character() -> None:
    assert loads('"\\ud83d\\ude00"') == "\U0001f600"


def test_loads_removes_one_byte_order_mark() -> None:
    assert loads('\ufeff{"a": 1}') == {"a": 1}


# -- the YAML reader -----------------------------------------------------------------


def test_yaml_is_read_under_the_core_schema() -> None:
    text = (
        "no: no\nyes: y\ndate: 2026-11-17\nfloat: 1e-05\nint: 2\nhex: 0x1F\n"
        "octal: 0o17\nzeros: 010\nnothing: ~\nempty:\nflag: True\nsexagesimal: 1:20\n"
        "underscore: 1_000\nbinary: 0b101\n"
    )
    assert _kind(loads(text)) == _kind(
        {
            "no": "no",
            "yes": "y",
            "date": "2026-11-17",
            "float": 1e-05,
            "int": 2,
            "hex": 31,
            "octal": 15,
            "zeros": 10,
            "nothing": None,
            "empty": None,
            "flag": True,
            "sexagesimal": "1:20",
            "underscore": "1_000",
            "binary": "0b101",
        }
    )


@pytest.mark.parametrize("text", ["", "# only a comment\n", "\n\n"], ids=repr)
def test_an_empty_yaml_text_reads_as_null(text: str) -> None:
    assert loads(text) is None


def test_yaml_keeps_integers_exact_and_reads_explicit_json_tags() -> None:
    assert loads(f"a: {2**70}\nb: !!str 1\nc: !!float 2\n") == {
        "a": 2**70,
        "b": "1",
        "c": 2.0,
    }
    assert type(loads("!!float 2\n")) is float


def test_yaml_reads_a_surrogate_pair_written_as_two_escapes() -> None:
    assert loads('a: "\\ud83d\\ude00"\n') == {"a": "\U0001f600"}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("a: 1\nb: 2\na: 3\n", 'the key "a" repeats at line 3, column 1'),
        ("a: &x 1\n", "an anchor is not read at line 1, column 4"),
        ("a: 1\nb: *x\n", "an alias is not read at line 2, column 4"),
        ("1: a\n", "a key that is not a string is not read at line 1, column 1"),
        ("? [a]\n: 1\n", "a key that is not a string is not read at line 1, column 3"),
        (
            "a: !!timestamp 2026-11-17\n",
            "the tag tag:yaml.org,2002:timestamp names no value of the JSON data "
            "model at line 1, column 4",
        ),
        (
            "a: !!binary aGk=\n",
            "the tag tag:yaml.org,2002:binary names no value of the JSON data "
            "model at line 1, column 4",
        ),
        (
            "a: !!set {x: null}\n",
            "the tag tag:yaml.org,2002:set names no value of the JSON data model "
            "at line 1, column 4",
        ),
        (
            "a: !!omap [{x: 1}]\n",
            "the tag tag:yaml.org,2002:omap names no value of the JSON data model "
            "at line 1, column 4",
        ),
        ("a: .inf\n", "'.inf' is not a finite float at line 1, column 4"),
        ("a: 1e309\n", "1e309 rounds to an infinity at line 1, column 4"),
        ('a: "\\ud800"\n', "a string holds a lone surrogate at line 1, column 4"),
        (
            "a\n---\nb\n",
            "expected a single document in the stream, but found another document "
            "at line 2, column 1",
        ),
    ],
    ids=[
        "duplicate key",
        "anchor",
        "alias",
        "integer key",
        "collection key",
        "timestamp",
        "binary",
        "set",
        "omap",
        "infinity",
        "overflow",
        "lone surrogate",
        "two documents",
    ],
)
def test_yaml_refusals_name_the_line_and_column(text: str, message: str) -> None:
    with pytest.raises(ValueError) as caught:
        loads(text)
    assert str(caught.value) == message


def test_yaml_nested_beyond_the_recursion_limit_is_refused_with_a_position() -> None:
    text = "- " * 2000 + "1"
    with pytest.raises(ValueError) as caught:
        loads(text)
    assert not isinstance(caught.value, RecursionError)
    prefix = "collections nest too deeply at line 1, column "
    message = str(caught.value)
    assert message.startswith(prefix)
    column = int(message.removeprefix(prefix))
    # The depth at which the limit is reached depends on the interpreter's
    # stack; the position is proven by the text: the start of a nested sequence.
    assert column % 2 == 1
    rest = text[column - 1 :]
    assert rest == "- " * ((len(rest) - 1) // 2) + "1"
    assert rest.startswith("- ")


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('"\U0001f600": &x 1\n', "an anchor is not read at line 1, column 6"),
        (
            '["\U0001f600", "\\ud800"]',
            "a string holds a lone surrogate at line 1, column 7",
        ),
    ],
    ids=["yaml", "json"],
)
def test_columns_count_code_points(text: str, message: str) -> None:
    with pytest.raises(ValueError) as caught:
        loads(text)
    assert str(caught.value) == message
