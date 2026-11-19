"""Statement rules: the context, reserved keys, IRIs and provenance of statements.

The schema checks the shape of ``@context``, every ``statements`` container
and every ``provenance`` list; the rules here reach beyond it, in this order:
a manifest carrying statements or provenance holds ``@context``
(``context``); no element of the manifest uses a key JSON-LD would read
(``reserved_key``); then, subject by subject, the subject's ID is an IRI
fragment, every compact IRI names a declared prefix (``iri``), every ``#``
reference names an element (``dangling_target``), a node naming an element
holds its ID alone (``element_value``), a statement value is no float
(``representation``), a date is a calendar day (``calendar_date``), and each
provenance entry matches a pair exactly when it is ``confirmed``
(``provenance_match``) and repeats no earlier entry's pair
(``provenance_duplicate``). The manifest is read with bare IDs; the IRIs of
statements are the same in either form. The walks read any value, so a
reader of part of a manifest can check its statements alone.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any

from ..serialization import spell
from ..statements import (
    BLANK,
    FORMAT_CONTEXT,
    URI_SCHEMES,
    _prefixes,
    calendar_date,
    same_pair,
    statement_positions,
    subjects,
)
from .diagnostics import (
    SchemaValidationError,
    _entries,
    _Path,
    string_id,
    timestamps_of,
    tree_ids,
)

_FRAGMENT = re.compile(
    "(?:[A-Za-z0-9\\-._~!$&'()*+,;=:@/?\\u0080-\\U0010ffff]|%[0-9A-Fa-f]{2})*"
)
_BLANK = re.compile(BLANK)
_SCHEME = re.compile("[A-Za-z][A-Za-z0-9_+.-]*:")

_ALLOWED_TERMS: dict[str, frozenset[str]] = {
    "manifest": frozenset({"id", "timelines", "groups", "statements", "provenance"}),
    "timeline": frozenset({"id", "children", "regions", "statements", "provenance"}),
    "region": frozenset({"id", "statements", "provenance"}),
    "group": frozenset({"id"}),
}
"""The terms of the format's context each kind of element may use as a key."""

_NAMED = {
    "manifest": "the manifest",
    "timeline": "a timeline",
    "region": "a region",
    "group": "a group",
}


def _context_problems(manifest: Mapping[str, Any]) -> Iterator[SchemaValidationError]:
    if "@context" in manifest:
        return
    for path, element, _ in subjects(manifest):
        for key in ("provenance", "statements"):
            if key in element:
                yield SchemaValidationError(
                    "context",
                    (*path, key),
                    "statements and provenance need the manifest's @context",
                )


def _elements(
    manifest: Mapping[str, Any],
) -> Iterator[tuple[_Path, Mapping[str, Any], str]]:
    yield from subjects(manifest)
    for index, group in enumerate(_entries(manifest, "groups")):
        if isinstance(group, Mapping):
            yield ("groups", index), group, "group"


def _reserved(key: str, kind: str, prefixes: Mapping[str, str]) -> bool:
    if key.startswith("@"):
        return not (kind == "manifest" and key == "@context")
    return (
        ":" in key
        or (key in FORMAT_CONTEXT and key not in _ALLOWED_TERMS[kind])
        or key in prefixes
    )


