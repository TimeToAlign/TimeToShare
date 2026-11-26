"""The version step a change to a repository of manifests requires.

A dataset's manifests and tables carry no version of their data: the
release tags of the repository that holds them version them together. A
release compares the tree of the last tag with the new one, every manifest
and every table of the repository, by value in the complete form and
canonical order, elements matched by their IDs:

- removing anything with an ID, a group member, a statement pair, a prefix
  of ``@context``, a row of a table or a manifest file is a **major** step;
  changing an ID is a removal and an addition;
- adding any of these, and editing what an element states (corrections
  included), is a **minor** step;
- a belief, a ``name``, ``meta``, anything in ``graphical`` other than named
  timestamps, named MatchStamps and their alignment anchors (an elision
  included), and a resource's ``url`` changed for the same bytes are a
  **patch**;
- another form or serialization of the same value, comments included, is
  no step at all: numbers compare by exact value wherever the format reads
  a number (``2``, ``2.0``, ``[2, 1]`` and ``[4, 2]`` are one value), while
  ``meta`` and the literals of statements and provenance compare as written;
- giving an ID to an element of another type, or again after its element
  was removed, is **refused**. Two states show the first; ``git_step`` with
  ``history=True`` reads the tags of the repository for the second.

A file that is a manifest in one state and cannot be read in the other is
**undetermined**, as is a changed table that cannot be compared by rows.

``manifest_step`` compares two manifests, ``tree_step`` two directories and
``git_step`` two git references (or a reference and the staged changes). Each
change is a :class:`Finding`; a :class:`StepReport` holds them with the step
they require together.
"""

from __future__ import annotations

import json
import math
import posixpath
import subprocess
import tempfile
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from fractions import Fraction
from functools import cache
from pathlib import Path, PurePosixPath
from typing import Any

from .defaults import DEFAULTS, complete
from .ids import CONTAINERS, ID_POSITIONS, definitions_of, with_bare_ids
from .manifest import canonical_order, fraction_pair
from .serialization import loads
from .validate import SCHEMA_VERSION, load_schema

__all__ = [
    "STEPS",
    "Finding",
    "StepReport",
    "git_step",
    "manifest_step",
    "tree_step",
]

STEPS = ("none", "patch", "minor", "major")
"""The version steps, from the smallest to the largest."""

REFUSED = "refused"
"""The step of a change no release may make: an ID given to another element
type, or again after its element was removed."""

UNDETERMINED = "undetermined"
"""The step of a change this package cannot judge: a table it cannot read, a
manifest of another format version, a manifest that no longer reads."""

TABLE_TYPES = ("MatchClaim", "Projection")
"""The resource types whose tables are compared row by row."""

_RANK = {step: rank for rank, step in enumerate(STEPS)}

_ELEMENT_POSITIONS = frozenset(
    definition
    for definition, member, shape in ID_POSITIONS
    if member == "id" and shape == "id"
)
"""The definitions whose ``id`` member holds their own ID; a member ``id``
that names another element (an address's) has the shape ``ref``."""

_HELD: dict[str, dict[str, tuple[str, str]]] = {}
for _definition, _member, _holding, _child in CONTAINERS:
    _HELD.setdefault(_definition, {})[_member] = (_holding, _child)

_DISPLAYED = ("Timestamp", "AlignmentAnchor")
"""The elements of ``graphical`` whose ``display`` is styling."""

_SERIALIZED = (".yaml", ".yml", ".json")
"""The file extensions of manifest files."""


@dataclass(frozen=True)
class Finding:
    """One change between two states of a repository of manifests.

    Attributes:
        kind: What changed, for example ``removed``, ``added``, ``edited``,
            ``belief`` or ``removed_row``.
        step: The step it requires, one of ``STEPS``, or ``"refused"`` or
            ``"undetermined"``.
        path: The manifest file's path relative to the tree, POSIX, or the
            path given to ``manifest_step``.
        id: The bare ID of the element it concerns; ``None`` for the
            manifest itself or a manifest file.
        detail: The change in words, one line.
    """

    kind: str
    step: str
    path: str
    id: str | None
    detail: str


@dataclass(frozen=True)
class StepReport:
    """The step a change requires, and the findings it rests on.

    Attributes:
        step: The highest step of all findings, one of ``STEPS``;
            ``"none"`` without findings.
        findings: Every finding, sorted by path, kind and ID.
        refused: Whether a finding is refused.
        undetermined: Whether a finding could not be judged.
        scope: The manifest file's stem when every finding lies in one
            manifest file, else the first path component when all lie under
            one top directory, else ``None``.
    """

    step: str
    findings: tuple[Finding, ...]
    refused: bool
    undetermined: bool
    scope: str | None

    @classmethod
    def of(cls, findings: list[Finding] | tuple[Finding, ...]) -> StepReport:
        """The report of a set of findings."""
        ordered = tuple(sorted(findings, key=_finding_key))
        ranks = [_RANK[f.step] for f in ordered if f.step in _RANK]
        return cls(
            step=STEPS[max(ranks, default=0)],
            findings=ordered,
            refused=any(f.step == REFUSED for f in ordered),
            undetermined=any(f.step == UNDETERMINED for f in ordered),
            scope=_scope(ordered),
        )

    def to_dict(self) -> dict[str, Any]:
        """The report as a JSON value."""
        return {
            "step": self.step,
            "scope": self.scope,
            "refused": self.refused,
            "undetermined": self.undetermined,
            "findings": [
                {
                    "kind": f.kind,
                    "step": f.step,
                    "path": f.path,
                    "id": f.id,
                    "detail": f.detail,
                }
                for f in self.findings
            ],
        }


