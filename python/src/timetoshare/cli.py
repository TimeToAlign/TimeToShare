"""The ``timetoshare`` command: the version step of a change, and two git hooks.

``timetoshare step OLD [NEW]`` prints the step a change of a repository of
manifests requires: OLD and NEW are two directories, or two git references
of the repository ``--repo`` (NEW left out: the staged changes). With
``--history`` (git references only) it also reports every ID of NEW that a
tag reachable from NEW or OLD held for an element that is gone since or of
another type: the check a release pull request's job runs.

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

from .commit_types import (
    _SKIPPED,
    check_message,
    message_text,
    parse_header,
    suggest_header,
    suggest_trailer,
)
from .serialization import dumps
from .version_step import StepReport, git_step, tree_step

__all__ = ["main"]

_UNTOUCHED_SOURCES = ("merge", "squash", "commit")
"""Sources of a message the first hook leaves alone: merges, squashes, amends."""

AMEND_BASE = "timetoshare-amend-base"
"""The file in the git directory naming the commit an amend replaces."""


def _report(old: str, new: str | None, repo: Path, history: bool) -> StepReport:
    if Path(old).is_dir() and new is not None and Path(new).is_dir():
        if history:
            raise ValueError("--history compares git references, not directories")
        return tree_step(Path(old), Path(new))
    if Path(old).is_dir() or (new is not None and Path(new).is_dir()):
        raise ValueError("OLD and NEW are both directories or both git references")
    return git_step(old, new, repo, history=history)


def _step(arguments: argparse.Namespace) -> int:
    try:
        report = _report(
            arguments.old, arguments.new, Path(arguments.repo), arguments.history
        )
    except ValueError as error:
        print(f"timetoshare step: {error}", file=sys.stderr)
        return 1
    if arguments.json:
        sys.stdout.write(dumps(report.to_dict(), "json"))
    else:
        print(f"step: {report.step}")
        print(f"scope: {report.scope or '-'}")
        for f in report.findings:
            cited = f"#{f.id}" if f.id is not None else "-"
            print(f"{f.step}\t{f.kind}\t{f.path}\t{cited}\t{f.detail}")
    return 2 if report.refused else 0


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
        description="The version step of a change to a repository of manifests.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    step = commands.add_parser("step", help="print the version step a change requires")
    step.add_argument("old", metavar="OLD", help="a directory or a git reference")
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
