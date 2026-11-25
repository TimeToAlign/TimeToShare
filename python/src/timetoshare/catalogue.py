"""The catalogue of identifier systems, verbs and types, which tools read.

A manifest holds statements as property–value pairs; the words a person
reads ("performed by", "is a recording of") are not in it. The catalogue,
one data file ``catalogue/catalogue.yaml`` shipped with this package and
with the JavaScript package, holds them:

* ``prefixes``, the namespaces of the vocabularies its patterns use, and
  ``aliases``, namespaces read as equal (``https://schema.org/`` as
  ``http://schema.org/``);
* ``systems``, each an identifier system with the vocabulary prefixes its
  own linked data uses, how its things are looked up (``lookup``) and its
  ``things``: the kinds of thing it identifies, each with the template of
  their IRIs (``iri``, holding ``{value}``, or null), the URLs it
  recognises (``patterns``, regular expressions each capturing the value in
  its one group), whether its values are written in lower case and the
  LRMoo class of its things;
* ``verbs``, each with a label and, per system, the alternative
  ``pattern``\\ s that express it there: a fragment of a statements
  container with slots (``{"id": "?"}`` a thing, ``"?"`` a literal or type
  IRI, ``"?name"`` a named literal), optionally only ``when`` the subject or
  value is of given types or things, and marked ``inverse`` where it reads
  the verb backwards (``inverse_label``); ``is_a`` comes first;
* ``types``, profiles of the things an element may stand for: their "is a"
  patterns, the verbs usually stated of them and the systems to look in.

The validators never consult it. The patterns of things use only the
syntax Python's ``re`` and JavaScript's ``RegExp`` read alike: no named
group, no lookbehind, no inline flag. A URL holding white space or a control
character is never recognised.
"""

from __future__ import annotations

import copy
import re
import string
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from typing import Any, NamedTuple
from urllib.parse import unquote

from .serialization import loads
from .statements import (
    BLANK,
    container_pairs,
    context_of,
    expand_iri,
    is_iri,
    is_node,
    is_value_object,
    pairs,
    prefix_of,
    strictly_equal,
)

__all__ = [
    "Catalogue",
    "Recognition",
    "Rectangle",
    "instantiate",
    "load_catalogue",
    "read_catalogue",
    "recognize",
    "rectangles",
    "verb_of",
]

_BLANK = re.compile(BLANK)
_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)
_ABSOLUTE = re.compile("[A-Za-z][A-Za-z0-9+.-]*:.")
_OUTSIDE_SUBSET = re.compile(r"\(\?[^:=!]")
_SAME_AS = (
    "http://schema.org/sameAs",
    "http://www.w3.org/2002/07/owl#sameAs",
)


@dataclass(frozen=True)
class Catalogue:
    """A catalogue as read: its prefixes, aliases, systems, verbs and types.

    Attributes:
        prefixes: Prefix name to namespace IRI.
        aliases: Namespace to the namespace it is read as.
        systems: The identifier systems, as the file writes them.
        verbs: The verbs, ``is_a`` first, as the file writes them.
        types: The types, as the file writes them.
    """

    prefixes: dict[str, str]
    aliases: dict[str, str]
    systems: tuple[dict[str, Any], ...]
    verbs: tuple[dict[str, Any], ...]
    types: tuple[dict[str, Any], ...]


class Recognition(NamedTuple):
    """What the catalogue recognises in a URL.

    Attributes:
        system: The ID of the system holding the thing.
        thing: The ID of the thing whose pattern matched.
        value: The captured value, written as the thing writes its values.
        iri: The thing's IRI, or ``None`` where it has no IRI template.
    """

    system: str
    thing: str
    value: str
    iri: str | None


class Rectangle(NamedTuple):
    """One verb about one thing, stated in one or more vocabularies.

    Attributes:
        verb: The verb's ID, or ``None`` for a pair no verb reads.
        inverse: Whether the pairs read the verb backwards.
        pairs: The pairs ``(property, value)``, in file order.
        things: The IRIs of the things the pairs name, in first-seen order.
        label: The first label of a node among the pairs, or ``None``.
    """

    verb: str | None
    inverse: bool
    pairs: tuple[tuple[str, Any], ...]
    things: tuple[str, ...]
    label: str | None


# Reading --------------------------------------------------------------------


