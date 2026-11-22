from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from fractions import Fraction
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

import timetoshare
from timetoshare import (
    SchemaValidationError,
    UnsupportedVersionError,
    dumps,
    json_pointer,
    loads,
    rejection_case,
    rejection_paths,
)

from .conftest import group, manifest, respellable, timeline, unknown_keys, validate

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SMALLEST = {
    "timetoshare": "0.2.0",
    "timelines": [{"id": "piece", "unit": "quarters", "length": [32, 1]}],
}

REJECTIONS = [
    "address_facet_with_part",
    "address_facet_without_id",
    "alignment_anchor_display_unknown",
    "alignment_anchor_id_repeated",
    "alignment_anchor_one_timeline",
    "alignment_anchor_timestamp_not_match",
    "alignment_anchor_timestamp_unknown",
    "band_order_missing_line",
    "band_order_old_form",
    "band_order_unknown_entry",
    "belief_actor_repeated",
    "belief_date_impossible",
    "belief_value_boolean",
    "belief_value_unknown",
    "child_end_beyond_parent",
    "child_id_control_character_newline",
    "child_missing_offset",
    "child_offset_beyond_parent",
    "child_offset_fraction_on_float_axis",
    "child_unit_differs",
    "combination_map_member_not_object",
    "context_absent_with_provenance",
    "context_absent_with_statements",
    "context_prefix_not_namespace",
    "context_prefix_reserved_name",
    "context_term_altered",
    "context_term_missing",
    "conversion_map_not_object",
    "conversion_map_null",
    "conversion_map_unknown_type",
    "dal_segno_without_target",
    "element_value_dangling",
    "element_value_with_label",
    "elision_depths_comma",
    "elision_depths_zero",
    "elision_display_none_with_word",
    "elision_display_strip",
    "elision_display_unknown",
    "elision_end_beyond_length",
    "elision_id_is_timeline_id",
    "elision_mode_unknown",
    "elision_name_empty",
    "elision_proportion_word",
    "elision_proportion_zero",
    "elision_ratio_zero",
    "elision_start_not_before_end",
    "elision_timeline_unknown",
    "elision_width_two_forms",
    "float_axis_int_not_exact",
    "flow_control_coordinate_dict",
    "flow_control_object",
    "flow_control_type_break",
    "flow_marker_manifestation_segno",
    "group_id_duplicate",
    "group_id_is_descendant_id",
    "group_id_is_timeline_id",
    "group_members_repeated",
    "group_missing_id",
    "group_missing_members",
    "group_order_not_member",
    "group_order_repeated",
    "groupstamp_child_without_group",
    "groupstamp_match_without_group",
    "groupstamp_member_parent",
    "groupstamp_without_group",
    "id_control_character_tab",
    "id_control_character_trailing_newline",
    "id_duplicate_across_kinds",
    "id_empty",
    "id_without_hash",
    "id_without_hash_short",
    "infinite_length",
    "iri_prefix_undeclared_id",
    "iri_prefix_undeclared_key",
    "iri_prefix_undeclared_type",
    "jump_target_flow_marker",
    "jump_to_target",
    "later_root_missing_unit",
    "length_coordinate_dict",
    "length_float_on_int_axis",
    "length_fraction_member_not_integral",
    "length_fraction_on_int_axis",
    "length_int_on_fraction_axis",
    "length_negative",
    "length_string_fraction",
    "length_three_element_fraction",
    "length_zero_denominator",
    "manifest_id_is_descendant_id",
    "manifest_id_is_group_id",
    "manifest_id_is_measure_map_id",
    "map_source_unit_mismatch",
    "match_timestamp_coordinate_repeated",
    "match_timestamp_in_no_matchstamp",
    "matchstamp_claims_repeated",
    "matchstamp_not_connected",
    "measure_map_id_is_timeline_id",
    "measure_map_row_actual_length_negative",
    "measure_map_row_offset_within_measure_zero",
    "measure_map_row_qstamp_negative",
    "measure_map_row_qstamp_string",
    "measure_map_row_without_count_or_id",
    "measure_map_rows_empty",
    "measure_map_rows_not_array",
    "measure_view_dangling",
    "measure_view_source_unit_ticks",
    "member_dangling",
    "members_contain_member",
    "members_inside_member",
    "nan_offset",
    "nested_map_id_duplicate",
    "order_missing_member",
    "order_not_array",
    "order_unknown_group",
    "ordered_values_null",
    "piecewise_map_breaks_not_increasing",
    "piecewise_map_maps_count",
    "provenance_basis_prefix_undeclared",
    "provenance_date_impossible",
    "provenance_date_not_written_so",
    "provenance_empty",
    "provenance_match_unknown",
    "provenance_method_unknown",
    "provenance_property_bare_word",
    "provenance_repeated",
    "reference_without_hash",
    "region_id_duplicate_across_roots",
    "region_id_is_timeline_id",
    "region_start_float_on_fraction_axis",
    "repeat_count_zero",
    "reserved_key_children_on_region",
    "reserved_key_context_on_timeline",
    "reserved_key_iri_on_region",
    "reserved_key_prefix_on_manifest",
    "reserved_key_statements_on_group",
    "reserved_key_term_on_timeline",
    "resource_integrity_algorithm_unknown",
    "resource_match_claim_twice",
    "resource_projection_twice",
    "resource_timeline_unknown",
    "root_missing_marker",
    "root_missing_timelines",
    "rule_select_coordinates_unknown",
    "rule_select_empty_addresses",
    "rule_select_inside_unknown_element",
    "rule_select_projection",
    "rule_select_unknown_element",
    "rule_set_content_not_string",
    "rule_set_dasharray_malformed",
    "rule_set_max_width_zero",
    "rule_set_neither_object_nor_string",
    "rule_set_opacity_above_one",
    "rule_set_shadow_lower_case",
    "rule_set_stroke_lower_case",
    "segment_line_flag_not_boolean",
    "segment_line_gap",
    "segment_line_gap_in_later_root",
    "segment_line_not_from_zero",
    "segment_line_segment_flag",
    "segment_line_short_of_length",
    "statement_key_bare_word",
    "statement_key_keyword",
    "statement_value_float",
    "statement_value_integral_float",
    "statement_value_null",
    "statement_values_empty",
    "statement_values_repeated",
    "statements_empty",
    "subject_id_not_fragment",
    "table_map_kind_nearest",
    "table_map_lengths_differ",
    "table_map_missing_x_values",
    "table_map_x_not_increasing",
    "timeline_missing_length",
    "timeline_name_not_string",
    "timeline_number_type_unknown",
    "timeline_quarters_int",
    "timeline_seconds_int",
    "timeline_ticks_float",
    "timeline_unit_unknown",
    "timelines_child_id_duplicate_across_roots",
    "timelines_id_duplicate_across_roots",
    "timelines_root_jump_target_dangling",
    "timestamp_coordinate_beyond_length",
    "timestamp_coordinate_negative",
    "timestamp_display_repeated",
    "timestamp_display_unknown",
    "timestamp_id_is_timeline_id",
    "timestamp_timeline_unknown",
    "to_coda_with_repeat_count",
    "type_bare_word",
    "value_node_blank_node_id",
    "value_node_empty",
    "value_object_language_and_type",
    "version_unknown",
]


