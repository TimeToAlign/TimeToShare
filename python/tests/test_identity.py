from __future__ import annotations

import copy
import math
from fractions import Fraction
from typing import Any

import pytest

import timetoshare
from timetoshare import (
    SchemaValidationError,
    rejection_case,
    rejection_paths,
    with_bare_ids,
)

from .conftest import (
    bundle,
    group,
    identity_problems,
    manifest,
    manifest_warnings,
    timeline,
    unknown_keys,
    validate,
)


def _problems(value: dict) -> list[tuple[tuple[str | int, ...], str]]:
    return [(problem.path, problem.message) for problem in identity_problems(value)]


def _only(value: dict) -> tuple[tuple[str | int, ...], str]:
    (problem,) = _problems(value)
    with pytest.raises(SchemaValidationError) as caught:
        validate(value)
    assert (caught.value.path, caught.value.message) == problem
    return problem


def _targets(*identifiers: str) -> list[dict]:
    return [
        {"id": i, "type": "jump_to", "manifestation": "segno", "coordinate": [k, 1]}
        for k, i in enumerate(identifiers)
    ]


def test_the_bundle_document_has_no_problem() -> None:
    assert _problems(bundle()) == []
    validate(bundle())


def test_a_repeated_id_within_a_root_is_reported_at_its_later_occurrence() -> None:
    child = timeline("c", offset=(0, 1), flow_control=_targets("m"))
    root = timeline("bare", flow_control=_targets("m", "m", "bare"), children=[child])
    assert _problems(manifest(root)) == [
        (
            ("timelines", 0, "flow_control", 1, "id"),
            "'m' is not unique in the manifest, "
            "first at #/timelines/0/flow_control/0/id",
        ),
        (
            ("timelines", 0, "flow_control", 2, "id"),
            "'bare' is not unique in the manifest, first at #/timelines/0/id",
        ),
        (
            ("timelines", 0, "children", 0, "flow_control", 0, "id"),
            "'m' is not unique in the manifest, "
            "first at #/timelines/0/flow_control/0/id",
        ),
    ]


def _linear(identifier: str) -> dict:
    return {
        "type": "LinearMap",
        "id": identifier,
        "source_unit": None,
        "target_unit": None,
    }


def test_one_scope_across_roots() -> None:
    value = manifest(
        timeline("a", flow_control=_targets("m")),
        timeline("b", flow_control=_targets("m")),
    )
    assert _only(value) == (
        ("timelines", 1, "flow_control", 0, "id"),
        "'m' is not unique in the manifest, first at #/timelines/0/flow_control/0/id",
    )
    score = timeline("score", regions=[{"id": "perf", "start": [0, 1], "end": [1, 1]}])
    take = timeline("take", children=[timeline("perf", offset=(0, 1))])
    assert _only(manifest(score, take)) == (
        ("timelines", 1, "children", 0, "id"),
        "'perf' is not unique in the manifest, first at #/timelines/0/regions/0/id",
    )
    chain = {
        "type": "ChainMap",
        "id": "c",
        "source_unit": None,
        "target_unit": None,
        "maps": [_linear("l")],
    }
    value = manifest(
        timeline("a", conversion_maps=[chain]),
        timeline("b", conversion_maps=[copy.deepcopy(chain) | {"id": "d"}]),
    )
    assert _only(value) == (
        ("timelines", 1, "conversion_maps", 0, "maps", 0, "id"),
        "'l' is not unique in the manifest, "
        "first at #/timelines/0/conversion_maps/0/maps/0/id",
    )
    value = manifest(copy.deepcopy(score), groups=[group("perf", "score")])
    assert _only(value) == (
        ("groups", 0, "id"),
        "'perf' is not unique in the manifest, first at #/timelines/0/regions/0/id",
    )
    value = manifest(copy.deepcopy(score), id="perf")
    assert _only(value) == (
        ("id",),
        "'perf' is not unique in the manifest, first at #/timelines/0/regions/0/id",
    )
    assert [problem.code for problem in identity_problems(value)] == ["manifest_id"]


def test_a_nested_map_id_shares_its_root_s_scope() -> None:
    linear = _linear
    units = {"source_unit": None, "target_unit": None}
    chain = {"type": "ChainMap", "id": "c", "maps": [linear("l"), linear("l")]} | units
    piecewise = {
        "type": "PiecewiseMap",
        "id": "p",
        "breaks": [[0, 1], [4, 1]],
        "maps": [linear("l")],
    } | units
    combination = {
        "type": "CombinationMap",
        "id": "cmap_1",
        "maps": {"output": linear("cmap_1")},
    } | units
    region = {"id": "l", "start": [0, 1], "end": [1, 1]}
    held = ("timelines", 0, "conversion_maps", 0, "maps")
    assert _only(manifest(timeline("s", conversion_maps=[chain]))) == (
        (*held, 1, "id"),
        "'l' is not unique in the manifest, "
        "first at #/timelines/0/conversion_maps/0/maps/0/id",
    )
    assert _only(
        manifest(timeline("s", conversion_maps=[piecewise], regions=[region]))
    ) == (
        (*held, 0, "id"),
        "'l' is not unique in the manifest, first at #/timelines/0/regions/0/id",
    )
    assert _only(manifest(timeline("s", conversion_maps=[combination]))) == (
        (*held, "output", "id"),
        "'cmap_1' is not unique in the manifest, "
        "first at #/timelines/0/conversion_maps/0/id",
    )


def test_targets_stay_within_their_timeline() -> None:
    def jump(
        identifier: str, target: str | None, manifestation: str = "dal_segno"
    ) -> dict:
        element = {
            "id": identifier,
            "type": "jump_from",
            "manifestation": manifestation,
            "coordinate": [4, 1],
        }
        return element if target is None else {**element, "target": target}

    fine = {
        "id": "fine",
        "type": "flow_marker",
        "manifestation": "fine",
        "coordinate": [6, 1],
    }
    child = timeline(
        "c",
        offset=(0, 1),
        flow_control=[*_targets("there"), jump("cj", "here")],
    )
    root = timeline(
        "bare",
        flow_control=[
            *_targets("here"),
            fine,
            jump("j1", "here"),
            jump("j2", None, "da_capo"),
            jump("j3", "there"),
            jump("j4", "fine"),
            jump("j5", None, "repeat_end"),
        ],
        children=[child],
    )
    assert _problems(manifest(root)) == [
        (
            ("timelines", 0, "flow_control", 4, "target"),
            "'there' names no jump_to of this timeline",
        ),
        (
            ("timelines", 0, "flow_control", 5, "target"),
            "'fine' names no jump_to of this timeline",
        ),
        (
            ("timelines", 0, "children", 0, "flow_control", 1, "target"),
            "'here' names no jump_to of this timeline",
        ),
    ]


ROWS = [{"count": 1, "qstamp": [0, 1], "actual_length": [4, 1]}]


def _table(x_values: list, y_values: list, identifier: str = "tempo") -> dict:
    return {
        "type": "TableMap",
        "id": identifier,
        "source_unit": "quarters",
        "target_unit": None,
        "x_values": x_values,
        "y_values": y_values,
    }


def _piecewise(breaks: list, maps: list) -> dict:
    return {
        "type": "PiecewiseMap",
        "id": "sections",
        "source_unit": "quarters",
        "target_unit": None,
        "breaks": breaks,
        "maps": maps,
    }


