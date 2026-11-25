from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

import timetoshare
from timetoshare import (
    SERIALIZATIONS,
    FileForm,
    dumps,
    dumps_file,
    file_form,
    fixture_paths,
    loads,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPOSITORY_ROOT / "fixtures" / "0.2.0"
FILE_FORMS = REPOSITORY_ROOT / "fixtures" / "file_forms"

CASES = {
    "neither.yaml": FileForm(minimal=False, styling=True, serialization="yaml"),
    "one_line.json": FileForm(minimal=True, styling=False, serialization="json"),
    "crlf.yaml": FileForm(minimal=True, styling=True, serialization="yaml"),
    "jcs_minimal.json": FileForm(minimal=True, styling=False, serialization="jcs"),
    "jcs_float_default.json": FileForm(
        minimal=False, styling=False, serialization="jcs"
    ),
}
"""The form each text of ``fixtures/file_forms/`` is read as, as the test README
states it."""


def _text(path: Path) -> str:
    """The text of a file, its line ends kept."""
    return path.read_bytes().decode("utf-8")


def _expected(path: Path) -> Path:
    return path.with_name(f"{path.stem}.expected{path.suffix}")


def _written(path: Path) -> list[tuple[str, str, bool]]:
    """Every text of a fixture: its value, and its value without ``graphical``,
    in each serialization, with that serialization and whether it holds
    ``graphical``."""
    value = loads(_text(path))
    unstyled = {key: member for key, member in value.items() if key != "graphical"}
    values = [value, unstyled] if "graphical" in value else [value]
    return [
        (dumps(each, serialization=serialization), serialization, "graphical" in each)
        for each in values
        for serialization in SERIALIZATIONS
    ]


@pytest.mark.parametrize(
    "path", fixture_paths(), ids=lambda path: str(path.relative_to(FIXTURES))
)
def test_every_fixture_comes_back_byte_for_byte(path: Path) -> None:
    is_twin = path.name.endswith(".minimal.yaml")
    for text, serialization, styled in _written(path):
        form = file_form(text)
        assert form == FileForm(
            minimal=is_twin, styling=styled, serialization=serialization
        )
        assert dumps_file(loads(text), form) == text


def test_the_fixtures_cover_bundles_and_groups() -> None:
    folders = {path.parent.relative_to(FIXTURES).as_posix() for path in fixture_paths()}
    assert folders == {".", "bundles", "flow", "groups", "statements"}
    assert len(fixture_paths()) == 206


def test_the_case_table_names_every_text() -> None:
    texts = {
        path.name for path in FILE_FORMS.iterdir() if ".expected." not in path.name
    }
    expected = {path.name for path in FILE_FORMS.iterdir() if ".expected." in path.name}
    assert texts == set(CASES)
    assert expected == {_expected(FILE_FORMS / name).name for name in CASES}


@pytest.mark.parametrize("name", CASES)
def test_a_case_reads_as_its_form_and_comes_back_as_expected(name: str) -> None:
    path = FILE_FORMS / name
    text = _text(path)
    assert file_form(text) == CASES[name]
    assert dumps_file(loads(text), file_form(text)) == _text(_expected(path))


def test_the_cases_come_back_as_the_fixtures_they_derive_from() -> None:
    complete, twin = (
        _text(FIXTURES / "bare.yaml"),
        _text(FIXTURES / "bare.minimal.yaml"),
    )
    assert _text(FILE_FORMS / "neither.expected.yaml") == complete
    assert _text(FILE_FORMS / "crlf.expected.yaml") == twin
    assert _text(FILE_FORMS / "crlf.yaml") == twin.replace("\n", "\r\n")
    assert "\n" not in _text(FILE_FORMS / "one_line.json")


JCS_MINIMAL_AS_YAML = """\
timelines:
  -
    conversion_maps:
      -
        id: "#cmap_1"
        scalar: 0.5
        source_unit: seconds
        target_unit: samples
        type: LinearMap
    id: "#s"
    length: 8.0
    offset: 0.0
    regions:
      -
        end: 4.5
        id: "#region_1"
        start: 0.0
    unit: seconds
timetoshare: "0.2.0"
"""
"""``jcs_minimal.json`` in canonical YAML after its ``@context``, its own-axis floats
spelled as floats."""


def _context_block() -> str:
    """The canonical YAML of the format's ``@context``.

    Every fixture opens with it.
    """
    text = _text(FIXTURES / "bare.minimal.yaml")
    return text[: text.index("\ngraphical:") + 1]


def test_rfc8785_json_reads_integers_that_the_number_type_respells() -> None:
    value = loads(_text(FILE_FORMS / "jcs_minimal.json"))
    (root,) = value["timelines"]
    assert [type(root["length"]), type(root["offset"])] == [int, int]
    form = file_form(_text(FILE_FORMS / "jcs_minimal.json"))
    as_yaml = dataclasses.replace(form, serialization="yaml")
    expected = _context_block() + JCS_MINIMAL_AS_YAML
    assert dumps_file(value, as_yaml) == expected
    assert file_form(expected) == as_yaml


def test_dumps_file_leaves_its_value_unchanged() -> None:
    value = loads(_text(FILE_FORMS / "neither.yaml"))
    before = dumps([value], serialization="json")
    dumps_file(value, FileForm(minimal=True, styling=False, serialization="jcs"))
    dumps_file(value, FileForm(minimal=False, styling=True, serialization="yaml"))
    assert dumps([value], serialization="json") == before


def test_a_file_form_is_frozen_and_equal_by_its_fields() -> None:
    form = FileForm(minimal=True, styling=False, serialization="json")
    assert form == FileForm(minimal=True, styling=False, serialization="json")
    assert form != FileForm(minimal=True, styling=False, serialization="jcs")
    with pytest.raises(dataclasses.FrozenInstanceError):
        form.minimal = False  # type: ignore[misc]


def test_the_serializations_are_named_in_order() -> None:
    assert SERIALIZATIONS == ("yaml", "json", "jcs")


@pytest.mark.parametrize(
    "name", ["FileForm", "file_form", "dumps_file", "SERIALIZATIONS"]
)
def test_the_names_are_exported_from_the_root(name: str) -> None:
    assert name in timetoshare.__all__
