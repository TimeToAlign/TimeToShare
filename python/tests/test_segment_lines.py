from __future__ import annotations

import math
from fractions import Fraction
from typing import Any

import pytest

import timetoshare
from timetoshare import SchemaValidationError, child_ends, identity_problems, validate

from .conftest import manifest, timeline

ID = "segment line 'line'"


def _segment(
    identifier: str, offset: Any, length: Any, unit: str = "quarters", **rest: Any
) -> dict:
    return timeline(identifier, unit, length, offset=offset, **rest)


def _line(*segments: dict, length: Any = (8, 1), unit: str = "quarters") -> dict:
    return manifest(
        timeline("line", unit, length, is_segment_line=True, children=list(segments))
    )


def _problems(value: dict) -> list[tuple[tuple[str | int, ...], str]]:
    validate_problems = [(p.path, p.message) for p in identity_problems(value)]
    if not validate_problems:
        validate(value)
    return validate_problems


AT = ("timelines", 0)


@pytest.mark.parametrize(
    "value",
    [
        _line(_segment("a", (0, 1), (3, 1)), _segment("b", (3, 1), (5, 1))),
        _line(length=(0, 1)),
        _line(length=None),
        _line(_segment("b", (3, 1), (5, 1)), _segment("a", (0, 1), (3, 1))),
        _line(
            _segment(
                "a",
                (0, 1),
                (4, 1),
                is_segment_line=True,
                children=[
                    _segment("a1", (0, 1), (1, 1)),
                    _segment("a2", (1, 1), (3, 1)),
                ],
            ),
            _segment(
                "b",
                (4, 1),
                (4, 1),
                is_segment_line=True,
                children=[_segment("b1", (0, 1), (4, 1))],
            ),
        ),
        _line(
            _segment("a", 0.0, 0.5, "seconds"),
            _segment("b", 0.5, 0.25, "seconds"),
            _segment("c", 0.75, 0.25, "seconds"),
            length=1.0,
            unit="seconds",
        ),
    ],
    ids=[
        "two segments",
        "empty of length 0",
        "empty of unknown length",
        "offset order",
        "nested",
        "exact floats",
    ],
)
def test_valid_segment_lines(value: dict) -> None:
    assert _problems(value) == []


def test_each_rule_one_problem() -> None:
    value = _line(_segment("a", (0, 1), (3, 1)), _segment("b", (3, 1), 5, "ticks"))
    assert _problems(value) == [
        (
            (*AT, "children", 1, "unit"),
            "child 'b' has unit 'ticks', its parent 'line' has 'quarters'",
        )
    ]
    value = _line(
        _segment("a", (0, 1), (3, 1)),
        _segment("b", (3, 1), (5, 1), is_segment_line=True),
    )
    assert _problems(value) == [
        (
            (*AT, "children", 1, "is_segment_line"),
            f"segment 'b' of {ID} differs from segment 'a' in is_segment_line",
        ),
        (
            (*AT, "children", 1, "length"),
            "the segments of segment line 'b' do not end at its length",
        ),
    ]
    value = _line(
        _segment("a", (0, 1), (3, 1), is_segment_line=True),
        _segment("b", (3, 1), (5, 1)),
    )
    assert _problems(value)[0] == (
        (*AT, "children", 1),
        f"segment 'b' of {ID} differs from segment 'a' in is_segment_line",
    )
    value = _line(_segment("a", (1, 1), (7, 1)))
    assert _problems(value) == [
        ((*AT, "children", 0, "offset"), f"segment 'a' of {ID} does not start at 0")
    ]
    for offset in ((4, 1), (2, 1)):
        value = _line(
            _segment("a", (0, 1), (3, 1)), _segment("b", offset, (8 - offset[0], 1))
        )
        assert _problems(value) == [
            (
                (*AT, "children", 1, "offset"),
                f"segment 'b' of {ID} does not start where the one before it ends",
            )
        ]
    value = _line(_segment("a", (0, 1), (7, 1)))
    assert _problems(value) == [
        ((*AT, "length"), f"the segments of {ID} do not end at its length")
    ]
    assert _problems(_line()) == [
        ((*AT, "length"), f"the segments of {ID} do not end at its length")
    ]


