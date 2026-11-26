"""The commit types of a dataset repository, and the check of a commit message.

A dataset repository versions its manifests and tables by release tags
that release-please computes from Conventional Commits 1.0.0 headers,
``type(scope)!: subject``. release-please makes a ``feat`` commit a minor
step, any commit with ``!`` a major one and every other commit a patch, so
the types of a dataset repository say which change a commit makes:

- ``feat`` (or ``feature``, which release-please reads alike): minor;
  adding, editing or correcting data;
- ``remove`` with ``!``: major; removing anything with an ID, a member, a
  pair, a row or a manifest, or changing an ID. Any type with ``!``, and a
  ``BREAKING CHANGE`` footer, make a major release; a removal is written
  ``remove`` with ``!`` and nothing else;
- ``belief`` (a belief), ``label`` (a ``name``), ``graphic``
  (``graphical``), ``meta`` (``meta``), ``move`` (a resource's ``url`` for
  the same bytes), ``docs`` (prose) and ``fix`` (the repository's
  scripts): patch;
- ``chore``, ``build``, ``ci``, ``refactor``, ``test``, ``style``: none;
- ``revert``: accepted without a check.

:func:`suggest_header` writes the header a staged change requires,
:func:`suggest_trailer` the lines that go below it, and
:func:`check_message` checks a message against a change.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .version_step import REFUSED, STEPS, UNDETERMINED, Finding, StepReport

__all__ = [
    "COMMIT_TYPES",
    "DATA_TYPES",
    "Header",
    "check_message",
    "parse_header",
    "suggest_header",
    "suggest_trailer",
]

COMMIT_TYPES: dict[str, str | None] = {
    "feat": "minor",
    "feature": "minor",
    "remove": "major",
    "belief": "patch",
    "label": "patch",
    "graphic": "patch",
    "meta": "patch",
    "move": "patch",
    "docs": "patch",
    "fix": "patch",
    "chore": "none",
    "build": "none",
    "ci": "none",
    "refactor": "none",
    "test": "none",
    "style": "none",
    "revert": None,
}
"""The step of each commit type; ``remove`` requires ``!``, ``revert`` none."""

DATA_TYPES = ("feat", "feature", "remove", "belief", "label", "graphic", "meta", "move")
"""The types that name a change of the data."""

_PATCH_TYPES = (
    ("belief", "belief"),
    ("label", "label"),
    ("graphic", "graphic"),
    ("meta", "meta"),
    ("moved", "move"),
)
"""The kind of each patch finding and its type, in the order that breaks ties."""

_RANK = {step: rank for rank, step in enumerate(STEPS)}

_HEADER = re.compile(
    r"(?P<type>[A-Za-z][A-Za-z0-9-]*)(?:\((?P<scope>[^()\r\n]*)\))?(?P<bang>!)?:(?: |$)"
)

_SKIPPED = ("Merge ", "fixup!", "squash!", "amend!", 'Revert "')
"""Beginnings of messages that git writes and that are not checked."""

_SCISSORS = " ------------------------ >8 ------------------------"
"""git's scissors line after the comment character."""

_BREAKING = re.compile(r"^BREAKING[ -]CHANGE: ", re.MULTILINE)


@dataclass(frozen=True)
class Header:
    """The header of a Conventional Commits message.

    Attributes:
        type: The type, lower case.
        scope: The scope, or ``None``.
        breaking: Whether the header carries ``!``.
        subject: The text after ``: ``; empty for a header ending ``:``.
    """

    type: str
    scope: str | None
    breaking: bool
    subject: str


def parse_header(line: str) -> Header | None:
    """The header a line writes, or ``None`` for a line that is no header.

    ``type(scope)!: subject``; the subject may be empty, and the line may end
    at the colon, as an editor that strips trailing spaces leaves it.
    """
    match = _HEADER.match(line)
    if match is None:
        return None
    return Header(
        match["type"].lower(),
        match["scope"],
        match["bang"] is not None,
        line[match.end() :],
    )


def message_text(message: str, comment: str = "#") -> str:
    """A message without its comment lines and everything below git's scissors.

    Args:
        message: The message file's text.
        comment: What starts a comment line, git's ``core.commentChar``.
    """
    lines: list[str] = []
    for line in message.splitlines():
        if line == comment + _SCISSORS:
            break
        if not line.startswith(comment):
            lines.append(line)
    return "\n".join(lines).strip("\n")


def _patch_type(findings: tuple[Finding, ...]) -> str:
    counts = Counter(f.kind for f in findings if f.step == "patch")
    best = max(_PATCH_TYPES, key=lambda pair: counts[pair[0]])
    return best[1] if counts[best[0]] else "fix"


def _type_of(report: StepReport) -> str | None:
    if report.step == "major":
        return "remove"
    if report.step == "minor":
        return "feat"
    if report.step == "patch":
        return _patch_type(report.findings)
    return None


def suggest_header(report: StepReport) -> str | None:
    """The header a change requires, ending ``: `` for the person's subject.

    ``remove(scope)!: `` for a major step, ``feat(scope): `` for a minor one,
    and for a patch the type of the kind with most findings (ties in the
    order belief, label, graphic, meta, move); without a scope when the
    findings lie in several manifests. ``None`` when no step is required.
    """
    kind = _type_of(report)
    if kind is None:
        return None
    scope = f"({report.scope})" if report.scope else ""
    bang = "!" if report.step == "major" else ""
    return f"{kind}{scope}{bang}: "


