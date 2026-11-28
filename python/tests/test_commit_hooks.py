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
    release_allows,
    release_problem,
    release_step,
    suggest_header,
    suggest_hints,
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
        "BREAKING CHANGE: removes #sketch"
    )
    assert suggest_trailer(report_of("timeline_removed")) == (
        "BREAKING CHANGE: removes #sketch"
    )
    assert suggest_trailer(report_of("manifest_removed")) == (
        "BREAKING CHANGE: removes sketches.tts.yaml"
    )
    assert suggest_trailer(report_of("region_added")) == ""


MIXED_ID = (
    "This commit mixes 2 kinds of change (1 added, 1 removed); one kind of "
    "change per commit keeps the history and the changelog clear."
)

LABEL = 'Suggested type "label(base):", since this commit changes names only'


@pytest.mark.parametrize(
    ("case", "hints"),
    [
        ("name_changed", [LABEL]),
        (
            "belief_added",
            ['Suggested type "belief(base):", since this commit records beliefs only'],
        ),
        (
            "graphical_rule_changed",
            [
                'Suggested type "graphic(base):", '
                "since this commit changes the drawing only"
            ],
        ),
        (
            "meta_changed",
            [
                'Suggested type "meta(base):", '
                "since this commit changes application data only"
            ],
        ),
        (
            "resource_moved",
            ['Suggested type "move(base):", since this commit moves resources only'],
        ),
        ("id_changed", [MIXED_ID]),
        ("region_added", []),
        ("timeline_removed", []),
        ("id_reused", []),
        ("minimal_to_complete", []),
    ],
)
def test_the_hints(case: str, hints: list[str]) -> None:
    assert suggest_hints(report_of(case)) == hints


def test_the_hints_of_mixed_patch_kinds() -> None:
    assert suggest_hints(patch_report("label", "belief", "label")) == [
        'Suggested type "label(a):", '
        "since this commit changes names, among other changes",
        "This commit mixes 2 kinds of change (1 belief, 2 label); one kind of "
        "change per commit keeps the history and the changelog clear.",
    ]


def test_a_typed_message_keeps_only_the_hint_at_a_mixed_change() -> None:
    assert suggest_hints(report_of("name_changed"), typed=True) == []
    assert suggest_hints(report_of("id_changed"), typed=True) == [MIXED_ID]
    assert suggest_hints(patch_report("label", "belief", "label"), typed=True) == [
        "This commit mixes 2 kinds of change (1 belief, 2 label); one kind of "
        "change per commit keeps the history and the changelog clear."
    ]


def test_an_undetermined_finding_is_no_kind_of_change() -> None:
    report = StepReport.of(
        [
            Finding("label", "patch", "a.yaml", "x", "the name of Timeline #x"),
            Finding("changed_table", "undetermined", "a.yaml", "t", "t.csv changed"),
        ]
    )
    assert suggest_hints(report) == [
        'Suggested type "label(a):", since this commit changes names only'
    ]


RENAMED = (
    "this commit changes the name of Timeline #score; suggested type: label(base):"
)

REMOVAL = (
    "this commit removes #sketch; write remove(...)!: and a BREAKING CHANGE footer"
)

BARE_REMOVE = "remove names a removal; this commit removes nothing"


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
                "base.tts.yaml: #region_1 was a Region and is now a Timeline; "
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
        (
            "name_changed",
            "rename the score",
            [],
            [f"the first line is no Conventional Commits header; {RENAMED}"],
        ),
        ("name_changed", "chore: rename the score", [], [RENAMED]),
        ("name_changed", "docs: rename the score", [], []),
        ("name_changed", "remove(base): rename the score", [], [BARE_REMOVE]),
        ("minimal_to_complete", "remove: tidy the scripts", [], [BARE_REMOVE]),
        (
            "region_added",
            "remove(base): add the second region",
            [
                "this commit adds or edits data (Region #region_2 added); "
                "write feat(...):"
            ],
            [BARE_REMOVE],
        ),
        (
            "region_added",
            "add the second region",
            [
                "the first line is no Conventional Commits header; this commit "
                "adds or edits data (Region #region_2 added); write feat(...):"
            ],
            [],
        ),
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