def _problem(value: Any) -> tuple[tuple[str | int, ...], str]:
    with pytest.raises(SchemaValidationError) as caught:
        validate(value)
    return caught.value.path, caught.value.message


# -- the units --------------------------------------------------------------------


def _accepted(value: dict) -> bool:
    try:
        validate(value)
    except SchemaValidationError:
        return False
    return True


@pytest.mark.parametrize("unit", ["css_pixels", "user_units"])
@pytest.mark.parametrize(
    ("number_type", "length", "accepted"),
    [("float", 600.5, True), ("fraction", [1201, 2], True), ("int", 600, False)],
)
def test_a_vector_graphics_unit_is_read_as_points_is(
    unit: str, number_type: str, length: Any, accepted: bool
) -> None:
    points = manifest(timeline("page", "points", length, number_type=number_type))
    root = manifest(timeline("page", unit, length, number_type=number_type))
    assert _accepted(points) is accepted
    assert _accepted(root) is accepted


_TWO = {"int": 2, "float": 2.0, "fraction": [2, 1]}
"""The value 2 as each number type spells it."""

_ZERO = {"int": 0, "float": 0.0, "fraction": [0, 1]}
"""The value 0 as each number type spells it."""

_ADMITTED = {
    "number": {"int", "float", "fraction"},
    **{unit: {"int"} for unit in ("ticks", "samples", "frames", "pixels")},
}
"""The number types a unit admits where it admits other than float and fraction."""


@pytest.mark.parametrize("number_type", ["int", "float", "fraction"])
@pytest.mark.parametrize("unit", list(timetoshare.UNITS))
def test_a_unit_admits_its_number_types(unit: str, number_type: str) -> None:
    admitted = number_type in _ADMITTED.get(unit, {"float", "fraction"})
    value = manifest(timeline("axis", unit, _TWO[number_type], number_type=number_type))
    if admitted:
        validate(value)
    else:
        with pytest.raises(SchemaValidationError) as caught:
            validate(value)
        assert (caught.value.code, caught.value.path) == (
            "schema",
            ("timelines", 0, "number_type"),
        )


@pytest.mark.parametrize("number_type", ["int", "float", "fraction"])
@pytest.mark.parametrize("unit", list(timetoshare.UNITS))
def test_a_child_admits_the_number_types_of_its_unit(
    unit: str, number_type: str
) -> None:
    admitted = number_type in _ADMITTED.get(unit, {"float", "fraction"})
    default = timetoshare.UNITS[unit].number_type
    child = timeline("axis", unit, _TWO[number_type], number_type=number_type)
    value = manifest(
        timeline(
            "parent",
            unit,
            _TWO[default],
            children=[{**child, "offset": _ZERO[default]}],
        )
    )
    if admitted:
        validate(value)
    else:
        with pytest.raises(SchemaValidationError) as caught:
            validate(value)
        assert (caught.value.code, caught.value.path) == (
            "schema",
            ("timelines", 0, "children", 0, "number_type"),
        )


@pytest.mark.parametrize("unit", ["px", "uu"])
def test_an_abbreviation_is_no_unit(unit: str) -> None:
    with pytest.raises(SchemaValidationError) as caught:
        validate(manifest(timeline("page", unit, 600.5)))
    assert caught.value.path == ("timelines", 0, "unit")
    assert caught.value.code == "schema"


# -- the version marker -----------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        {"timelines": []},
        {"meta": {"schema_version": "0.2.0"}, "timelines": []},
        [],
        "0.2.0",
    ],
    ids=["no marker", "version in meta", "list", "string"],
)
def test_a_value_without_the_marker_is_no_manifest(value: Any) -> None:
    assert _problem(value) == ((), "not a TimeToShare manifest")


@pytest.mark.parametrize("version", ["9.9.9", "0.1.0", "0.1", 1])
def test_another_version_is_unsupported(version: Any) -> None:
    with pytest.raises(UnsupportedVersionError) as caught:
        validate({"timetoshare": version})
    assert caught.value.version == version


def test_the_unsupported_version_message() -> None:
    with pytest.raises(UnsupportedVersionError) as caught:
        validate({"timetoshare": "9.9.9", "timelines": []})
    assert str(caught.value) == (
        'unsupported TimeToShare version "9.9.9"; this package reads 0.2.0 only'
    )


def test_the_smallest_and_the_empty_manifest_validate() -> None:
    validate(SMALLEST)
    validate({"timetoshare": "0.2.0", "timelines": []})


# -- representation ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("root", "message"),
    [
        (
            timeline("score", length=32),
            "length 32 of 'score' is an int on a fraction axis: write [32, 1]",
        ),
        (
            timeline("score", length=0.5),
            "length 0.5 of 'score' is a float on a fraction axis: write [1, 2]",
        ),
        (
            timeline("score", length=0.1),
            "length 0.1 of 'score' is a float on a fraction axis: write "
            "[3602879701896397, 36028797018963968]",
        ),
        (
            timeline("take", "seconds", (3, 4)),
            "length [3, 4] of 'take' is a fraction on a float axis: write 0.75",
        ),
        (
            timeline("take", "seconds", (1, 3)),
            "length [1, 3] of 'take' is a fraction on a float axis: write a float",
        ),
        (
            timeline("midi", "ticks", (480, 1)),
            "length [480, 1] of 'midi' is a fraction on an int axis: write 480",
        ),
        (
            timeline("midi", "ticks", 0.5),
            "length 0.5 of 'midi' is a float on an int axis: write an int",
        ),
        (
            timeline("midi", "ticks", (1, 2)),
            "length [1, 2] of 'midi' is a fraction on an int axis: write an int",
        ),
        (
            timeline("take", "seconds", 9007199254740993),
            "length 9007199254740993 of 'take' is an int on a float axis: "
            "write a float",
        ),
        (
            timeline("take", "seconds", 2.0, number_type="fraction"),
            "length 2.0 of 'take' is a float on a fraction axis: write [2, 1]",
        ),
        (
            timeline("score", length=(2, 1), number_type="float"),
            "length [2, 1] of 'score' is a fraction on a float axis: write 2.0",
        ),
        (
            timeline("score", offset=3),
            "offset 3 of 'score' is an int on a fraction axis: write [3, 1]",
        ),
    ],
)
def test_a_length_or_offset_in_another_representation(root: dict, message: str) -> None:
    key = message.split(" ", 1)[0]
    assert _problem(manifest(root)) == (("timelines", 0, key), message)


