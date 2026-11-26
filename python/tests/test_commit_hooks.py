"""The commit types of a dataset repository and the two git hooks."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from timetoshare import Finding, StepReport, tree_step
from timetoshare.cli import AMEND_BASE, main
from timetoshare.commit_types import (
    check_message,
    message_text,
    suggest_header,
    suggest_trailer,
)
from timetoshare.validate import data_root

VERSIONS = data_root() / "fixtures" / "versions"

TEMPLATE = (
    "\n"
    "# Please enter the commit message for your changes. Lines starting\n"
    "# with '#' will be ignored, and an empty message aborts the commit.\n"
)


def report_of(case: str) -> StepReport:
    return tree_step(VERSIONS / case / "old", VERSIONS / case / "new")


@pytest.mark.parametrize(
    ("case", "header"),
    [
        ("timeline_removed", "remove(base)!: "),
        ("region_added", "feat(base): "),
        ("belief_added", "belief(base): "),
        ("name_changed", "label(base): "),
        ("graphical_rule_changed", "graphic(base): "),
        ("elision_removed", "graphic(base): "),
        ("meta_changed", "meta(base): "),
        ("resource_moved", "move(base): "),
        ("manifest_added", "feat(sketches): "),
        ("minimal_to_complete", None),
    ],
)
def test_the_suggested_header(case: str, header: str | None) -> None:
    assert suggest_header(report_of(case)) == header


def patch_report(*kinds: str) -> StepReport:
    return StepReport.of(
        [Finding(kind, "patch", "a.yaml", f"x{i}", "") for i, kind in enumerate(kinds)]
    )


def test_the_patch_type_follows_the_count_then_the_order() -> None:
    assert suggest_header(patch_report("label", "belief")) == "belief(a): "
    assert suggest_header(patch_report("moved", "meta")) == "meta(a): "
    assert suggest_header(patch_report("label", "label", "belief")) == "label(a): "
    assert suggest_header(patch_report("moved", "moved", "graphic")) == "move(a): "


def test_the_trailer() -> None:
    assert suggest_trailer(report_of("id_changed")) == (
        "also: 1 added\n\nBREAKING CHANGE: removes #sketch"
    )
    assert suggest_trailer(report_of("timeline_removed")) == (
        "BREAKING CHANGE: removes #sketch"
    )
    assert suggest_trailer(report_of("manifest_removed")) == (
        "BREAKING CHANGE: removes sketches.yaml"
    )
    assert suggest_trailer(report_of("region_added")) == ""


REMOVAL = (
    "this commit removes #sketch; write remove(...)!: and a BREAKING CHANGE footer"
)


@pytest.mark.parametrize(
    ("case", "message", "errors", "warnings"),
    [
        (
            "region_added",
            "label(base): name the development",
            [
                "this commit adds or edits data (Region #region_2 added); "
                "write feat(...):"
            ],
            [],
        ),
        ("timeline_removed", "feat(base): drop the sketch", [REMOVAL], []),
        (
            "timeline_removed",
            "remove(base): drop the sketch",
            ["remove requires '!': write remove(...)!:", REMOVAL],
            [],
        ),
        (
            "timeline_removed",
            "remove(base)!: drop the sketch",
            [],
            ["the BREAKING CHANGE footer does not name #sketch"],
        ),
        (
            "timeline_removed",
            "remove(base)!: drop the sketch\n\nBREAKING CHANGE: removes #sketch\n"
            "# a comment line naming nothing",
            [],
            [],
        ),
        (
            "timeline_removed",
            "drop the sketch",
            [f"the first line is no Conventional Commits header; {REMOVAL}"],
            [],
        ),
        (
            "id_reused",
            "remove(base)!: drop the sketch\n\nBREAKING CHANGE: removes #sketch",
            [
                "base.yaml: #region_1 was a Region and is now a Timeline; "
                "an ID is never reused"
            ],
            [],
        ),
        (
            "belief_added",
            "feat(base): record a doubt",
            [],
            ["feat declares a minor step; the staged change requires patch"],
        ),
        ("belief_added", "belief(base): record a doubt", [], []),
        ("minimal_to_complete", "docs: explain the sources", [], []),
        ("minimal_to_complete", "chore: tidy the scripts", [], []),
        ("timeline_removed", "Merge branch 'sketches'", [], []),
        ("timeline_removed", "fixup! feat(base): add", [], []),
        ("timeline_removed", "squash! feat(base): add", [], []),
        ("timeline_removed", "amend! feat(base): add", [], []),
        ("timeline_removed", 'Revert "feat(base): add"', [], []),
        ("timeline_removed", "revert: feat(base): add", [], []),
        (
            "timeline_removed",
            "feat(base)!: drop the sketch",
            [REMOVAL],
            ["the BREAKING CHANGE footer does not name #sketch"],
        ),
        (
            "timeline_removed",
            "fix(base)!: drop the sketch\n\nBREAKING CHANGE: removes #sketch",
            [REMOVAL],
            [],
        ),
        ("timeline_removed", "feature(base): drop the sketch", [REMOVAL], []),
        (
            "region_added",
            "feat(base)!: add the second region",
            [],
            ["feat! declares a major step; the staged change requires minor"],
        ),
        (
            "minimal_to_complete",
            "fix(base)!: rewrite the loader",
            [],
            ["fix! declares a major step; the staged change requires none"],
        ),
        ("region_added", "feature(base): add the second region", [], []),
        (
            "region_added",
            "feat(base): add the second region\n\nBREAKING CHANGE: removes nothing",
            [],
            [
                "the BREAKING CHANGE footer makes a major release; this commit "
                "removes nothing"
            ],
        ),
        (
            "name_changed",
            "label(base): \n",
            ['write what the commit does after "label(base): "'],
            [],
        ),
        (
            "name_changed",
            "label(base):",
            ['write what the commit does after "label(base): "'],
            [],
        ),
        (
            "timeline_removed",
            "remove(base)!:\n\nBREAKING CHANGE: removes #sketch",
            ['write what the commit does after "remove(base)!: "'],
            [],
        ),
    ],
)
def test_the_check(
    case: str, message: str, errors: list[str], warnings: list[str]
) -> None:
    assert check_message(message, report_of(case)) == (errors, warnings)


def test_the_comment_character_is_gits() -> None:
    message = (
        "label(base): name the score\n"
        "; feat(base): a comment line\n"
        "#3 is the score's number\n"
        "; ------------------------ >8 ------------------------\n"
        "label(base): below the scissors\n"
    )
    assert check_message(message, report_of("name_changed"), ";") == ([], [])
    assert message_text(message, ";") == (
        "label(base): name the score\n#3 is the score's number"
    )


def test_an_undetermined_change_warns() -> None:
    report = StepReport.of(
        [Finding("changed_table", "undetermined", "a.yaml", "t", "t.csv changed")]
    )
    assert check_message("feat(a): add", report) == (
        [],
        [
            "a.yaml: t.csv changed",
            "feat declares a minor step; the staged change requires none",
        ],
    )


# The hooks -----------------------------------------------------------------


def environment(home: Path) -> dict[str, str]:
    """An environment for git with no global or system configuration."""
    return {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.org",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.org",
        "HOME": str(home),
    }


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=environment(repo.parent),
        capture_output=True,
        text=True,
        check=check,
    )


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository whose one commit holds the base manifest, as the current
    directory."""
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "--quiet")
    shutil.copy(VERSIONS / "region_added" / "old" / "base.yaml", path / "base.yaml")
    git(path, "add", "base.yaml")
    git(path, "commit", "--quiet", "-m", "feat(base): add the score")
    for name, value in environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("PRE_COMMIT_COMMIT_MSG_SOURCE", raising=False)
    monkeypatch.chdir(path)
    return path


