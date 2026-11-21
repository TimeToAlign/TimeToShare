"""Property–value statements about the things a manifest's elements stand for.

The bundle (the manifest), every timeline at any depth and every region may
carry ``statements``: an object whose keys are ``type`` ("is a") or property
IRIs, written compactly with a prefix of the manifest's ``@context`` or in
full, and whose values are the non-empty lists of that property's values. A
value is a literal (a string, an integer or a boolean), a value object
(``@value`` with ``@language`` or ``@type``), a node (a thing: its ``id``
where it has one, ``type``, a ``label`` kept as a cache, its own pairs as
property-IRI keys and its own ``provenance``) or ``{"list": [...]}`` for
values in order. A string is never read as an IRI: a thing is ``{"id": ...}``.

Beside the container, ``provenance`` holds an entry per pair (the entry of
the provenance schema, ``provenance.schema.json``): it repeats a pair's
``property`` and ``value`` and says who stated it (``stated_by``), when
(``date``), how (``method``, ``service``, ``basis``, ``match``), with a
``note``, and who believes it (``beliefs``: per actor one of the strings
``"true"``, ``"false"`` and ``"unlikely"``). An entry whose pair is stated
annotates it; an entry whose pair is not stated is a candidate, which an
actor believing it ``"false"`` is not offered again. Nothing derives a
truth value from the beliefs.
The manifest's inline JSON-LD context ``@context`` holds the format's terms
(``FORMAT_CONTEXT``) and the prefixes the statements use, which makes the
manifest a YAML-LD document whose statements read as plain triples and whose
annotations read as RDF reification of those triples.

A subject is addressed by its path in the manifest: ``()`` the bundle, a path
ending in ``("timelines" | "children" | "regions", i)`` an element, a path
passing on through ``statements`` to an item of a list of values a value
node. Every function is pure: it
returns a new value and leaves its argument as it is. IRIs inside
``statements`` and ``provenance``, the references to elements (``{"id":
"#clt_1"}``) included, are identical in a manifest file and in memory, so
every function reads either ID form. The JavaScript package offers the same
functions (``withPair``, ``samePair``, ...) with the same values and the
same messages.
"""

from __future__ import annotations

import copy
import datetime
import re
from collections.abc import Collection, Iterator, Mapping, Sequence
from typing import Any, Literal, cast

from .serialization import spell
from .validation.diagnostics import _Path, json_pointer

__all__ = [
    "BELIEFS",
    "BELIEF_STATES",
    "BLANK",
    "DEFAULT_BELIEFS",
    "FORMAT_CONTEXT",
    "MATCHES",
    "METHODS",
    "NAMESPACE",
    "BeliefState",
    "candidates",
    "check_belief_filter",
    "compact_iri",
    "entries",
    "expand_iri",
    "pairs",
    "same_pair",
    "subject_path",
    "subjects",
    "used_prefixes",
    "with_belief",
    "with_candidate",
    "with_context",
    "with_pair",
    "with_references_renamed",
    "without_pair",
]

NAMESPACE = "https://timetoalign.github.io/timetoshare/ns#"
"""The namespace of the format's own provenance properties and their words."""

_RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_RDFS = "http://www.w3.org/2000/01/rdf-schema#"
_SKOS = "http://www.w3.org/2004/02/skos/core#"
_PROV = "http://www.w3.org/ns/prov#"

FORMAT_CONTEXT: dict[str, Any] = {
    "@version": 1.1,
    "id": "@id",
    "type": "@type",
    "statements": "@nest",
    "list": "@list",
    "timelines": "@included",
    "children": "@included",
    "regions": "@included",
    "groups": "@included",
    "label": _RDFS + "label",
    "provenance": {"@reverse": _RDF + "subject"},
    "property": {"@id": _RDF + "predicate", "@type": "@vocab"},
    "value": _RDF + "object",
    "stated_by": {"@id": _PROV + "wasAttributedTo", "@type": "@id"},
    "date": {
        "@id": "http://purl.org/dc/terms/date",
        "@type": "http://www.w3.org/2001/XMLSchema#date",
    },
    "method": {"@id": NAMESPACE + "method", "@type": "@vocab"},
    "service": {"@id": NAMESPACE + "service", "@type": "@id"},
    "basis": {"@id": _PROV + "hadPrimarySource", "@type": "@id"},
    "match": {"@id": NAMESPACE + "match", "@type": "@vocab"},
    "note": _RDFS + "comment",
    "beliefs": NAMESPACE + "beliefs",
    "actor": {"@id": NAMESPACE + "actor", "@type": "@id"},
    "belief": {"@id": NAMESPACE + "belief", "@type": "@vocab"},
    "manual": NAMESPACE + "Manual",
    "reconciled": NAMESPACE + "Reconciled",
    "imported": NAMESPACE + "Imported",
    "inferred": NAMESPACE + "Inferred",
    "true": NAMESPACE + "True",
    "false": NAMESPACE + "False",
    "unlikely": NAMESPACE + "Unlikely",
    "exact": _SKOS + "exactMatch",
    "close": _SKOS + "closeMatch",
    "broad": _SKOS + "broadMatch",
    "narrow": _SKOS + "narrowMatch",
    "related": _SKOS + "relatedMatch",
}
"""The format's terms of ``@context``, each exactly as the schema fixes it.

The 35 terms and no prefix; treat it as read-only. ``with_context`` adds the
prefixes a manifest uses.
"""

