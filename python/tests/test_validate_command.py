"""The ``timetoshare validate`` command and the repository's pre-commit hooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from timetoshare import dumps, loads
from timetoshare.cli import _parser, main
from timetoshare.validate import data_root

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BASE = data_root() / "fixtures" / "versions" / "region_added" / "old" / "base.yaml"

WITHOUT_CONTEXT = {
    "timetoshare": "0.2.0",
    "timelines": [{"id": "#dlt_1", "length": 8, "unit": "ticks"}],
}


def base() -> dict[str, Any]:
    return loads(BASE.read_text(encoding="utf-8"))


def written(directory: Path, name: str, value: Any) -> str:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    serialization = "json" if path.suffix == ".json" else "yaml"
    path.write_text(dumps(value, serialization), encoding="utf-8")
    return str(path)


def validated(capsys: pytest.CaptureFixture, *paths: str) -> tuple[int, list[str], str]:
    status = main(["validate", *paths])
    captured = capsys.readouterr()
    return status, captured.out.splitlines(), captured.err


def test_a_valid_manifest_prints_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    path = written(tmp_path, "base.yaml", base())
    assert validated(capsys, path) == (0, [], "")


def test_a_warning_is_printed_and_accepted(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    path = written(tmp_path, "plain.yaml", WITHOUT_CONTEXT)
    assert validated(capsys, path) == (
        0,
        [
            f"{Path(path).as_posix()}: warning: context_absent at #: the manifest "
            "has no @context"
        ],
        "",
    )


def duplicated() -> dict[str, Any]:
    value = base()
    value["timelines"].append(value["timelines"][0])
    return value


@pytest.mark.parametrize(
    ("name", "value", "line"),
    [
        (
            "untimed.yaml",
            {"timetoshare": "0.2.0"},
            "schema at #: 'timelines' is a required property",
        ),
        (
            "twice.json",
            "duplicated",
            "duplicate_id at #/timelines/1/id: 'score' is not unique in the "
            "manifest, first at #/timelines/0/id",
        ),
        (
            "earlier.json",
            {"timetoshare": "0.1.0", "timelines": []},
            "unsupported_version at #/timetoshare: unsupported TimeToShare version "
            '"0.1.0"; this package reads 0.2.0 only',
        ),
    ],
)
def test_a_refused_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture, name: str, value: Any, line: str
) -> None:
    path = written(tmp_path, name, duplicated() if value == "duplicated" else value)
    assert validated(capsys, path) == (1, [f"{Path(path).as_posix()}: {line}"], "")


@pytest.mark.parametrize(
    ("name", "content", "line"),
    [
        (
            "anchored.yaml",
            b'timetoshare: &v "0.2.0"\ntimelines: []\n',
            "unreadable at #: an anchor is not read at line 1, column 14",
        ),
        (
            "broken.yaml",
            b"timetoshare: [\n",
            "unreadable at #: while parsing a flow node, expected the node "
            "content, but found '<stream end>' at line 2, column 1",
        ),
        (
            "latin.yaml",
            b'timetoshare: "\xe9"\n',
            "unreadable at #: 'utf-8' codec can't decode byte 0xe9 in position 14: "
            "invalid continuation byte",
        ),
    ],
)
def test_an_unreadable_file_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture, name: str, content: bytes, line: str
) -> None:
    path = tmp_path / name
    path.write_bytes(content)
    assert validated(capsys, str(path)) == (1, [f"{path.as_posix()}: {line}"], "")


def test_files_that_are_no_manifests_are_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    (tmp_path / "settings.yaml").write_text("name: x\n", encoding="utf-8")
    (tmp_path / "list.json").write_text("[1, 2]\n", encoding="utf-8")
    (tmp_path / "workflow.yml").write_text("a: &x 1\nb: *x\n", encoding="utf-8")
    paths = [str(tmp_path / n) for n in ("settings.yaml", "list.json", "workflow.yml")]
    assert validated(capsys, *paths) == (0, [], "")


def test_without_arguments_every_file_under_the_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    written(tmp_path, "b.yml", {"timetoshare": "0.2.0"})
    written(tmp_path, "a/base.json", base())
    written(tmp_path, "a/plain.yaml", WITHOUT_CONTEXT)
    written(tmp_path, ".git/refused.yaml", {"timetoshare": "0.2.0"})
    written(tmp_path, "notes.txt", {"timetoshare": "0.2.0"})
    monkeypatch.chdir(tmp_path)
    assert validated(capsys) == (
        1,
        [
            "a/plain.yaml: warning: context_absent at #: the manifest has no @context",
            "b.yml: schema at #: 'timelines' is a required property",
        ],
        "",
    )


def test_the_hooks_of_the_repository() -> None:
    manifest = yaml.safe_load(
        (REPOSITORY_ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
    )
    common = {"language": "python", "additional_dependencies": ["./python[tables]"]}
    assert [
        {key: hook.get(key) for key in ("id", "entry", "stages", "always_run", "files")}
        for hook in manifest
    ] == [
        {
            "id": "timetoshare-commit-type",
            "entry": "timetoshare hook prepare-commit-msg",
            "stages": ["prepare-commit-msg"],
            "always_run": True,
            "files": None,
        },
        {
            "id": "timetoshare-commit-check",
            "entry": "timetoshare hook commit-msg",
            "stages": ["commit-msg"],
            "always_run": True,
            "files": None,
        },
        {
            "id": "timetoshare-validate",
            "entry": "timetoshare validate",
            "stages": ["pre-commit"],
            "always_run": None,
            "files": r"\.(ya?ml|json)$",
        },
    ]
    for hook in manifest:
        assert {key: hook[key] for key in common} == common
        assert hook["pass_filenames"] is True
        command, *arguments = hook["entry"].split()
        assert command == "timetoshare"
        parsed = _parser().parse_args([*arguments, "MSGFILE"])
        assert parsed.run.__name__ in ("_prepare", "_check", "_validate")