def test_a_float_line_adds_as_doubles() -> None:
    value = _line(
        _segment("a", 0.0, 0.1, "seconds"),
        _segment("b", 0.1, 0.2, "seconds"),
        _segment("c", 0.3, 0.7, "seconds"),
        length=1.0,
        unit="seconds",
    )
    assert 0.1 + 0.2 == 0.30000000000000004
    assert 0.3 + 0.7 == 1.0
    assert _problems(value) == [
        (
            (*AT, "children", 2, "offset"),
            f"segment 'c' of {ID} does not start where the one before it ends",
        ),
    ]


def test_the_double_sum_decides_where_the_exact_one_differs() -> None:
    # 76.70371459980326 and 855.5289364103584 are doubles whose exact sum exceeds
    # 932.2326510101616 by 3/2^46 while their double sum equals it.
    def with_b(b_offset: Any, b_length: Any, **b_rest: Any) -> dict:
        return _line(
            _segment("a", 0.0, 76.70371459980326, "points"),
            _segment("b", b_offset, b_length, "points", **b_rest),
            _segment("c", 932.2326510101616, 67.7673489898384, "points"),
            length=1000.0,
            unit="points",
        )

    assert 76.70371459980326 + 855.5289364103584 == 932.2326510101616
    assert 932.2326510101616 + 67.7673489898384 == 1000.0
    assert Fraction(76.70371459980326) + Fraction(855.5289364103584) == Fraction(
        932.2326510101616
    ) + Fraction(3, 2**46)
    assert Fraction(932.2326510101616) + Fraction(67.7673489898384) == 1000 - Fraction(
        1, 2**46
    )
    assert _problems(with_b(76.70371459980326, 855.5289364103584)) == []

    assert math.nextafter(76.70371459980326, math.inf) == 76.70371459980328
    assert 76.70371459980328 + 855.5289364103584 == 932.2326510101616
    assert _problems(with_b(76.70371459980328, 855.5289364103584)) == [
        (
            (*AT, "children", 1, "offset"),
            f"segment 'b' of {ID} does not start where the one before it ends",
        ),
    ]

    pairs = {
        76.70371459980326: (5397544070150107, 70368744177664),
        855.5289364103584: (7525312107856185, 8796093022208),
        932.2326510101616: (2050001279156237, 2199023255552),
        67.7673489898384: (4768703244664415, 70368744177664),
    }
    assert all(Fraction(*pair) == Fraction(value) for value, pair in pairs.items())
    exact = _line(
        _segment("a", (0, 1), pairs[76.70371459980326], "points"),
        _segment("b", pairs[76.70371459980326], pairs[855.5289364103584], "points"),
        _segment("c", pairs[932.2326510101616], pairs[67.7673489898384], "points"),
        length=(1000, 1),
        unit="points",
    )
    for node in (exact["timelines"][0], *exact["timelines"][0]["children"]):
        node["number_type"] = "fraction"
    assert _problems(exact) == [
        (
            (*AT, "children", 2, "offset"),
            f"segment 'c' of {ID} does not start where the one before it ends",
        ),
        ((*AT, "length"), f"the segments of {ID} do not end at its length"),
    ]
    mixed = with_b(76.70371459980326, pairs[855.5289364103584], number_type="fraction")
    assert _problems(mixed) == [
        (
            (*AT, "children", 2, "offset"),
            f"segment 'c' of {ID} does not start where the one before it ends",
        ),
    ]