BELIEFS = ("true", "false", "unlikely")
"""The beliefs an actor may hold in an item, strings in the schema's order."""

BeliefState = Literal["true", "undecided", "unlikely", "false"]
"""An item's state for one actor: the actor's belief in it, or ``"undecided"``
where the actor holds none."""

BELIEF_STATES: tuple[BeliefState, ...] = ("true", "undecided", "unlikely", "false")
"""The four states of the belief filter, in that order."""

DEFAULT_BELIEFS: tuple[BeliefState, ...] = ("true", "undecided", "unlikely")
"""The states the belief filter keeps by default: every state but ``"false"``."""


def check_belief_filter(beliefs: Collection[str]) -> frozenset[BeliefState]:
    """Return the states a belief filter keeps, checked.

    Args:
        beliefs: A collection of :data:`BELIEF_STATES`, in any order; empty
            keeps none.

    Raises:
        ValueError: If ``beliefs`` is a single string, or names a word that is
            none of :data:`BELIEF_STATES` (the first by code point is named;
            a member that is no string is spelled as :func:`spell` spells it).
    """
    if isinstance(beliefs, str):
        raise ValueError(
            "the belief filter takes a collection of states, not the string "
            f"'{beliefs}': write ['{beliefs}']"
        )
    states = frozenset(beliefs)
    unknown = sorted(
        state if isinstance(state, str) else spell(state)
        for state in states - set(BELIEF_STATES)
    )
    if unknown:
        raise ValueError(
            f"'{unknown[0]}' is no belief state: write 'true', 'undecided', "
            "'unlikely' or 'false'"
        )
    return cast(frozenset[BeliefState], states)


METHODS = ("manual", "reconciled", "imported", "inferred")
"""The words of a provenance entry's ``method``; any other method is an IRI."""

MATCHES = ("exact", "close", "broad", "narrow", "related")
"""The words of a provenance entry's ``match``, the SKOS mapping properties."""

BLANK = (
    "[\\u0000-\\u0020\\u007f-\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029"
    "\\u202f\\u205f\\u3000\\ufeff]"
)
"""White space and control characters, which no IRI holds.

The class the schema's ``Iri``, ``IriReference`` and ``PrefixIri`` refuse,
written out because Python's ``\\s`` and JavaScript's ``\\s`` differ.
"""

URI_SCHEMES = ("info", "mailto", "tag", "urn")
"""The URI schemes read as such where they stand before a colon, never as prefixes."""

RDF_TYPE = _RDF + "type"
"""The IRI the key ``type`` stands for."""

NODE_MEMBERS = ("id", "label", "provenance")
"""The keys of a value node that are no pair of it."""

_SCHEME = re.compile("[A-Za-z][A-Za-z0-9_+.-]*:")
_PROPERTY = re.compile("[A-Za-z][A-Za-z0-9_+.-]*:.")
_BLANK = re.compile(BLANK)
_DATE = re.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}")
_ELEMENT_LISTS = ("timelines", "children", "regions")


def calendar_date(text: str) -> datetime.date:
    """Read a date written ``YYYY-MM-DD``, a day of the Gregorian calendar.

    The calendar's years run from 1 to 9999, its months from 1 to 12, and
    February has 29 days in a year divisible by 4 and not by 100, or by 400.
    The JavaScript package refuses the same texts with the same message.

    Raises:
        ValueError: If ``text`` is not written so or names a day the
            calendar lacks, such as ``2026-02-30``.
    """
    if _DATE.fullmatch(text) is not None:
        try:
            return datetime.date.fromisoformat(text)
        except ValueError:
            pass
    raise ValueError(f"'{text}' is no Gregorian calendar date written YYYY-MM-DD")


def _prefixes(context: Any) -> Mapping[str, str]:
    """The prefixes a context declares: its keys that are no format term."""
    if not isinstance(context, Mapping):
        return {}
    return {
        key: value
        for key, value in context.items()
        if key not in FORMAT_CONTEXT and isinstance(value, str)
    }


def _term_iri(term: str) -> str | None:
    """The IRI a format term maps to, or ``None`` where it maps to a keyword."""
    if term == "type":
        return RDF_TYPE
    mapped = FORMAT_CONTEXT.get(term)
    if isinstance(mapped, Mapping):
        mapped = mapped.get("@id")
    if isinstance(mapped, str) and not mapped.startswith("@"):
        return mapped
    return None


def expand_iri(context: Mapping[str, Any] | None, text: str) -> str | None:
    """Return the absolute IRI ``text`` stands for under ``context``, or ``None``.

    ``type`` is ``rdf:type``; another format term mapping to an IRI is that
    IRI; ``p:rest`` is ``text`` itself when ``rest`` begins with ``//`` or
    ``p`` is one of the URI schemes ``info``, ``mailto``, ``tag`` and
    ``urn``, and the namespace of ``p`` followed by ``rest`` when ``context``
    declares the prefix ``p``. Anything else expands to nothing.
    """
    if not isinstance(text, str):
        return None
    if text in FORMAT_CONTEXT:
        return _term_iri(text)
    prefix, colon, rest = text.partition(":")
    if not colon:
        return None
    if rest.startswith("//") or prefix in URI_SCHEMES:
        return text
    namespace = _prefixes(context).get(prefix)
    return None if namespace is None else namespace + rest