@pytest.mark.parametrize(
    ("root", "coordinate", "message"),
    [
        (
            timeline("score"),
            3,
            "coordinate 3 of 'timestamp_1' is an int on a fraction axis: write [3, 1]",
        ),
        (
            timeline("take", "seconds", 60.0),
            [1, 2],
            "coordinate [1, 2] of 'timestamp_1' is a fraction on a float axis: "
            "write 0.5",
        ),
        (
            timeline("midi", "ticks", 480),
            0.5,
            "coordinate 0.5 of 'timestamp_1' is a float on an int axis: write an int",
        ),
    ],
)
def test_a_named_timestamp_coordinate_lies_on_its_timelines_axis(
    root: dict, coordinate: Any, message: str
) -> None:
    stamp = {"id": "timestamp_1", "timeline": root["id"], "coordinate": coordinate}
    value = manifest(root, graphical={"timestamps": [{**stamp, "name": "Entry"}]})
    assert _problem(value) == (("graphical", "timestamps", 0, "coordinate"), message)


def test_a_named_timestamp_coordinate_on_a_child_is_read_on_the_childs_axis() -> None:
    child = timeline("verse", "seconds", 4.0, offset=1.0)
    root = timeline("take", "seconds", 60.0, children=[child])
    stamp = {"id": "timestamp_1", "timeline": "verse", "coordinate": 2, "name": "x"}
    validate(manifest(root, graphical={"timestamps": [stamp]}))
    stamp["coordinate"] = [2, 1]
    assert _problem(manifest(root, graphical={"timestamps": [stamp]})) == (
        ("graphical", "timestamps", 0, "coordinate"),
        "coordinate [2, 1] of 'timestamp_1' is a fraction on a float axis: write 2.0",
    )


@pytest.mark.parametrize("child_unit", ["seconds", "quarters"])
def test_a_child_offset_lies_on_its_parents_axis(child_unit: str) -> None:
    child = timeline("take", child_unit, 4.0 if child_unit == "seconds" else (4, 1))
    child["offset"] = [1, 2]
    value = manifest(timeline("recording", "seconds", 60.0, children=[child]))
    assert _problem(value) == (
        ("timelines", 0, "children", 0, "offset"),
        "offset [1, 2] of 'take' is a fraction on a float axis: write 0.5",
    )


@pytest.mark.parametrize(
    ("member", "entry", "key"),
    [
        ("regions", {"id": "intro", "start": 1, "end": [2, 1]}, "start"),
        ("regions", {"id": "intro", "start": [1, 1], "end": 2}, "end"),
        (
            "flow_control",
            {
                "id": "fine",
                "type": "flow_marker",
                "manifestation": "fine",
                "coordinate": 4,
            },
            "coordinate",
        ),
        (
            "flow_control",
            {
                "id": "segno",
                "type": "jump_to",
                "manifestation": "segno",
                "coordinate": 4,
            },
            "coordinate",
        ),
        (
            "flow_control",
            {
                "id": "back",
                "type": "jump_from",
                "manifestation": "da_capo",
                "coordinate": 4,
            },
            "coordinate",
        ),
    ],
)
def test_every_own_axis_value_is_checked(member: str, entry: dict, key: str) -> None:
    root = timeline("score")
    root[member] = [entry]
    path = ("timelines", 0, member, 0, key)
    value = entry[key]
    assert _problem(manifest(root)) == (
        path,
        f"{key} {value} of '{entry['id']}' is an int on a fraction axis: "
        f"write [{value}, 1]",
    )


@pytest.mark.parametrize(
    "root",
    [
        timeline("midi", "ticks", 8),
        timeline("midi", "ticks", 8.0),
        timeline("take", "seconds", 8),
        timeline("take", "seconds", 0.5),
        timeline("take", "seconds", 9007199254740992),
        timeline("take", "seconds", 10**20),
        timeline("score", length=(8, 1)),
        timeline("score", length=None),
        timeline("take", "seconds", 2.5, offset=-1700000000.25),
        timeline("score", offset=[-3, 2]),
    ],
)
def test_values_in_their_axis_representation_validate(root: dict) -> None:
    validate(manifest(root))


def test_the_first_representation_problem_is_raised() -> None:
    root = timeline("score", length=8, regions=[{"id": "r", "start": 0, "end": [1, 1]}])
    assert _problem(manifest(root))[0] == ("timelines", 0, "length")


ACCEPTANCES = REPOSITORY_ROOT / "fixtures" / "acceptances" / "0.2.0" / "numbers.yaml"

ACCEPTANCE_ROWS = [
    ("fraction", "[2, 4]"),
    ("fraction", "[1, 8.0]"),
    ("fraction", "[4, 8.0]"),
    ("fraction", "[-3, 6]"),
    ("int", "480"),
    ("int", "480.0"),
    ("float", "2"),
    ("float", "0.1"),
    ("int", "[480, 1]"),
    ("int", "2.5"),
    ("fraction", "12"),
    ("fraction", "12.0"),
    ("float", "[25, 2]"),
    ("float", "9007199254740993"),
]
"""The number type and the value, as JSON spells it, of every row in order."""

_AXIS_UNITS = {"int": "ticks", "float": "seconds", "fraction": "quarters"}
"""A unit taking each number type, the axis of the acceptance rows."""


def _acceptance_rows() -> list[dict[str, Any]]:
    return loads(ACCEPTANCES.read_text(encoding="utf-8"))


def _exact(value: Any) -> Fraction:
    """The exact value a bare Number states; a member ``8.0`` is the integer 8."""
    if isinstance(value, list):
        return Fraction(int(value[0]), int(value[1]))
    return Fraction(value)


def test_the_acceptance_rows_are_stated() -> None:
    rows = _acceptance_rows()
    assert [(row["number_type"], json.dumps(row["value"])) for row in rows] == (
        ACCEPTANCE_ROWS
    )
    assert dumps(rows) == ACCEPTANCES.read_text(encoding="utf-8")