def _cited(finding: Finding) -> str:
    """How a breaking change footer names what a major finding removes."""
    if finding.kind == "removed" and finding.id is not None:
        return f"#{finding.id}"
    if finding.kind == "removed_manifest":
        return finding.path
    return finding.detail


def suggest_trailer(report: StepReport) -> str:
    """The lines below the header: the smaller changes, then the removals.

    A body line ``also: <n> <kind>, …`` counts the findings of lower steps
    than the report's, and for a major step the footer ``BREAKING CHANGE:
    removes …`` names every removal in finding order. Empty when there is
    nothing to say.
    """
    lower = Counter(
        f.kind
        for f in report.findings
        if f.step in _RANK and _RANK[f.step] < _RANK[report.step]
    )
    blocks: list[str] = []
    if lower:
        blocks.append(
            "also: " + ", ".join(f"{n} {kind}" for kind, n in sorted(lower.items()))
        )
    if report.step == "major":
        removed = [_cited(f) for f in report.findings if f.step == "major"]
        blocks.append("BREAKING CHANGE: removes " + ", ".join(removed))
    return "\n\n".join(blocks)


def _declared(header: Header) -> str:
    if header.breaking:
        return "major"
    if header.type == "remove":
        return "patch"
    step = COMMIT_TYPES.get(header.type, "patch")
    return step if step is not None else "none"


def _requirement(report: StepReport) -> str:
    """What the change requires, in words, with the header to write."""
    wanted = suggest_header(report) or ""
    of_step = [f for f in report.findings if f.step == report.step]
    named = ", ".join(_cited(f) if f.step == "major" else f.detail for f in of_step)
    if report.step == "major":
        return (
            f"this commit removes {named}; write {_with_dots(wanted)} and a "
            "BREAKING CHANGE footer"
        )
    if report.step == "minor":
        return f"this commit adds or edits data ({named}); write {_with_dots(wanted)}"
    return f"this commit changes {named}; write {_with_dots(wanted)}"


def _with_dots(header: str) -> str:
    """A suggested header with ``...`` for its scope, as a message names it."""
    match = _HEADER.match(header)
    if match is None:  # pragma: no cover - suggest_header writes a header
        return header
    return f"{match['type']}(...){match['bang'] or ''}:"


def check_message(
    message: str, report: StepReport, comment: str = "#"
) -> tuple[list[str], list[str]]:
    """Check a commit message against the change it commits.

    Comment lines (starting with ``comment``) and everything below git's
    scissors line are ignored. Messages git writes for merges, fixups,
    squashes, amends and reverts, and the type ``revert``, are not checked.

    Returns:
        The errors and the warnings. An error where the declared step is
        lower than the change requires, for a removal written with any type
        but ``remove`` with ``!`` (``feat!`` included), for ``remove``
        without ``!``, for a header with an empty subject, for a message
        without a header when the change requires a step, and for every
        refused finding (an ID given again). A warning where a data type or
        a ``!`` declares a higher step than the change requires, where a
        ``BREAKING CHANGE`` footer stands on a commit that removes nothing,
        where a major commit's footer misses a removed ID, and where a change
        could not be judged.
    """
    text = message_text(message, comment)
    if text.startswith(_SKIPPED):
        return [], []
    errors: list[str] = []
    warnings: list[str] = []
    first = text.split("\n", 1)[0]
    header = parse_header(first)
    if header is not None and header.type == "revert":
        return [], []
    for finding in report.findings:
        if finding.step == REFUSED:
            errors.append(f"{finding.path}: {finding.detail}; an ID is never reused")
        elif finding.step == UNDETERMINED:
            warnings.append(f"{finding.path}: {finding.detail}")
    if header is None:
        if report.step != "none":
            errors.append(
                f"the first line is no Conventional Commits header; "
                f"{_requirement(report)}"
            )
        return errors, warnings
    if not header.subject.strip():
        written = first[: len(first) - len(header.subject)].rstrip()
        errors.append(f'write what the commit does after "{written} "')
    if header.type == "remove" and not header.breaking:
        errors.append("remove requires '!': write remove(...)!:")
    if header.type not in COMMIT_TYPES:
        warnings.append(f"'{header.type}' is no type of a dataset repository")
    declared = _declared(header)
    footer = _BREAKING.search(text)
    removal = report.step == "major"
    if _RANK[declared] < _RANK[report.step] or (removal and header.type != "remove"):
        errors.append(_requirement(report))
    elif (header.type in DATA_TYPES or header.breaking) and _RANK[declared] > _RANK[
        report.step
    ]:
        warnings.append(
            f"{header.type}{'!' if header.breaking else ''} declares a {declared} "
            f"step; the staged change requires {report.step}"
        )
    if footer is not None and not removal:
        warnings.append(
            "the BREAKING CHANGE footer makes a major release; this commit "
            "removes nothing"
        )
    if declared == "major" and removal:
        cited = text[footer.end() :] if footer else ""
        missing = [
            f"#{f.id}"
            for f in report.findings
            if f.kind == "removed"
            and f.id is not None
            and not re.search(rf"#{re.escape(f.id)}(?![\w:.-])", cited)
        ]
        if missing:
            warnings.append(
                "the BREAKING CHANGE footer does not name " + ", ".join(missing)
            )
    return errors, warnings