def _linear(identifier: str) -> dict:
    return {
        "type": "LinearMap",
        "id": identifier,
        "source_unit": None,
        "target_unit": None,
    }


def _view(identifier: str, reference: str) -> dict:
    return {
        "type": "MeasureNumberMap",
        "id": identifier,
        "source_unit": "quarters",
        "target_unit": None,
        "measure_map": reference,
    }


def _maps(*conversion_maps: dict) -> dict:
    return manifest(timeline("score", conversion_maps=list(conversion_maps)))


def test_a_table_maps_arrays_agree() -> None:
    assert _only(_maps(_table([[0, 1], [4, 1], [8, 1]], [60, 72]))) == (
        ("timelines", 0, "conversion_maps", 0, "y_values"),
        "TableMap 'tempo' has 3 x values and 2 y values",
    )
    assert _only(_maps(_table([[0, 1], [2, 1], 2.0], [1, 2, 3]))) == (
        ("timelines", 0, "conversion_maps", 0, "x_values", 2),
        "x value 2.0 of TableMap 'tempo' does not exceed the one before it",
    )
    accepted = _maps(_table([[0, 1], 0.5, [3, 4]], [1, 2, 3]))
    assert _problems(accepted) == []
    validate(accepted)


def test_a_piecewise_map_has_one_map_per_interval() -> None:
    assert _only(_maps(_piecewise([[0, 1], [8, 1], [16, 1]], [_linear("a")]))) == (
        ("timelines", 0, "conversion_maps", 0, "maps"),
        "PiecewiseMap 'sections' has 1 map for 3 breaks; it needs 2 maps",
    )
    pieces = _piecewise([[0, 1], [8, 1], [4, 1]], [_linear("a"), _linear("b")])
    assert _only(_maps(pieces)) == (
        ("timelines", 0, "conversion_maps", 0, "breaks", 2),
        "break [4, 1] of PiecewiseMap 'sections' does not exceed the one before it",
    )


def test_nested_maps_are_checked_at_their_own_paths() -> None:
    def repeated(identifier: str) -> dict:
        return _table([[1, 1], [1, 1]], [1, 2], identifier)

    chain = {
        "type": "ChainMap",
        "id": "chain",
        "source_unit": "quarters",
        "target_unit": None,
        "maps": [repeated("tc")],
    }
    both = {
        "type": "CombinationMap",
        "id": "both",
        "source_unit": "quarters",
        "target_unit": None,
        "maps": {"b": repeated("tb"), "a": repeated("ta")},
    }
    pieces = _piecewise([[0, 1], [8, 1]], [repeated("tp")])
    child = timeline("c", offset=(0, 1), conversion_maps=[repeated("tk")])
    root = timeline("score", conversion_maps=[chain, both, pieces], children=[child])
    message = "x value [1, 1] of TableMap {} does not exceed the one before it"
    assert _problems(manifest(root)) == [
        (
            ("timelines", 0, "conversion_maps", 0, "maps", 0, "x_values", 1),
            message.format("'tc'"),
        ),
        (
            ("timelines", 0, "conversion_maps", 1, "maps", "a", "x_values", 1),
            message.format("'ta'"),
        ),
        (
            ("timelines", 0, "conversion_maps", 1, "maps", "b", "x_values", 1),
            message.format("'tb'"),
        ),
        (
            ("timelines", 0, "conversion_maps", 2, "maps", 0, "x_values", 1),
            message.format("'tp'"),
        ),
        (
            ("timelines", 0, "children", 0, "conversion_maps", 0, "x_values", 1),
            message.format("'tk'"),
        ),
    ]
    assert {problem.code for problem in identity_problems(manifest(root))} == {
        "conversion_map"
    }


def _record(identifier: str = "bars") -> dict:
    return {
        "type": "MeasureRecordMap",
        "id": identifier,
        "source_unit": "quarters",
        "target_unit": None,
        "measure_map": "measures",
    }


def _scale(
    source: str | None, target: str | None = "quarters", identifier: str = "scale"
) -> dict:
    return {
        "type": "LinearMap",
        "id": identifier,
        "source_unit": source,
        "target_unit": target,
        "scalar": [1, 480],
    }


def _holder(kind: str, source: str | None, maps: list | dict, **rest: object) -> dict:
    identifier = {"ChainMap": "chain", "CombinationMap": "both"}.get(kind, "sections")
    return {
        "type": kind,
        "id": identifier,
        "source_unit": source,
        "target_unit": None,
        "maps": maps,
        **rest,
    }


def _ticks(*conversion_maps: dict, children: list | None = None) -> dict:
    root = timeline(
        "score",
        "ticks",
        3840,
        conversion_maps=list(conversion_maps),
        children=children or [],
    )
    return manifest(root, measure_maps=[{"id": "measures", "rows": ROWS}])


def test_a_map_converts_from_its_timelines_unit() -> None:
    assert _only(_ticks(_record())) == (
        ("timelines", 0, "conversion_maps", 0, "source_unit"),
        "MeasureRecordMap 'bars' has source unit 'quarters', its timeline 'score' "
        "has 'ticks'",
    )
    child = timeline("c", "ticks", 960, offset=0, conversion_maps=[_record()])
    assert _only(_ticks(children=[child])) == (
        ("timelines", 0, "children", 0, "conversion_maps", 0, "source_unit"),
        "MeasureRecordMap 'bars' has source unit 'quarters', its timeline 'c' "
        "has 'ticks'",
    )
    chained = _holder("ChainMap", "ticks", [_scale("ticks"), _record()])
    loose = _scale(None, None, "loose")
    held = _scale("seconds", identifier="held")
    unstated = _holder("PiecewiseMap", None, [held], breaks=[0, 960])
    accepted = _ticks(chained, loose, unstated)
    assert _problems(accepted) == []
    validate(accepted)


def test_a_held_map_converts_from_its_holders_source_unit() -> None:
    later = _scale("seconds", identifier="later")
    chain = _holder("ChainMap", "quarters", [_scale("ticks"), later])
    assert _only(_maps(chain)) == (
        ("timelines", 0, "conversion_maps", 0, "maps", 0, "source_unit"),
        "LinearMap 'scale' has source unit 'ticks', its ChainMap 'chain' has "
        "'quarters'",
    )
    both = _holder("CombinationMap", "ticks", {"bar": _record("bar")})
    assert _only(_ticks(both)) == (
        ("timelines", 0, "conversion_maps", 0, "maps", "bar", "source_unit"),
        "MeasureRecordMap 'bar' has source unit 'quarters', its CombinationMap "
        "'both' has 'ticks'",
    )
    pieces = _holder(
        "PiecewiseMap", "quarters", [_scale("seconds")], breaks=[[0, 1], [8, 1]]
    )
    assert _only(_maps(pieces)) == (
        ("timelines", 0, "conversion_maps", 0, "maps", 0, "source_unit"),
        "LinearMap 'scale' has source unit 'seconds', its PiecewiseMap "
        "'sections' has 'quarters'",
    )
    assert {problem.code for problem in identity_problems(_maps(chain))} == {
        "conversion_map"
    }