def test_a_segment_without_a_double_sum_ends_at_the_exact_sum() -> None:
    assert math.isinf(1e308 + 1e308)
    overflowing = _line(
        _segment("a", 0.0, 1e308, "points"),
        _segment("b", 1e308, 1e308, "points"),
        _segment("c", 1.7976931348623157e308, 1.0, "points"),
        length=None,
        unit="points",
    )
    assert _problems(overflowing) == [
        (
            (*AT, "children", 2, "offset"),
            f"segment 'c' of {ID} does not start where the one before it ends",
        ),
    ]
    beyond = _line(
        _segment("a", 0.0, 10**400, "points"),
        _segment("b", 10**400, 1.0, "points"),
        length=None,
        unit="points",
    )
    assert list(identity_problems(beyond)) == []
    with pytest.raises(SchemaValidationError) as caught:
        validate(beyond)
    assert caught.value.code == "representation"


@pytest.mark.parametrize(
    "value",
    [
        _line(_segment("a", (0, 1), None), _segment("b", (5, 1), (3, 1))),
        _line(_segment("a", (0, 1), None), _segment("b", (7, 1), (1, 1))),
        _line(_segment("a", (0, 1), (3, 1)), _segment("b", (3, 1), None)),
        _line(
            _segment("a", (0, 1), (3, 1)), _segment("b", (3, 1), (5, 1)), length=None
        ),
        _line(
            _segment("a", (0, 1), (3, 1)), _segment("b", (3, 1), (9, 1)), length=None
        ),
    ],
    ids=[
        "unknown first",
        "unknown first, late successor",
        "unknown last",
        "unknown line",
        "unknown line, long segments",
    ],
)
def test_unknown_lengths_skip_what_needs_them(value: dict) -> None:
    assert _problems(value) == []


def test_an_unknown_line_still_checks_contiguity() -> None:
    value = _line(
        _segment("a", (0, 1), (3, 1)), _segment("b", (4, 1), (4, 1)), length=None
    )
    assert _problems(value) == [
        (
            (*AT, "children", 1, "offset"),
            f"segment 'b' of {ID} does not start where the one before it ends",
        )
    ]


def test_order_and_scope() -> None:
    inner = _segment("d", (5, 1), (1, 1), is_segment_line=True)
    value = _line(
        _segment("a", (0, 1), (3, 1)),
        _segment("b", (3, 1), 1, "ticks"),
        _segment("c", (4, 1), (1, 1), is_segment_line=True),
        inner,
    )
    assert _problems(value) == [
        (
            (*AT, "children", 1, "unit"),
            "child 'b' has unit 'ticks', its parent 'line' has 'quarters'",
        ),
        (
            (*AT, "children", 2, "is_segment_line"),
            f"segment 'c' of {ID} differs from segment 'a' in is_segment_line",
        ),
        (
            (*AT, "children", 3, "is_segment_line"),
            f"segment 'd' of {ID} differs from segment 'a' in is_segment_line",
        ),
        ((*AT, "length"), f"the segments of {ID} do not end at its length"),
        (
            (*AT, "children", 2, "length"),
            "the segments of segment line 'c' do not end at its length",
        ),
        (
            (*AT, "children", 3, "length"),
            "the segments of segment line 'd' do not end at its length",
        ),
    ]


def test_a_timeline_that_is_no_segment_line_is_never_checked() -> None:
    value = manifest(
        timeline("free", children=[timeline("x", offset=(5, 1), length=(1, 1))])
    )
    assert _problems(value) == []


def test_child_ends_is_public_and_adds_floats_as_doubles() -> None:
    assert timetoshare.child_ends is child_ends
    assert "child_ends" in timetoshare.__all__
    line = timeline(
        "line",
        "seconds",
        1.0,
        children=[
            _segment("a", 0.1, 0.2, "seconds"),
            _segment("b", 0.5, 0.25, "seconds"),
            _segment("c", 0.75, None, "seconds"),
        ],
    )
    assert child_ends(line) == [Fraction(0.1 + 0.2), Fraction(3, 4), None]
    assert Fraction(0.1 + 0.2) != Fraction(0.1) + Fraction(0.2)