@pytest.mark.parametrize("index", range(len(ACCEPTANCE_ROWS)))
def test_an_acceptance_row_is_read_as_stated(index: int) -> None:
    row = _acceptance_rows()[index]
    number_type = row["number_type"]
    value = manifest(
        timeline(
            "axis",
            _AXIS_UNITS[number_type],
            None,
            number_type=number_type,
            offset=row["value"],
        )
    )
    if "refused" in row:
        assert sorted(row) == ["number_type", "refused", "value"]
        with pytest.raises(SchemaValidationError) as caught:
            validate(value)
        assert (caught.value.code, caught.value.path) == (
            row["refused"],
            ("timelines", 0, "offset"),
        )
        return
    assert sorted(row) == ["number_type", "read", "value"]
    validate(value)
    assert _exact(row["value"]) == _exact(row["read"])
    written = timetoshare.canonical_order(value)["timelines"][0]["offset"]
    assert dumps(written) == dumps(row["read"])


def test_values_are_read_by_their_number_type() -> None:
    value = respellable()
    written = dumps([value], serialization="json")
    validate(value)
    assert unknown_keys(value) == []
    assert dumps([value], serialization="json") == written


# -- unknown length ---------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        manifest(timeline("score", length=None)),
        manifest(timeline("score", length=None, locked=True)),
        manifest(
            timeline("score", children=[timeline("c", length=None, offset=(2, 1))])
        ),
        manifest(
            timeline("score", length=None, children=[timeline("c", offset=(2, 1))])
        ),
        manifest(
            timeline("score"),
            timeline("perf", "seconds", None),
            groups=[{"id": "g", "members": ["perf", "score"]}],
        ),
    ],
    ids=["root", "locked", "child", "known child of unknown parent", "group member"],
)
def test_an_unknown_length_is_no_violation(value: dict) -> None:
    validate(value)


# -- shared rejections -------------------------------------------------------------


def test_the_rejection_cases_are_stated() -> None:
    assert [path.stem for path in rejection_paths()] == REJECTIONS


@pytest.mark.parametrize("path", rejection_paths(), ids=lambda path: path.stem)
def test_shared_rejection_is_rejected_at_its_path(path: Path) -> None:
    case = rejection_case(path)
    message = loads(path.read_text(encoding="utf-8"))["message"]
    if case.error == "UnsupportedVersionError":
        assert case.path == ("timetoshare",)
        assert case.code is None
        with pytest.raises(UnsupportedVersionError) as unsupported:
            timetoshare.validate(case.manifest)
        assert str(unsupported.value) == message
        return
    assert case.error is None
    with pytest.raises(SchemaValidationError) as caught:
        timetoshare.validate(case.manifest)
    assert caught.value.path == case.path
    assert caught.value.code == case.code
    assert caught.value.message == message


# -- several problems: the one path rule ------------------------------------------

PRECEDENCE = REPOSITORY_ROOT / "fixtures" / "precedence" / "0.2.0" / "cases.yaml"


def _precedence_cases() -> list[dict[str, Any]]:
    return loads(PRECEDENCE.read_text(encoding="utf-8"))


def _with_edits(case: dict[str, Any]) -> Any:
    fixture = REPOSITORY_ROOT / "fixtures" / "0.2.0" / f"{case['fixture']}.yaml"
    value = loads(fixture.read_text(encoding="utf-8"))
    for edit in case["set"]:
        owner = value
        for step in edit["path"][:-1]:
            owner = owner[step]
        owner[edit["path"][-1]] = edit["value"]
    return value


def _reported(value: Any) -> tuple[str, list[str | int], str]:
    with pytest.raises(SchemaValidationError) as caught:
        timetoshare.validate(value)
    return caught.value.code, list(caught.value.path), caught.value.message


def test_the_cases_of_several_problems_are_stated() -> None:
    assert PRECEDENCE.read_text(encoding="utf-8") == dumps(_precedence_cases())
    assert [case["name"] for case in _precedence_cases()] == [
        "declarations_by_key",
        "prefixes_by_key",
        "deeper_root_wins",
        "timeline_members_by_key",
        "conversion_maps_by_index",
        "number_type_first_applied",
    ]


@pytest.mark.parametrize("case", _precedence_cases(), ids=lambda case: case["name"])
def test_several_problems_report_the_one_the_path_rule_selects(case: dict) -> None:
    assert _reported(_with_edits(case)) == (case["code"], case["path"], case["message"])


_SEEDED = """
import json, sys
from pathlib import Path
from timetoshare import SchemaValidationError, loads, validate

cases = loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
root = Path(sys.argv[2])
reported = []
for case in cases:
    value = loads((root / f"{case['fixture']}.yaml").read_text(encoding="utf-8"))
    for edit in case["set"]:
        owner = value
        for step in edit["path"][:-1]:
            owner = owner[step]
        owner[edit["path"][-1]] = edit["value"]
    try:
        validate(value)
    except SchemaValidationError as error:
        reported.append(list(error.path))
print(json.dumps(reported))
"""


def test_the_path_rule_does_not_depend_on_the_hash_seed() -> None:
    expected = [case["path"] for case in _precedence_cases()]
    fixtures = REPOSITORY_ROOT / "fixtures" / "0.2.0"
    for seed in ("1", "2", "3"):
        environment = {**os.environ, "PYTHONHASHSEED": seed}
        run = subprocess.run(
            [sys.executable, "-c", _SEEDED, str(PRECEDENCE), str(fixtures)],
            capture_output=True,
            check=True,
            env=environment,
            text=True,
        )
        assert json.loads(run.stdout) == expected, seed


def _rejection(name: str) -> Path:
    (path,) = [path for path in rejection_paths() if path.stem == name]
    return path


def test_the_rejection_reader_puts_the_non_finite_value_at_its_path() -> None:
    nan = rejection_case(_rejection("nan_offset"))
    assert nan.path == ("timelines", 0, "children", 0, "offset")
    assert math.isnan(nan.manifest["timelines"][0]["children"][0]["offset"])
    infinite = rejection_case(_rejection("infinite_length"))
    assert infinite.path == ("timelines", 0, "length")
    assert infinite.manifest["timelines"][0]["length"] == math.inf
    assert infinite.code == "finite_number"
    assert infinite.error is None
    for case, message in [
        (nan, "offset of 'take' is not a finite number"),
        (infinite, "length of 'recording' is not a finite number"),
    ]:
        with pytest.raises(SchemaValidationError) as caught:
            timetoshare.validate(case.manifest)
        assert (caught.value.path, caught.value.message) == (case.path, message)


def test_the_rejection_reader_keeps_any_other_case_as_written() -> None:
    path = _rejection("id_empty")
    stored = loads(path.read_text(encoding="utf-8"))
    case = rejection_case(path)
    assert case.manifest == stored["manifest"]
    assert case.path == tuple(stored["path"])
    assert (case.code, case.error, case.reason) == (
        "schema",
        None,
        "An id must not be empty.",
    )