def test_a_measure_view_names_a_measure_map() -> None:
    both = {
        "type": "CombinationMap",
        "id": "both",
        "source_unit": "quarters",
        "target_unit": None,
        "maps": {"bar": _view("bar", "ghost")},
    }
    value = manifest(
        timeline("score", conversion_maps=[_view("number", "ghost"), both]),
        measure_maps=[{"id": "measures", "rows": ROWS}],
    )
    assert _problems(value) == [
        (
            ("timelines", 0, "conversion_maps", 0, "measure_map"),
            "'ghost' names no MeasureMap of this manifest",
        ),
        (
            ("timelines", 0, "conversion_maps", 1, "maps", "bar", "measure_map"),
            "'ghost' names no MeasureMap of this manifest",
        ),
    ]
    assert {problem.code for problem in identity_problems(value)} == {"dangling_target"}
    named = manifest(
        timeline("score", conversion_maps=[_view("number", "measures")]),
        timeline("take", "seconds", 60.0),
        measure_maps=[{"id": "measures", "rows": ROWS}],
    )
    assert _problems(named) == []
    validate(named)


def test_measure_map_ids_share_the_manifest_scope() -> None:
    value = manifest(
        timeline("score"),
        groups=[group("g", "score")],
        measure_maps=[
            {"id": identifier, "rows": ROWS} for identifier in ("score", "g", "m", "m")
        ],
    )
    assert _problems(value) == [
        (
            ("measure_maps", 0, "id"),
            "'score' is not unique in the manifest, first at #/timelines/0/id",
        ),
        (
            ("measure_maps", 1, "id"),
            "'g' is not unique in the manifest, first at #/groups/0/id",
        ),
        (
            ("measure_maps", 3, "id"),
            "'m' is not unique in the manifest, first at #/measure_maps/2/id",
        ),
    ]
    assert {problem.code for problem in identity_problems(value)} == {"duplicate_id"}
    named = manifest(
        timeline("score"), id="m", measure_maps=[{"id": "m", "rows": ROWS}]
    )
    assert _only(named) == (
        ("id",),
        "'m' is not unique in the manifest, first at #/measure_maps/0/id",
    )
    assert [problem.code for problem in identity_problems(named)] == ["manifest_id"]


def test_a_child_shares_its_parents_unit() -> None:
    value = manifest(
        timeline("score", children=[timeline("take", "seconds", 4.0, offset=(2, 1))])
    )
    assert _only(value) == (
        ("timelines", 0, "children", 0, "unit"),
        "child 'take' has unit 'seconds', its parent 'score' has 'quarters'",
    )
    number = timeline("n", "number", (4, 1), offset=(0, 1), number_type="fraction")
    assert _only(manifest(timeline("score", children=[number]))) == (
        ("timelines", 0, "children", 0, "unit"),
        "child 'n' has unit 'number', its parent 'score' has 'quarters'",
    )
    grandchild = timeline("b", "ticks", 4, offset=(1, 1))
    value = manifest(
        timeline(
            "score", children=[timeline("a", offset=(0, 1), children=[grandchild])]
        )
    )
    assert _only(value) == (
        ("timelines", 0, "children", 0, "children", 0, "unit"),
        "child 'b' has unit 'ticks', its parent 'a' has 'quarters'",
    )
    assert (
        _problems(manifest(timeline("score", children=[timeline("c", offset=(0, 1))])))
        == []
    )


def test_a_negative_offset_is_accepted_on_a_child_or_a_root() -> None:
    def take(offset: float) -> dict:
        return manifest(
            timeline(
                "recording",
                "seconds",
                60.0,
                children=[timeline("take", "seconds", 4.0, offset=offset)],
            )
        )

    grandchild = timeline("b", offset=(-1, 2))
    for document in (
        take(-1.5),
        manifest(timeline("score", children=[timeline("c", offset=(-1, 1000000))])),
        manifest(
            timeline(
                "score", children=[timeline("a", offset=(0, 1), children=[grandchild])]
            )
        ),
        {
            "timetoshare": "0.2.0",
            "timelines": [
                {
                    "id": "piece",
                    "unit": "quarters",
                    "length": [32, 1],
                    "children": [
                        {
                            "id": "take",
                            "unit": "quarters",
                            "offset": [-3, 2],
                            "length": [4, 1],
                        }
                    ],
                }
            ],
        },
        manifest(timeline("score", children=[timeline("c", offset=(0, 1))])),
        take(-0.0),
        manifest(timeline("take", "seconds", 2.5, offset=-1700000000.25)),
        manifest(timeline("score", offset=[-3, 2])),
    ):
        assert _problems(document) == []
        validate(document)
    long = timeline("take", length=(40, 1), offset=(-3, 2))
    value = manifest(timeline("piece", length=(32, 1), children=[long]))
    assert _only(value) == (
        ("timelines", 0, "children", 0, "length"),
        "child 'take' ends at [77, 2], beyond the length [32, 1] of its parent 'piece'",
    )


def test_a_child_lies_within_its_parents_known_length() -> None:
    def recording(length: float, *children: dict) -> dict:
        return manifest(
            timeline("recording", "seconds", length, children=list(children))
        )

    def take(length: float | None, offset: float) -> dict:
        return timeline("take", "seconds", length, offset=offset)

    assert _only(recording(60.0, take(None, 75.0))) == (
        ("timelines", 0, "children", 0, "offset"),
        "offset 75.0 of 'take' is beyond the length 60.0 of its parent 'recording'",
    )
    score = timeline("score", children=[timeline("c", length=(2, 1), offset=(9, 1))])
    assert _only(manifest(score)) == (
        ("timelines", 0, "children", 0, "offset"),
        "offset [9, 1] of 'c' is beyond the length [8, 1] of its parent 'score'",
    )
    coda = timeline("coda", length=(4, 1), offset=(8, 1))
    assert _only(manifest(timeline("score", length=(10, 1), children=[coda]))) == (
        ("timelines", 0, "children", 0, "length"),
        "child 'coda' ends at [12, 1], beyond the length [10, 1] of its parent 'score'",
    )
    assert _only(recording(0.75, take(0.5, 0.5))) == (
        ("timelines", 0, "children", 0, "length"),
        "child 'take' ends at 1.0, beyond the length 0.75 of its parent 'recording'",
    )
    assert _only(recording(0.3, take(0.2, 0.1))) == (
        ("timelines", 0, "children", 0, "length"),
        "child 'take' ends at 0.30000000000000004, beyond the length 0.3 of its "
        "parent 'recording'",
    )
    third = timeline("take", "seconds", [1, 3], offset=0.5, number_type="fraction")
    assert _only(recording(0.75, third)) == (
        ("timelines", 0, "children", 0, "length"),
        "child 'take' ends at [5, 6], beyond the length 0.75 of its parent 'recording'",
    )
    midi = timeline(
        "midi", "ticks", 480, children=[timeline("m", "ticks", 240, offset=480)]
    )
    assert _only(manifest(midi)) == (
        ("timelines", 0, "children", 0, "length"),
        "child 'm' ends at 720, beyond the length 480 of its parent 'midi'",
    )
    loose = timeline("f", length=2.5, offset=(7, 1), number_type="float")
    assert _only(manifest(timeline("score", children=[loose]))) == (
        ("timelines", 0, "children", 0, "length"),
        "child 'f' ends at [19, 2], beyond the length [8, 1] of its parent 'score'",
    )
    other = timeline("take", "seconds", 100.0, offset=(2, 1))
    assert _problems(manifest(timeline("score", children=[other]))) == [
        (
            ("timelines", 0, "children", 0, "unit"),
            "child 'take' has unit 'seconds', its parent 'score' has 'quarters'",
        )
    ]
    grandchild = timeline("b", length=(2, 1), offset=(3, 1))
    child = timeline("a", length=(4, 1), offset=(0, 1), children=[grandchild])
    assert _only(manifest(timeline("score", children=[child]))) == (
        ("timelines", 0, "children", 0, "children", 0, "length"),
        "child 'b' ends at [5, 1], beyond the length [4, 1] of its parent 'a'",
    )
    line = timeline(
        "line",
        is_segment_line=True,
        children=[
            timeline("a", length=None, offset=(0, 1)),
            timeline("b", length=(1, 1), offset=(10, 1)),
        ],
    )
    assert _problems(manifest(line)) == [
        (
            ("timelines", 0, "children", 0, "length"),
            "child 'a' ends at [10, 1], beyond the length [8, 1] of its parent 'line'",
        ),
        (
            ("timelines", 0, "children", 1, "offset"),
            "offset [10, 1] of 'b' is beyond the length [8, 1] of its parent 'line'",
        ),
        (
            ("timelines", 0, "length"),
            "the segments of segment line 'line' do not end at its length",
        ),
    ]
    for document in (
        recording(60.0, take(None, 60.0)),
        manifest(
            timeline(
                "score",
                length=(10, 1),
                children=[timeline("c", length=(2, 1), offset=(8, 1))],
            )
        ),
        recording(0.75, take(0.25, 0.5)),
        manifest(
            timeline(
                "score",
                length=None,
                children=[timeline("c", length=(8, 1), offset=(100, 1))],
            )
        ),
    ):
        assert _problems(document) == []
        validate(document)


