"""The ``timetoshare`` command: validation, the version step of a change, two hooks.

``timetoshare validate [PATH ...]`` validates manifest files: the files
named, whatever their names, or every file under the current directory
outside ``.git`` whose name ends ``.tts.yaml``, ``.tts.yml`` or
``.tts.json``. A file that is no manifest is skipped.

``timetoshare step OLD [NEW]`` prints the step a change of a repository of
manifests requires: OLD and NEW are two directories, or two git references
of the repository ``--repo`` (NEW left out: the staged changes; OLD ``-``:
the empty tree, for a repository without a release). With ``--history``
(git references only) it also reports every ID of NEW that a tag reachable
from NEW or OLD held for an element that is gone since or of another type:
the check a release pull request's job runs.

``timetoshare release-check`` is the check of a dataset repository's
release workflow. Its ``HEAD`` is a release when the version in
``.release-please-manifest.json`` is not ``0.0.0`` and has no tag
``v<version>`` yet; the check then compares the last version tag reachable
from ``HEAD`` (the empty tree without one) with ``HEAD``, with the history of
the tags, and fails when a change is refused or undetermined or when the
release allows a lower step than the change requires. On any other
``HEAD`` it reports the same comparison and passes. ``--summary FILE``
appends the report to FILE as Markdown, the job summary of a workflow.

``timetoshare registry [--check] [PACKAGE]`` rewrites the non-event rows of
the registry of the package PACKAGE (a folder holding ``package.yaml``, the
current directory without it) from its manifests, MatchClaim tables and
Parse table, inside the one registry file, its event rows kept with
their values unchanged and the file written in the order of the format;
with ``--check`` it writes
nothing and lists every non-event row that is missing, extra or differs, one
line each, exiting 1 when there is one: the check of the pre-commit hook
``timetoshare-registry``.

``timetoshare hook prepare-commit-msg MSGFILE [SOURCE [SHA]]`` writes the
commit type of a minor or a major step in front of a message without one,
and suggests one for a patch; a message that already has a type gets no
suggestion, only the hint that a commit mixes kinds of change. The
suggestion and the hint are comment lines where the message is edited and
git removes comment lines. They go to standard error where the message is
given with ``-m`` or ``-F`` (also ``git commit -m x -e``: git hands over the
source ``message``, so they are printed before the editor opens) and where
``git config commit.cleanup`` is ``whitespace``, ``verbatim`` or
``scissors``, with which git keeps the comment lines above the scissors
line. A ``--cleanup=`` option of ``git commit`` is invisible to the hook,
which reads only the configuration.
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
import json
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from ._urls import is_manifest_name
from .commit_types import (
    _SKIPPED,
    check_message,
    message_text,
    parse_header,
    release_allows,
    release_problem,
    suggest_header,
    suggest_hints,
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

_GIVEN_SOURCE = "message"
"""The source of a message given with ``-m`` or ``-F``, whose comment lines
git keeps."""

_KEPT_COMMENTS = ("whitespace", "verbatim", "scissors")
"""The values of ``commit.cleanup`` with which git keeps the comment lines
of an edited message (above the scissors line)."""

AMEND_BASE = "timetoshare-amend-base"
"""The file in the git directory naming the commit an amend replaces."""

EMPTY_TREE = "-"
"""The OLD argument of ``timetoshare step`` that names the empty tree."""

RELEASE_MANIFEST = ".release-please-manifest.json"
"""The file of a dataset repository holding its version, release-please's."""

NO_RELEASE = "0.0.0"
"""The version of a dataset repository before its first release."""


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
        print("\n".join(_report_lines(report)))
    return 2 if report.refused else 0


def _report_lines(report: StepReport, release: str | None = None) -> list[str]:
    """The lines of a report: the step, the scope, the release (``release``,
    where the release check names one) and one line per finding."""
    lines = [f"step: {report.step}", f"scope: {report.scope or '-'}"]
    if release is not None:
        lines.append(f"release: {release}")
    for f in report.findings:
        cited = f"#{f.id}" if f.id is not None else "-"
        lines.append(f"{f.step}\t{f.kind}\t{f.path}\t{cited}\t{f.detail}")
    return lines


def _git_in(repo: Path, *args: str) -> str | None:
    """The output of a git command in ``repo``; ``None`` on failure."""
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    return done.stdout.strip() if done.returncode == 0 else None


