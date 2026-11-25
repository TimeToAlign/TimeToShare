"""The converter of the earlier form of flow control (see "Flow" in tests/README.md)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from timetoshare import dumps, loads, minimal

from .conftest import manifest, timeline, validate

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPOSITORY_ROOT / "scripts" / "convert_flow_control.py"

_spec = importlib.util.spec_from_file_location("convert_flow_control", SCRIPT)
assert _spec is not None and _spec.loader is not None
converter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(converter)


def earlier(
    identifier: str, kind: str, manifestation: str, at: int, **more: Any
) -> dict:
    return {
        "id": identifier,
        "type": kind,
        "manifestation": manifestation,
        "coordinate": [at, 1],
        **more,
    }


def _converted(*flow: dict, **members: Any) -> tuple[list[dict], list[str], dict]:
    value = manifest(timeline("score", flow_control=list(flow)), **members)
    given = dumps(value)
    result, report = converter.convert(value)
    assert dumps(value) == given
    validate(result)
    return result["timelines"][0]["flow_control"], report, result


def test_each_element_type_becomes_its_role() -> None:
    flow, report, _ = _converted(
        earlier("start", "jump_to", "repeat_start", 1, name="Start"),
        earlier("segno", "jump_to", "segno", 2),
        earlier("again", "jump_from", "repeat_end", 3, target="start", repeat_count=2),
        earlier("once", "jump_from", "repeat_end", 4, label="Repeat", meta={"k": 1}),
        earlier("fine", "flow_marker", "fine", 5, label="Fine"),
        earlier("part", "flow_marker", "section_break", 6),
        earlier("thin", "flow_marker", "double_barline", 6),
        earlier("thick", "flow_marker", "final_barline", 8),
        earlier("ds", "jump_from", "dal_segno_al_fine", 7, target="segno"),
        earlier("dc", "jump_from", "da_capo", 8),
    )
    assert report == []
    assert flow == [
        {
            "id": "start",
            "coordinate": [1, 1],
            "name": "Start",
            "role": "jump_target",
            "manifestation": "repeat_start",
        },
        {
            "id": "segno",
            "coordinate": [2, 1],
            "role": "jump_target",
            "manifestation": "segno",
        },
        {
            "id": "again",
            "coordinate": [3, 1],
            "role": "jump",
            "targets": [
                {"to": "start", "manifestation": "repeat_end", "repeat_count": 2}
            ],
        },
        {
            "id": "once",
            "coordinate": [4, 1],
            "label": "Repeat",
            "meta": {"k": 1},
            "role": "jump",
            "targets": [{"manifestation": "repeat_end", "repeat_count": 1}],
        },
        {
            "id": "fine",
            "coordinate": [5, 1],
            "label": "Fine",
            "role": "break",
            "manifestation": "fine",
            "ends": {"after": {"jump": "ds"}},
        },
        {"id": "part", "coordinate": [6, 1], "role": "section_break"},
        {
            "id": "thin",
            "coordinate": [6, 1],
            "role": "barline",
            "manifestation": "double_barline",
        },
        {
            "id": "thick",
            "coordinate": [8, 1],
            "role": "barline",
            "manifestation": "final_barline",
        },
        {
            "id": "ds",
            "coordinate": [7, 1],
            "role": "jump",
            "targets": [
                {
                    "to": "segno",
                    "manifestation": "dal_segno_al_fine",
                    "repeat_count": 1,
                    "reset": False,
                }
            ],
        },
        {
            "id": "dc",
            "coordinate": [8, 1],
            "role": "jump",
            "targets": [
                {"manifestation": "da_capo", "repeat_count": 1, "reset": False}
            ],
        },
    ]


def test_a_to_coda_waits_for_the_one_jump_al_coda() -> None:
    flow, report, _ = _converted(
        earlier("segno", "jump_to", "segno", 1),
        earlier("leave", "jump_from", "to_coda", 3, target="coda"),
        earlier("ds", "jump_from", "dal_segno_al_coda", 6, target="segno"),
        earlier("coda", "jump_to", "coda", 6),
    )
    assert report == []
    assert flow[1]["targets"] == [
        {"to": "coda", "manifestation": "to_coda", "after": {"jump": "ds"}}
    ]


def test_two_jumps_at_one_coordinate_become_one() -> None:
    address = {"id": "repeat", "part": ["label"]}
    rules = [
        {
            "select": {"addresses": [address, {"id": "ds"}]},
            "set": {"stroke": "#000000"},
        },
    ]
    flow, report, result = _converted(
        earlier("start", "jump_to", "repeat_start", 1),
        earlier("segno", "jump_to", "segno", 2),
        earlier("repeat", "jump_from", "repeat_end", 6, target="start", label="Repeat"),
        earlier(
            "ds",
            "jump_from",
            "dal_segno_al_fine",
            6,
            target="segno",
            label="D.S.",
            name="Leap",
        ),
        earlier("fine", "flow_marker", "fine", 4),
        graphical={"rules": rules},
    )
    assert [entry["id"] for entry in flow] == ["start", "segno", "ds", "fine"]
    assert flow[2] == {
        "id": "ds",
        "coordinate": [6, 1],
        "label": "D.S.",
        "name": "Leap",
        "role": "jump",
        "targets": [
            {
                "to": "segno",
                "manifestation": "dal_segno_al_fine",
                "repeat_count": 1,
                "reset": False,
                "label": "D.S.",
            },
            {
                "to": "start",
                "manifestation": "repeat_end",
                "repeat_count": 1,
                "label": "Repeat",
            },
        ],
    }
    assert flow[3]["ends"] == {"after": {"jump": "ds", "to": "segno"}}
    assert report == [
        "'repeat' and 'ds' of 'score' lie at one coordinate: merged into the jump "
        "'ds' with both destinations"
    ]
    assert result["graphical"]["rules"][0]["select"]["addresses"] == [
        {"id": "ds", "part": ["label"]},
        {"id": "ds"},
    ]


def test_a_merge_reports_what_it_drops() -> None:
    _, report, _ = _converted(
        earlier("a", "jump_from", "repeat_end", 6, target="s"),
        earlier("b", "jump_from", "da_capo", 6, name="Back", meta={"source": "x"}),
        earlier("s", "jump_to", "repeat_start", 1),
    )
    assert report == [
        "'b' and 'a' of 'score' lie at one coordinate: merged into the jump 'a' "
        "with both destinations; the name and meta of 'b' dropped"
    ]


@pytest.mark.parametrize(
    ("flow", "problems"),
    [
        (
            [earlier("fine", "flow_marker", "fine", 4)],
            [
                "the fine 'fine' of 'score' waits for one da capo or dal segno al "
                "fine, and the timeline has none: nothing is guessed"
            ],
        ),
        (
            [
                earlier("fine", "flow_marker", "fine", 4),
                earlier("a", "jump_from", "da_capo_al_fine", 6),
                earlier("b", "jump_from", "da_capo_al_fine", 8),
            ],
            [
                "the fine 'fine' of 'score' waits for one da capo or dal segno al "
                "fine, and the timeline has 2: nothing is guessed"
            ],
        ),
        (
            [
                earlier("coda", "jump_to", "coda", 6),
                earlier("leave", "jump_from", "to_coda", 3, target="coda"),
            ],
            [
                "the to_coda 'leave' of 'score' waits for one da capo or dal segno "
                "al coda, and the timeline has none: nothing is guessed"
            ],
        ),
        (
            [
                earlier("a", "jump_from", "repeat_end", 6),
                earlier("b", "jump_from", "da_capo", 6),
            ],
            [
                "'b' and 'a' of 'score' lie at one coordinate and lead to one "
                "place: one jump cannot hold two destinations at one place"
            ],
        ),
        (
            [earlier("odd", "flow_marker", "segno", 4)],
            [
                "the flow marker 'odd' of 'score' has the manifestation 'segno', "
                "which names no role"
            ],
        ),
    ],
)
def test_nothing_is_guessed(flow: list[dict], problems: list[str]) -> None:
    value = manifest(timeline("score", flow_control=flow))
    with pytest.raises(converter.ConversionRefused) as refused:
        converter.convert(value)
    assert refused.value.problems == problems
    assert isinstance(refused.value, ValueError)


def test_drawing_rules_follow_the_element_types() -> None:
    def rule(**select: Any) -> dict:
        return {"select": select, "set": {"stroke": "#000000"}}

    rules = [
        rule(element="timeline"),
        rule(element="jump_from", domain="logical"),
        rule(element="flow_marker", within="score"),
        rule(inside="jump_from"),
    ]
    value = manifest(timeline("score"), graphical={"rules": rules})
    assert converter.needs_conversion(value)
    result, report = converter.convert(value)
    validate(result)
    assert [entry["select"] for entry in result["graphical"]["rules"]] == [
        {"element": "timeline"},
        {"element": "jump", "domain": "logical"},
        {"element": "break", "within": "score"},
        {"element": "section_break", "within": "score"},
        {"element": "barline", "within": "score"},
        {"inside": "jump"},
    ]
    assert report == [
        "a drawing rule selecting the element type 'flow_marker' became 3 rules, "
        "for 'break', 'section_break' and 'barline'"
    ]


def test_a_converted_manifest_is_left_as_it_is() -> None:
    value = manifest(
        timeline(
            "score",
            flow_control=[{"id": "b", "role": "barline", "coordinate": [1, 1]}],
        )
    )
    assert not converter.needs_conversion(value)
    assert converter.convert(value) == (value, [])
    text = dumps(value)
    assert converter.convert_text(text) == (text, [])


def test_a_file_comes_back_in_the_form_it_was_read_in(tmp_path: Path) -> None:
    flow = [
        earlier("start", "jump_to", "repeat_start", 1, name=None),
        earlier("again", "jump_from", "repeat_end", 3, target="start", repeat_count=1),
    ]
    value = minimal(manifest(timeline("score", flow_control=flow)))
    value = loads(dumps(value))
    path = tmp_path / "score.json"
    path.write_text(dumps(value, serialization="json"), encoding="utf-8")
    checked = subprocess.run(
        [sys.executable, str(SCRIPT), "--check", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (checked.returncode, checked.stdout) == (
        0,
        f"{path}: would be converted\n",
    )
    assert loads(path.read_text(encoding="utf-8")) == value
    done = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (done.returncode, done.stdout) == (0, f"{path}: converted\n")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("{\n")
    written = loads(text)
    assert written["timelines"][0]["flow_control"] == [
        {
            "coordinate": [1, 1],
            "id": "start",
            "manifestation": "repeat_start",
            "role": "jump_target",
        },
        {
            "coordinate": [3, 1],
            "id": "again",
            "role": "jump",
            "targets": [
                {"manifestation": "repeat_end", "repeat_count": 1, "to": "start"}
            ],
        },
    ]
    again = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (again.returncode, again.stdout) == (0, f"{path}: nothing to convert\n")


def test_a_refused_file_is_left_unconverted(tmp_path: Path) -> None:
    value = manifest(
        timeline("score", flow_control=[earlier("fine", "flow_marker", "fine", 4)])
    )
    path = tmp_path / "score.yaml"
    text = dumps(value)
    path.write_text(text, encoding="utf-8")
    refused = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode == 1
    assert refused.stdout == (
        f"{path}: refused: the fine 'fine' of 'score' waits for one da capo or dal "
        "segno al fine, and the timeline has none: nothing is guessed\n"
    )
    assert path.read_text(encoding="utf-8") == text
