from __future__ import annotations

import hashlib
import importlib.util
import json
from fractions import Fraction
from pathlib import Path

import pytest

from timetoshare import FONT_FILES, dumps, font_metrics, font_paths

TEXT_SHA256 = "7da195a74c55bef988d0d48f9508bd5d849425c1770dba5d7bfc6ce9ed848954"
MUSIC_SHA256 = "26c0a28d7c6f96c70f1401db23066c5ea0ee1cdf155c79bc01ad2efb040de816"
METRICS_FILE = "dejavu-sans-2.37+noto-music-2.004.metrics.json"
SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "extract_font_metrics.py"


def _metrics_path() -> Path:
    return font_paths()[0].parent / METRICS_FILE


def test_the_fonts_are_the_release_files_with_their_licences() -> None:
    assert FONT_FILES == ("DejaVuSans.ttf", "NotoMusic-Regular.ttf")
    text, music = font_paths()
    assert (text.name, music.name) == FONT_FILES
    assert hashlib.sha256(text.read_bytes()).hexdigest() == TEXT_SHA256
    assert hashlib.sha256(music.read_bytes()).hexdigest() == MUSIC_SHA256
    assert (text.parent / "DejaVuSans-LICENSE").is_file()
    assert (music.parent / "NotoMusic-LICENSE").is_file()


def test_the_metrics_hold_the_stated_values() -> None:
    metrics = font_metrics()
    assert list(metrics) == [
        "advances",
        "ascender",
        "descender",
        "fallback",
        "units_per_em",
    ]
    assert metrics["units_per_em"] == 2048
    assert metrics["ascender"] == 1901
    assert metrics["descender"] == 483
    assert metrics["fallback"] == 1229
    advances = metrics["advances"]
    assert len(advances) == 6467
    assert list(advances) == sorted(advances)
    assert advances["9833"] == 966
    assert advances["48"] == 1303
    assert advances["32"] == 651
    assert advances["119133"] == 1053
    assert advances["119070"] == 1456
    assert advances["119135"] == 819
    assert advances["118784"] == 973
    assert advances["119296"] == 1810


def test_the_metrics_merge_both_fonts_by_the_stated_rule() -> None:
    ttlib = pytest.importorskip("fontTools.ttLib")
    text, music = (ttlib.TTFont(path) for path in font_paths())
    text_cmap, music_cmap = text.getBestCmap(), music.getBestCmap()
    music_units_per_em = music["head"].unitsPerEm
    assert music_units_per_em == 1000
    advances = {int(key): value for key, value in font_metrics()["advances"].items()}
    text_advances = {c: a for c, a in advances.items() if c in text_cmap}
    music_advances = {c: a for c, a in advances.items() if c not in text_cmap}
    assert text_advances == {
        c: text["hmtx"][glyph][0] for c, glyph in text_cmap.items()
    }
    assert min(advances) == 0x20
    expected = {}
    for code_point, glyph in music_cmap.items():
        if code_point >= 0x20 and code_point not in text_cmap:
            scaled = Fraction(music["hmtx"][glyph][0] * 2048, 1000)
            assert scaled - int(scaled) != Fraction(1, 2)
            expected[code_point] = int(scaled + Fraction(1, 2))
    assert len(expected) == 549
    assert music_advances == expected


def test_the_metrics_file_is_written_by_dumps() -> None:
    text = _metrics_path().read_text(encoding="utf-8")
    assert dumps(json.loads(text)) == text


def test_font_accessors_work_from_any_working_directory(tmp_path, monkeypatch) -> None:
    expected_paths = font_paths()
    monkeypatch.chdir(tmp_path)
    assert font_paths() == expected_paths
    assert all(path.is_file() for path in font_paths())
    assert font_metrics()["units_per_em"] == 2048


def _script():
    pytest.importorskip("fontTools")
    spec = importlib.util.spec_from_file_location("extract_font_metrics", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_extraction_reproduces_the_metrics_file() -> None:
    script = _script()
    assert dumps(script.metrics(*font_paths())) == _metrics_path().read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("altered_index", "expected"), [(0, TEXT_SHA256), (1, MUSIC_SHA256)]
)
def test_the_extraction_refuses_another_file(
    tmp_path, altered_index: int, expected: str
) -> None:
    script = _script()
    paths = list(font_paths())
    altered = tmp_path / FONT_FILES[altered_index]
    altered.write_bytes(paths[altered_index].read_bytes() + b"\0")
    paths[altered_index] = altered
    digest = hashlib.sha256(altered.read_bytes()).hexdigest()
    with pytest.raises(SystemExit) as caught:
        script.metrics(*paths)
    assert str(caught.value) == f"{altered}: SHA-256 {digest}, expected {expected}"