def stage(repo: Path, case: str) -> None:
    shutil.copy(VERSIONS / case / "new" / "base.yaml", repo / "base.yaml")
    git(repo, "add", "base.yaml")


def prepared(repo: Path, text: str, *arguments: str) -> tuple[int, str]:
    message = repo.parent / "COMMIT_EDITMSG"
    message.write_text(text, encoding="utf-8")
    status = main(["hook", "prepare-commit-msg", str(message), *arguments])
    return status, message.read_text(encoding="utf-8")


def test_prepare_writes_the_type_before_a_given_subject(repo: Path) -> None:
    stage(repo, "region_added")
    assert prepared(repo, "add the second region\n", "message") == (
        0,
        "feat(base): add the second region\n",
    )


def test_prepare_writes_a_removal_and_its_footer(repo: Path) -> None:
    stage(repo, "timeline_removed")
    assert prepared(repo, "drop the sketch\n", "message") == (
        0,
        "remove(base)!: drop the sketch\n\nBREAKING CHANGE: removes #sketch\n",
    )


def test_prepare_writes_before_the_comments_of_a_template(repo: Path) -> None:
    stage(repo, "region_added")
    assert prepared(repo, TEMPLATE) == (0, "feat(base): \n" + TEMPLATE)


@pytest.mark.parametrize(
    ("text", "arguments", "source"),
    [
        ("add the second region\n", ("commit", "HEAD"), None),
        ("add the second region\n", ("merge",), None),
        ("add the second region\n", ("squash",), None),
        ("add the second region\n", (), "commit"),
        ("add the second region\n", (), "merge"),
        ("label(base): name the region\n", ("message",), None),
        ("data(base): add the second region\n", ("message",), None),
        ("feat(base):\n", ("message",), None),
        ("Merge branch 'sketches'\n", ("message",), None),
    ],
)
def test_prepare_leaves_a_message_alone(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    text: str,
    arguments: tuple[str, ...],
    source: str | None,
) -> None:
    stage(repo, "region_added")
    if source is not None:
        monkeypatch.setenv("PRE_COMMIT_COMMIT_MSG_SOURCE", source)
    assert prepared(repo, text, *arguments) == (0, text)