def test_a_child_on_a_float_axis_ends_at_the_double_sum() -> None:
    def nested(length: Any, child_length: Any, offset: Any, number_type: str) -> dict:
        inner = timeline(
            "inner", "points", child_length, offset=offset, number_type=number_type
        )
        return manifest(
            timeline(
                "outer", "points", length, number_type=number_type, children=[inner]
            )
        )

    # Three doubles whose exact sum exceeds the parent by 3/2^46 while their
    # double sum equals it.
    fits = nested(932.2326510101616, 855.5289364103584, 76.70371459980326, "float")
    assert 76.70371459980326 + 855.5289364103584 == 932.2326510101616
    assert _problems(fits) == []
    validate(fits)
    assert _only(nested(932.2326510101616, 855.53, 76.70371459980326, "float")) == (
        ("timelines", 0, "children", 0, "length"),
        "child 'inner' ends at 932.2337145998032, beyond the length 932.2326510101616 "
        "of its parent 'outer'",
    )
    pairs = (
        [2050001279156237, 2199023255552],
        [7525312107856185, 8796093022208],
        [5397544070150107, 70368744177664],
    )
    assert [Fraction(*pair) for pair in pairs] == [
        Fraction(932.2326510101616),
        Fraction(855.5289364103584),
        Fraction(76.70371459980326),
    ]
    exact = nested(*pairs, "fraction")
    assert _only(exact) == (
        ("timelines", 0, "children", 0, "length"),
        "child 'inner' ends at [65600040932999587, 70368744177664], beyond the length "
        "[2050001279156237, 2199023255552] of its parent 'outer'",
    )


def test_a_child_without_a_double_sum_ends_at_the_exact_sum() -> None:
    largest = 1.7976931348623157e308
    assert math.isinf(1e308 + 1e308)
    assert _only(
        manifest(
            timeline(
                "outer",
                "points",
                largest,
                children=[timeline("inner", "points", 1e308, offset=1e308)],
            )
        )
    ) == (
        ("timelines", 0, "children", 0, "length"),
        f"child 'inner' ends at [{2 * int(1e308)}, 1], beyond the length "
        "1.7976931348623157e+308 of its parent 'outer'",
    )
    beyond = manifest(
        timeline(
            "outer",
            "points",
            1.0,
            children=[timeline("inner", "points", 10**400, offset=0.5)],
        )
    )
    with pytest.raises(OverflowError):
        float(10**400)
    assert _problems(beyond) == [
        (
            ("timelines", 0, "children", 0, "length"),
            f"child 'inner' ends at [{2 * 10**400 + 1}, 2], beyond the length 1.0 "
            "of its parent 'outer'",
        )
    ]
    with pytest.raises(SchemaValidationError) as caught:
        validate(beyond)
    assert caught.value.code == "representation"


@pytest.mark.parametrize(
    ("name", "message"),
    [
        (
            "child_unit_differs",
            "child 'take' has unit 'seconds', its parent 'score' has 'quarters'",
        ),
        (
            "child_offset_beyond_parent",
            "offset 75.0 of 'take' is beyond the length 60.0 of its parent 'recording'",
        ),
        (
            "child_end_beyond_parent",
            "child 'coda' ends at [12, 1], beyond the length [10, 1] of its parent "
            "'score'",
        ),
        (
            "region_id_duplicate_across_roots",
            "'region_1' is not unique in the manifest, "
            "first at #/timelines/0/regions/0/id",
        ),
        (
            "band_order_unknown_entry",
            "'annotations' is not 'line' or a facet, in the band order of 'score'",
        ),
        (
            "band_order_missing_line",
            "'line' is missing from the band order of 'score'",
        ),
        (
            "band_order_old_form",
            "'score/regions_1' is not 'line' or a facet, in the band order of 'score'",
        ),
        (
            "order_unknown_group",
            "'group_9' names no group or timeline of this manifest",
        ),
        (
            "timestamp_timeline_unknown",
            "'ghost' names no timeline of this manifest",
        ),
        (
            "timestamp_coordinate_beyond_length",
            "coordinate [5, 1] of 'timestamp_1' is beyond the length [4, 1] of its "
            "timeline 'verse'",
        ),
        (
            "timestamp_coordinate_negative",
            "coordinate [-1, 1] of 'timestamp_1' lies before the start of its "
            "timeline 'score'",
        ),
        (
            "timestamp_id_is_timeline_id",
            "'timestamp_1' is not unique in the manifest, first at #/timelines/0/id",
        ),
        (
            "groupstamp_without_group",
            "'timestamp_1' is a groupstamp, but its timeline 'clt_1' is a member of "
            "no group and lies in none",
        ),
        (
            "groupstamp_child_without_group",
            "'timestamp_3' is a groupstamp, but its timeline 'clt_2' is a member of "
            "no group and lies in none",
        ),
        (
            "groupstamp_member_parent",
            "'timestamp_5' is a groupstamp, but its timeline 'piece' is a member of "
            "no group and lies in none",
        ),
    ],
)
def test_the_shared_identity_rejections_carry_their_messages(
    name: str, message: str
) -> None:
    (path,) = [path for path in rejection_paths() if path.stem == name]
    case = rejection_case(path)
    assert _only(with_bare_ids(case.manifest)) == (case.path, message)


