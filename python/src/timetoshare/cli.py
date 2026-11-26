"""The ``timetoshare`` command: validation, the version step of a change, two hooks.

``timetoshare validate [PATH ...]`` validates manifest files: the files
named, or every ``.yaml``, ``.yml`` and ``.json`` file under the current
directory outside ``.git``. A file that is no manifest is skipped.

``timetoshare step OLD [NEW]`` prints the step a change of a repository of
manifests requires: OLD and NEW are two directories, or two git references
of the repository ``--repo`` (NEW left out: the staged changes; OLD ``-``:
the empty tree, for a repository without a release). With ``--history``
(git references only) it also reports every ID of NEW that a tag reachable
from NEW or OLD held for an element that is gone since or of another type:
the check a release pull request's job runs. ``--require-version FROM TO``
also refuses the change where a release from version FROM to TO carries a
lower step than it requires.

``timetoshare hook prepare-commit-msg MSGFILE [SOURCE [SHA]]`` writes the
commit type the staged change requires in front of the message, and
``timetoshare hook commit-msg MSGFILE`` checks the final message against
the staged change. Both run as git hooks directly or through pre-commit,
which hands over the message file as the one file name, the source of the
message in ``PRE_COMMIT_COMMIT_MSG_SOURCE`` and its commit in
``PRE_COMMIT_COMMIT_OBJECT_NAME``. When the source is ``commit`` and the
commit names ``HEAD`` (``git commit --amend`` with the editor or
``--no-edit``, for which git hands over ``commit HEAD``), the first hook
records it in the file ``timetoshare-amend-base`` of the git directory, and
the second compares the amended commit's parent, not ``HEAD``, with the
index. ``git commit --amend -m`` hands over the source ``message`` and is
compared with ``HEAD``; ``git commit -c HEAD`` and ``-C HEAD`` hand over
what an amend does and are taken for one.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

from .commit_types import (
    _SKIPPED,
    check_message,
    message_text,
    parse_header,
    release_problem,
    release_step,
    suggest_header,
    suggest_trailer,
)
from .serialization import dumps, loads
from .validate import (
    SchemaValidationError,
    UnsupportedVersionError,
    json_pointer,
    manifest_warnings,
)
from .version_step import StepReport, git_step, tree_step

__all__ = ["main"]

_UNTOUCHED_SOURCES = ("merge", "squash", "commit")
"""Sources of a message the first hook leaves alone: merges, squashes, amends."""

AMEND_BASE = "timetoshare-amend-base"
"""The file in the git directory naming the commit an amend replaces."""

EMPTY_TREE = "-"
"""The OLD argument of ``timetoshare step`` that names the empty tree."""

_SERIALIZED = (".yaml", ".yml", ".json")
"""The file extensions ``timetoshare validate`` reads without arguments."""


def _empty_tree(repo: Path) -> str:
    """The name of the empty tree in the object format of ``repo``."""
    done = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "-t", "tree", "--stdin"],
        capture_output=True,
        input=b"",
    )
    if done.returncode:
        raise ValueError(done.stderr.decode(errors="replace").strip())
    return done.stdout.decode().strip()


def _report(old: str, new: str | None, repo: Path, history: bool) -> StepReport:
    if old == EMPTY_TREE and not (new is not None and Path(new).is_dir()):
        return git_step(_empty_tree(repo), new, repo, history=history)
    if Path(old).is_dir() and new is not None and Path(new).is_dir():
        if history:
            raise ValueError("--history compares git references, not directories")
        return tree_step(Path(old), Path(new))
    if Path(old).is_dir() or (new is not None and Path(new).is_dir()):
        raise ValueError("OLD and NEW are both directories or both git references")
    return git_step(old, new, repo, history=history)


def _step(arguments: argparse.Namespace) -> int:
    release = arguments.require_version
    try:
        carried = release_step(*release) if release else None
        report = _report(
            arguments.old, arguments.new, Path(arguments.repo), arguments.history
        )
    except ValueError as error:
        print(f"timetoshare step: {error}", file=sys.stderr)
        return 1
    problem = release_problem(report, *release) if release else None
    if arguments.json:
        written = report.to_dict()
        if release:
            written["release"] = {
                "from": release[0],
                "to": release[1],
                "carries": carried,
            }
        sys.stdout.write(dumps(written, "json"))
    else:
        print(f"step: {report.step}")
        print(f"scope: {report.scope or '-'}")
        if release:
            print(f"release: {release[0]} to {release[1]} carries {carried}")
        for f in report.findings:
            cited = f"#{f.id}" if f.id is not None else "-"
            print(f"{f.step}\t{f.kind}\t{f.path}\t{cited}\t{f.detail}")
    if problem is not None:
        print(f"timetoshare step: {problem}", file=sys.stderr)
    return 2 if report.refused or problem is not None else 0


def _readable_elsewhere(text: str) -> bool | None:
    """Whether a text ``loads`` refuses reads, as PyYAML reads it, as an object
    holding ``timetoshare``; ``None`` where PyYAML cannot read it either."""
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    return isinstance(value, dict) and "timetoshare" in value


def file_problems(path: Path) -> tuple[list[str], list[str]] | None:
    """The refusals and the warnings of a manifest file; ``None`` for a file
    that is no manifest.

    A file is a manifest when ``loads`` reads it as an object holding
    ``timetoshare``. A file ``loads`` refuses is refused (``unreadable``) when
    PyYAML reads it as such an object or cannot read it at all, and is no
    manifest otherwise. Each refusal and warning is one line, ``<code> at
    <JSON pointer>: <message>``, a warning's prefixed ``warning: ``; a file is
    refused for its first violation, as ``validate`` raises it.
    """
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [f"unreadable at #: {error}"], []
    try:
        value = loads(text)
    except ValueError as error:
        if _readable_elsewhere(text) is False:
            return None
        return [f"unreadable at #: {error}"], []
    if not isinstance(value, dict) or "timetoshare" not in value:
        return None
    try:
        warnings = manifest_warnings(value)
    except SchemaValidationError as error:
        return [f"{error.code} at {json_pointer(error.path)}: {error.message}"], []
    except UnsupportedVersionError as error:
        return [f"unsupported_version at #/timetoshare: {error}"], []
    return [], [
        f"warning: {w['code']} at {json_pointer(w['path'])}: {w['message']}"
        for w in warnings
    ]


def _found_files(root: Path) -> list[Path]:
    """The ``.yaml``, ``.yml`` and ``.json`` files under ``root`` outside
    ``.git``, sorted."""
    return sorted(
        file
        for file in root.rglob("*")
        if file.suffix in _SERIALIZED
        and ".git" not in file.relative_to(root).parts
        and file.is_file()
    )


def _validate(arguments: argparse.Namespace) -> int:
    paths = [Path(p) for p in arguments.paths] or _found_files(Path("."))
    refused = False
    for path in paths:
        found = file_problems(path)
        if found is None:
            continue
        errors, warnings = found
        refused = refused or bool(errors)
        for line in (*errors, *warnings):
            print(f"{path.as_posix()}: {line}")
    return 1 if refused else 0


def _git(*args: str) -> str | None:
    """The output of a git command in the current directory; ``None`` on failure."""
    done = subprocess.run(["git", *args], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def _comment() -> str:
    """git's comment character: ``core.commentString`` or ``core.commentChar``,
    the one set last; ``#`` when neither is set or the value is ``auto``."""
    found = _git("config", "--get-regexp", r"^core\.comment(char|string)$")
    values = [
        line.split(" ", 1)[1] for line in (found or "").splitlines() if " " in line
    ]
    if values and values[-1] and values[-1] != "auto":
        return values[-1]
    return "#"