def _alternatives(cells: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    """The alternatives of a verb's ``patterns`` or a type's ``is_a``, by system."""
    if not isinstance(cells, Mapping):
        return
    for system, alternatives in cells.items():
        for alternative in alternatives if isinstance(alternatives, list) else ():
            if isinstance(alternative, Mapping):
                yield system, alternative


def _cells(document: Mapping[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    """Every alternative: the verbs' first, then the types' ``is_a``."""
    for verb in document.get("verbs", ()):
        yield from _alternatives(verb.get("patterns"))
    for profile in document.get("types", ()):
        yield from _alternatives(profile.get("is_a"))


def _things(document: Mapping[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    for system in document.get("systems", ()):
        for thing in system.get("things", ()):
            yield system["id"], thing


def _pattern_iris(value: Any) -> Iterator[str]:
    """The places of a pattern that hold IRIs: its keys, ``type`` items and ``id``\\ s.

    At any depth; a literal constant (``"foo:bar"`` as a value) is no IRI.
    """
    if isinstance(value, list):
        for item in value:
            yield from _pattern_iris(item)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield key
            if key == "type" and isinstance(item, list):
                yield from (entry for entry in item if isinstance(entry, str))
            elif key == "id" and isinstance(item, str):
                yield item
            else:
                yield from _pattern_iris(item)


def _used_prefixes(document: Mapping[str, Any]) -> Iterator[str]:
    for system in document.get("systems", ()):
        yield from system.get("prefixes", ())
        for thing in system.get("things", ()):
            if isinstance(thing.get("prefix"), str):
                yield thing["prefix"]
            if isinstance(thing.get("lrmoo_class"), str):
                yield from _compact_prefixes([thing["lrmoo_class"]])
    for _, alternative in _cells(document):
        yield from _compact_prefixes(_pattern_iris(alternative.get("pattern")))


def _compact_prefixes(texts: Any) -> Iterator[str]:
    for text in texts:
        if is_iri(text):
            prefix = prefix_of(text)
            if prefix is not None:
                yield prefix


def _thing_problem(thing: Mapping[str, Any]) -> str | None:
    for pattern in thing.get("patterns", ()):
        where = f"pattern '{pattern}' of thing '{thing['id']}'"
        if _OUTSIDE_SUBSET.search(pattern) is not None:
            return (
                f"{where} uses syntax outside the shared subset; only (?:, (?= "
                "and (?! may follow '(?'"
            )
        try:
            groups = re.compile(pattern).groups
        except re.error:
            return f"{where} is no regular expression"
        if groups != 1:
            return f"{where} has {groups} capturing groups; it needs exactly one"
    return None


def _checks(document: Mapping[str, Any]) -> Iterator[str]:
    """The cross-reference problems of a catalogue, in the order they are refused."""
    kinds = (
        ("system", document.get("systems", ())),
        ("thing", [thing for _, thing in _things(document)]),
        ("verb", document.get("verbs", ())),
        ("type", document.get("types", ())),
    )
    for kind, entries in kinds:
        seen: set[str] = set()
        for entry in entries:
            if entry["id"] in seen:
                yield f"the catalogue holds the {kind} '{entry['id']}' twice"
            seen.add(entry["id"])
    declared = document.get("prefixes", {})
    for prefix in _used_prefixes(document):
        if prefix not in declared:
            yield f"the catalogue uses the prefix '{prefix}' without declaring it"
    systems = {system["id"] for system in document.get("systems", ())}
    named_systems = [system for system, _ in _cells(document)]
    for profile in document.get("types", ()):
        named_systems.extend(profile.get("lookup", ()))
    for system in named_systems:
        if system not in systems:
            yield f"the catalogue names the system '{system}', which it does not hold"
    things = {thing["id"] for _, thing in _things(document)}
    for _, alternative in _cells(document):
        for thing in alternative.get("when", {}).get("value", ()):
            if thing not in things:
                yield f"the catalogue names the thing '{thing}', which no system holds"
    verbs = {verb["id"] for verb in document.get("verbs", ())}
    for profile in document.get("types", ()):
        for verb in profile.get("verbs", ()):
            if verb not in verbs:
                yield f"the catalogue names the verb '{verb}', which it does not hold"
    types = {profile["id"] for profile in document.get("types", ())}
    for _, alternative in _cells(document):
        for profile in alternative.get("when", {}).get("subject", ()):
            if profile not in types:
                yield (
                    f"the catalogue names the type '{profile}', which it does not hold"
                )
    for _, thing in _things(document):
        problem = _thing_problem(thing)
        if problem is not None:
            yield problem


def read_catalogue(document: Mapping[str, Any]) -> Catalogue:
    """Read a catalogue document after checking its cross-references.

    The shape is not checked here (the test suites check the shipped file
    against ``catalogue/catalogue.schema.json``); the references are, and
    the first problem raised, in this order: an ID held twice (systems,
    things, verbs, types); a prefix used without being declared (a system's
    ``prefixes``, a thing's ``prefix`` and ``lrmoo_class``, the keys,
    ``type`` items and node ``id``\\ s of every pattern); a system, thing,
    verb or type named but not held; a thing pattern that is no regular
    expression of the shared subset with exactly one capturing group.

    Raises:
        ValueError: With the first problem.
    """
    problem = next(_checks(document), None)
    if problem is not None:
        raise ValueError(problem)
    return Catalogue(
        prefixes=dict(copy.deepcopy(document.get("prefixes", {}))),
        aliases=dict(copy.deepcopy(document.get("aliases", {}))),
        systems=tuple(copy.deepcopy(document.get("systems", []))),
        verbs=tuple(copy.deepcopy(document.get("verbs", []))),
        types=tuple(copy.deepcopy(document.get("types", []))),
    )


@cache
def load_catalogue() -> Catalogue:
    """Return the catalogue of the shipped file ``catalogue/catalogue.yaml``.

    It is read once; treat it as read-only.
    """
    from .validate import data_root

    path = data_root() / "catalogue" / "catalogue.yaml"
    return read_catalogue(loads(path.read_text(encoding="utf-8")))


# Recognising URLs -----------------------------------------------------------


def _identifier_value(captured: str) -> str | None:
    try:
        decoded = unquote(captured, encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        return None
    return decoded.replace(" ", "_")


def recognize(catalogue: Catalogue, url: str) -> Recognition | None:
    """Return what the catalogue recognises in ``url``, or ``None``.

    The things of every system are tried in order, and the first whose
    pattern matches the whole URL recognises it. A thing with an IRI
    template gives the captured value as written and its IRI; one without
    gives the value percent-decoded as UTF-8 with underscores for spaces, as
    a wiki writes a page name, and no IRI. Where the thing's ``lowercase``
    is true, the letters ``A`` to ``Z`` of the value are then lowered. A URL
    that is no absolute IRI is never recognised, and neither is one whose
    value is not percent-encoded UTF-8.
    """
    if _ABSOLUTE.match(url) is None or _BLANK.search(url) is not None:
        return None
    for system in catalogue.systems:
        for thing in system.get("things", ()):
            for pattern in thing.get("patterns", ()):
                match = re.fullmatch(pattern, url)
                if match is None or match.group(1) is None:
                    continue
                template = thing.get("iri")
                value = (
                    match.group(1)
                    if template is not None
                    else _identifier_value(match.group(1))
                )
                if value is None:
                    return None
                if thing.get("lowercase"):
                    value = value.translate(_LOWER)
                iri = None if template is None else template.replace("{value}", value)
                return Recognition(system["id"], thing["id"], value, iri)
    return None


# Patterns -------------------------------------------------------------------


def _verb(catalogue: Catalogue, verb: str) -> dict[str, Any]:
    for entry in catalogue.verbs:
        if entry["id"] == verb:
            return entry
    raise ValueError(f"the catalogue has no verb '{verb}'")


def _filled(
    template: Any, value: Any, label: str | None, slots: Mapping[str, Any], where: str
) -> Any:
    if isinstance(template, str) and template.startswith("?"):
        if template == "?":
            return copy.deepcopy(value)
        name = template[1:]
        if name not in slots:
            raise ValueError(f"the pattern of {where} needs a value for '?{name}'")
        return copy.deepcopy(slots[name])
    if isinstance(template, list):
        return [_filled(item, value, label, slots, where) for item in template]
    if isinstance(template, Mapping):
        if dict(template) == {"id": "?"}:
            node: dict[str, Any] = {"id": copy.deepcopy(value)}
            if label is not None:
                node["label"] = label
            return node
        return {
            key: _filled(item, value, label, slots, where)
            for key, item in template.items()
        }
    return copy.deepcopy(template)


def instantiate(
    catalogue: Catalogue,
    verb: str,
    system: str,
    value: Any,
    *,
    alternative: int = 0,
    label: str | None = None,
    slots: Mapping[str, Any] | None = None,
) -> list[tuple[str, Any]]:
    """Return the pairs that state ``verb`` of ``value`` in ``system``'s pattern.

    The alternative's pairs, keys in code-point order: ``{"id": "?"}``
    becomes ``{"id": value}`` (with ``label`` where given), ``"?"`` becomes
    ``value`` and ``"?name"`` becomes ``slots[name]``.

    Raises:
        ValueError: If the catalogue has no such verb, the verb has no
            pattern in the system or not the alternative asked for, or a
            named slot has no value.
    """
    cells = _verb(catalogue, verb).get("patterns", {}).get(system)
    if not cells:
        raise ValueError(f"the verb '{verb}' has no pattern in '{system}'")
    if not 0 <= alternative < len(cells):
        raise ValueError(f"the verb '{verb}' has {len(cells)} patterns in '{system}'")
    where = f"'{verb}' in '{system}'"
    filled = _filled(cells[alternative]["pattern"], value, label, slots or {}, where)
    return container_pairs(filled)


class _Reading:
    """How a catalogue reads the pairs of one manifest: two contexts and the aliases."""

    def __init__(self, catalogue: Catalogue, context: Mapping[str, Any] | None) -> None:
        self.catalogue = catalogue
        self.context = context

    def aliased(self, iri: str) -> str:
        """An IRI with the first alias whose namespace starts it applied."""
        for namespace, target in self.catalogue.aliases.items():
            if iri.startswith(namespace):
                return target + iri[len(namespace) :]
        return iri

    def own(self, text: str) -> str:
        """An IRI of the catalogue, expanded by its prefixes, aliases applied."""
        return self.aliased(expand_iri(self.catalogue.prefixes, text) or text)

    def held(self, text: str) -> str:
        """An IRI of the manifest, expanded by its context, aliases applied."""
        return self.aliased(expand_iri(self.context, text) or text)

    def reference(self, text: Any) -> Any:
        """A node's ``id`` as its IRI; a relative reference as written."""
        if isinstance(text, str) and is_iri(text):
            return self.held(text)
        return text

    def constant(self, template: Any, value: Any) -> bool:
        """Whether a constant equals a value: as written, by IRI, or as JSON."""
        if isinstance(template, str) and isinstance(value, str):
            return template == value or (
                is_iri(template) and self.own(template) == self.held(value)
            )
        return strictly_equal(template, value)

    def matches(self, template: Any, value: Any) -> int | None:
        """The number of constants of a template that ``value`` matches, or ``None``."""
        if isinstance(template, str) and template.startswith("?"):
            literal = not isinstance(value, list) and (
                not isinstance(value, Mapping) or is_value_object(value)
            )
            return 0 if literal else None
        if not isinstance(template, Mapping):
            return 1 if self.constant(template, value) else None
        if not is_node(value):
            return None
        count = 0
        for key, item in template.items():
            if key == "id":
                if "id" not in value:
                    return None
                if item != "?":
                    if self.own(item) != self.reference(value["id"]):
                        return None
                    count += 1
            elif key == "type":
                held = [self.held(entry) for entry in value.get("type", ())]
                for entry in item:
                    if entry == "?":
                        if not held:
                            return None
                    elif self.own(entry) in held:
                        count += 1
                    else:
                        return None
            else:
                found = self.member(key, item, value)
                if found is None:
                    return None
                count += found
        return count

    def member(self, key: str, items: list[Any], node: Mapping[str, Any]) -> int | None:
        """How the node's values of a template's key match the template's one item."""
        iri = self.own(key)
        best: int | None = None
        for held, values in node.items():
            if held in ("id", "label", "provenance", "type") or self.held(held) != iri:
                continue
            for value in values if isinstance(values, list) else ():
                for template in items:
                    found = self.matches(template, value)
                    if found is not None and (best is None or found > best):
                        best = found
        return best

    def verb_of(self, property: str, value: Any) -> tuple[str, bool] | None:
        """The verb a pair states and whether it reads it backwards, or ``None``."""
        iri = self.held(property)
        best: tuple[int, str, bool] | None = None
        for verb in self.catalogue.verbs:
            for _, alternative in _alternatives(verb.get("patterns")):
                for key, templates in alternative["pattern"].items():
                    if self.own(key) != iri:
                        continue
                    for template in templates:
                        found = self.matches(template, value)
                        if found is not None and (best is None or found > best[0]):
                            best = (found, verb["id"], bool(alternative.get("inverse")))
        return None if best is None else (best[1], best[2])

    def things(self, property: str, value: Any) -> list[str]:
        """The things a pair names: a ``type``'s class, a node's own and sameAs IDs."""
        if property == "type" and isinstance(value, str):
            return [self.held(value)]
        if not is_node(value):
            return []
        found = [self.reference(value["id"])] if "id" in value else []
        for key, members in value.items():
            if key in ("id", "label", "provenance", "type"):
                continue
            if self.held(key) not in _SAME_AS:
                continue
            for member in members if isinstance(members, list) else ():
                if is_node(member) and "id" in member:
                    found.append(self.reference(member["id"]))
        return found


def verb_of(
    catalogue: Catalogue,
    context: Mapping[str, Any] | None,
    property: str,
    value: Any,
) -> tuple[str, bool] | None:
    """Return the verb a pair states and whether it reads it backwards, or ``None``.

    The pair's property is expanded by the manifest's ``context``, each
    pattern key by the catalogue's prefixes, both with the catalogue's
    aliases applied; an alternative fits where a key expands to the
    property's IRI and its template matches the value: a slot any value of
    its kind, a constant by expanded IRI or JSON equality, a template
    node's keys among the value's and its ``type`` items among the value's.
    Of several, the one with most constants wins, ties in catalogue order.
    """
    return _Reading(catalogue, context).verb_of(property, value)


def rectangles(
    catalogue: Catalogue,
    manifest: Mapping[str, Any],
    subject: Sequence[str | int],
) -> list[Rectangle]:
    """Return a subject's pairs gathered into rectangles: one verb about one thing.

    Pairs of the same verb read the same way fall into one rectangle when
    both state ``is_a``, they name a common thing, or both value nodes carry
    a string ``label`` and the labels are equal (transitively): the thing of
    a node is its ``id`` and the ``id``\\ s under its ``schema:sameAs`` and
    ``owl:sameAs``, the thing of a ``type`` pair its class. A pair no verb
    reads is a rectangle of its own. The ``is_a`` rectangle comes first,
    empty where nothing is stated; then the others by their first pair.
    Pairs keep file order, things first-seen order, and the label is the
    first label of a node among the pairs.

    Raises:
        ValueError: If the path addresses no element and no value node.
    """
    stated = pairs(manifest, subject)
    reading = _Reading(catalogue, context_of(manifest))
    things = [reading.things(property, value) for property, value in stated]
    labels = [
        value["label"]
        if is_node(value) and isinstance(value.get("label"), str)
        else None
        for _, value in stated
    ]
    groups: list[tuple[tuple[str, bool] | None, list[int]]] = []
    for index, (property, value) in enumerate(stated):
        key = reading.verb_of(property, value)
        joined = [
            number
            for number, (other, members) in enumerate(groups)
            if key is not None
            and other == key
            and (
                key[0] == "is_a"
                or any(
                    thing in things[member]
                    for member in members
                    for thing in things[index]
                )
                or (
                    labels[index] is not None
                    and any(labels[member] == labels[index] for member in members)
                )
            )
        ]
        if not joined:
            groups.append((key, [index]))
            continue
        merged = groups[joined[0]][1]
        for number in reversed(joined[1:]):
            merged.extend(groups.pop(number)[1])
        merged.append(index)
    found: list[Rectangle] = []
    for key, members in sorted(groups, key=lambda group: min(group[1])):
        chosen = sorted(members)
        label = next(
            (labels[number] for number in chosen if labels[number] is not None), None
        )
        found.append(
            Rectangle(
                verb=None if key is None else key[0],
                inverse=False if key is None else key[1],
                pairs=tuple(stated[number] for number in chosen),
                things=tuple(
                    dict.fromkeys(
                        thing for number in chosen for thing in things[number]
                    )
                ),
                label=label,
            )
        )
    is_a = [rectangle for rectangle in found if rectangle.verb == "is_a"]
    if not is_a:
        is_a = [Rectangle("is_a", False, (), (), None)]
    return [*is_a, *(rectangle for rectangle in found if rectangle.verb != "is_a")]