def test_prepare_leaves_a_change_without_data_alone(repo: Path) -> None:
    (repo / "README.md").write_text("A dataset.\n", encoding="utf-8")
    git(repo, "add", "README.md")
    assert prepared(repo, "describe the dataset\n", "message") == (
        0,
        "describe the dataset\n",
    )


def checked(repo: Path, text: str, capsys: pytest.CaptureFixture) -> tuple[int, str]:
    message = repo.parent / "COMMIT_EDITMSG"
    message.write_text(text, encoding="utf-8")
    status = main(["hook", "commit-msg", str(message)])
    return status, capsys.readouterr().err


def test_commit_msg_refuses_an_understated_type(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    stage(repo, "timeline_removed")
    assert checked(repo, "feat(base): drop the sketch\n", capsys) == (
        1,
        f"timetoshare: error: {REMOVAL}\n",
    )


def test_commit_msg_accepts_the_written_type(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    stage(repo, "timeline_removed")
    text = (
        "remove(base)!: drop the sketch\n\nBREAKING CHANGE: removes #sketch\n"
        + TEMPLATE
    )
    assert checked(repo, text, capsys) == (0, "")


def install_hooks(repo: Path) -> None:
    for hook in ("prepare-commit-msg", "commit-msg"):
        script = repo / ".git" / "hooks" / hook
        script.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" -m timetoshare.cli hook {hook} "$@"\n',
            encoding="utf-8",
        )
        script.chmod(0o755)


@pytest.mark.skipif(sys.platform == "win32", reason="git hooks run by sh")
def test_git_commit_through_the_hooks(repo: Path) -> None:
    install_hooks(repo)
    stage(repo, "region_added")
    git(repo, "commit", "--quiet", "-m", "add the second region")
    assert git(repo, "log", "-1", "--format=%B").stdout == (
        "feat(base): add the second region\n\n"
    )
    stage(repo, "timeline_removed")
    done = git(repo, "commit", "--quiet", "-m", "label(base): rename", check=False)
    assert done.returncode == 1
    assert git(repo, "rev-list", "--count", "HEAD").stdout == "2\n"


def test_prepare_writes_before_comments_of_gits_comment_character(repo: Path) -> None:
    git(repo, "config", "core.commentChar", ";")
    stage(repo, "region_added")
    template = TEMPLATE.replace("#", ";")
    assert prepared(repo, template) == (0, "feat(base): \n" + template)


def editor(repo: Path, text: str) -> str:
    """A GIT_EDITOR that replaces the message with ``text``."""
    script = repo.parent / "editor.sh"
    script.write_text(f"#!/bin/sh\nprintf '%s' '{text}' > \"$1\"\n", encoding="utf-8")
    script.chmod(0o755)
    return str(script)


@pytest.mark.skipif(sys.platform == "win32", reason="git hooks run by sh")
def test_an_amend_is_judged_against_the_amended_commits_parent(repo: Path) -> None:
    install_hooks(repo)
    stage(repo, "timeline_removed")
    message = "remove(base)!: drop the sketch\n\nBREAKING CHANGE: removes #sketch\n"
    git(repo, "commit", "--quiet", "-m", message)
    removal = git(repo, "rev-parse", "HEAD").stdout
    base_file = Path(git(repo, "rev-parse", "--absolute-git-dir").stdout.strip())
    base_file = base_file / AMEND_BASE
    done = subprocess.run(
        ["git", "commit", "--amend", "--quiet"],
        cwd=repo,
        env={**environment(repo.parent), "GIT_EDITOR": editor(repo, "label(base): x")},
        capture_output=True,
        text=True,
    )
    assert done.returncode == 1
    assert "this commit removes #sketch" in done.stderr
    assert git(repo, "rev-parse", "HEAD").stdout == removal
    assert not base_file.exists()
    git(repo, "commit", "--amend", "--quiet", "--no-edit")
    assert git(repo, "log", "-1", "--format=%B").stdout == message + "\n"
    assert git(repo, "rev-list", "--count", "HEAD").stdout == "2\n"
    assert not base_file.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="git hooks run by sh")