def _id_documents(word: str) -> list[tuple[dict, tuple[str | int, ...]]]:
    """``word`` as the id of each kind, with the path of that id."""
    region = {"id": word, "start": [0, 1], "end": [1, 1]}
    linear = {
        "type": "LinearMap",
        "id": word,
        "source_unit": None,
        "target_unit": None,
    }
    rows = [{"count": 1, "qstamp": [0, 1], "actual_length": [4, 1]}]
    flow = [
        {
            "id": word,
            "type": "flow_marker",
            "manifestation": "fine",
            "coordinate": [1, 1],
        },
        {
            "id": word,
            "type": "jump_from",
            "manifestation": "da_capo",
            "coordinate": [1, 1],
        },
        {"id": word, "type": "jump_to", "manifestation": "coda", "coordinate": [1, 1]},
    ]
    holders = [
        (
            {"type": "ChainMap", "id": "c", "maps": [linear]},
            ("maps", 0, "id"),
        ),
        (
            {
                "type": "PiecewiseMap",
                "id": "p",
                "breaks": [[0, 1], [4, 1]],
                "maps": [linear],
            },
            ("maps", 0, "id"),
        ),
        (
            {"type": "CombinationMap", "id": "o", "maps": {"output": linear}},
            ("maps", "output", "id"),
        ),
    ]
    documents = [
        (manifest(timeline(word)), ("timelines", 0, "id")),
        (
            manifest(timeline("s", conversion_maps=[linear])),
            ("timelines", 0, "conversion_maps", 0, "id"),
        ),
        *(
            (
                manifest(
                    timeline(
                        "s",
                        conversion_maps=[
                            {"source_unit": None, "target_unit": None} | holder
                        ],
                    )
                ),
                ("timelines", 0, "conversion_maps", 0, *at),
            )
            for holder, at in holders
        ),
        (
            manifest(timeline("s", regions=[region])),
            ("timelines", 0, "regions", 0, "id"),
        ),
        (manifest(timeline("s"), groups=[group(word, "s")]), ("groups", 0, "id")),
        (
            manifest(timeline("s"), measure_maps=[{"id": word, "rows": rows}]),
            ("measure_maps", 0, "id"),
        ),
        (manifest(timeline("s"), id=word), ("id",)),
    ]
    for element in flow:
        documents.append(
            (
                manifest(timeline("s", flow_control=[element])),
                ("timelines", 0, "flow_control", 0, "id"),
            )
        )
    return documents


@pytest.mark.parametrize(
    "word",
    [
        "start",
        "end",
        "name",
        "label",
        "card",
        "regions_1",
        "flow_control_907",
        "perf/take 2",
        "https://example.org/piece/score#exposition",
    ],
)
def test_no_id_is_reserved(word: str) -> None:
    for document, _ in _id_documents(word):
        assert _problems(document) == []
        validate(document)


def test_timeline_ids_are_unique_across_roots() -> None:
    value = manifest(timeline("piece"), timeline("piece"))
    assert _only(value) == (
        ("timelines", 1, "id"),
        "'piece' is not unique in the manifest, first at #/timelines/0/id",
    )
    child = timeline("excerpt", offset=(0, 1))
    value = manifest(
        timeline("a", children=[child]), timeline("b", children=[copy.deepcopy(child)])
    )
    assert _only(value) == (
        ("timelines", 1, "children", 0, "id"),
        "'excerpt' is not unique in the manifest, first at #/timelines/0/children/0/id",
    )


def test_a_timeline_id_repeated_within_a_root_is_reported_once() -> None:
    value = manifest(timeline("a", children=[timeline("a", offset=(0, 1))]))
    assert _problems(value) == [
        (
            ("timelines", 0, "children", 0, "id"),
            "'a' is not unique in the manifest, first at #/timelines/0/id",
        )
    ]


def test_group_ids() -> None:
    value = manifest(timeline("score"), groups=[group("score")])
    assert _only(value) == (
        ("groups", 0, "id"),
        "'score' is not unique in the manifest, first at #/timelines/0/id",
    )
    value = manifest(timeline("score"), groups=[group("g"), group("g")])
    assert _only(value) == (
        ("groups", 1, "id"),
        "'g' is not unique in the manifest, first at #/groups/0/id",
    )


def test_the_manifest_id() -> None:
    value = manifest(timeline("score"), id="score")
    assert _only(value) == (
        ("id",),
        "'score' is not unique in the manifest, first at #/timelines/0/id",
    )
    value = manifest(timeline("score"), id="g", groups=[group("g")])
    assert _only(value) == (
        ("id",),
        "'g' is not unique in the manifest, first at #/groups/0/id",
    )
    value = manifest(timeline("g"), id="g", groups=[group("g")])
    assert _problems(value) == [
        (
            ("groups", 0, "id"),
            "'g' is not unique in the manifest, first at #/timelines/0/id",
        ),
        (("id",), "'g' is not unique in the manifest, first at #/timelines/0/id"),
    ]


def test_members() -> None:
    value = manifest(timeline("score"), groups=[group("g", "tempo")])
    assert _only(value) == (
        ("groups", 0, "members", 0),
        "'tempo' names no timeline of this manifest",
    )
    piece = timeline("piece", children=[timeline("half", offset=(4, 1), length=(4, 1))])
    value = manifest(piece, groups=[group("g", "piece", "half")])
    assert _only(value) == (
        ("groups", 0, "members", 1),
        "member 'half' lies inside member 'piece' of the same group",
    )
    value = manifest(copy.deepcopy(piece), groups=[group("g", "half", "piece")])
    assert _only(value) == (
        ("groups", 0, "members", 1),
        "member 'piece' contains member 'half' of the same group",
    )


def test_a_child_and_its_root_in_other_groups_or_none() -> None:
    value = bundle()
    validate(value)
    value["groups"][0]["members"].append("recording")
    value["graphical"]["order"]["group_1"].append("recording")
    validate(value)


def test_a_timeline_in_two_groups() -> None:
    value = manifest(
        timeline("t"),
        timeline("u"),
        timeline("v"),
        groups=[group("g1", "t", "u"), group("g2", "t", "v")],
    )
    assert _problems(value) == []
    validate(value)


def test_a_group_without_members_stays_valid() -> None:
    validate(manifest(timeline("score"), groups=[group("empty")]))


def test_display_orders() -> None:
    value = bundle()
    value["graphical"]["order"]["g9"] = []
    assert _only(value) == (
        ("graphical", "order", "g9"),
        "'g9' names no group or timeline of this manifest",
    )
    value = bundle()
    value["graphical"]["order"]["group_1"] = ["score", "page", "performance"]
    assert _only(value) == (
        ("graphical", "order", "group_1", 1),
        "'page' is not a member of group 'group_1'",
    )
    value = bundle()
    value["graphical"]["order"]["group_2"] = ["page"]
    assert _only(value) == (
        ("graphical", "order", "group_2"),
        "member 'excerpt' of group 'group_2' is missing",
    )
    value = bundle()
    del value["graphical"]["order"]["group_2"]
    validate(value)


SCORE_BANDS = [
    "children",
    "markers",
    "line",
    "conversion_maps",
    "regions",
    "flow_control",
]
"""The band order of the README's example."""

B_BANDS = [
    "flow_control",
    "regions",
    "markers",
    "line",
    "conversion_maps",
    "children",
]
"""The reverse of the default band order, for the child ``b``."""

DEFAULT_BANDS = [
    "children",
    "conversion_maps",
    "line",
    "markers",
    "regions",
    "flow_control",
]
"""The default band order."""


