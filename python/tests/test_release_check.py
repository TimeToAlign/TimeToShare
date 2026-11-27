"""The release check of a dataset repository: ``timetoshare release-check``."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from timetoshare.cli import main

from .test_version_step import VERSIONS, git, repository, table_manifest, write


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    return repository(tmp_path)


def commit(repo: Path, case: str, side: str, version: str, tag: str = "") -> None:
    """Commit the base manifest of a version case and the version ``version``."""
    shutil.copy(VERSIONS / case / side / "base.yaml", repo / "base.yaml")
    (repo / ".release-please-manifest.json").write_text(
        f'{{".": "{version}"}}\n', encoding="utf-8"
    )
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "--allow-empty", "-m", f"{case} {side}")
    if tag:
        git(repo, "tag", tag)


def checked(
    repo: Path, capsys: pytest.CaptureFixture, summary: Path | None = None
) -> tuple[int, list[str], str]:
    arguments = ["release-check", "--repo", str(repo)]
    if summary is not None:
        arguments += ["--summary", str(summary)]
    status = main(arguments)
    captured = capsys.readouterr()
    return status, captured.out.splitlines(), captured.err


ADDED = "minor\tadded_manifest\tbase.yaml\t-\tthe manifest base.yaml"
REMOVED = "major\tremoved\tbase.yaml\t#sketch\tTimeline #sketch removed"
REGION = "minor\tadded\tbase.yaml\t#region_2\tRegion #region_2 added"


def test_no_tag_and_no_version_only_reports(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    commit(repo, "region_added", "old", "0.0.0")
    assert checked(repo, capsys) == (
        0,
        [
            "no release: the version 0.0.0 is no release",
            "the data from the empty tree to HEAD",
            "step: minor",
            "scope: base",
            ADDED,
        ],
        "",
    )


def test_the_first_release_compares_with_the_empty_tree(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    commit(repo, "region_added", "old", "0.1.0")
    assert checked(repo, capsys) == (
        0,
        [
            "the data from the empty tree to HEAD",
            "step: minor",
            "scope: base",
            "release: 0.1.0 is the first release; it allows any change",
            ADDED,
            "passes",
        ],
        "",
    )


def test_a_tagged_version_only_reports(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    commit(repo, "timeline_removed", "old", "0.1.0", tag="v0.1.0")
    commit(repo, "timeline_removed", "new", "0.1.0")
    assert checked(repo, capsys) == (
        0,
        [
            "no release: the version 0.1.0 is tagged v0.1.0",
            "the data from v0.1.0 to HEAD",
            "step: major",
            "scope: base",
            REMOVED,
        ],
        "",
    )


def test_a_removal_in_a_patch_release_fails(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    commit(repo, "timeline_removed", "old", "0.1.0", tag="v0.1.0")
    commit(repo, "timeline_removed", "new", "0.1.1")
    assert checked(repo, capsys) == (
        2,
        [
            "the data from v0.1.0 to HEAD",
            "step: major",
            "scope: base",
            "release: 0.1.0 to 0.1.1 allows changes up to minor",
            REMOVED,
            "fails: a release from 0.1.0 to 0.1.1 allows changes up to minor; "
            "the change requires major",
        ],
        "",
    )


def test_an_addition_in_a_patch_release_below_one_passes(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    commit(repo, "region_added", "old", "0.1.0", tag="v0.1.0")
    commit(repo, "region_added", "new", "0.1.1")
    assert checked(repo, capsys) == (
        0,
        [
            "the data from v0.1.0 to HEAD",
            "step: minor",
            "scope: base",
            "release: 0.1.0 to 0.1.1 allows changes up to minor",
            REGION,
            "passes",
        ],
        "",
    )


def test_the_last_tag_is_the_nearest_version_tag(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    commit(repo, "region_added", "old", "0.1.0", tag="v0.1.0")
    commit(repo, "region_added", "new", "0.1.0", tag="draft")
    git(repo, "tag", "release-notes")
    assert checked(repo, capsys)[1][:2] == [
        "no release: the version 0.1.0 is tagged v0.1.0",
        "the data from v0.1.0 to HEAD",
    ]


def test_a_reused_id_fails_a_release(repo: Path, capsys: pytest.CaptureFixture) -> None:
    commit(repo, "timeline_removed", "old", "0.1.0", tag="v0.1.0")
    commit(repo, "timeline_removed", "new", "0.2.0", tag="v0.2.0")
    commit(repo, "timeline_removed", "old", "0.2.1")
    status, lines, _ = checked(repo, capsys)
    assert (status, lines[-2:]) == (
        2,
        [
            "refused\treused_id\tbase.yaml\t#sketch\t#sketch was a Timeline in "
            "v0.1.0, is gone in v0.2.0 and is now a Timeline again",
            "fails: a change is refused",
        ],
    )


def undetermined(repo: Path, version: str) -> None:
    """A tag ``v0.1.0`` holding a table of a type that is not compared, and a
    later commit changing its bytes."""
    (repo / ".release-please-manifest.json").write_text(
        '{".": "0.1.0"}\n', encoding="utf-8"
    )
    write(repo / "notes.yaml", table_manifest("Note", "notes.csv"))
    (repo / "notes.csv").write_bytes(b"one")
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", "notes")
    git(repo, "tag", "v0.1.0")
    (repo / "notes.csv").write_bytes(b"two")
    (repo / ".release-please-manifest.json").write_text(
        f'{{".": "{version}"}}\n', encoding="utf-8"
    )
    git(repo, "commit", "--quiet", "-am", "notes changed")


UNDETERMINED = (
    "undetermined\tchanged_table\tnotes.yaml\t#claims\tnotes.csv changed; tables "
    "of the type Note are not compared"
)


def test_an_undetermined_change_fails_a_release(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    undetermined(repo, "0.2.0")
    assert checked(repo, capsys) == (
        2,
        [
            "the data from v0.1.0 to HEAD",
            "step: none",
            "scope: notes",
            "release: 0.1.0 to 0.2.0 allows any change",
            UNDETERMINED,
            "fails: a change is undetermined",
        ],
        "",
    )


def test_an_undetermined_change_outside_a_release_is_reported(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    undetermined(repo, "0.1.0")
    assert checked(repo, capsys) == (
        0,
        [
            "no release: the version 0.1.0 is tagged v0.1.0",
            "the data from v0.1.0 to HEAD",
            "step: none",
            "scope: notes",
            UNDETERMINED,
        ],
        "",
    )


def test_the_summary_holds_the_report_and_the_verdict(
    repo: Path, capsys: pytest.CaptureFixture, tmp_path: Path
) -> None:
    summary = tmp_path / "summary.md"
    summary.write_text("before\n", encoding="utf-8")
    commit(repo, "timeline_removed", "old", "0.1.0", tag="v0.1.0")
    commit(repo, "timeline_removed", "new", "0.1.1")
    status, lines, _ = checked(repo, capsys, summary)
    assert status == 2
    assert summary.read_text(encoding="utf-8") == "\n".join(
        ["before", "### Release 0.1.1: fails", "", "```text", *lines, "```", ""]
    )
    commit(repo, "timeline_removed", "new", "0.0.0")
    git(repo, "tag", "--delete", "v0.1.0")
    summary.write_text("", encoding="utf-8")
    status, lines, _ = checked(repo, capsys, summary)
    assert status == 0
    assert summary.read_text(encoding="utf-8") == "\n".join(
        ["### No release", "", "```text", *lines, "```", ""]
    )


@pytest.mark.parametrize(
    ("content", "error"),
    [
        (
            None,
            ".release-please-manifest.json cannot be read: [Errno 2] No such file "
            "or directory: '{repo}/.release-please-manifest.json'",
        ),
        ('{"sub": "0.1.0"}', '.release-please-manifest.json names no version of "."'),
    ],
)
def test_without_a_version_the_check_fails(
    repo: Path,
    capsys: pytest.CaptureFixture,
    tmp_path: Path,
    content: str | None,
    error: str,
) -> None:
    if content is not None:
        (repo / ".release-please-manifest.json").write_text(content, encoding="utf-8")
    summary = tmp_path / "summary.md"
    message = error.format(repo=repo)
    assert checked(repo, capsys, summary) == (
        1,
        [],
        f"timetoshare release-check: {message}\n",
    )
    assert summary.read_text(encoding="utf-8") == "\n".join(
        ["### Release check: error", "", "```text", f"error: {message}", "```", ""]
    )


def test_a_version_below_the_last_tag_fails(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    commit(repo, "region_added", "old", "0.2.0", tag="v0.2.0")
    commit(repo, "region_added", "new", "0.1.9")
    assert checked(repo, capsys) == (
        1,
        [],
        "timetoshare release-check: the version 0.1.9 is lower than 0.2.0\n",
    )