def _amend_base_file() -> Path | None:
    directory = _git("rev-parse", "--absolute-git-dir")
    return Path(directory) / AMEND_BASE if directory else None


def prepared_message(text: str, header: str, trailer: str, comment: str = "#") -> str:
    """A message with ``header`` in front of its first line and ``trailer`` below.

    Comment lines (starting with ``comment``) from the first one on stay
    where they are, after the message.
    """
    lines = text.split("\n")
    comments = next(
        (index for index, line in enumerate(lines) if line.startswith(comment)),
        len(lines),
    )
    message, rest = lines[:comments], lines[comments:]
    while message and message[-1].strip() == "":
        message.pop()
    first, body = (message[0], message[1:]) if message else ("", [])
    written = [header + first, *body]
    if trailer:
        written += ["", *trailer.split("\n")]
    result = "\n".join(written) + "\n"
    if rest:
        result += "\n" + "\n".join(rest)
    return result


def _prepare(arguments: argparse.Namespace) -> int:
    source = arguments.source or os.environ.get("PRE_COMMIT_COMMIT_MSG_SOURCE")
    commit = arguments.sha or os.environ.get("PRE_COMMIT_COMMIT_OBJECT_NAME")
    base = _amend_base_file()
    if base is not None:
        base.unlink(missing_ok=True)
        head = _git("rev-parse", "--verify", "--quiet", "HEAD")
        if source == "commit" and commit and head:
            if _git("rev-parse", "--verify", "--quiet", commit) == head:
                base.write_text(head + "\n", encoding="utf-8")
    if source in _UNTOUCHED_SOURCES:
        return 0
    path = Path(arguments.msgfile)
    text = path.read_text(encoding="utf-8")
    comment = _comment()
    first = message_text(text, comment).split("\n", 1)[0]
    if first.startswith(_SKIPPED) or parse_header(first) is not None:
        return 0
    try:
        report = git_step("HEAD", None, Path.cwd())
    except ValueError as error:
        print(f"timetoshare: no commit type written: {error}", file=sys.stderr)
        return 0
    suggested = suggest_header(report)
    if suggested is None:
        return 0
    path.write_text(
        prepared_message(text, suggested, suggest_trailer(report), comment),
        encoding="utf-8",
    )
    return 0