def _band_orders(**orders: list[str]) -> dict:
    """``score`` with its child ``b`` grouped with ``perf``, and the given orders."""
    return manifest(
        timeline(
            "score",
            children=[timeline("b", length=(4, 1), offset=(0, 1))],
            regions=[{"id": "intro", "start": [0, 1], "end": [1, 1]}],
        ),
        timeline("perf", "seconds", 61.5),
        groups=[group("g", "perf", "score")],
        graphical={"order": {"g": ["score", "perf"], **orders}},
    )


def test_band_orders_at_a_root_and_at_a_descendant() -> None:
    for value in (
        _band_orders(score=DEFAULT_BANDS),
        _band_orders(score=SCORE_BANDS),
        _band_orders(b=B_BANDS),
        _band_orders(score=SCORE_BANDS, b=B_BANDS),
    ):
        assert _problems(value) == []
        validate(value)


@pytest.mark.parametrize(
    "stranger", ["annotations", "region", "score", "score/regions_1", "Regions"]
)
def test_a_band_order_entry_that_is_no_facet(stranger: str) -> None:
    assert _only(_band_orders(score=[*SCORE_BANDS, stranger])) == (
        ("graphical", "order", "score", 6),
        f"'{stranger}' is not 'line' or a facet, in the band order of 'score'",
    )


@pytest.mark.parametrize(
    "order",
    [
        ["markers", "line"],
        ["line", "flow_control"],
        ["line"],
        ["regions", "line"],
        SCORE_BANDS[:-1],
    ],
)
def test_a_band_order_may_leave_out_facets(order: list[str]) -> None:
    value = _band_orders(score=order, b=["line", "children"])
    assert _problems(value) == []
    validate(value)


@pytest.mark.parametrize("order", [["markers", "regions"], []])
def test_a_band_order_missing_its_line(order: list[str]) -> None:
    assert _only(_band_orders(score=order)) == (
        ("graphical", "order", "score"),
        "'line' is missing from the band order of 'score'",
    )


def test_an_order_keyed_by_a_region() -> None:
    assert _only(_band_orders(intro=DEFAULT_BANDS)) == (
        ("graphical", "order", "intro"),
        "'intro' names no group or timeline of this manifest",
    )


def _stamp(identifier: str, line: str, coordinate: object, name: str = "Entry") -> dict:
    return {"id": identifier, "timeline": line, "coordinate": coordinate, "name": name}


def _displayed(display: object) -> dict:
    """A named timestamp on ``score`` at 1 stating ``display``."""
    return {**_stamp("timestamp_1", "score", [1, 1]), "display": display}


def _stamped(*timestamps: dict, **members: object) -> dict:
    """``score`` (8 quarters) with ``verse`` (4 at 2), and named timestamps."""
    root = timeline("score", children=[timeline("verse", length=(4, 1), offset=(2, 1))])
    return manifest(root, graphical={"timestamps": list(timestamps)}, **members)


def test_named_timestamps_lie_on_their_timelines() -> None:
    segments = timeline(
        "form",
        is_segment_line=True,
        children=[
            timeline("a", length=(4, 1), offset=(0, 1)),
            timeline("b", length=(4, 1), offset=(4, 1)),
        ],
    )
    for document in (
        _stamped(
            _stamp("timestamp_1", "score", [0, 1]),
            _stamp("timestamp_2", "score", [8, 1]),
            _stamp("timestamp_3", "verse", [0, 1]),
            _stamp("timestamp_4", "verse", [4, 1]),
            _stamp("timestamp_5", "score", [3, 2], "Climax"),
            _stamp("timestamp_6", "score", [3, 2], "Climax"),
        ),
        manifest(
            timeline("score"),
            segments,
            graphical={"timestamps": [_stamp("timestamp_1", "b", [4, 1])]},
        ),
        manifest(
            timeline("take", "seconds", None),
            graphical={"timestamps": [_stamp("timestamp_1", "take", 1e6)]},
        ),
        manifest(
            timeline("midi", "ticks", 480),
            graphical={"timestamps": [_stamp("timestamp_1", "midi", 480)]},
        ),
    ):
        assert _problems(document) == []
        validate(document)


def test_a_named_timestamp_displays_any_set_of_its_parts() -> None:
    every = ["wedge", "name", "id", "coordinate", "cross_section"]
    for display in ([], ["id"], every, every[::-1]):
        document = _stamped(_displayed(display))
        assert _problems(document) == []
        validate(document)


def test_a_named_timestamp_names_a_timeline() -> None:
    assert _only(_stamped(_stamp("timestamp_1", "ghost", [1, 1]))) == (
        ("graphical", "timestamps", 0, "timeline"),
        "'ghost' names no timeline of this manifest",
    )
    # A group ID is no timeline.
    value = _stamped(_stamp("timestamp_1", "g", [1, 1]), groups=[group("g", "score")])
    assert _only(value) == (
        ("graphical", "timestamps", 0, "timeline"),
        "'g' names no timeline of this manifest",
    )


def test_a_named_timestamp_lies_within_its_timeline() -> None:
    assert _only(_stamped(_stamp("timestamp_1", "score", [17, 2]))) == (
        ("graphical", "timestamps", 0, "coordinate"),
        "coordinate [17, 2] of 'timestamp_1' is beyond the length [8, 1] of its "
        "timeline 'score'",
    )
    assert _problems(_stamped(_stamp("timestamp_1", "score", [16, 2]))) == []
    assert _only(_stamped(_stamp("timestamp_1", "verse", [5, 1]))) == (
        ("graphical", "timestamps", 0, "coordinate"),
        "coordinate [5, 1] of 'timestamp_1' is beyond the length [4, 1] of its "
        "timeline 'verse'",
    )
    assert _only(_stamped(_stamp("timestamp_1", "verse", [-1, 2]))) == (
        ("graphical", "timestamps", 0, "coordinate"),
        "coordinate [-1, 2] of 'timestamp_1' lies before the start of its "
        "timeline 'verse'",
    )
    take = manifest(
        timeline("take", "seconds", 60.0),
        graphical={"timestamps": [_stamp("timestamp_1", "take", 60.5)]},
    )
    assert _only(take) == (
        ("graphical", "timestamps", 0, "coordinate"),
        "coordinate 60.5 of 'timestamp_1' is beyond the length 60.0 of its "
        "timeline 'take'",
    )
    open_ended = manifest(
        timeline("take", "seconds", None),
        graphical={"timestamps": [_stamp("timestamp_1", "take", -0.5)]},
    )
    assert _only(open_ended) == (
        ("graphical", "timestamps", 0, "coordinate"),
        "coordinate -0.5 of 'timestamp_1' lies before the start of its timeline 'take'",
    )


def test_named_timestamp_ids_share_the_manifest_scope() -> None:
    root = timeline("timestamp_1")
    value = manifest(
        root, graphical={"timestamps": [_stamp("timestamp_1", "timestamp_1", [1, 1])]}
    )
    assert _only(value) == (
        ("graphical", "timestamps", 0, "id"),
        "'timestamp_1' is not unique in the manifest, first at #/timelines/0/id",
    )
    value = _stamped(
        _stamp("timestamp_1", "score", [1, 1]), groups=[group("timestamp_1", "score")]
    )
    assert _only(value) == (
        ("graphical", "timestamps", 0, "id"),
        "'timestamp_1' is not unique in the manifest, first at #/groups/0/id",
    )
    value = _stamped(
        _stamp("timestamp_1", "score", [1, 1]), _stamp("timestamp_1", "verse", [1, 1])
    )
    assert _only(value) == (
        ("graphical", "timestamps", 1, "id"),
        "'timestamp_1' is not unique in the manifest, "
        "first at #/graphical/timestamps/0/id",
    )
    value = _stamped(_stamp("timestamp_1", "score", [1, 1]), id="timestamp_1")
    assert _only(value) == (
        ("id",),
        "'timestamp_1' is not unique in the manifest, "
        "first at #/graphical/timestamps/0/id",
    )