@pytest.mark.parametrize(
    ("old", "new", "step"),
    [
        ("1.2.3", "2.0.0", "major"),
        ("1.2.3", "1.3.0", "minor"),
        ("1.2.3", "1.2.4", "patch"),
        ("1.9.0", "1.10.0", "minor"),
        ("1.2.3", "1.2.3", "none"),
        ("0.3.0", "0.4.0", "major"),
        ("0.3.0", "0.3.1", "minor"),
        ("0.3.4", "1.0.0", "major"),
        ("0.3.0", "0.3.0", "none"),
    ],
)
def test_the_step_a_release_allows(old: str, new: str, step: str) -> None:
    assert release_step(old, new) == step


@pytest.mark.parametrize(
    ("old", "new", "words"),
    [
        ("0.0.0", "0.1.0", "any change"),
        ("1.2.3", "1.3.0", "changes up to minor"),
        ("1.2.3", "1.2.4", "changes up to patch"),
        ("0.3.0", "0.3.1", "changes up to minor"),
        ("1.2.3", "1.2.3", "no change"),
    ],
)
def test_what_a_release_allows_in_words(old: str, new: str, words: str) -> None:
    assert release_allows(old, new) == words


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("1.2.3", "1.2.2", "the version 1.2.2 is lower than 1.2.3"),
        ("v1.0.0", "1.0.1", "'v1.0.0' is no version MAJOR.MINOR.PATCH"),
        ("1.0.0", "1.0.0-rc.1", "'1.0.0-rc.1' is no version MAJOR.MINOR.PATCH"),
        ("01.0.0", "1.0.1", "'01.0.0' is no version MAJOR.MINOR.PATCH"),
        ("1.0", "1.0.1", "'1.0' is no version MAJOR.MINOR.PATCH"),
    ],
)
def test_a_release_step_refuses(old: str, new: str, message: str) -> None:
    with pytest.raises(ValueError) as raised:
        release_step(old, new)
    assert str(raised.value) == message


def test_the_problem_of_a_release() -> None:
    removal = report_of("timeline_removed")
    addition = report_of("region_added")
    assert removal.step == "major" and addition.step == "minor"
    assert release_problem(removal, "0.3.0", "0.4.0") is None
    assert release_problem(removal, "0.3.0", "0.3.1") == (
        "a release from 0.3.0 to 0.3.1 allows changes up to minor; the change "
        "requires major"
    )
    assert release_problem(addition, "1.0.0", "1.0.0") == (
        "a release from 1.0.0 to 1.0.0 allows no change; the change requires minor"
    )
    assert release_problem(report_of("minimal_to_complete"), "1.0.0", "1.0.0") is None
    assert release_problem(report_of("name_changed"), "1.0.0", "1.0.1") is None


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
    shutil.copy(
        VERSIONS / "region_added" / "old" / "base.tts.yaml", path / "base.tts.yaml"
    )
    git(path, "add", "base.tts.yaml")
    git(path, "commit", "--quiet", "-m", "feat(base): add the score")
    for name, value in environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("PRE_COMMIT_COMMIT_MSG_SOURCE", raising=False)
    monkeypatch.chdir(path)
    return path


def stage(repo: Path, case: str) -> None:
    shutil.copy(VERSIONS / case / "new" / "base.tts.yaml", repo / "base.tts.yaml")
    git(repo, "add", "base.tts.yaml")


def prepared(repo: Path, text: str, *arguments: str) -> tuple[int, str]:
    message = repo.parent / "COMMIT_EDITMSG"
    message.write_text(text, encoding="utf-8")
    status = main(["hook", "prepare-commit-msg", str(message), *arguments])
    return status, message.read_text(encoding="utf-8")