def _finding_key(finding: Finding) -> tuple[str, str, str, str]:
    return (finding.path, finding.kind, finding.id or "", finding.detail)


def _scope(findings: tuple[Finding, ...]) -> str | None:
    paths = {PurePosixPath(f.path) for f in findings if f.path}
    if not paths or len(paths) != len({f.path for f in findings}):
        return None
    if len(paths) == 1:
        return next(iter(paths)).stem or None
    tops = {path.parts[0] for path in paths if len(path.parts) > 1}
    if len(tops) == 1 and all(len(path.parts) > 1 for path in paths):
        return next(iter(tops))
    return None


def _exact(value: Fraction) -> list[Any]:
    return ["\u0000", value.numerator, value.denominator]


def _text(value: Any) -> str:
    """A key equal for two values exactly when they are equal.

    Object keys are sorted. A number the format reads by value stands as a
    ``Fraction`` (:func:`_by_value`), equal to another of equal value
    whatever its spelling; every other integer, float and boolean is
    compared as written.
    """
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=_exact)


# Numbers by value -----------------------------------------------------------

_NUMBERS = ("integer", "number")

_AS_WRITTEN = frozenset({"@context", "meta", "statements", "provenance"})
"""Members whose values are compared as written: their literals are data."""


@cache
def _definitions() -> dict[str, Any]:
    return load_schema()["$defs"]


def _resolved(node: Any) -> Mapping[str, Any] | None:
    """A schema node with its ``$ref`` followed; ``None`` outside the manifest's."""
    seen = 0
    while isinstance(node, Mapping) and "$ref" in node and seen < 16:
        reference = node["$ref"]
        if not isinstance(reference, str) or not reference.startswith("#/$defs/"):
            return None
        node = _definitions().get(reference.removeprefix("#/$defs/"))
        seen += 1
    return node if isinstance(node, Mapping) else None


def _branches(node: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    found = []
    for key in ("allOf", "oneOf", "anyOf"):
        for branch in node.get(key, ()):
            resolved = _resolved(branch)
            if resolved is not None:
                found.append(resolved)
    return found


def _admits(node: Mapping[str, Any], value: Any) -> bool:
    """Whether a node admits ``value`` as a number: a JSON number or a pair."""
    kinds = node.get("type")
    kinds = kinds if isinstance(kinds, list) else [kinds]
    if isinstance(value, list):
        if "array" in kinds and "prefixItems" in node:
            prefix = [_resolved(item) or {} for item in node["prefixItems"]]
            return len(prefix) == 2 and all(i.get("type") == "integer" for i in prefix)
    elif any(kind in _NUMBERS for kind in kinds):
        return True
    return any(_admits(branch, value) for branch in _branches(node))


def _number_of(node: Mapping[str, Any], value: Any) -> Fraction | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, list):
        pair = fraction_pair(value)
        return pair if pair is not None and _admits(node, value) else None
    if isinstance(value, int) or (isinstance(value, float) and math.isfinite(value)):
        return Fraction(value) if _admits(node, value) else None
    return None


def _member_schemas(
    node: Mapping[str, Any], value: Mapping[str, Any]
) -> tuple[dict[str, Any], Any]:
    """The schemas of an object's members, and of any further member."""
    members: dict[str, Any] = {}
    further: Any = None
    pending = [node]
    while pending:
        current = pending.pop(0)
        members = {**current.get("properties", {}), **members}
        extra = current.get("additionalProperties")
        if further is None and isinstance(extra, Mapping):
            further = extra
        for branch in _branches(current):
            const = branch.get("properties", {}).get("type", {}).get("const")
            if const is None or const == value.get("type"):
                pending.append(branch)
    return members, further


def _items(node: Mapping[str, Any]) -> Any:
    if isinstance(node.get("items"), Mapping):
        return node["items"]
    for branch in _branches(node):
        if isinstance(branch.get("items"), Mapping):
            return branch["items"]
    return None