def _is_iri(text: str) -> bool:
    """Whether ``text`` begins with a scheme or a prefix: no relative reference."""
    return _SCHEME.match(text) is not None


def _prefix_of(text: str) -> str | None:
    """The prefix of a compact IRI, or ``None`` for an absolute IRI or no IRI."""
    prefix, colon, rest = text.partition(":")
    if not colon or rest.startswith("//") or prefix in URI_SCHEMES:
        return None
    return prefix


# The walk of statements -----------------------------------------------------

Position = tuple[str, _Path, Any]
"""A position of the statements of a manifest: ``(kind, path, value)``.

``subject`` an element carrying statements or provenance, before its pairs;
``iri`` an IRI; ``ref`` an IRI or a relative reference; ``date`` an entry's
date; ``float`` a statement value that is a float; ``element`` a node whose
``id`` names an element and that holds another key; ``annotated`` the end
of a subject with provenance, its value ``(pairs, entries, path of
provenance)``.
"""


def _entries_of(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def subjects(manifest: Any) -> Iterator[tuple[_Path, Mapping[str, Any], str]]:
    """Yield the elements that may carry statements, in subject order.

    The manifest, then root by root the timeline, its regions in array
    order and its children, depth first; each with its path and its kind
    (``manifest``, ``timeline``, ``region``). An entry that is no object is
    passed over, so the walk reads any value.
    """
    if not isinstance(manifest, Mapping):
        return
    yield (), manifest, "manifest"

    def visit(timeline: Any, path: _Path) -> Iterator[tuple[_Path, Mapping, str]]:
        if not isinstance(timeline, Mapping):
            return
        yield path, timeline, "timeline"
        for index, region in enumerate(_entries_of(timeline.get("regions"))):
            if isinstance(region, Mapping):
                yield (*path, "regions", index), region, "region"
        for index, child in enumerate(_entries_of(timeline.get("children"))):
            yield from visit(child, (*path, "children", index))

    for index, root in enumerate(_entries_of(manifest.get("timelines"))):
        yield from visit(root, ("timelines", index))


def container_pairs(container: Any) -> list[tuple[str, Any]]:
    """The pairs of a container: keys in code-point order, values in list order."""
    if not isinstance(container, Mapping):
        return []
    found: list[tuple[str, Any]] = []
    for key in sorted(container):
        found.extend((key, value) for value in _entries_of(container[key]))
    return found


def _node_container(node: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in node.items() if key not in NODE_MEMBERS}


def _is_value_object(value: Any) -> bool:
    return isinstance(value, Mapping) and "@value" in value


def _is_ordered(value: Any) -> bool:
    return isinstance(value, Mapping) and "list" in value


def _is_node(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and not _is_value_object(value)
        and not _is_ordered(value)
    )


def _visit_value(value: Any, path: _Path) -> Iterator[Position]:
    if isinstance(value, float):
        yield "float", path, value
    elif not isinstance(value, Mapping):
        return
    elif _is_ordered(value):
        for index, item in enumerate(_entries_of(value["list"])):
            yield from _visit_value(item, (*path, "list", index))
    elif _is_value_object(value):
        if isinstance(value.get("@type"), str):
            yield "iri", (*path, "@type"), value["@type"]
    else:
        identifier = value.get("id")
        if isinstance(identifier, str):
            yield "ref", (*path, "id"), identifier
            if identifier.startswith("#") and len(value) > 1:
                yield "element", path, value
        yield from _visit_subject(
            _node_container(value), path, value.get("provenance"), path
        )


def _visit_entry(entry: Mapping[str, Any], path: _Path) -> Iterator[Position]:
    for key in sorted(entry):
        member, at = entry[key], (*path, key)
        if key in ("basis", "stated_by"):
            for index, item in enumerate(_entries_of(member)):
                if isinstance(item, str):
                    yield "ref", (*at, index), item
        elif key == "beliefs":
            for index, belief in enumerate(_entries_of(member)):
                if not isinstance(belief, Mapping):
                    continue
                for name in sorted(belief):
                    item = belief[name]
                    if name == "actor" and isinstance(item, str):
                        yield "ref", (*at, index, name), item
                    elif name == "date" and isinstance(item, str):
                        yield "date", (*at, index, name), item
        elif key == "date" and isinstance(member, str):
            yield "date", at, member
        elif key == "method" and isinstance(member, str) and member not in METHODS:
            yield "iri", at, member
        elif key == "property" and isinstance(member, str):
            yield "iri", at, member
        elif key == "service" and isinstance(member, str):
            yield "ref", at, member
        elif key == "value":
            yield from _visit_value(member, at)


def _visit_subject(
    container: Any, key_path: _Path, provenance: Any, subject: _Path
) -> Iterator[Position]:
    if isinstance(container, Mapping):
        for key in sorted(container):
            at = (*key_path, key)
            if key == "type":
                for index, item in enumerate(_entries_of(container[key])):
                    if isinstance(item, str):
                        yield "iri", (*at, index), item
                continue
            yield "iri", at, key
            for index, item in enumerate(_entries_of(container[key])):
                yield from _visit_value(item, (*at, index))
    if not isinstance(provenance, list):
        return
    at = (*subject, "provenance")
    for index, entry in enumerate(provenance):
        if isinstance(entry, Mapping):
            yield from _visit_entry(entry, (*at, index))
    yield "annotated", subject, (container_pairs(container), provenance, at)


def statement_positions(manifest: Any) -> Iterator[Position]:
    """Yield every position of the statements of a manifest, in the order of the rules.

    Subject by subject (``subjects``), each element carrying ``statements``
    or ``provenance``: the element itself, then its container's keys in
    code-point order (each ``type`` item an IRI; any other key an IRI, then
    its values), then its provenance entries, each entry's keys in
    code-point order, then the end of the subject. A value node is visited
    where it stands: its ``id``, the node if it names an element and holds
    another key, then its own pairs and provenance as a subject's.
    """
    for path, element, _ in subjects(manifest):
        if "statements" not in element and "provenance" not in element:
            continue
        yield "subject", path, element
        yield from _visit_subject(
            element.get("statements"),
            (*path, "statements"),
            element.get("provenance"),
            path,
        )


def used_prefixes(manifest: Mapping[str, Any]) -> list[str]:
    """Return the sorted names of the prefixes the statements of a manifest use.

    Every ``p`` of a ``p:rest`` (``rest`` not beginning with ``//``, ``p``
    none of the URI schemes ``info``, ``mailto``, ``tag`` and ``urn``) at
    every IRI position of every subject's statements and provenance.
    """
    found: set[str] = set()
    for kind, _, text in statement_positions(manifest):
        if kind == "iri" or (kind == "ref" and _is_iri(text)):
            prefix = _prefix_of(text)
            if prefix is not None:
                found.add(prefix)
    return sorted(found)


def with_context(
    manifest: Mapping[str, Any], prefixes: Mapping[str, str]
) -> dict[str, Any]:
    """Return the manifest with the format's terms and its prefixes in ``@context``.

    Each prefix of ``used_prefixes`` takes its namespace from the manifest's
    own ``@context`` where it declares the prefix, else from ``prefixes``; a
    prefix the statements do not use is dropped.

    Raises:
        ValueError: If a prefix the statements use is declared neither in the
            manifest's ``@context`` nor in ``prefixes``.
    """
    declared = _prefixes(manifest.get("@context"))
    context = copy.deepcopy(FORMAT_CONTEXT)
    for prefix in used_prefixes(manifest):
        if prefix in declared:
            context[prefix] = declared[prefix]
        elif isinstance(prefixes.get(prefix), str):
            context[prefix] = prefixes[prefix]
        else:
            raise ValueError(
                f"the prefix '{prefix}' is declared neither in the manifest's "
                "@context nor in the given prefixes"
            )
    result = copy.deepcopy(dict(manifest))
    result["@context"] = context
    return result


_LOCAL_NAME = re.compile("[A-Za-z0-9_][A-Za-z0-9_.-]*")


def compact_iri(
    prefixes: Mapping[str, str],
    iri: str,
    *,
    aliases: Mapping[str, str] | None = None,
) -> str:
    """Return ``iri`` written ``name:rest`` with one of ``prefixes``, or as given.

    Where a namespace of ``aliases`` (the first in its order) begins ``iri``,
    it is first replaced by the namespace it is read as. Among the prefixes
    whose namespace begins the IRI so read and leaves a rest of letters,
    digits, ``_``, ``.`` and ``-`` that does not begin with ``.`` or ``-``,
    the longest namespace wins, a tie going to the code-point-smaller name.
    Without such a prefix the IRI is returned as given, no alias applied.
    The JavaScript package's ``compactIri`` gives the same texts.

    Args:
        prefixes: Prefix name to namespace, as a catalogue or a context
            declares them.
        iri: An absolute IRI.
        aliases: Namespace to the namespace it is read as.
    """
    read = iri
    for namespace, target in (aliases or {}).items():
        if iri.startswith(namespace):
            read = target + iri[len(namespace) :]
            break
    best: tuple[str, str] | None = None
    for name, namespace in prefixes.items():
        if not read.startswith(namespace):
            continue
        if _LOCAL_NAME.fullmatch(read[len(namespace) :]) is None:
            continue
        if best is None or (-len(namespace), name) < (-len(best[1]), best[0]):
            best = (name, namespace)
    if best is None:
        return iri
    return f"{best[0]}:{read[len(best[1]) :]}"


# References to elements -----------------------------------------------------


class _References:
    """Renames and drops the references to elements in one copy of a manifest."""

    def __init__(self, renamed: Mapping[str, str | None]) -> None:
        self.renamed = {
            "#" + old: None if new is None else "#" + new
            for old, new in renamed.items()
        }

    def dropped(self, text: Any) -> bool:
        return (
            isinstance(text, str)
            and text in self.renamed
            and self.renamed[text] is None
        )

    def text(self, text: Any) -> Any:
        """A reference renamed; any other value as it is."""
        if isinstance(text, str) and self.renamed.get(text) is not None:
            return self.renamed[text]
        return text

    def values(self, items: list[Any]) -> list[Any]:
        """The values of a list kept, each renamed."""
        return [value for value in items if self.value(value)]

    def value(self, value: Any) -> bool:
        """Rename the references of a value in place; whether it is kept."""
        if _is_ordered(value) and isinstance(value["list"], list):
            value["list"] = self.values(value["list"])
            return bool(value["list"])
        if not _is_node(value):
            return True
        if self.dropped(value.get("id")):
            return False
        if "id" in value:
            value["id"] = self.text(value["id"])
        self.subject(value, node=True)
        return bool(value)

    def subject(self, holder: dict[str, Any], *, node: bool) -> None:
        """Rename the references of a subject's pairs and entries in place."""
        container = holder if node else holder.get("statements")
        if isinstance(container, dict):
            for key in list(container):
                if key == "type" or (node and key in NODE_MEMBERS):
                    continue
                if isinstance(container[key], list):
                    container[key] = self.values(container[key])
                    if not container[key]:
                        del container[key]
            if not node and not container:
                del holder["statements"]
        provenance = holder.get("provenance")
        if isinstance(provenance, list):
            holder["provenance"] = [
                entry
                for entry in provenance
                if not isinstance(entry, dict) or self.entry(entry)
            ]
            if not holder["provenance"]:
                del holder["provenance"]

    def entry(self, entry: dict[str, Any]) -> bool:
        """Rename the references of an entry in place; whether it is kept."""
        if "value" in entry and not self.value(entry["value"]):
            return False
        for key in ("basis", "stated_by"):
            if isinstance(entry.get(key), list):
                entry[key] = [
                    self.text(item) for item in entry[key] if not self.dropped(item)
                ]
                if not entry[key]:
                    del entry[key]
        if self.dropped(entry.get("service")):
            del entry["service"]
        elif "service" in entry:
            entry["service"] = self.text(entry["service"])
        if isinstance(entry.get("beliefs"), list):
            entry["beliefs"] = [
                belief
                for belief in entry["beliefs"]
                if not isinstance(belief, dict) or not self.dropped(belief.get("actor"))
            ]
            for belief in entry["beliefs"]:
                if isinstance(belief, dict) and "actor" in belief:
                    belief["actor"] = self.text(belief["actor"])
            if not entry["beliefs"]:
                del entry["beliefs"]
        return True


def with_references_renamed(
    manifest: Mapping[str, Any], renamed: Mapping[str, str | None]
) -> dict[str, Any]:
    """Return the manifest with the references to renamed elements renamed or dropped.

    The keys and values of ``renamed`` are bare IDs. A reference is the text
    ``"#" + old`` exactly (``other.yaml#old`` names an element of another
    manifest and is none) where statements name things: a node's ``id``, a
    provenance entry's ``basis`` and ``stated_by`` items and its ``service``,
    and a belief's ``actor``, in the statements and provenance of the
    manifest, of every timeline at any depth and of every region, and of
    every node within them, a node in an entry's ``value`` included. Where
    ``renamed[old]`` is an ID, each reference becomes ``"#" + renamed[old]``.
    Where it is ``None``, a value that is a node naming the element leaves
    its list, an entry whose ``value`` names it leaves ``provenance``, a
    ``basis`` or ``stated_by`` item naming it leaves its list, a belief whose
    ``actor`` it is leaves ``beliefs`` and a ``service`` naming it is
    deleted; then every list of values, container, ``basis``, ``stated_by``,
    ``beliefs`` and ``provenance`` left empty is deleted, as are a node
    without ``id`` and ordered values left without anything. Each reference
    is renamed once: with ``{"a": "b", "b": "c"}``, ``#a`` becomes ``#b`` and
    ``#b`` becomes ``#c``. The elements' own IDs are never read, so either ID
    form is taken. The JavaScript package's ``withReferencesRenamed`` gives the same
    values.
    """
    references = _References(renamed)
    result = copy.deepcopy(dict(manifest))
    for _, element, _ in subjects(result):
        if isinstance(element, dict):
            references.subject(element, node=False)
    return result


# Pairs ----------------------------------------------------------------------


def _strictly_equal(left: Any, right: Any) -> bool:
    """JSON equality that tells a boolean, an integer and a float apart."""
    if type(left) is not type(right) and not (
        isinstance(left, Mapping) and isinstance(right, Mapping)
    ):
        return False
    if isinstance(left, Mapping):
        return left.keys() == right.keys() and all(
            _strictly_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _strictly_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def _reference_iri(context: Mapping[str, Any] | None, text: Any) -> Any:
    """An ``id`` compared as its IRI; a relative reference as written."""
    if isinstance(text, str) and _is_iri(text):
        return expand_iri(context, text) or text
    return text


def _same_value(context: Mapping[str, Any] | None, left: Any, right: Any) -> bool:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if _is_value_object(left) or _is_value_object(right):
            return (
                _is_value_object(left)
                and _is_value_object(right)
                and _strictly_equal(left.get("@value"), right.get("@value"))
                and left.get("@language") == right.get("@language")
                and _reference_iri(context, left.get("@type"))
                == _reference_iri(context, right.get("@type"))
            )
        if _is_ordered(left) or _is_ordered(right):
            items = (_entries_of(left.get("list")), _entries_of(right.get("list")))
            return (
                _is_ordered(left)
                and _is_ordered(right)
                and len(items[0]) == len(items[1])
                and all(_same_value(context, a, b) for a, b in zip(*items, strict=True))
            )
        if "id" in left or "id" in right:
            return (
                "id" in left
                and "id" in right
                and _reference_iri(context, left["id"])
                == _reference_iri(context, right["id"])
            )
        return _strictly_equal(
            {key: value for key, value in left.items() if key != "provenance"},
            {key: value for key, value in right.items() if key != "provenance"},
        )
    return _strictly_equal(left, right)


def _as_thing(property: str, value: Any) -> Any:
    """A ``type`` item ``T`` read as the thing ``{"id": T}``."""
    return {"id": value} if property == "type" and isinstance(value, str) else value


def _property_iri(context: Mapping[str, Any] | None, property: str) -> str:
    """A property as its IRI; an entry's ``rdf:type`` even with ``rdf`` undeclared."""
    expanded = expand_iri(context, property)
    if expanded is None and property == "rdf:type":
        return RDF_TYPE
    return expanded or property


def same_pair(
    context: Mapping[str, Any] | None,
    a: tuple[str, Any],
    b: tuple[str, Any],
) -> bool:
    """Whether two pairs ``(property, value)`` are the same pair under ``context``.

    The properties are equal after expansion (``type`` is ``rdf:type``, which
    an entry writes ``rdf:type`` whether or not the context declares ``rdf``). Of
    the values, literals are equal with the same JSON type (``true`` is not
    ``1``); value objects after expanding ``@type``; a node with an ``id`` is
    equal to any node with the same expanded ``id``, whatever else either
    holds, a ``type`` item ``T`` counting as ``{"id": T}``; nodes without
    ``id`` are equal as JSON after dropping their own ``provenance``; ordered
    values item by item. A relative reference compares as written.
    """
    (left_property, left_value), (right_property, right_value) = a, b
    if _property_iri(context, left_property) != _property_iri(context, right_property):
        return False
    return _same_value(
        context,
        _as_thing(left_property, left_value),
        _as_thing(right_property, right_value),
    )


# Subjects -------------------------------------------------------------------


def _element_at(manifest: Any, subject: _Path) -> tuple[Any, int]:
    """The element a subject path begins with and the length of its prefix."""
    target, position = manifest, 0
    expected = ("timelines",)
    while position + 1 < len(subject) and subject[position] in expected:
        key, index = subject[position], subject[position + 1]
        entries = target.get(key) if isinstance(target, Mapping) else None
        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or not isinstance(entries, list)
            or not 0 <= index < len(entries)
        ):
            return None, position
        target, position = entries[index], position + 2
        if key == "regions":
            break
        expected = ("children", "regions")
    return target, position


def _holder(manifest: Any, subject: Sequence[str | int]) -> tuple[dict, bool]:
    """The object holding a subject's pairs and whether the subject is an element."""
    path = tuple(subject)
    missing = ValueError(f"{json_pointer(path)} addresses no element and no value node")
    target, position = _element_at(manifest, path)
    if not isinstance(target, dict):
        raise missing
    if position == len(path):
        return target, True
    last = path[-1]
    if (
        path[position] != "statements"
        or "provenance" in path[position:]
        or not isinstance(last, int)
        or isinstance(last, bool)
    ):
        raise missing
    for step in path[position:]:
        if isinstance(target, dict) and isinstance(step, str) and step in target:
            target = target[step]
        elif (
            isinstance(target, list)
            and isinstance(step, int)
            and not isinstance(step, bool)
            and 0 <= step < len(target)
        ):
            target = target[step]
        else:
            raise missing
    if not isinstance(target, dict) or not _is_node(target):
        raise missing
    return target, False


def _container(holder: Mapping[str, Any], element: bool) -> Any:
    return holder.get("statements") if element else _node_container(holder)


def _context(manifest: Any) -> Mapping[str, Any] | None:
    context = manifest.get("@context") if isinstance(manifest, Mapping) else None
    return context if isinstance(context, Mapping) else None


def subject_path(manifest: Mapping[str, Any], element_id: str | None) -> _Path:
    """Return the path of the subject an element ID names.

    ``None`` names the bundle, ``()``; an ID names the timeline (at any
    depth) or region whose ``id`` is ``element_id`` as written in this
    manifest, the first in document order.

    Raises:
        ValueError: If no timeline or region has that ID.
    """
    if element_id is None:
        return ()
    for path, element, kind in subjects(manifest):
        if kind != "manifest" and element.get("id") == element_id:
            return path
    raise ValueError(f"no timeline or region of the manifest has the ID '{element_id}'")


def pairs(manifest: Mapping[str, Any], subject: Sequence[str | int]) -> list:
    """Return a subject's pairs ``(property, value)``.

    Keys in code-point order, values in list order; each ``type`` item is a
    pair ``("type", iri)``. A node's pairs are its property-IRI keys and
    ``type``.

    Raises:
        ValueError: If the path addresses no element and no value node.
    """
    holder, element = _holder(manifest, subject)
    return copy.deepcopy(container_pairs(_container(holder, element)))


def entries(
    manifest: Mapping[str, Any], subject: Sequence[str | int]
) -> list[dict[str, Any]]:
    """Return a subject's provenance entries, in their order.

    Raises:
        ValueError: If the path addresses no element and no value node.
    """
    holder, _ = _holder(manifest, subject)
    return [copy.deepcopy(entry) for entry in _entries_of(holder.get("provenance"))]


def _believes(
    context: Mapping[str, Any] | None, entry: Mapping[str, Any], actor: str, belief: Any
) -> bool:
    """Whether ``actor`` holds ``belief`` in an entry's pair, compared as IRIs."""
    wanted = _reference_iri(context, actor)
    return any(
        isinstance(held, Mapping)
        and _reference_iri(context, held.get("actor")) == wanted
        and _strictly_equal(held.get("belief"), belief)
        for held in _entries_of(entry.get("beliefs"))
    )


def candidates(
    manifest: Mapping[str, Any],
    subject: Sequence[str | int],
    actor: str | None = None,
) -> list[dict[str, Any]]:
    """Return a subject's candidates: the entries of pairs the subject does not state.

    With ``actor``, a candidate the actor believes ``"false"`` is left out:
    it is not offered to that actor again. Actors compare as their IRIs.

    Raises:
        ValueError: If the path addresses no element and no value node.
    """
    holder, element = _holder(manifest, subject)
    context = _context(manifest)
    stated = container_pairs(_container(holder, element))
    return [
        copy.deepcopy(entry)
        for entry in _entries_of(holder.get("provenance"))
        if isinstance(entry, Mapping)
        and not any(
            same_pair(context, pair, (entry.get("property"), entry.get("value")))
            for pair in stated
        )
        and (actor is None or not _believes(context, entry, actor, "false"))
    ]


# Writing pairs --------------------------------------------------------------


def _checked_property(property: Any) -> str:
    if property == "type" or (
        isinstance(property, str)
        and _PROPERTY.match(property) is not None
        and _BLANK.search(property) is None
    ):
        return property
    raise ValueError(
        f"'{property}' is no property: write 'type', a compact IRI or an absolute IRI"
    )


def _checked_belief(belief: Any) -> str:
    if isinstance(belief, str) and belief in BELIEFS:
        return belief
    raise ValueError(
        f"{spell(belief)} is no belief: write 'true', 'false' or 'unlikely'"
    )


class _Edit:
    """One edit of a subject's pairs and entries, on a copy of the manifest."""

    def __init__(
        self,
        manifest: Mapping[str, Any],
        subject: Sequence[str | int],
        property: str,
        value: Any,
        *dates: str | None,
    ) -> None:
        self.property = _checked_property(property)
        self.result = copy.deepcopy(dict(manifest))
        self.holder, self.element = _holder(self.result, subject)
        for date in dates:
            if date is not None:
                calendar_date(date)
        self.context = _context(self.result)
        self.pair = (property, copy.deepcopy(value))

    def matches(self, pair: tuple[str, Any]) -> bool:
        return same_pair(self.context, pair, self.pair)

    def stated(self) -> tuple[str, int] | None:
        """The key and index of the stated value of the pair, or ``None``."""
        container = _container(self.holder, self.element)
        if not isinstance(container, Mapping):
            return None
        for key in sorted(container):
            for index, value in enumerate(_entries_of(container[key])):
                if self.matches((key, value)):
                    return key, index
        return None

    def entry(self) -> dict[str, Any] | None:
        """The pair's provenance entry, or ``None``."""
        for entry in _entries_of(self.holder.get("provenance")):
            if self.matches((entry["property"], entry["value"])):
                return entry
        return None

    def new_entry(self, **members: Any) -> dict[str, Any]:
        """A new entry of the pair holding ``members``, ``beliefs`` among them."""
        property, value = self.pair
        if property == "type":
            written: Any = {"id": value}
        elif _is_node(value) and "id" in value:
            written = {"id": value["id"]}
        else:
            written = copy.deepcopy(value)
        entry = {"property": "rdf:type" if property == "type" else property}
        entry["value"] = written
        entry.update(
            (key, copy.deepcopy(member))
            for key, member in members.items()
            if key not in ("property", "value")
        )
        return entry

    def the_entry(self) -> dict[str, Any]:
        """The pair's entry, appended with the pair alone where it has none."""
        entry = self.entry()
        if entry is None:
            entry = self.new_entry()
            self.holder.setdefault("provenance", []).append(entry)
        return entry

    def believe(self, actor: str, belief: Any, date: str, note: str | None) -> None:
        """Record ``actor``'s belief in the pair's entry, replacing an earlier one."""
        held: dict[str, Any] = {"actor": actor, "belief": belief, "date": date}
        if note is not None:
            held["note"] = note
        beliefs = self.the_entry().setdefault("beliefs", [])
        wanted = _reference_iri(self.context, actor)
        for index, earlier in enumerate(beliefs):
            if (
                isinstance(earlier, Mapping)
                and _reference_iri(self.context, earlier.get("actor")) == wanted
            ):
                beliefs[index] = held
                return
        beliefs.append(held)

    def state(self) -> None:
        if self.element:
            container = self.holder.setdefault("statements", {})
        else:
            container = self.holder
        container.setdefault(self.pair[0], []).append(copy.deepcopy(self.pair[1]))

    def unstate(self, at: tuple[str, int]) -> None:
        key, index = at
        container = self.holder["statements"] if self.element else self.holder
        del container[key][index]
        if not container[key]:
            del container[key]
        if self.element and not container:
            del self.holder["statements"]

    def drop_entry(self) -> None:
        entry = self.entry()
        if entry is not None:
            self.holder["provenance"].remove(entry)

    def done(self) -> dict[str, Any]:
        if self.holder.get("provenance") == []:
            del self.holder["provenance"]
        return self.result


def with_pair(
    manifest: Mapping[str, Any],
    subject: Sequence[str | int],
    property: str,
    value: Any,
    *,
    provenance: Mapping[str, Any] | None = None,
    actor: str | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    """Return the manifest with the pair ``(property, value)`` stated of a subject.

    The value is appended to the property's list (``type`` takes a class IRI
    string). An entry of the pair, a candidate until now, stays as the
    stated pair's entry. With ``provenance`` (the members of an entry but
    ``property``, ``value`` and ``beliefs``), they are set on the pair's
    entry, which is appended where the pair has none: its ``value`` is
    ``{"id": ...}`` for a node with an ``id`` and for a ``type`` pair, else
    the value itself, and a ``type`` pair's property is written
    ``rdf:type``. With ``actor``, the person stating the pair, the entry
    records that actor's belief ``"true"`` on ``date``, replacing the actor's
    earlier belief.

    Raises:
        ValueError: If ``property`` is no property, the path addresses no
            element and no value node, a date is no calendar date, ``actor``
            is given without ``date``, or the subject already has the pair.
    """
    if actor is not None and date is None:
        raise ValueError("a belief needs a date")
    stated_on = None if provenance is None else provenance.get("date")
    edit = _Edit(manifest, subject, property, value, stated_on, date)
    if edit.stated() is not None:
        raise ValueError(f"'{property}' already has this value")
    edit.state()
    if provenance is not None:
        edit.the_entry().update(
            (key, copy.deepcopy(member))
            for key, member in provenance.items()
            if key not in ("property", "value", "beliefs")
        )
    if actor is not None:
        edit.believe(actor, "true", date, None)
    return edit.done()


def without_pair(
    manifest: Mapping[str, Any],
    subject: Sequence[str | int],
    property: str,
    value: Any,
) -> dict[str, Any]:
    """Return the manifest without the pair ``(property, value)`` of a subject.

    The pair's entry goes with it; an emptied list, container or
    ``provenance`` is removed.

    Raises:
        ValueError: If ``property`` is no property, the path addresses no
            element and no value node, or the subject does not have the pair.
    """
    edit = _Edit(manifest, subject, property, value)
    at = edit.stated()
    if at is None:
        raise ValueError(f"'{property}' does not have this value")
    edit.unstate(at)
    edit.drop_entry()
    return edit.done()


def with_candidate(
    manifest: Mapping[str, Any],
    subject: Sequence[str | int],
    property: str,
    value: Any,
    *,
    stated_by: Sequence[str],
    date: str,
    method: str,
    service: str | None = None,
    basis: Sequence[str] = (),
    match: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Return the manifest with a candidate: an entry of a pair it does not state.

    The entry replaces, in place, another entry of the pair, whose
    ``beliefs`` it keeps; the statements are left as they are. ``basis`` is
    written only when it is not empty, ``service``, ``match`` and ``note``
    only when given. A service or a loader proposing a pair holds no belief.

    Raises:
        ValueError: If ``property`` is no property, the path addresses no
            element and no value node, ``date`` is no calendar date, or the
            subject states the pair.
    """
    edit = _Edit(manifest, subject, property, value, date)
    if edit.stated() is not None:
        raise ValueError(
            f"'{property}' already has this value; a stated pair is no candidate"
        )
    members: dict[str, Any] = {
        "stated_by": list(stated_by),
        "date": date,
        "method": method,
    }
    optional = {"service": service, "match": match, "note": note}
    members.update(
        (key, member) for key, member in optional.items() if member is not None
    )
    if basis:
        members["basis"] = list(basis)
    earlier = edit.entry()
    if earlier is None:
        edit.holder.setdefault("provenance", []).append(edit.new_entry(**members))
    else:
        if "beliefs" in earlier:
            members["beliefs"] = earlier["beliefs"]
        replacement = edit.new_entry(**members)
        earlier.clear()
        earlier.update(replacement)
    return edit.done()


def with_belief(
    manifest: Mapping[str, Any],
    subject: Sequence[str | int],
    property: str,
    value: Any,
    *,
    actor: str,
    belief: str,
    date: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Return the manifest with an actor's belief in a pair of a subject.

    ``belief`` is one of the strings ``"true"``, ``"false"`` and
    ``"unlikely"`` (:data:`BELIEFS`). The pair's entry,
    appended with the pair alone where it has none, records ``{"actor",
    "belief", "date"}`` (and ``note`` where given), replacing in place the
    actor's earlier belief; actors compare as their IRIs. Whether the pair
    is stated is left as it is: one actor's belief leaves the statement and
    every other actor's belief standing. A candidate an actor believes
    ``"false"`` is not offered to that actor again (:func:`candidates`).

    Raises:
        ValueError: If ``property`` is no property, the path addresses no
            element and no value node, ``belief`` is none of the three, or
            ``date`` is no calendar date.
    """
    _checked_belief(belief)
    edit = _Edit(manifest, subject, property, value, date)
    edit.believe(actor, belief, date, note)
    return edit.done()