def test_prepare_writes_the_type_before_a_given_subject(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    stage(repo, "region_added")
    assert prepared(repo, "add the second region\n", "message") == (
        0,
        "feat(base): add the second region\n",
    )
    assert capsys.readouterr().err == ""


def test_prepare_writes_a_removal_and_its_footer(repo: Path) -> None:
    stage(repo, "timeline_removed")
    assert prepared(repo, "drop the sketch\n", "message") == (
        0,
        "remove(base)!: drop the sketch\n\nBREAKING CHANGE: removes #sketch\n",
    )


def test_prepare_writes_before_the_comments_of_a_template(repo: Path) -> None:
    stage(repo, "region_added")
    assert prepared(repo, TEMPLATE) == (0, "feat(base): \n" + TEMPLATE)


def test_prepare_suggests_a_patch_type_on_standard_error(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    stage(repo, "name_changed")
    assert prepared(repo, "rename the score\n", "message") == (0, "rename the score\n")
    assert capsys.readouterr().err == f"timetoshare: {LABEL}\n"


@pytest.mark.parametrize("arguments", [(), ("template",)])
def test_prepare_suggests_a_patch_type_as_a_comment(
    repo: Path, capsys: pytest.CaptureFixture, arguments: tuple[str, ...]
) -> None:
    stage(repo, "name_changed")
    assert prepared(repo, TEMPLATE, *arguments) == (
        0,
        f"\n# {LABEL}\n#\n" + TEMPLATE[1:],
    )
    assert capsys.readouterr().err == ""


def test_prepare_comments_with_gits_comment_character(repo: Path) -> None:
    git(repo, "config", "core.commentChar", ";")
    stage(repo, "name_changed")
    template = TEMPLATE.replace("#", ";")
    assert prepared(repo, template) == (0, f"\n; {LABEL}\n;\n" + template[1:])


def test_prepare_hints_at_a_mixed_change_on_standard_error(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    stage(repo, "id_changed")
    assert prepared(repo, "rename the sketch\n", "message") == (
        0,
        "remove(base)!: rename the sketch\n\nBREAKING CHANGE: removes #sketch\n",
    )
    assert capsys.readouterr().err == f"timetoshare: {MIXED_ID}\n"


def test_prepare_hints_at_a_mixed_change_as_a_comment(repo: Path) -> None:
    stage(repo, "id_changed")
    assert prepared(repo, TEMPLATE) == (
        0,
        "remove(base)!: \n\nBREAKING CHANGE: removes #sketch\n\n"
        f"# {MIXED_ID}\n#\n" + TEMPLATE[1:],
    )


@pytest.mark.parametrize(
    ("text", "arguments", "source"),
    [
        ("add the second region\n", ("commit", "HEAD"), None),
        ("add the second region\n", ("merge",), None),
        ("add the second region\n", ("squash",), None),
        ("add the second region\n", (), "commit"),
        ("add the second region\n", (), "merge"),
        ("Merge branch 'sketches'\n", ("message",), None),
    ],
)
def test_prepare_leaves_a_message_alone(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    text: str,
    arguments: tuple[str, ...],
    source: str | None,
) -> None:
    stage(repo, "id_changed")
    if source is not None:
        monkeypatch.setenv("PRE_COMMIT_COMMIT_MSG_SOURCE", source)
    assert prepared(repo, text, *arguments) == (0, text)
    assert capsys.readouterr().err == ""


TYPED = [
    "label(base): name the region\n",
    "data(base): add the second region\n",
    "feat(base):\n",
]


@pytest.mark.parametrize("text", TYPED)
def test_prepare_hints_at_a_mixed_change_of_a_typed_message(
    repo: Path, capsys: pytest.CaptureFixture, text: str
) -> None:
    stage(repo, "id_changed")
    assert prepared(repo, text, "message") == (0, text)
    assert capsys.readouterr().err == f"timetoshare: {MIXED_ID}\n"


def test_prepare_comments_on_a_mixed_change_of_a_typed_template(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    stage(repo, "id_changed")
    template = "label(base): name the region\n" + TEMPLATE
    assert prepared(repo, template) == (
        0,
        f"label(base): name the region\n\n# {MIXED_ID}\n#\n" + TEMPLATE[1:],
    )
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("text", TYPED)
def test_prepare_leaves_a_typed_message_of_one_kind_alone(
    repo: Path, capsys: pytest.CaptureFixture, text: str
) -> None:
    stage(repo, "name_changed")
    assert prepared(repo, text, "message") == (0, text)
    assert prepared(repo, text + TEMPLATE) == (0, text + TEMPLATE)
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("cleanup", ["scissors", "verbatim"])
def test_prepare_suggests_on_standard_error_where_git_keeps_comments(
    repo: Path, capsys: pytest.CaptureFixture, cleanup: str
) -> None:
    git(repo, "config", "commit.cleanup", cleanup)
    stage(repo, "name_changed")
    assert prepared(repo, TEMPLATE) == (0, TEMPLATE)
    assert capsys.readouterr().err == f"timetoshare: {LABEL}\n"


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


def test_commit_msg_warns_on_a_patch_without_a_type(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    stage(repo, "name_changed")
    assert checked(repo, "rename the score\n", capsys) == (
        0,
        "timetoshare: warning: the first line is no Conventional Commits header; "
        f"{RENAMED}\n",
    )
    assert checked(repo, "chore: rename the score\n", capsys) == (
        0,
        f"timetoshare: warning: {RENAMED}\n",
    )


def test_commit_msg_refuses_an_addition_without_a_type(
    repo: Path, capsys: pytest.CaptureFixture
) -> None:
    stage(repo, "region_added")
    assert checked(repo, "add the second region\n", capsys) == (
        1,
        "timetoshare: error: the first line is no Conventional Commits header; "
        "this commit adds or edits data (Region #region_2 added); write feat(...):\n",
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


@pytest.mark.skipif(sys.platform == "win32", reason="git hooks run by sh")
def test_git_commit_of_a_patch_without_a_type(repo: Path) -> None:
    install_hooks(repo)
    stage(repo, "name_changed")
    done = git(repo, "commit", "--quiet", "-m", "rename the score")
    assert done.stderr == (
        f"timetoshare: {LABEL}\n"
        "timetoshare: warning: the first line is no Conventional Commits header; "
        f"{RENAMED}\n"
    )
    assert git(repo, "log", "-1", "--format=%B").stdout == "rename the score\n\n"


@pytest.mark.skipif(sys.platform == "win32", reason="git hooks run by sh")
def test_git_strips_the_suggestion_of_the_editor(repo: Path) -> None:
    install_hooks(repo)
    stage(repo, "name_changed")
    received = repo.parent / "received"
    script = repo.parent / "editor.sh"
    script.write_text(
        f'#!/bin/sh\ncp "$1" "{received}"\n'
        f"{{ printf '%s\\n' 'label(base): rename the score'; cat \"{received}\"; }}"
        ' > "$1"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    done = subprocess.run(
        ["git", "commit", "--quiet"],
        cwd=repo,
        env={**environment(repo.parent), "GIT_EDITOR": str(script)},
        capture_output=True,
        text=True,
    )
    assert (done.returncode, done.stderr) == (0, "")
    assert received.read_text(encoding="utf-8").startswith(
        f"\n# {LABEL}\n#\n# Please enter the commit message for your changes."
    )
    assert git(repo, "log", "-1", "--format=%B").stdout == (
        "label(base): rename the score\n\n"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="git hooks run by sh")
def test_git_keeps_no_suggestion_with_the_scissors_cleanup(repo: Path) -> None:
    install_hooks(repo)
    git(repo, "config", "commit.cleanup", "scissors")
    stage(repo, "name_changed")
    script = repo.parent / "editor.sh"
    script.write_text(
        "#!/bin/sh\n"
        f"{{ printf '%s\\n' 'label(base): rename the score'; cat \"$1\"; }}"
        f' > "{repo.parent / "edited"}"\n'
        f'mv "{repo.parent / "edited"}" "$1"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    done = subprocess.run(
        ["git", "commit", "--quiet"],
        cwd=repo,
        env={**environment(repo.parent), "GIT_EDITOR": str(script)},
        capture_output=True,
        text=True,
    )
    assert (done.returncode, done.stderr) == (0, f"timetoshare: {LABEL}\n")
    assert git(repo, "log", "-1", "--format=%B").stdout == (
        "label(base): rename the score\n\n"
    )


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
    assert "adds or edits data (the manifest base.tts.yaml)" in done.stderr
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