def _amended_parent() -> str:
    """What the staged change is compared with: ``HEAD``, or for an amend the
    parent of the amended commit (the empty tree for a root commit)."""
    base = _amend_base_file()
    if base is None or not base.is_file():
        return "HEAD"
    commit = base.read_text(encoding="utf-8").strip()
    base.unlink()
    if commit != _git("rev-parse", "HEAD"):
        return "HEAD"
    parent = _git("rev-parse", "--verify", "--quiet", f"{commit}^")
    if parent:
        return parent
    return _git("hash-object", "-t", "tree", os.devnull) or "HEAD"


def _check(arguments: argparse.Namespace) -> int:
    text = Path(arguments.msgfile).read_text(encoding="utf-8")
    try:
        report = git_step(_amended_parent(), None, Path.cwd())
    except ValueError as error:
        message = f"timetoshare: the staged change cannot be read: {error}"
        print(message, file=sys.stderr)
        return 1
    errors, warnings = check_message(text, report, _comment())
    for warning in warnings:
        print(f"timetoshare: warning: {warning}", file=sys.stderr)
    for error in errors:
        print(f"timetoshare: error: {error}", file=sys.stderr)
    return 1 if errors else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="timetoshare",
        description="Validate manifests and name the version step of a change to "
        "a repository of manifests.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate manifest files")
    validate.add_argument(
        "paths",
        metavar="PATH",
        nargs="*",
        help="a file; none: every .yaml, .yml and .json file under the current "
        "directory outside .git",
    )
    validate.set_defaults(run=_validate)
    step = commands.add_parser("step", help="print the version step a change requires")
    step.add_argument(
        "old",
        metavar="OLD",
        help="a directory or a git reference; '-': the empty tree",
    )
    step.add_argument(
        "new",
        metavar="NEW",
        nargs="?",
        help="a directory or a git reference; left out: the staged changes",
    )
    step.add_argument("--repo", default=".", help="the git repository (default: .)")
    step.add_argument("--json", action="store_true", help="print the report as JSON")
    step.add_argument(
        "--history",
        action="store_true",
        help="also refuse an ID that a reachable tag held for an element gone "
        "since or of another type (git references only)",
    )
    step.add_argument(
        "--require-version",
        nargs=2,
        metavar=("FROM", "TO"),
        help="also refuse the change where a release from version FROM to TO "
        "carries a lower step than it requires",
    )
    step.set_defaults(run=_step)
    hook = commands.add_parser("hook", help="run as a git hook")
    hooks = hook.add_subparsers(dest="hook", required=True)
    prepare = hooks.add_parser(
        "prepare-commit-msg", help="write the commit type the staged change requires"
    )
    prepare.add_argument("msgfile", metavar="MSGFILE")
    prepare.add_argument("source", metavar="SOURCE", nargs="?")
    prepare.add_argument("sha", metavar="SHA", nargs="?")
    prepare.set_defaults(run=_prepare)
    check = hooks.add_parser(
        "commit-msg", help="check the commit message against the staged change"
    )
    check.add_argument("msgfile", metavar="MSGFILE")
    check.set_defaults(run=_check)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line; return the exit status."""
    arguments = _parser().parse_args(argv)
    return arguments.run(arguments)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