def _by_value(schema: Any, value: Any) -> Any:
    """A value with every number the format reads by value as a ``Fraction``.

    Guided by the schema: where a node admits a number, an integer, a float
    and a Fraction pair of equal value become one ``Fraction`` (``2``,
    ``2.0``, ``[2, 1]`` and ``[4, 2]`` alike); a list of two integers where
    the schema admits no pair stays a list. ``meta``, ``statements``,
    ``provenance`` and ``@context`` keep every literal as written.
    """
    node = _resolved(schema)
    if node is None:
        return value
    number = _number_of(node, value)
    if number is not None:
        return number
    if isinstance(value, Mapping):
        members, further = _member_schemas(node, value)
        return {
            key: item
            if key in _AS_WRITTEN
            else _by_value(members.get(key, further), item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        items = _items(node)
        return [_by_value(items, item) for item in value]
    return value


# Elements -------------------------------------------------------------------


@dataclass(frozen=True)
class _Element:
    """An element with an ID, its nested elements cut out of its content."""

    definition: str
    content: dict[str, Any]
    owner: str | None
    place: tuple[str, ...]
    graphical: bool


_CUT = object()
"""Stands for an element cut out of the content of the one that holds it."""


class _Elements:
    """Every element with an ID of one manifest, and the manifest's own content."""

    def __init__(self, manifest: Mapping[str, Any]) -> None:
        self.found: dict[str, _Element] = {}
        root = {key: value for key, value in manifest.items() if key != "id"}
        self.root: dict[str, Any] = self._cut(root, "Manifest", None, (), False, True)

    def _cut(
        self,
        value: Any,
        definition: str,
        owner: str | None,
        place: tuple[str, ...],
        graphical: bool,
        root: bool = False,
    ) -> Any:
        if not isinstance(value, Mapping):
            return value
        definitions = definitions_of(definition, value)
        own = value.get("id")
        is_element = (
            not root
            and isinstance(own, str)
            and any(name in _ELEMENT_POSITIONS for name in definitions)
        )
        holder, at = (own, ()) if is_element else (owner, place)
        holds: dict[str, tuple[str, str]] = {}
        for name in definitions:
            holds.update(_HELD.get(name, {}))
        content: dict[str, Any] = {}
        for key, member in value.items():
            if key not in holds:
                content[key] = member
                continue
            holding, child = holds[key]
            inside = graphical or child == "Graphical"
            kept = self._holding(member, holding, child, holder, (*at, key), inside)
            # A list or object left empty once its elements are cut out says
            # nothing an absent one does not: its elements are compared alone.
            if kept is not _CUT and (holding == "one" or kept):
                content[key] = kept
        if not is_element:
            return content
        self.found[own] = _Element(definition, content, owner, place, graphical)
        return _CUT

    def _holding(
        self,
        value: Any,
        holding: str,
        child: str,
        owner: str | None,
        place: tuple[str, ...],
        graphical: bool,
    ) -> Any:
        if holding == "one":
            return self._cut(value, child, owner, place, graphical)
        if holding == "list" and isinstance(value, list):
            cut = (self._cut(item, child, owner, place, graphical) for item in value)
            return [item for item in cut if item is not _CUT]
        if holding == "values" and isinstance(value, Mapping):
            return {
                key: kept
                for key, item in value.items()
                if (kept := self._cut(item, child, owner, place, graphical)) is not _CUT
            }
        return value


def _prepared(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """A manifest with bare IDs, in the complete form and in canonical order,
    its numbers by value."""
    prepared = canonical_order(complete(with_bare_ids(manifest)))
    if not isinstance(prepared.get("graphical"), Mapping):
        prepared["graphical"] = {}
    for key, value in DEFAULTS["graphical"].items():
        prepared["graphical"].setdefault(key, json.loads(json.dumps(value)))
    return _by_value({"$ref": "#/$defs/Manifest"}, prepared)


def _named(element: _Element | None, id: str | None) -> str:
    if element is None or id is None:
        return "the manifest"
    return f"{element.definition} #{id}"


class _Comparison:
    """The findings between two manifests of one path."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.findings: list[Finding] = []

    def add(self, kind: str, step: str, id: str | None, detail: str) -> None:
        self.findings.append(Finding(kind, step, self.path, id, detail))

    def manifests(self, old: Mapping[str, Any], new: Mapping[str, Any]) -> None:
        old, new = _prepared(old), _prepared(new)
        before, after = _Elements(old), _Elements(new)
        old_id, new_id = old.get("id"), new.get("id")
        if old_id != new_id:
            if old_id is not None:
                self.add("removed", "major", old_id, f"the manifest's ID #{old_id}")
            if new_id is not None:
                self.add("added", "minor", new_id, f"the manifest's ID #{new_id}")
        self._root(before.root, after.root)
        for id in sorted(before.found.keys() | after.found.keys()):
            self._element(id, before.found.get(id), after.found.get(id))

    def _root(self, old: dict[str, Any], new: dict[str, Any]) -> None:
        old, new = dict(old), dict(new)
        for key in ("timetoshare", "$schema"):
            old.pop(key, None)
            new.pop(key, None)
        self._context(old.pop("@context", None), new.pop("@context", None))
        old_graphical, new_graphical = old.pop("graphical"), new.pop("graphical")
        changed = _changed_keys(old_graphical, new_graphical)
        if changed:
            self.add("graphic", "patch", None, "graphical: " + ", ".join(changed))
        self._content(None, None, old, new)

    def _context(self, old: Any, new: Any) -> None:
        old = old if isinstance(old, Mapping) else {}
        new = new if isinstance(new, Mapping) else {}
        for prefix in sorted(old.keys() | new.keys()):
            if prefix not in new:
                self.add("removed_prefix", "major", None, f"the prefix {prefix}")
            elif prefix not in old:
                self.add("added_prefix", "minor", None, f"the prefix {prefix}")
            elif _text(old[prefix]) != _text(new[prefix]):
                self.add("edited", "minor", None, f"the IRI of the prefix {prefix}")

    def _element(self, id: str, old: _Element | None, new: _Element | None) -> None:
        if old is not None and new is not None and old.definition != new.definition:
            self.add(
                "reused_id",
                REFUSED,
                id,
                f"#{id} was a {old.definition} and is now a {new.definition}",
            )
            return
        either = old or new
        assert either is not None
        if either.definition == "Elision" and (old is None or new is None):
            done = "removed" if new is None else "added"
            self.add("graphic", "patch", id, f"{_named(either, id)} {done}")
            return
        if new is None:
            self.add("removed", "major", id, f"{_named(old, id)} removed")
            return
        if old is None:
            self.add("added", "minor", id, f"{_named(new, id)} added")
            return
        if (old.owner, old.place) != (new.owner, new.place):
            where = f"#{new.owner}" if new.owner else "the manifest"
            self.add("edited", "minor", id, f"{_named(new, id)} now held by {where}")
        self._content(id, new, old.content, new.content)

    def _content(
        self,
        id: str | None,
        element: _Element | None,
        old: dict[str, Any],
        new: dict[str, Any],
    ) -> None:
        """Compare an element's own content, nested elements cut out."""
        name = _named(element, id)
        old, new = dict(old), dict(new)
        if element is not None and element.definition == "Elision":
            changed = _changed_keys(old, new)
            if changed:
                self.add("graphic", "patch", id, f"{name}: " + ", ".join(changed))
            return
        if element is not None and element.definition in _DISPLAYED:
            if _text(old.pop("display", None)) != _text(new.pop("display", None)):
                self.add("graphic", "patch", id, f"the display of {name}")
        if element is not None and element.definition == "Resource":
            if self._moved(id, old, new):
                return
        if _text(old.pop("name", None)) != _text(new.pop("name", None)):
            self.add("label", "patch", id, f"the name of {name}")
        if _text(old.pop("meta", None)) != _text(new.pop("meta", None)):
            self.add("meta", "patch", id, f"the meta of {name}")
        if element is not None and element.definition == "Group":
            self._members(id, name, old.pop("members", None), new.pop("members", None))
        self._statements(
            id, name, old.pop("statements", None), new.pop("statements", None)
        )
        self._provenance(
            id, name, old.pop("provenance", None), new.pop("provenance", None)
        )
        changed = _changed_keys(old, new)
        if changed:
            self.add("edited", "minor", id, f"{name}: " + ", ".join(changed))

    def _moved(self, id: str | None, old: dict[str, Any], new: dict[str, Any]) -> bool:
        """Whether a resource's one change is its ``url``, for the same bytes."""
        integrity = old.get("integrity")
        rest_old = {key: value for key, value in old.items() if key != "url"}
        rest_new = {key: value for key, value in new.items() if key != "url"}
        if (
            integrity is None
            or _text(old.get("url")) == _text(new.get("url"))
            or _text(rest_old) != _text(rest_new)
        ):
            return False
        self.add(
            "moved",
            "patch",
            id,
            f"Resource #{id} moved from {old.get('url')} to {new.get('url')}",
        )
        return True

    def _members(self, id: str | None, name: str, old: Any, new: Any) -> None:
        old_members = (
            Counter(_text(m) for m in old) if isinstance(old, list) else Counter()
        )
        new_members = (
            Counter(_text(m) for m in new) if isinstance(new, list) else Counter()
        )
        for member in sorted((old_members - new_members).elements()):
            self.add(
                "removed_member", "major", id, f"member #{json.loads(member)} of {name}"
            )
        for member in sorted((new_members - old_members).elements()):
            self.add(
                "added_member", "minor", id, f"member #{json.loads(member)} of {name}"
            )

    def _statements(self, id: str | None, name: str, old: Any, new: Any) -> None:
        old = old if isinstance(old, Mapping) else {}
        new = new if isinstance(new, Mapping) else {}
        for prop in sorted(old.keys() | new.keys()):
            before = Counter(_value_key(v) for v in _listed(old.get(prop)))
            after = Counter(_value_key(v) for v in _listed(new.get(prop)))
            gone, came = before - after, after - before
            if gone and came:
                self.add("edited_pair", "minor", id, f"pair {prop} of {name}")
                continue
            for _ in gone.elements():
                self.add("removed_pair", "major", id, f"pair {prop} of {name}")
            for _ in came.elements():
                self.add("added_pair", "minor", id, f"pair {prop} of {name}")
        before_nodes = dict(_node_provenance(old, ()))
        after_nodes = dict(_node_provenance(new, ()))
        for at in sorted(before_nodes.keys() & after_nodes.keys()):
            self._provenance(id, name, before_nodes[at], after_nodes[at])

    def _provenance(self, id: str | None, name: str, old: Any, new: Any) -> None:
        before, after = _entries(old), _entries(new)
        if before.keys() != after.keys():
            self.add("edited", "minor", id, f"the provenance of {name}")
        for key in sorted(before.keys() & after.keys()):
            old_beliefs, new_beliefs = before[key], after[key]
            for actor in sorted(old_beliefs.keys() | new_beliefs.keys()):
                if actor not in new_beliefs:
                    done = "removed"
                elif actor not in old_beliefs:
                    done = "added"
                elif old_beliefs[actor] != new_beliefs[actor]:
                    done = "changed"
                else:
                    continue
                self.add("belief", "patch", id, f"a belief of {actor} {done} on {name}")


def _listed(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _without_provenance(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _without_provenance(item)
            for key, item in value.items()
            if key != "provenance"
        }
    if isinstance(value, list):
        return [_without_provenance(item) for item in value]
    return value


def _value_key(value: Any) -> str:
    """A statement's value as compared: a value node without its provenance."""
    return _text(_without_provenance(value))


def _node_provenance(
    value: Any, at: tuple[str, ...]
) -> Iterator[tuple[tuple[str, ...], Any]]:
    """The provenance of every value node, by the path of properties and values."""
    if isinstance(value, Mapping):
        if "provenance" in value and at:
            yield at, value["provenance"]
        for key, item in value.items():
            if key != "provenance":
                yield from _node_provenance(item, (*at, key))
    elif isinstance(value, list):
        for item in value:
            yield from _node_provenance(item, (*at, _value_key(item)))


def _entries(value: Any) -> dict[str, dict[str, str]]:
    """Provenance entries by their content without beliefs, each actor's belief."""
    found: dict[str, dict[str, str]] = {}
    for entry in _listed(value):
        if not isinstance(entry, Mapping):
            found[_text(entry)] = {}
            continue
        rest = {key: item for key, item in entry.items() if key != "beliefs"}
        beliefs: dict[str, str] = {}
        for belief in _listed(entry.get("beliefs")):
            if isinstance(belief, Mapping):
                actor = belief.get("actor")
                beliefs[actor if isinstance(actor, str) else _text(actor)] = _text(
                    belief
                )
        found[_text(rest)] = beliefs
    return found


def _changed_keys(old: Any, new: Any) -> list[str]:
    old = old if isinstance(old, Mapping) else {}
    new = new if isinstance(new, Mapping) else {}
    return [
        key
        for key in sorted(old.keys() | new.keys())
        if key not in old or key not in new or _text(old[key]) != _text(new[key])
    ]


def manifest_step(
    old: Mapping[str, Any], new: Mapping[str, Any], path: str = ""
) -> tuple[Finding, ...]:
    """Compare two states of one manifest.

    Both are read with bare IDs, in the complete form and in canonical order,
    so the minimal and the complete form of one manifest, or two
    serializations of it, give no finding. Elements are matched by ID at any
    depth, each compared without the elements it holds, which are compared
    on their own. ``timetoshare`` and ``$schema`` take no part; a manifest
    declaring a format version this package does not read gives one finding
    ``unsupported_version``, undetermined.

    Args:
        old: The earlier manifest, as ``loads`` reads it.
        new: The later manifest.
        path: The manifest file's path, written into every finding.

    Returns:
        The findings, sorted by path, kind and ID.

    Raises:
        FileIdError: If an ID of either manifest is not written as one.
        ValueError: If either manifest cannot be put in canonical order.
    """
    for manifest in (old, new):
        version = manifest.get("timetoshare")
        if version != SCHEMA_VERSION:
            return (
                Finding(
                    "unsupported_version",
                    UNDETERMINED,
                    path,
                    None,
                    f"a manifest declares the version {version!r}; this package "
                    f"reads {SCHEMA_VERSION}",
                ),
            )
    comparison = _Comparison(path)
    comparison.manifests(old, new)
    return tuple(sorted(comparison.findings, key=_finding_key))


# Trees ----------------------------------------------------------------------


def _manifest_of(text: bytes) -> dict[str, Any] | None:
    """The manifest a file's bytes hold; ``None`` for a file that is none.

    Raises:
        ValueError: If the bytes cannot be read as JSON or YAML text.
    """
    try:
        value = loads(text.decode("utf-8"))
    except TypeError as error:
        raise ValueError(str(error)) from error
    if not isinstance(value, dict) or "timetoshare" not in value:
        return None
    return value


def _manifests(
    root: Path,
) -> tuple[dict[str, tuple[str, dict[str, Any]]], dict[str, tuple[str, str]]]:
    """The manifests under a directory by their path without extension, and the
    files there that cannot be read, with the reason."""
    found: dict[str, tuple[str, dict[str, Any]]] = {}
    unreadable: dict[str, tuple[str, str]] = {}
    if not root.is_dir():
        return found, unreadable
    for file in sorted(root.rglob("*")):
        relative = file.relative_to(root)
        if ".git" in relative.parts or file.suffix not in _SERIALIZED:
            continue
        if not file.is_file():
            continue
        key = relative.with_suffix("").as_posix()
        try:
            value = _manifest_of(file.read_bytes())
        except ValueError as error:
            unreadable.setdefault(key, (relative.as_posix(), str(error)))
            continue
        if value is not None:
            found.setdefault(key, (relative.as_posix(), value))
    return found, unreadable


def _resources(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    found: dict[str, Mapping[str, Any]] = {}
    for resource in _listed(manifest.get("resources")):
        if isinstance(resource, Mapping) and isinstance(resource.get("id"), str):
            found[resource["id"]] = resource
    return found


def _table_file(root: Path, path: str, url: Any) -> Path | None:
    """The file a resource's ``url`` names inside a tree; ``None`` outside it."""
    if not isinstance(url, str) or "://" in url or url.startswith("/"):
        return None
    return root / PurePosixPath(path).parent / url


def _table_findings(
    old_root: Path,
    new_root: Path,
    old_path: str,
    new_path: str,
    old: Mapping[str, Any],
    new: Mapping[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    before, after = _resources(old), _resources(new)
    for id in sorted(before.keys() & after.keys()):
        old_file = _table_file(old_root, old_path, before[id].get("url"))
        new_file = _table_file(new_root, new_path, after[id].get("url"))
        if old_file is None or new_file is None:
            continue
        old_held, new_held = old_file.is_file(), new_file.is_file()
        if not old_held and not new_held:
            continue
        bare = id[1:] if id.startswith("#") else id
        url = after[id].get("url")
        if old_held != new_held:
            side = "earlier" if not old_held else "later"
            findings.append(
                Finding(
                    "changed_table",
                    UNDETERMINED,
                    new_path,
                    bare,
                    f"{url} is missing from the {side} tree",
                )
            )
            continue
        if old_file.read_bytes() == new_file.read_bytes():
            continue
        kind = after[id].get("type")
        findings.extend(_rows(old_file, new_file, kind, new_path, bare, str(url)))
    return findings


def _rows(
    old_file: Path, new_file: Path, kind: Any, path: str, id: str, url: str
) -> list[Finding]:
    """The findings between two versions of one table."""
    if kind not in TABLE_TYPES:
        return [
            Finding(
                "changed_table",
                UNDETERMINED,
                path,
                id,
                f"{url} changed; tables of the type {kind} are not compared",
            )
        ]
    try:
        import pyarrow.parquet as pq

        from .tables import row_provenance
    except ImportError:
        return [
            Finding(
                "changed_table",
                UNDETERMINED,
                path,
                id,
                f"{url} changed; comparing its rows needs pyarrow: pip install "
                f'"timetoshare[tables]"',
            )
        ]
    try:
        old_rows = _keyed(pq.read_table(old_file), row_provenance)
        new_rows = _keyed(pq.read_table(new_file), row_provenance)
    except (OSError, ValueError, KeyError) as error:
        return [
            Finding(
                "changed_table",
                UNDETERMINED,
                path,
                id,
                f"{url} changed and cannot be read by rows: {error}",
            )
        ]
    findings: list[Finding] = []
    for row in sorted(old_rows.keys() | new_rows.keys()):
        if row not in new_rows:
            findings.append(
                Finding("removed_row", "major", path, row, f"row {row} of {url}")
            )
        elif row not in old_rows:
            findings.append(
                Finding("added_row", "minor", path, row, f"row {row} of {url}")
            )
        elif _text(old_rows[row]) != _text(new_rows[row]):
            findings.append(_row_change(old_rows[row], new_rows[row], path, row, url))
    return findings


def _keyed(table: Any, row_provenance: Any) -> dict[str, dict[str, Any]]:
    if "id" not in table.column_names:
        raise KeyError("the table has no column id")
    rows = table.to_pylist()
    if "provenance" in table.column_names:
        for row, provenance in zip(rows, row_provenance(table), strict=True):
            row["provenance"] = provenance
    return {str(row["id"]): row for row in rows}


def _row_change(
    old: dict[str, Any], new: dict[str, Any], path: str, id: str, url: str
) -> Finding:
    old_rest = {key: value for key, value in old.items() if key != "provenance"}
    new_rest = {key: value for key, value in new.items() if key != "provenance"}
    if _text(old_rest) == _text(new_rest):
        old_entry = old.get("provenance") or {}
        new_entry = new.get("provenance") or {}
        if _text({k: v for k, v in old_entry.items() if k != "beliefs"}) == _text(
            {k: v for k, v in new_entry.items() if k != "beliefs"}
        ):
            return Finding(
                "belief", "patch", path, id, f"the beliefs of row {id} of {url}"
            )
    return Finding("edited_row", "minor", path, id, f"row {id} of {url}")


def tree_step(old_root: Path, new_root: Path) -> StepReport:
    """Compare two trees of manifests and the tables they name.

    A manifest is every ``.yaml``, ``.yml`` or ``.json`` file outside ``.git``
    that ``loads`` reads as an object holding ``timetoshare``. Manifests are
    matched by their path without the extension, so a manifest rewritten in
    another serialization is the same manifest. A file that is a manifest in
    one tree and cannot be read in the other gives ``unreadable_manifest``,
    undetermined, never a removal or an addition. For a resource of the type
    ``MatchClaim`` or ``Projection`` in both states whose file's bytes
    differ, the rows are compared by their ``id``, which needs pyarrow;
    without it, or for a table of any other type, the change is
    undetermined.

    Args:
        old_root: The directory of the earlier state; a missing directory is
            an empty tree.
        new_root: The directory of the later state.
    """
    old_root, new_root = Path(old_root), Path(new_root)
    (before, old_unreadable), (after, new_unreadable) = (
        _manifests(old_root),
        _manifests(new_root),
    )
    findings: list[Finding] = []
    for key in sorted(before.keys() | after.keys()):
        for side, held, unreadable in (
            ("later", after, new_unreadable),
            ("earlier", before, old_unreadable),
        ):
            if key not in held and key in unreadable:
                path, reason = unreadable[key]
                findings.append(
                    Finding(
                        "unreadable_manifest",
                        UNDETERMINED,
                        path,
                        None,
                        f"the manifest cannot be read in the {side} tree: {reason}",
                    )
                )
        if key in new_unreadable and key not in after:
            continue
        if key in old_unreadable and key not in before:
            continue
        if key not in after:
            path = before[key][0]
            findings.append(
                Finding("removed_manifest", "major", path, None, f"the manifest {path}")
            )
            continue
        if key not in before:
            path = after[key][0]
            findings.append(
                Finding("added_manifest", "minor", path, None, f"the manifest {path}")
            )
            continue
        (old_path, old), (new_path, new) = before[key], after[key]
        try:
            found = manifest_step(old, new, new_path)
        except ValueError as error:
            found = (
                Finding(
                    "unreadable_manifest",
                    UNDETERMINED,
                    new_path,
                    None,
                    f"the manifest cannot be compared: {error}",
                ),
            )
        findings.extend(found)
        if not any(f.step == UNDETERMINED for f in found):
            findings.extend(
                _table_findings(old_root, new_root, old_path, new_path, old, new)
            )
    return StepReport.of(findings)


# Git ------------------------------------------------------------------------


def _git(
    repo: Path, *args: str, input: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, input=input
    )


def _failed(done: subprocess.CompletedProcess[bytes]) -> ValueError:
    return ValueError(done.stderr.decode(errors="replace").strip())


def _files(repo: Path, ref: str | None) -> dict[str, str] | None:
    """The regular files of a reference's tree, or of the index for ``None``,
    as path and blob name; ``None`` for ``HEAD`` without commits.

    Raises:
        ValueError: If the reference names no tree, or git fails.
    """
    if ref is None:
        done = _git(repo, "ls-files", "--stage", "-z")
    else:
        tree = _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{tree}}")
        if tree.returncode:
            if ref == "HEAD":
                return None
            raise ValueError(f"'{ref}' names no commit of {repo}")
        name = tree.stdout.decode().strip()
        done = _git(repo, "ls-tree", "-r", "--full-tree", "-z", name)
    if done.returncode:
        raise _failed(done)
    files: dict[str, str] = {}
    for entry in done.stdout.decode("utf-8", errors="surrogateescape").split("\0"):
        if not entry:
            continue
        info, path = entry.split("\t", 1)
        fields = info.split()
        mode, blob = fields[0], fields[1] if ref is None else fields[2]
        if mode in ("100644", "100755") and (ref is not None or fields[2] == "0"):
            files[path] = blob
    return files


def _blobs(repo: Path, names: set[str]) -> dict[str, bytes]:
    """The contents of blobs, read by one ``git cat-file --batch``."""
    if not names:
        return {}
    ordered = sorted(names)
    done = _git(
        repo, "cat-file", "--batch", input="".join(f"{n}\n" for n in ordered).encode()
    )
    if done.returncode:
        raise _failed(done)
    found: dict[str, bytes] = {}
    out, at = done.stdout, 0
    for name in ordered:
        end = out.index(b"\n", at)
        header = out[at:end].split()
        at = end + 1
        if len(header) < 3:
            raise ValueError(f"git holds no object {name}")
        size = int(header[2])
        found[name] = out[at : at + size]
        at += size + 1
    return found


def _manifest_files(files: Mapping[str, str]) -> dict[str, str]:
    return {
        path: blob
        for path, blob in files.items()
        if PurePosixPath(path).suffix in _SERIALIZED
    }


def _named_tables(path: str, text: bytes) -> Iterator[str]:
    """The paths, inside the tree, of the files a manifest's resources name."""
    try:
        manifest = _manifest_of(text)
    except ValueError:
        return
    for resource in _listed((manifest or {}).get("resources")):
        url = resource.get("url") if isinstance(resource, Mapping) else None
        if not isinstance(url, str) or "://" in url or url.startswith("/"):
            continue
        named = posixpath.normpath(posixpath.join(posixpath.dirname(path), url))
        if named != ".." and not named.startswith("../"):
            yield named


def _materialise(repo: Path, ref: str | None, target: Path) -> None:
    """Write the manifests of a reference's tree, or of the index for ``None``,
    and the table files their resources name, into ``target``.

    Only files ending ``.yaml``, ``.yml`` or ``.json`` and the files the
    resources of those that are manifests name are read from git, whatever
    the repository's ``export-ignore`` attributes say.
    """
    target.mkdir(parents=True, exist_ok=True)
    files = _files(repo, ref)
    if files is None:
        return
    manifests = _manifest_files(files)
    texts = _blobs(repo, set(manifests.values()))
    written = {path: texts[blob] for path, blob in manifests.items()}
    tables = {
        named: files[named]
        for path, text in written.items()
        for named in _named_tables(path, text)
        if named in files and named not in written
    }
    contents = _blobs(repo, set(tables.values()))
    written.update({path: contents[blob] for path, blob in tables.items()})
    for path, data in written.items():
        file = target / PurePosixPath(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)


def _held_ids(repo: Path, ref: str) -> dict[str, dict[str, str]]:
    """The element type of every ID each manifest of a reference's tree holds,
    by the manifest's path without extension; unreadable manifests held none."""
    files = _files(repo, ref) or {}
    manifests = _manifest_files(files)
    texts = _blobs(repo, set(manifests.values()))
    held: dict[str, dict[str, str]] = {}
    for path, blob in sorted(manifests.items()):
        try:
            manifest = _manifest_of(texts[blob])
            if manifest is None or manifest.get("timetoshare") != SCHEMA_VERSION:
                continue
            found = _Elements(_prepared(manifest)).found
        except ValueError:
            continue
        key = PurePosixPath(path).with_suffix("").as_posix()
        held.setdefault(key, {id: e.definition for id, e in found.items()})
    return held


def _lines(done: subprocess.CompletedProcess[bytes]) -> list[str]:
    if done.returncode:
        raise _failed(done)
    return [line for line in done.stdout.decode().splitlines() if line]


def _history(
    repo: Path, old_ref: str, new_ref: str | None, new_root: Path, found: list[Finding]
) -> list[Finding]:
    """``reused_id`` for every ID of the later state that an earlier tagged
    state held for an element that is gone since or of another type."""
    tip = new_ref or "HEAD"
    tips = [
        ref
        for ref in (tip, old_ref)
        if _git(
            repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"
        ).returncode
        == 0
    ]
    if not tips:
        return []
    tags: set[str] = set()
    for ref in tips:
        tags.update(_lines(_git(repo, "tag", "--merged", ref)))
    states = [(tag, f"refs/tags/{tag}") for tag in sorted(tags)]
    if old_ref in tips:
        states.append((old_ref, old_ref))
    commits = {
        label: _lines(_git(repo, "rev-parse", f"{ref}^{{commit}}"))[0]
        for label, ref in states
    }
    order = {
        commit: index
        for index, commit in enumerate(
            _lines(_git(repo, "rev-list", "--topo-order", "--reverse", *tips))
        )
    }
    states.sort(key=lambda state: (order.get(commits[state[0]], -1), state[0]))
    held = {label: _held_ids(repo, ref) for label, ref in states}
    seen = {(f.path, f.id) for f in found if f.kind == "reused_id"}
    findings: list[Finding] = []
    now, _ = _manifests(new_root)
    for key, (path, manifest) in sorted(now.items()):
        try:
            elements = _Elements(_prepared(manifest)).found
        except ValueError:
            continue
        for id, element in sorted(elements.items()):
            if (path, id) in seen:
                continue
            detail = _reuse(id, element.definition, key, states, commits, order, held)
            if detail is not None:
                findings.append(Finding("reused_id", REFUSED, path, id, detail))
    return findings


def _reuse(
    id: str,
    definition: str,
    key: str,
    states: list[tuple[str, str]],
    commits: Mapping[str, str],
    order: Mapping[str, int],
    held: Mapping[str, Mapping[str, Mapping[str, str]]],
) -> str | None:
    """How the tagged states show an ID given again; ``None`` where they do not."""
    for index, (label, _) in enumerate(states):
        earlier = held[label].get(key, {}).get(id)
        if earlier is None:
            continue
        if earlier != definition:
            return f"#{id} was a {earlier} in {label} and is now a {definition}"
        at = order.get(commits[label], -1)
        for later, _ in states[index + 1 :]:
            if order.get(commits[later], -1) > at and id not in held[later].get(
                key, {}
            ):
                return (
                    f"#{id} was a {earlier} in {label}, is gone in {later} and is "
                    f"now a {definition} again"
                )
    return None


def git_step(
    old_ref: str, new_ref: str | None, repo: Path, history: bool = False
) -> StepReport:
    """Compare the trees of two git references of a repository.

    Only the manifests and the table files their resources name are read
    from git (``git ls-tree``, ``git ls-files --stage`` and ``git cat-file
    --batch``), so the rest of the tree, audio included, is never written
    out.

    Args:
        old_ref: The earlier reference, such as a release tag. ``HEAD`` in a
            repository without commits is an empty tree.
        new_ref: The later reference; ``None`` for the index, the changes
            staged for the next commit.
        repo: A directory inside the repository; its whole tree is compared.
        history: Also check every tag reachable from ``new_ref`` (``HEAD``
            for the index) or from ``old_ref``, and ``old_ref`` itself: an ID
            of the later state that one of these held for an element of
            another type, or for an element that a later one of them no
            longer holds, gives ``reused_id``, refused. The states are
            ordered as ``git rev-list --topo-order`` lists their commits.

    Raises:
        ValueError: If a reference names no commit, or git fails.
    """
    top = _git(Path(repo), "rev-parse", "--show-toplevel")
    if top.returncode:
        raise _failed(top)
    root = Path(top.stdout.decode().strip())
    with tempfile.TemporaryDirectory() as scratch:
        old_dir, new_dir = Path(scratch, "old"), Path(scratch, "new")
        _materialise(root, old_ref, old_dir)
        _materialise(root, new_ref, new_dir)
        report = tree_step(old_dir, new_dir)
        if not history:
            return report
        found = list(report.findings)
        return StepReport.of(found + _history(root, old_ref, new_ref, new_dir, found))
