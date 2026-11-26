"""The ``timetoshare`` command: the version step of a change, and two git hooks.

``timetoshare step OLD [NEW]`` prints the step a change of a repository of
manifests requires: OLD and NEW are two directories, or two git references
of the repository ``--repo`` (NEW left out: the staged changes).

``timetoshare hook prepare-commit-msg MSGFILE [SOURCE [SHA]]`` writes the
commit type the staged change requires in front of the message, and
``timetoshare hook commit-msg MSGFILE`` checks the final message against
the staged change. Both run as git hooks directly or through pre-commit,
which hands over the message file as the one file name and the source of
the message in ``PRE_COMMIT_COMMIT_MSG_SOURCE``.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from .commit_types import (
    _SKIPPED,
    COMMIT_TYPES,
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


def _report(old: str, new: str | None, repo: Path) -> StepReport:
    if Path(old).is_dir() and new is not None and Path(new).is_dir():
        return tree_step(Path(old), Path(new))
    if Path(old).is_dir() or (new is not None and Path(new).is_dir()):
        raise ValueError("OLD and NEW are both directories or both git references")
    return git_step(old, new, repo)


def _step(arguments: argparse.Namespace) -> int:
    try:
        report = _report(arguments.old, arguments.new, Path(arguments.repo))
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


def prepared_message(text: str, header: str, trailer: str) -> str:
    """A message with ``header`` in front of its first line and ``trailer`` below.

    Comment lines from the first one on stay where they are, after the
    message.
    """
    lines = text.split("\n")
    comments = next(
        (index for index, line in enumerate(lines) if line.startswith("#")),
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
    if source in _UNTOUCHED_SOURCES:
        return 0
    path = Path(arguments.msgfile)
    text = path.read_text(encoding="utf-8")
    first = message_text(text).split("\n", 1)[0]
    header = parse_header(first)
    if first.startswith(_SKIPPED) or (
        header is not None and header.type in COMMIT_TYPES
    ):
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
        prepared_message(text, suggested, suggest_trailer(report)), encoding="utf-8"
    )
    return 0


def _check(arguments: argparse.Namespace) -> int:
    text = Path(arguments.msgfile).read_text(encoding="utf-8")
    try:
        report = git_step("HEAD", None, Path.cwd())
    except ValueError as error:
        message = f"timetoshare: the staged change cannot be read: {error}"
        print(message, file=sys.stderr)
        return 1
    errors, warnings = check_message(text, report)
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