def test_amending_a_root_commit_compares_with_the_empty_tree(repo: Path) -> None:
    install_hooks(repo)
    done = subprocess.run(
        ["git", "commit", "--amend", "--quiet"],
        cwd=repo,
        env={**environment(repo.parent), "GIT_EDITOR": editor(repo, "docs: x")},
        capture_output=True,
        text=True,
    )
    assert done.returncode == 1
    assert "adds or edits data (the manifest base.yaml)" in done.stderr
    git(repo, "commit", "--amend", "--quiet", "--no-edit")
    assert git(repo, "log", "-1", "--format=%s").stdout == (
        "feat(base): add the score\n"
    )


def test_pre_commits_source_and_commit_record_an_amend(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    stage(repo, "timeline_removed")
    git(repo, "commit", "--quiet", "-m", "remove(base)!: drop the sketch")
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    monkeypatch.setenv("PRE_COMMIT_COMMIT_MSG_SOURCE", "commit")
    monkeypatch.setenv("PRE_COMMIT_COMMIT_OBJECT_NAME", "HEAD")
    text = "label(base): rename\n"
    assert prepared(repo, text) == (0, text)
    assert (repo / ".git" / AMEND_BASE).read_text(encoding="utf-8") == head + "\n"
    assert checked(repo, text, capsys) == (1, f"timetoshare: error: {REMOVAL}\n")
    assert not (repo / ".git" / AMEND_BASE).exists()
    assert checked(repo, text, capsys) == (
        0,
        "timetoshare: warning: label declares a patch step; the staged change "
        "requires none\n",
    )