def test_a_named_timestamp_takes_any_id() -> None:
    document = _stamped(
        _stamp("timestamp_3kq9x0m2ztb7a", "score", [1, 1]),
        _stamp("Bar 2", "score", [2, 1]),
        _stamp("timestamp_01", "verse", [1, 1]),
    )
    assert _problems(document) == []
    validate(document)


# -- elisions ----------------------------------------------------------------------


def _elision(
    identifier: str, line: str, start: object, end: object, **rest: object
) -> dict:
    return {"id": identifier, "timeline": line, "start": start, "end": end, **rest}


def _elided(*elisions: dict, **members: object) -> dict:
    """``score`` (8 quarters) with ``verse`` (4 at 2), and elisions."""
    root = timeline("score", children=[timeline("verse", length=(4, 1), offset=(2, 1))])
    return manifest(root, graphical={"elisions": list(elisions)}, **members)


def test_overlapping_elisions_are_accepted_without_a_warning() -> None:
    document = _elided(
        _elision("elision_1", "score", [0, 1], [4, 1]),
        _elision("elision_2", "score", [2, 1], [6, 1]),
        _elision("elision_3", "verse", [0, 1], [4, 1]),
        _elision("elision_4", "score", [0, 1], [4, 1], width={"canvas": 12}),
        **{"@context": timetoshare.FORMAT_CONTEXT},
    )
    assert _problems(document) == []
    validate(document)
    assert manifest_warnings(document) == []
    assert unknown_keys(document) == []


def test_elisions_lie_on_their_timelines() -> None:
    segments = timeline(
        "form",
        is_segment_line=True,
        children=[
            timeline("a", length=(4, 1), offset=(0, 1)),
            timeline("b", length=(4, 1), offset=(4, 1)),
        ],
    )
    for document in (
        _elided(_elision("elision_1", "score", [0, 1], [8, 1])),
        manifest(
            timeline("score"),
            segments,
            graphical={"elisions": [_elision("elision_1", "b", [1, 1], [4, 1])]},
        ),
        manifest(
            timeline("take", "quarters", None),
            graphical={"elisions": [_elision("elision_1", "take", [100, 1], [200, 1])]},
        ),
        manifest(
            timeline("take", "seconds", 60.0),
            graphical={"elisions": [_elision("elision_1", "take", 1, 2.5)]},
        ),
    ):
        assert _problems(document) == []
        validate(document)


def test_an_elision_names_a_timeline() -> None:
    assert _only(_elided(_elision("elision_1", "ghost", [1, 1], [3, 1]))) == (
        ("graphical", "elisions", 0, "timeline"),
        "'ghost' names no timeline of this manifest",
    )
    value = _elided(
        _elision("elision_1", "g", [1, 1], [3, 1]), groups=[group("g", "score")]
    )
    assert _only(value) == (
        ("graphical", "elisions", 0, "timeline"),
        "'g' names no timeline of this manifest",
    )


def test_an_elision_lies_in_order_within_its_timeline() -> None:
    assert _only(_elided(_elision("elision_1", "score", [-1, 1], [3, 1]))) == (
        ("graphical", "elisions", 0, "start"),
        "start [-1, 1] of 'elision_1' lies before the start of its timeline 'score'",
    )
    assert _only(_elided(_elision("elision_1", "verse", [1, 1], [5, 1]))) == (
        ("graphical", "elisions", 0, "end"),
        "end [5, 1] of 'elision_1' is beyond the length [4, 1] of its timeline 'verse'",
    )
    assert _only(_elided(_elision("elision_1", "score", [5, 1], [2, 1]))) == (
        ("graphical", "elisions", 0, "end"),
        "end [2, 1] of 'elision_1' does not lie after its start [5, 1]",
    )
    assert _only(_elided(_elision("elision_1", "score", [3, 1], [3, 1]))) == (
        ("graphical", "elisions", 0, "end"),
        "end [3, 1] of 'elision_1' does not lie after its start [3, 1]",
    )
    # The start is reported before anything else of the same elision.
    assert _problems(_elided(_elision("elision_1", "verse", [-1, 1], [-2, 1])))[0] == (
        ("graphical", "elisions", 0, "start"),
        "start [-1, 1] of 'elision_1' lies before the start of its timeline 'verse'",
    )
    open_ended = manifest(
        timeline("take", "quarters", None),
        graphical={"elisions": [_elision("elision_1", "take", [-1, 1], [2, 1])]},
    )
    assert _only(open_ended) == (
        ("graphical", "elisions", 0, "start"),
        "start [-1, 1] of 'elision_1' lies before the start of its timeline 'take'",
    )


def test_elision_ids_share_the_manifest_scope() -> None:
    value = _elided(_elision("timestamp_1", "score", [1, 1], [3, 1]))
    value["graphical"]["timestamps"] = [_stamp("timestamp_1", "score", [1, 1])]
    assert _only(value) == (
        ("graphical", "elisions", 0, "id"),
        "'timestamp_1' is not unique in the manifest, "
        "first at #/graphical/timestamps/0/id",
    )
    value = _elided(_elision("elision_1", "score", [1, 1], [3, 1]), id="elision_1")
    assert _only(value) == (
        ("id",),
        "'elision_1' is not unique in the manifest, first at #/graphical/elisions/0/id",
    )


@pytest.mark.parametrize(
    ("elision", "path", "message"),
    [
        (
            _elision("elision_1", "score", 1.0, [3, 1]),
            ("graphical", "elisions", 0, "start"),
            "start 1.0 of 'elision_1' is a float on a fraction axis: write [1, 1]",
        ),
        (
            _elision("elision_1", "score", [1, 1], [3, 1], width={"span": 2}),
            ("graphical", "elisions", 0, "width", "span"),
            "span 2 of 'elision_1' is an int on a fraction axis: write [2, 1]",
        ),
    ],
)
def test_an_elision_is_read_as_its_timelines_number_type(
    elision: dict, path: tuple, message: str
) -> None:
    with pytest.raises(SchemaValidationError) as caught:
        validate(_elided(elision))
    assert (caught.value.code, caught.value.path, caught.value.message) == (
        "representation",
        path,
        message,
    )


FREE_IDS = {
    "#matchstamp_1": "#matchstamp_3kq9x0m2ztb7a",
    "#matchstamp_2": "#Take 2, downbeat",
    "#anchor_1": "#anchor_00000000000zz",
    "#anchor_2": "#Bar 2",
    "#timestamp_1": "#score at bar 2",
}
"""The IDs of the MatchStamp fixture given free spellings: two as the format
mints them (13 base-36 characters after the prefix), the others with spaces
and a comma."""