def _reserved_key_problems(
    manifest: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    prefixes = _prefixes(manifest.get("@context"))
    for path, element, kind in _elements(manifest):
        for key in sorted(key for key in element if isinstance(key, str)):
            if _reserved(key, kind, prefixes):
                yield SchemaValidationError(
                    "reserved_key",
                    (*path, key),
                    f"'{key}' is reserved on {_NAMED[kind]}",
                )


def _manifest_ids(manifest: Mapping[str, Any]) -> set[str]:
    """Every ID of the manifest, of any kind, read wherever it is a string."""
    found = {identifier for identifier in (string_id(manifest),) if identifier}
    for index, root in enumerate(_entries(manifest, "timelines")):
        found.update(
            identifier for identifier, _ in tree_ids(root, ("timelines", index))
        )
    for entries in (
        _entries(manifest, "groups"),
        _entries(manifest, "measure_maps"),
        timestamps_of(manifest),
    ):
        found.update(
            identifier
            for identifier in (string_id(entry) for entry in entries)
            if identifier is not None
        )
    return found


def _is_fragment(text: str) -> bool:
    return _FRAGMENT.fullmatch(text) is not None and _BLANK.search(text) is None


class _Walk:
    """The subject walk of one manifest: its context and its IDs."""

    def __init__(self, manifest: Mapping[str, Any]) -> None:
        context = manifest.get("@context")
        self.context = context if isinstance(context, Mapping) else None
        self.prefixes = _prefixes(context)
        self.ids = _manifest_ids(manifest)

    def iri(self, text: str, path: _Path) -> Iterator[SchemaValidationError]:
        prefix, _, rest = text.partition(":")
        if rest.startswith("//") or prefix in self.prefixes or prefix in URI_SCHEMES:
            return
        yield SchemaValidationError(
            "iri",
            path,
            f"'{text}': the prefix '{prefix}' is not declared in @context",
        )

    def ref(self, text: str, path: _Path) -> Iterator[SchemaValidationError]:
        if _SCHEME.match(text) is not None:
            yield from self.iri(text, path)
        elif text.startswith("#") and text[1:] not in self.ids:
            yield SchemaValidationError(
                "dangling_target", path, f"'{text}' names no element of this manifest"
            )

    def annotations(
        self, pairs: list[tuple[str, Any]], provenance: list[Any], path: _Path
    ) -> Iterator[SchemaValidationError]:
        written: list[tuple[str, Any]] = []
        for index, entry in enumerate(provenance):
            pair = (entry["property"], entry["value"])
            at = (*path, index)
            stated = any(same_pair(self.context, held, pair) for held in pairs)
            status = entry["status"]
            if status == "confirmed" and not stated:
                yield SchemaValidationError(
                    "provenance_match",
                    at,
                    "no pair of this subject matches the entry; an entry that "
                    "matches none is proposed or rejected",
                )
            elif status != "confirmed" and stated:
                yield SchemaValidationError(
                    "provenance_match",
                    at,
                    f"the pair is stated; a {status} pair is never stated",
                )
            earlier = next(
                (
                    number
                    for number, other in enumerate(written)
                    if same_pair(self.context, other, pair)
                ),
                None,
            )
            if earlier is not None:
                yield SchemaValidationError(
                    "provenance_duplicate",
                    at,
                    f"the entry repeats the pair of entry {earlier}",
                )
            written.append(pair)

    def problems(self, manifest: Mapping[str, Any]) -> Iterator[SchemaValidationError]:
        for kind, path, value in statement_positions(manifest):
            if kind == "subject":
                identifier = value.get("id")
                if isinstance(identifier, str) and not _is_fragment(identifier):
                    yield SchemaValidationError(
                        "iri",
                        (*path, "id"),
                        f"the ID '{identifier}' of an element with statements is "
                        "no IRI fragment",
                    )
            elif kind == "iri":
                yield from self.iri(value, path)
            elif kind == "ref":
                yield from self.ref(value, path)
            elif kind == "date":
                try:
                    calendar_date(value)
                except ValueError as error:
                    yield SchemaValidationError("calendar_date", path, str(error))
            elif kind == "float":
                yield SchemaValidationError(
                    "representation",
                    path,
                    "a statement value is an integer or a string, never a float: "
                    f"{spell(value)}",
                )
            elif kind == "element":
                yield SchemaValidationError(
                    "element_value",
                    path,
                    f"'{value['id']}' names an element; a value naming an element "
                    "holds its id alone",
                )
            elif kind == "annotated":
                yield from self.annotations(*value)


def statement_rule_problems(
    manifest: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """Yield every problem of the statement rules, in the order of the rules.

    The context rule over every subject, then the reserved keys of the
    manifest, the timelines and regions in subject order and the groups,
    each element's keys in code-point order, then the subject walk. The
    manifest is taken with bare IDs and its statements and provenance as
    schema-checked; everything else is read wherever it has the expected
    type.
    """
    yield from _context_problems(manifest)
    yield from _reserved_key_problems(manifest)
    yield from _Walk(manifest).problems(manifest)


def statement_warnings(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the warnings of a valid manifest, sorted by path, then code.

    ``context_absent`` at the root for a manifest without ``@context``;
    ``bundle_blank`` at ``statements`` (else ``provenance``) for a manifest
    stating pairs or provenance without an ``id``, whose subject is then a
    blank node.
    """
    found: list[dict[str, Any]] = []
    if "@context" not in manifest:
        found.append(
            {
                "code": "context_absent",
                "path": [],
                "message": "the manifest has no @context",
            }
        )
    if "id" not in manifest:
        key = next(
            (key for key in ("statements", "provenance") if key in manifest), None
        )
        if key is not None:
            found.append(
                {
                    "code": "bundle_blank",
                    "path": [key],
                    "message": "the manifest has statements but no ID; its subject "
                    "is a blank node",
                }
            )
    return sorted(found, key=lambda warning: (warning["path"], warning["code"]))