def test_the_rejection_reader_refuses_an_unknown_non_finite_name(
    tmp_path: Path,
) -> None:
    path = tmp_path / "huge.yaml"
    path.write_text(
        dumps(
            {
                "code": "finite_number",
                "manifest": {"timetoshare": "0.2.0", "timelines": []},
                "non_finite": "Huge",
                "path": ["timelines"],
                "reason": "x",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="'Huge' names no non-finite number"):
        rejection_case(path)


def test_rejections_cover_every_rule_code() -> None:
    codes = {rejection_case(path).code for path in rejection_paths()}
    assert codes - {None} == {
        "band_order",
        "calendar_date",
        "child_end",
        "child_offset",
        "child_unit",
        "context",
        "conversion_map",
        "dangling_target",
        "display_order",
        "duplicate_id",
        "element_value",
        "elision_stretch",
        "elision_timeline",
        "finite_number",
        "group_member",
        "iri",
        "manifest_id",
        "not_a_manifest",
        "order_key",
        "provenance_duplicate",
        "representation",
        "reserved_key",
        "schema",
        "segment_line",
        "timestamp_coordinate",
        "timestamp_timeline",
        "groupstamp",
        "match_timestamp",
        "alignment_anchor",
        "matchstamp",
        "resource_timeline",
        "resource_type",
        "belief_actor",
    }


# -- the finite-number rule ---------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "path", "detail"),
    [
        (
            manifest(timeline("take", "seconds", math.inf)),
            ("timelines", 0, "length"),
            "length of 'take' is not a finite number",
        ),
        (
            manifest(
                timeline(
                    "score",
                    "quarters",
                    [8, 1],
                    regions=[{"id": "r", "start": [0, 1], "end": [math.nan, 1]}],
                )
            ),
            ("timelines", 0, "regions", 0, "end", 0),
            "end of 'r' is not a finite number",
        ),
        (
            manifest(
                timeline("take"), graphical={"styles": {"s": {"opacity": -math.inf}}}
            ),
            ("graphical", "styles", "s", "opacity"),
            "#/graphical/styles/s/opacity is not a finite number",
        ),
    ],
)
def test_a_non_finite_number_is_refused_before_any_other_rule(
    value: dict, path: tuple, detail: str
) -> None:
    # A repeated root breaks the identity rules too; the finite rule runs first.
    value["timelines"].append(value["timelines"][0])
    with pytest.raises(SchemaValidationError) as caught:
        validate(value)
    assert (caught.value.code, caught.value.path, caught.value.message) == (
        "finite_number",
        path,
        detail,
    )


# -- errors and paths ---------------------------------------------------------------


def test_error_renders_as_json_pointer() -> None:
    with pytest.raises(SchemaValidationError) as caught:
        validate(manifest(timeline("score", unit="beats")))
    assert caught.value.path == ("timelines", 0, "unit")
    assert str(caught.value).startswith("#/timelines/0/unit: ")


def test_json_pointer_rendering() -> None:
    assert json_pointer(()) == "#"
    assert json_pointer(("a/b", "c~d", 0)) == "#/a~1b/c~0d/0"


@pytest.mark.parametrize("value", [9007199254740993, 9223372036854775807])
def test_integer_boundaries_validate_and_preserve(value: int) -> None:
    document = manifest(timeline("midi", "ticks", value))
    validate(document)
    assert loads(dumps(document))["timelines"][0]["length"] == value


def _styled(declaration: dict) -> dict:
    return manifest(
        timeline("score"),
        graphical={"rules": [{"select": {"element": "timeline"}, "set": declaration}]},
    )


@pytest.mark.parametrize(
    "declaration",
    [
        {"stroke-width": 0, "rx": 0},
        {"opacity": 0},
        {"opacity": 1},
        {"font-size": 0.5, "max-width": 1},
        {"max-width": "none", "content": "Score"},
        {"stroke-dasharray": "none"},
        {"stroke-dasharray": "4 2.5"},
        {"rotation": -45},
        {"rotation": 180},
        {"rotation": -180},
        {"rotation": 45.0},
    ],
)
def test_graphical_property_bounds_accept_exact_valid_values(declaration: dict) -> None:
    validate(_styled(declaration))


@pytest.mark.parametrize(
    ("declaration", "member"),
    [
        ({"stroke-width": -1}, "stroke-width"),
        ({"rx": -0.5}, "rx"),
        ({"opacity": -0.1}, "opacity"),
        ({"opacity": 1.1}, "opacity"),
        ({"font-size": 0}, "font-size"),
        ({"max-width": 0}, "max-width"),
        ({"content": 5}, "content"),
        ({"stroke-dasharray": "4,2"}, "stroke-dasharray"),
        ({"rotation": 181}, "rotation"),
        ({"rotation": -180.5}, "rotation"),
        ({"rotation": "45"}, "rotation"),
    ],
)
def test_graphical_property_bounds_reject_at_the_property(
    declaration: dict, member: str
) -> None:
    path = _problem(_styled(declaration))[0]
    assert path == ("graphical", "rules", 0, "set", member)


@pytest.mark.parametrize(
    "rule",
    [
        {"select": {"element": "card"}, "set": {"rx": 5}},
        {"select": {"inside": "ancestor"}, "set": {"opacity": 0.35}},
        {"select": {"element": "card"}, "set": {"shadow": "#B8BEC8"}},
        {"select": {"element": "frame"}, "set": {"stroke": "#7F00FF"}},
        {"select": {"element": "ancestor_card"}, "set": {"display": "none"}},
        {
            "select": {
                "element": "ancestor_card",
                "addresses": [{"id": "score", "part": ["card"]}],
            },
            "set": {"display": "none"},
        },
    ],
)
def test_card_frame_inside_and_shadow_validate(rule: dict) -> None:
    validate(manifest(timeline("score"), graphical={"rules": [rule]}))


@pytest.mark.parametrize(
    "select",
    [
        {"element": "band"},
        {"element": "band", "facet": "markers"},
        {"element": "band", "facet": "conversion_maps"},
        {"element": "band", "facet": "children"},
        {"element": "band", "facet": "regions"},
        {"element": "band", "facet": "flow_control"},
        {"addresses": [{"id": "score", "facet": "regions"}]},
        {"inside": "band"},
    ],
)
def test_band_selectors_validate(select: dict) -> None:
    rule = {"select": select, "set": {"display": "none"}}
    validate(manifest(timeline("score"), graphical={"rules": [rule]}))


@pytest.mark.parametrize(
    "select",
    [{"coordinates": "primary"}, {"element": "wedge", "coordinates": "secondary"}],
)
def test_a_selector_chooses_a_stamps_primary_or_secondary_coordinates(
    select: dict,
) -> None:
    rule = {"select": select, "set": {"display": "none"}}
    value = manifest(timeline("score"), graphical={"rules": [rule]})
    validate(value)
    assert unknown_keys(value) == []


def test_a_selector_names_every_card_of_a_timeline_in_several_groups() -> None:
    card = {"id": "t", "part": ["card"]}
    rule = {"select": {"addresses": [card]}, "set": {"stroke": "#B8BEC8"}}
    validate(
        manifest(
            timeline("t"),
            timeline("u"),
            timeline("v"),
            groups=[group("g1", "t", "u"), group("g2", "t", "v")],
            graphical={"rules": [rule]},
        )
    )


def test_the_schema_shapes_each_order_entry() -> None:
    value = manifest(timeline("score"), graphical={"order": {"score": [""]}})
    assert _problem(value)[0] == ("graphical", "order", "#score", 0)


def test_the_schema_refuses_a_repeated_order_entry() -> None:
    order = ["line", "markers", "line"]
    value = manifest(timeline("score"), graphical={"order": {"score": order}})
    assert _problem(value)[0] == ("graphical", "order", "#score")


def test_a_da_capo_and_a_repeat_end_need_no_target() -> None:
    def origin(identifier: str, manifestation: str) -> dict:
        return {
            "id": identifier,
            "type": "jump_from",
            "manifestation": manifestation,
            "coordinate": [8, 1],
        }

    flow = [
        origin("dc", "da_capo"),
        origin("dcf", "da_capo_al_fine"),
        origin("dcc", "da_capo_al_coda"),
        {**origin("again", "repeat_end"), "repeat_count": 2},
    ]
    value = manifest(timeline("score", flow_control=flow))
    validate(value)
    assert unknown_keys(value) == []
    missing = manifest(timeline("score", flow_control=[origin("ds", "dal_segno")]))
    assert _problem(missing)[0] == ("timelines", 0, "flow_control", 0)


def _refuses_patterns(refused: Any) -> bool:
    """Whether a ``not`` refuses patterns or words, alone or as an ``anyOf``."""
    if not isinstance(refused, dict) or refused == {}:
        return False
    return all(
        isinstance(branch, dict) and branch.keys() in ({"pattern"}, {"enum"})
        for branch in refused.get("anyOf", [refused])
    )


def _worded_places(node: Any, pointer: str) -> list[str]:
    """The places of a schema the package words itself, as JSON pointers."""
    places: list[str] = []
    if isinstance(node, dict):
        for keyword in ("oneOf", "anyOf"):
            branches = node.get(keyword)
            if isinstance(branches, list) and all(
                isinstance(branch, dict) and "const" in branch for branch in branches
            ):
                places.append(f"{pointer}/{keyword}")
        if node.get("not") in ({}, True) or _refuses_patterns(node.get("not")):
            places.append(f"{pointer}/not")
        for key, child in node.items():
            if key in ("properties", "patternProperties", "$defs") and isinstance(
                child, dict
            ):
                places.extend(
                    f"{pointer}/{key}/{name}"
                    for name, member in child.items()
                    if member is False
                )
            places.extend(_worded_places(child, f"{pointer}/{key}"))
    elif isinstance(node, list):
        for index, child in enumerate(node):
            places.extend(_worded_places(child, f"{pointer}/{index}"))
    return places


def test_the_worded_shapes_lie_where_the_cases_below_reach() -> None:
    element = "#/$defs/FlowControlElement"
    assert _worded_places(timetoshare.load_schema(), "#") == [
        "#/$defs/Resource/properties/media_type/not",
        "#/$defs/Resource/properties/integrity/properties/digest/not",
        "#/$defs/TimeUnit/oneOf",
        "#/$defs/Id/not",
        f"{element}/then/then/properties/repeat_count/not",
        f"{element}/then/else/else/properties/repeat_count/not",
        f"{element}/else/properties/target/not",
        f"{element}/else/properties/repeat_count/not",
        "#/$defs/Order/items/not",
        "#/$defs/Paint/not",
        "#/$defs/Declaration/properties/stroke-dasharray/not",
        "#/$defs/Declaration/properties/elision-depths/not",
        "#/$defs/Declaration/properties/elision-display/not",
        "#/$defs/PrefixName/not",
        "#/$defs/PrefixIri/not",
        "#/$defs/Iri/not",
        "#/$defs/IriReference/not",
        "#/$defs/LanguageTag/not",
    ]


def test_an_unknown_unit_names_the_admitted_units() -> None:
    assert _problem(manifest(timeline("score", "furlongs"))) == (
        ("timelines", 0, "unit"),
        "'furlongs' is not one of ['number', 'floating_measures', 'whole_notes', "
        "'quarters', 'ticks', 'milliseconds', 'seconds', 'minutes', 'samples', "
        "'frames', 'pixels', 'meters', 'centimeters', 'millimeters', 'inches', "
        "'points', 'css_pixels', 'user_units']",
    )


def test_a_unit_of_another_type_keeps_the_type_message() -> None:
    assert _problem(manifest(timeline("score", 4))) == (
        ("timelines", 0, "unit"),
        "4 is not of type 'string'",
    )


@pytest.mark.parametrize(
    ("element", "key"),
    [
        (
            {
                "type": "jump_from",
                "manifestation": "dal_segno",
                "target": "s",
                "repeat_count": 2,
            },
            "repeat_count",
        ),
        (
            {"type": "jump_from", "manifestation": "da_capo", "repeat_count": 2},
            "repeat_count",
        ),
        ({"type": "jump_to", "manifestation": "segno", "target": "s"}, "target"),
        (
            {"type": "flow_marker", "manifestation": "fine", "repeat_count": 1},
            "repeat_count",
        ),
    ],
)
def test_a_forbidden_flow_control_member_is_named(element: dict, key: str) -> None:
    flow = [
        {"id": "s", "type": "jump_to", "manifestation": "segno", "coordinate": [2, 1]},
        {"id": "e", "coordinate": [6, 1], **element},
    ]
    assert _problem(manifest(timeline("score", flow_control=flow))) == (
        ("timelines", 0, "flow_control", 1, key),
        f"the key '{key}' is not admitted here",
    )


def _fixture(name: str) -> Any:
    return loads((REPOSITORY_ROOT / "fixtures" / "0.2.0" / name).read_text("utf-8"))


def _edited(name: str, path: tuple[str | int, ...], value: Any) -> Any:
    """The minimal fixture ``name`` with the member at ``path`` set to ``value``."""
    document = _fixture(name)
    holder = document
    for key in path[:-1]:
        holder = holder[key]
    holder[path[-1]] = value
    return document


def _file_problem(value: Any) -> tuple[tuple[str | int, ...], str]:
    with pytest.raises(SchemaValidationError) as caught:
        timetoshare.validate(value)
    assert caught.value.code == "schema"
    return caught.value.path, caught.value.message


STYLED = "styled__score.minimal.yaml"
RESOURCES = "bundles/bundle_resources.minimal.yaml"
STATEMENTS = "statements/nielsen_record.minimal.yaml"
CONTROL = "no control character (U+0000 to U+001F) is admitted here"
SPACE = "no whitespace and no control character is admitted here"
BANDS = ["children", "markers", "line\t", "conversion_maps", "regions", "flow_control"]


@pytest.mark.parametrize(
    ("name", "path", "value", "at", "message"),
    [
        (
            STYLED,
            ("timelines", 0, "id"),
            "#a\tb",
            (),
            f"'#a\\tb' holds U+0009: {CONTROL}",
        ),
        (
            STYLED,
            ("graphical", "order", "#score"),
            BANDS,
            (2,),
            f"'line\\t' holds U+0009: {CONTROL}",
        ),
        (
            STYLED,
            ("graphical", "rules", 0, "set", "fill"),
            "#404040\n",
            (),
            f"'#404040\\n' holds U+000A: {CONTROL}",
        ),
        (
            STYLED,
            ("graphical", "rules", 0, "set", "stroke-dasharray"),
            "3 3\n",
            (),
            f"'3 3\\n' holds U+000A: {CONTROL}",
        ),
        (
            STYLED,
            ("graphical", "rules", 0, "set", "elision-depths"),
            "1 2\n",
            (),
            f"'1 2\\n' holds U+000A: {CONTROL}",
        ),
        (
            STYLED,
            ("graphical", "rules", 0, "set", "elision-display"),
            "name\n",
            (),
            f"'name\\n' holds U+000A: {CONTROL}",
        ),
        (
            RESOURCES,
            ("resources", 0, "media_type"),
            "application/x\n",
            (),
            f"'application/x\\n' holds U+000A: {CONTROL}",
        ),
        (
            RESOURCES,
            ("resources", 0, "integrity"),
            {"algorithm": "SHA-256", "digest": "ab\n"},
            ("digest",),
            f"'ab\\n' holds U+000A: {CONTROL}",
        ),
        (
            RESOURCES,
            ("resources", 0, "url"),
            "match claims.parquet",
            (),
            f"'match claims.parquet' holds U+0020: {SPACE}",
        ),
        (
            RESOURCES,
            ("resources", 0, "url"),
            "_:b0",
            (),
            "'_:b0' begins with '_:': no blank node identifier is admitted here",
        ),
        (
            RESOURCES,
            ("resources", 0, "url"),
            "@id",
            (),
            "'@id' begins with '@': no keyword is admitted here",
        ),
        (
            STATEMENTS,
            ("@context", "wd"),
            "http://www.wikidata.org/\u00a0entity/",
            (),
            f"'http://www.wikidata.org/\\xa0entity/' holds U+00A0: {SPACE}",
        ),
        (
            STATEMENTS,
            ("statements", "rdfs:label"),
            [{"@value": "Sang", "@type": "xsd:da te"}],
            (0, "@type"),
            f"'xsd:da te' holds U+0020: {SPACE}",
        ),
        (
            STATEMENTS,
            ("statements", "rdfs:label"),
            [{"@value": "Sang", "@language": "en_GB"}],
            (0, "@language"),
            "'en_GB' holds '_': only A-Z, a-z, 0-9 and '-' are admitted here",
        ),
    ],
)
def test_a_refused_pattern_names_the_part_and_what_is_not_admitted(
    name: str,
    path: tuple[str | int, ...],
    value: Any,
    at: tuple[str | int, ...],
    message: str,
) -> None:
    assert _file_problem(_edited(name, path, value)) == ((*path, *at), message)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (
            "my.wd",
            "'my.wd' holds '.': only A-Z, a-z, 0-9, '_' and '-' are admitted here",
        ),
        (
            "https",
            "'https' is not admitted here: it names a key of the manifest's elements "
            "or a URI scheme the format reads as such",
        ),
    ],
)
def test_a_refused_prefix_name_names_the_part_and_what_is_not_admitted(
    value: str, message: str
) -> None:
    module = import_module("timetoshare.validate")
    schema = timetoshare.load_schema()
    definition = {"$defs": schema["$defs"], "$ref": "#/$defs/PrefixName"}
    checker = Draft202012Validator(definition)
    (error,) = checker.iter_errors(value)
    assert error.validator == "not"
    assert module.worded(error) == message