def _renamed(value: Any) -> Any:
    """A value in the file form with every reference in ``FREE_IDS`` renamed."""
    if isinstance(value, dict):
        return {key: _renamed(member) for key, member in value.items()}
    if isinstance(value, list):
        return [_renamed(member) for member in value]
    return FREE_IDS.get(value, value) if isinstance(value, str) else value


def test_resources_matchstamps_and_anchors_take_any_id() -> None:
    (path,) = [
        path
        for path in timetoshare.fixture_paths()
        if path.name == "bundle_matchstamps.yaml"
    ]
    value = _renamed(timetoshare.loads(path.read_text("utf-8")))
    value["resources"] = [
        {
            "id": "#MatchClaims of both takes",
            "type": "MatchClaim",
            "timelines": ["#score", "#take_1", "#take_2"],
            "url": "match_claims.parquet",
        },
        {
            "id": "#resource_0a1b2c3d4e5f6",
            "type": "Projection",
            "timelines": ["#take_2"],
            "url": "projections.parquet",
        },
    ]
    assert timetoshare.identity_problems(value) == []
    assert timetoshare.matchstamp_problems(value) == []
    timetoshare.validate(value)


@pytest.mark.parametrize(
    ("timestamp", "path"),
    [
        (
            _stamp("timestamp_1", "score", [1, 1], ""),
            ("graphical", "timestamps", 0, "name"),
        ),
        (
            {**_stamp("timestamp_1", "score", [1, 1]), "name": None},
            ("graphical", "timestamps", 0, "name"),
        ),
        (
            {"id": "timestamp_1", "timeline": "score", "name": "Entry"},
            ("graphical", "timestamps", 0),
        ),
        (_displayed("wedge"), ("graphical", "timestamps", 0, "display")),
        (_displayed(["wedge", "Wedge"]), ("graphical", "timestamps", 0, "display", 1)),
        (_displayed(["line"]), ("graphical", "timestamps", 0, "display", 0)),
        (_displayed([1]), ("graphical", "timestamps", 0, "display", 0)),
        (_displayed(["name", "name"]), ("graphical", "timestamps", 0, "display")),
    ],
    ids=[
        "empty name",
        "null name",
        "no coordinate",
        "display not an array",
        "display word in another case",
        "display part word",
        "display number",
        "display repeated word",
    ],
)
def test_the_schema_shapes_a_named_timestamp(timestamp: dict, path: tuple) -> None:
    with pytest.raises(SchemaValidationError) as caught:
        validate(_stamped(timestamp))
    assert (caught.value.code, caught.value.path) == ("schema", path)


def test_every_step_in_order() -> None:
    jump = {
        "id": "j",
        "type": "jump_from",
        "manifestation": "dal_segno",
        "coordinate": [1, 1],
        "target": "nowhere",
    }
    first = timeline(
        "first",
        flow_control=[jump],
        conversion_maps=[
            _view("bars", "no-measures"),
            _table([[0, 1], [4, 1], [8, 1]], [60, 72]),
        ],
        children=[
            timeline("kid", "seconds", 1.0, offset=(-1, 1)),
            timeline("gone", length=None, offset=(9, 1)),
            timeline("late", offset=(6, 1)),
        ],
    )
    value = manifest(
        first,
        timeline("second", regions=[{"id": "kid", "start": [0, 1], "end": [1, 1]}]),
        timeline("second"),
        id="g2",
        groups=[
            group("first", "ghost", "second"),
            group("g2", "second"),
        ],
        measure_maps=[{"id": "first", "rows": ROWS}],
        graphical={
            "order": {
                "zz": [],
                "kid": [
                    "regions_2",
                    "children",
                    "conversion_maps",
                    "markers",
                    "regions",
                    "flow_control",
                ],
                "g2": ["stranger"],
            },
            "timestamps": [
                _stamp("timestamp_1", "nowhere", [1, 1]),
                _stamp("timestamp_2", "first", [9, 1]),
                _stamp("timestamp_2", "first", [-1, 1]),
            ],
        },
    )
    assert _problems(value) == [
        (
            ("timelines", 0, "flow_control", 0, "target"),
            "'nowhere' names no jump_to of this timeline",
        ),
        (
            ("timelines", 0, "conversion_maps", 0, "measure_map"),
            "'no-measures' names no MeasureMap of this manifest",
        ),
        (
            ("timelines", 0, "conversion_maps", 1, "y_values"),
            "TableMap 'tempo' has 3 x values and 2 y values",
        ),
        (
            ("timelines", 0, "children", 0, "unit"),
            "child 'kid' has unit 'seconds', its parent 'first' has 'quarters'",
        ),
        (
            ("timelines", 0, "children", 1, "offset"),
            "offset [9, 1] of 'gone' is beyond the length [8, 1] of its parent 'first'",
        ),
        (
            ("timelines", 0, "children", 2, "length"),
            "child 'late' ends at [14, 1], beyond the length [8, 1] of its parent "
            "'first'",
        ),
        (
            ("timelines", 1, "regions", 0, "id"),
            "'kid' is not unique in the manifest, first at #/timelines/0/children/0/id",
        ),
        (
            ("timelines", 2, "id"),
            "'second' is not unique in the manifest, first at #/timelines/1/id",
        ),
        (
            ("groups", 0, "id"),
            "'first' is not unique in the manifest, first at #/timelines/0/id",
        ),
        (
            ("measure_maps", 0, "id"),
            "'first' is not unique in the manifest, first at #/timelines/0/id",
        ),
        (
            ("graphical", "timestamps", 2, "id"),
            "'timestamp_2' is not unique in the manifest, "
            "first at #/graphical/timestamps/1/id",
        ),
        (("id",), "'g2' is not unique in the manifest, first at #/groups/1/id"),
        (("groups", 0, "members", 0), "'ghost' names no timeline of this manifest"),
        (("graphical", "order", "g2", 0), "'stranger' is not a member of group 'g2'"),
        (("graphical", "order", "g2"), "member 'second' of group 'g2' is missing"),
        (
            ("graphical", "order", "kid", 0),
            "'regions_2' is not 'line' or a facet, in the band order of 'kid'",
        ),
        (
            ("graphical", "order", "kid"),
            "'line' is missing from the band order of 'kid'",
        ),
        (
            ("graphical", "order", "zz"),
            "'zz' names no group or timeline of this manifest",
        ),
        (
            ("graphical", "timestamps", 0, "timeline"),
            "'nowhere' names no timeline of this manifest",
        ),
        (
            ("graphical", "timestamps", 1, "coordinate"),
            "coordinate [9, 1] of 'timestamp_2' is beyond the length [8, 1] of its "
            "timeline 'first'",
        ),
        (
            ("graphical", "timestamps", 2, "coordinate"),
            "coordinate [-1, 1] of 'timestamp_2' lies before the start of its "
            "timeline 'first'",
        ),
    ]
    assert [problem.code for problem in identity_problems(value)] == [
        *["dangling_target"] * 2,
        "conversion_map",
        "child_unit",
        "child_offset",
        "child_end",
        *["duplicate_id"] * 5,
        "manifest_id",
        "group_member",
        *["display_order"] * 2,
        *["band_order"] * 2,
        "order_key",
        "timestamp_timeline",
        *["timestamp_coordinate"] * 2,
    ]
    with pytest.raises(SchemaValidationError) as caught:
        validate(value)
    assert (caught.value.path, caught.value.message) == _problems(value)[0]