def _release_state(repo: Path) -> tuple[str, str | None, bool]:
    """The version of a dataset repository, its last version tag, and whether
    its ``HEAD`` is a release.

    The version is the root package's (``"."``) in
    ``.release-please-manifest.json`` of the work tree. The last version tag
    is the nearest tag matching ``v[0-9]*`` reachable from ``HEAD`` (``git
    describe``), ``None`` where there is none. ``HEAD`` is a release when the
    version is not ``0.0.0`` and no tag ``v<version>`` exists yet: the push
    that merges a release pull request, before release-please tags it.

    Raises:
        ValueError: If the file cannot be read or names no version of ``"."``.
    """
    try:
        value = json.loads((repo / RELEASE_MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"{RELEASE_MANIFEST} cannot be read: {error}") from None
    version = value.get(".") if isinstance(value, dict) else None
    if not isinstance(version, str):
        raise ValueError(f'{RELEASE_MANIFEST} names no version of "."')
    last = _git_in(repo, "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*")
    tagged = _git_in(repo, "rev-parse", "--verify", "--quiet", f"refs/tags/v{version}")
    return version, last or None, version != NO_RELEASE and tagged is None


def _since(since: str, repo: Path) -> StepReport:
    """The report from ``since`` (a reference or ``-``) to ``HEAD``, with the
    history of the tags."""
    return _report(since, "HEAD", repo, history=True)


def _release_lines(repo: Path) -> tuple[str, list[str], bool]:
    """The heading, the lines and the failure of the release check of ``repo``.

    The check compares the last version tag (:func:`_release_state`; the empty
    tree without one) with ``HEAD``, with the history of the tags. Outside a
    release it only reports, and an error comparing is one more line. At a
    release (the version ``v<new>`` untagged) it fails when a change is
    refused, when a change is undetermined, or when the release from the last
    tag's version (``0.0.0`` without one) to the new allows a lower step
    than the change requires (:func:`release_problem`).

    Raises:
        ValueError: If the version cannot be read, or, at a release, if a
            version is none, is lower than the last tag's, or the change
            cannot be compared.
    """
    version, last, release = _release_state(repo)
    since = last or EMPTY_TREE
    data = f"the data from {last or 'the empty tree'} to HEAD"
    if not release:
        why = f"is tagged v{version}" if version != NO_RELEASE else "is no release"
        try:
            lines = _report_lines(_since(since, repo))
        except ValueError as error:
            lines = [f"error: {error}"]
        return (
            "No release",
            [f"no release: the version {version} {why}", data, *lines],
            False,
        )
    previous = last.removeprefix("v") if last else NO_RELEASE
    allows = release_allows(previous, version)
    report = _since(since, repo)
    problem = release_problem(report, previous, version)
    reasons = [
        *(["a change is refused"] if report.refused else []),
        *(["a change is undetermined"] if report.undetermined else []),
        *([problem] if problem is not None else []),
    ]
    named = (
        f"{version} is the first release; it allows {allows}"
        if last is None
        else f"{previous} to {version} allows {allows}"
    )
    lines = [
        data,
        *_report_lines(report, named),
        *([f"fails: {reason}" for reason in reasons] or ["passes"]),
    ]
    verdict = "fails" if reasons else "passes"
    return f"Release {version}: {verdict}", lines, bool(reasons)


def _release_check(arguments: argparse.Namespace) -> int:
    repo = Path(arguments.repo)
    try:
        heading, lines, failed = _release_lines(repo)
        status = 2 if failed else 0
    except ValueError as error:
        heading, lines, status = "Release check: error", [f"error: {error}"], 1
        print(f"timetoshare release-check: {error}", file=sys.stderr)
    if status != 1:
        print("\n".join(lines))
    if arguments.summary:
        block = "\n".join(["", "```text", *lines, "```", ""])
        with open(arguments.summary, "a", encoding="utf-8") as summary:
            summary.write(f"### {heading}\n{block}")
    return status


_YAML_MARKER = re.compile(
    r"""^(timetoshare|"timetoshare"|'timetoshare')[ \t]*:""", re.M
)
"""A line of YAML text starting with the top-level key ``timetoshare``."""

_BRACED_MARKER = re.compile(r"""\btimetoshare["']?\s*:""")
"""The key ``timetoshare`` in a text in braces, quoted or not."""


def _names_the_format(text: str) -> bool:
    """Whether a text ``loads`` refuses holds a top-level key ``timetoshare``.

    In YAML that is a line starting with the key (``timetoshare: 0.2.0``). A
    text starting with ``{`` is read as JSON: it names the format when it is
    an object holding the key or, where it cannot be read as JSON, when the
    key stands anywhere in it, quoted or not.
    """
    if _YAML_MARKER.search(text):
        return True
    stripped = text.lstrip("\ufeff \t\r\n")
    if not stripped.startswith("{"):
        return False
    try:
        value = json.loads(stripped)
    except ValueError:
        return _BRACED_MARKER.search(stripped) is not None
    return isinstance(value, dict) and "timetoshare" in value


def file_problems(path: Path) -> tuple[list[str], list[str]] | None:
    """The refusals and the warnings of a manifest file; ``None`` for a file
    that is no manifest.

    A file is a manifest when ``loads`` reads it as an object holding
    ``timetoshare``. A file ``loads`` refuses (or whose bytes are no UTF-8) is
    refused (``unreadable``) when its text holds a top-level key
    ``timetoshare`` (:func:`_names_the_format`), and is no manifest
    otherwise: a YAML file with several documents or with tags such as
    ``!!python/name:`` is skipped. Each refusal and warning is one line,
    ``<code> at <JSON pointer>: <message>``, a warning's prefixed
    ``warning: ``; a file is refused for its first violation, as ``validate``
    raises it.
    """
    try:
        data = path.read_bytes()
    except OSError as error:
        return [f"unreadable at #: {error}"], []
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        if _names_the_format(data.decode("utf-8", errors="replace")):
            return [f"unreadable at #: {error}"], []
        return None
    try:
        value = loads(text)
    except ValueError as error:
        if _names_the_format(text):
            return [f"unreadable at #: {error}"], []
        return None
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
    """The files under ``root`` outside ``.git`` named like manifest files
    (``<name>.tts.yaml``, ``.tts.yml`` or ``.tts.json``), sorted."""
    return sorted(
        file
        for file in root.rglob("*")
        if is_manifest_name(file.name)
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


def _registry(arguments: argparse.Namespace) -> int:
    try:
        from .tables import stale_non_event_rows, write_non_event_rows
    except ImportError as error:
        print(f"timetoshare: {error}", file=sys.stderr)
        return 1
    root = Path(arguments.package)
    try:
        if not arguments.check:
            written = write_non_event_rows(root)
            print(f"wrote {written.relative_to(root).as_posix()}")
            return 0
        problems = stale_non_event_rows(root)
    except (OSError, ValueError) as error:
        print(f"timetoshare: {error}", file=sys.stderr)
        return 1
    for problem in problems:
        at = "" if problem.row is None else f" row {problem.row}:"
        print(f"{problem.file}:{at} {problem.code}: {problem.message}")
    return 1 if problems else 0


def _git(*args: str) -> str | None:
    """The output of a git command in the current directory; ``None`` on failure."""
    return _git_in(Path.cwd(), *args)


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


def with_hints(text: str, hints: list[str], comment: str = "#") -> str:
    """A message with ``hints`` as comment lines before its first comment line.

    A lone comment character separates them from comment lines that follow;
    without comment lines the hints go to the end.
    """
    if not hints:
        return text
    noted = [f"{comment} {hint}" for hint in hints]
    lines = text.split("\n")
    at = next(
        (index for index, line in enumerate(lines) if line.startswith(comment)), None
    )
    if at is None:
        ended = text if text.endswith("\n") else text + "\n"
        return ended + "\n".join(noted) + "\n"
    return "\n".join([*lines[:at], *noted, comment, *lines[at:]])


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
    if first.startswith(_SKIPPED):
        return 0
    typed = parse_header(first) is not None
    try:
        report = git_step("HEAD", None, Path.cwd())
    except ValueError as error:
        if not typed:
            print(f"timetoshare: no commit type written: {error}", file=sys.stderr)
        return 0
    hints = suggest_hints(report, typed=typed)
    if typed and not hints:
        return 0
    if not typed and report.step in ("minor", "major"):
        header = suggest_header(report) or ""
        text = prepared_message(text, header, suggest_trailer(report), comment)
    if source == _GIVEN_SOURCE or _git("config", "commit.cleanup") in _KEPT_COMMENTS:
        for hint in hints:
            print(f"timetoshare: {hint}", file=sys.stderr)
    else:
        text = with_hints(text, hints, comment)
    path.write_text(text, encoding="utf-8")
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
        help="a file; none: every file named <name>.tts.yaml, .tts.yml or "
        ".tts.json under the current directory outside .git",
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
    step.set_defaults(run=_step)
    registry = commands.add_parser(
        "registry", help="rewrite or check the non-event rows of a package's registry"
    )
    registry.add_argument(
        "package",
        metavar="PACKAGE",
        nargs="?",
        default=".",
        help="a folder holding package.yaml (default: .)",
    )
    registry.add_argument(
        "--check",
        action="store_true",
        help="write nothing; list every non-event row that is missing, extra or "
        "differs, and fail if there is one",
    )
    registry.set_defaults(run=_registry)
    check_release = commands.add_parser(
        "release-check",
        help="check the release a dataset repository's HEAD makes, or report the "
        "step since its last tag",
    )
    check_release.add_argument(
        "--repo", default=".", help="the git repository (default: .)"
    )
    check_release.add_argument(
        "--summary",
        metavar="FILE",
        help="also append the report as Markdown to FILE (a job summary)",
    )
    check_release.set_defaults(run=_release_check)
    hook = commands.add_parser("hook", help="run as a git hook")
    hooks = hook.add_subparsers(dest="hook", required=True)
    prepare = hooks.add_parser(
        "prepare-commit-msg",
        help="write the commit type a minor or a major change requires, suggest "
        "one for a patch",
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