def test_a_context_key_that_is_no_prefix_name_keeps_the_term_list() -> None:
    edited = _fixture(STATEMENTS)
    edited["@context"]["my.wd"] = "http://www.wikidata.org/entity/"
    path, message = _file_problem(edited)
    assert path == ("@context",)
    assert message.startswith("'my.wd' is not one of ['@version', 'id', 'type', ")


def test_a_not_requiring_members_keeps_the_library_message() -> None:
    address = {"id": "#a", "facet": "markers", "part": ["name"]}
    value = _edited(STYLED, ("graphical", "rules", 2, "select", "addresses"), [address])
    path, message = _file_problem(value)
    assert path == ("graphical", "rules", 2, "select", "addresses", 0)
    assert message == (
        "{'id': '#a', 'facet': 'markers', 'part': ['name']} should not be valid "
        "under {'required': ['facet', 'part']}"
    )


@pytest.mark.parametrize(
    ("select", "member"),
    [
        ({"class": "regions"}, "class"),
        ({"class": "band"}, "class"),
        ({"element": "group"}, "element"),
        ({"inside": "group"}, "inside"),
        ({"addresses": []}, "addresses"),
    ],
)
def test_the_selector_refuses_the_older_vocabulary(select: dict, member: str) -> None:
    rule = {"select": select, "set": {"display": "none"}}
    value = manifest(timeline("score"), graphical={"rules": [rule]})
    assert _problem(value)[0] == ("graphical", "rules", 0, "select", member)


def _defaults_block() -> dict:
    """The JSON block of section 4 of the drawing specification."""
    text = (REPOSITORY_ROOT / "docs" / "drawing.md").read_text(encoding="utf-8")
    section = text.split("\n## 4. Defaults\n", 1)[1]
    block = section.split("```json\n", 1)[1].split("\n```", 1)[0]
    return json.loads(block)


def test_the_defaults_are_a_valid_graphical_object() -> None:
    defaults = _defaults_block()
    assert len(defaults["styles"]) == 3
    assert len(defaults["rules"]) == 38
    validate({**SMALLEST, "graphical": defaults})


def test_names_remain_unrestricted() -> None:
    validate(manifest(timeline("score", name="tab\there\nnewline")))


MATCHSTAMP_MESSAGES = {
    "alignment_anchor_timestamp_unknown": (
        "'timestamp_99' names no timestamp of this manifest"
    ),
    "alignment_anchor_timestamp_not_match": "'timestamp_2' is no match timestamp",
    "alignment_anchor_one_timeline": (
        "the timestamps of 'anchor_2' both lie on the timeline 'score'"
    ),
    "groupstamp_match_without_group": (
        "'timestamp_1' is a groupstamp, but its timeline 'score' is a member of "
        "no group and lies in none"
    ),
    "match_timestamp_in_no_matchstamp": (
        "the match timestamp 'timestamp_11' belongs to no MatchStamp"
    ),
    "match_timestamp_coordinate_repeated": (
        "'timestamp_11' lies on the coordinate of the match timestamp 'timestamp_1'"
    ),
    "matchstamp_not_connected": (
        "the alignment anchors of 'matchstamp_1' are not one connected set"
    ),
    "alignment_anchor_id_repeated": (
        "'anchor_1' is not unique in the manifest, first at "
        "#/graphical/matchstamps/0/alignment_anchors/0/id"
    ),
    "resource_timeline_unknown": "'take_3' names no timeline of this manifest",
    "resource_match_claim_twice": (
        "a manifest names at most one resource of the type MatchClaim; "
        "'resource_1' is one"
    ),
    "resource_projection_twice": (
        "a manifest names at most one resource of the type Projection; "
        "'resource_2' is one"
    ),
}


@pytest.mark.parametrize("name", sorted(MATCHSTAMP_MESSAGES))
def test_a_matchstamp_or_resource_case_pins_its_message(name: str) -> None:
    (path,) = [path for path in rejection_paths() if path.stem == name]
    case = rejection_case(path)
    with pytest.raises(SchemaValidationError) as raised:
        timetoshare.validate(case.manifest)
    assert raised.value.message == MATCHSTAMP_MESSAGES[name]


def test_the_matchstamp_rules_report_every_problem() -> None:
    (path,) = [
        path for path in rejection_paths() if path.stem == "matchstamp_not_connected"
    ]
    value = rejection_case(path).manifest
    value["graphical"]["timestamps"].append(
        {
            "coordinate": [6, 1],
            "display": ["cross_section"],
            "groupstamp": True,
            "id": "#timestamp_12",
            "matchstamp": True,
            "timeline": "#score",
        }
    )
    value["graphical"]["matchstamps"][0]["alignment_anchors"][0]["timestamps"] = [
        "#timestamp_7",
        "#timestamp_8",
    ]
    found = [
        (problem.code, problem.path) for problem in timetoshare.identity_problems(value)
    ]
    anchors = ("graphical", "matchstamps", 0, "alignment_anchors")
    assert found == [
        ("groupstamp", ("graphical", "timestamps", 10, "groupstamp")),
        ("alignment_anchor", (*anchors, 0, "timestamps", 0)),
        ("alignment_anchor", (*anchors, 0, "timestamps", 1)),
        ("matchstamp", anchors),
        ("match_timestamp", ("graphical", "timestamps", 1)),
        ("match_timestamp", ("graphical", "timestamps", 4)),
        ("match_timestamp", ("graphical", "timestamps", 10)),
        ("match_timestamp", ("graphical", "timestamps", 10)),
    ]


MATCHSTAMP_CASES = [
    "alignment_anchor_display_unknown",
    "alignment_anchor_id_repeated",
    "alignment_anchor_one_timeline",
    "alignment_anchor_timestamp_not_match",
    "alignment_anchor_timestamp_unknown",
    "match_timestamp_coordinate_repeated",
    "match_timestamp_in_no_matchstamp",
    "matchstamp_claims_repeated",
    "matchstamp_not_connected",
]
"""The rejection cases whose fault lies in the named MatchStamps."""


@pytest.mark.parametrize("name", MATCHSTAMP_CASES)
def test_the_matchstamps_alone_give_the_first_problem_of_validate(name: str) -> None:
    case = rejection_case(_rejection(name))
    with pytest.raises(SchemaValidationError) as raised:
        timetoshare.validate(case.manifest)
    first = timetoshare.matchstamp_problems(case.manifest)[0]
    assert (first.code, first.path, first.message) == (
        raised.value.code,
        raised.value.path,
        raised.value.message,
    )
    assert first.path == case.path


def test_the_matchstamps_alone_pass_every_other_case() -> None:
    others = sorted(
        path.stem
        for path in rejection_paths()
        if path.stem not in MATCHSTAMP_CASES
        and timetoshare.matchstamp_problems(rejection_case(path).manifest)
    )
    assert others == []
    for path in timetoshare.fixture_paths():
        assert timetoshare.matchstamp_problems(loads(path.read_text("utf-8"))) == []


def test_a_malformed_match_timestamp_is_reported_by_the_schema() -> None:
    value = rejection_case(_rejection("matchstamp_not_connected")).manifest
    del value["graphical"]["timestamps"][1]["timeline"]
    found = [
        (problem.code, problem.path)
        for problem in timetoshare.matchstamp_problems(value)
    ]
    assert found == [("schema", ("graphical", "timestamps", 1))]


@pytest.mark.parametrize(
    ("member", "path", "message"),
    [
        (
            "coordinate",
            ("graphical", "timestamps", 1, "coordinate"),
            "coordinate of 'timestamp_1' is not a finite number",
        ),
        (
            "match_claims",
            ("graphical", "matchstamps", 0, "match_claims", 2),
            "match_claims of 'matchstamp_1' is not a finite number",
        ),
    ],
)
def test_the_matchstamps_alone_refuse_a_non_finite_number_as_validate_does(
    member: str, path: tuple[str | int, ...], message: str
) -> None:
    value = rejection_case(_rejection("matchstamp_not_connected")).manifest
    if member == "coordinate":
        value["graphical"]["timestamps"][1]["coordinate"] = math.inf
    else:
        value["graphical"]["matchstamps"][0]["match_claims"].append(math.inf)
    with pytest.raises(SchemaValidationError) as raised:
        timetoshare.validate(value)
    found = [
        (problem.code, problem.path, problem.message)
        for problem in timetoshare.matchstamp_problems(value)
    ]
    expected = ("finite_number", path, message)
    assert found == [expected]
    assert (raised.value.code, raised.value.path, raised.value.message) == expected


def test_the_matchstamps_alone_pass_over_a_timestamp_that_is_no_object() -> None:
    (path,) = [
        path
        for path in timetoshare.fixture_paths()
        if path.name == "bundle_matchstamps.yaml"
    ]
    value = loads(path.read_text("utf-8"))
    value["graphical"]["timestamps"].append(None)
    assert timetoshare.matchstamp_problems(value) == []
