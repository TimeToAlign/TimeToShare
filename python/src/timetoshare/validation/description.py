"""Description rules: the dates and references of links, and their unregistered terms.

The schema checks the shape of every link; four rules reach beyond it and
are checked here: a scheme's ID is unique across every ID of the manifest,
and, link by link, an assertion's ``asserted_on`` names a day of the
Gregorian calendar, an identifier's ``scheme`` names a scheme of the
manifest or is an absolute URI, and a part slot's ``represented_by`` names a
timeline (at any depth) or a region of the manifest. The open vocabularies
are never refused: a bare term outside the words registered for its key is
listed as a warning.

The walks of this module read the description layer of any manifest: the
arrays it consists of (``description_arrays``) and the IDs its rules read
outside it are found whatever the rest of the manifest holds, so a reader of
part of a manifest can check its description layer alone.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from ..description import (
    ABSENCE_REASONS,
    METHODS,
    PARTS_RELATIONS,
    RELATIONS,
    _calendar_date,
)
from ..registry import is_absolute_uri
from .diagnostics import (
    SchemaValidationError,
    _entries,
    _Path,
    duplicate_problem,
    string_id,
    timestamps_of,
    tree_ids,
)

_Found = tuple[Mapping[str, Any], _Path]

_Array = tuple[str, str, Any, _Path, str | None]
"""An array of the description layer: the definition declaring it, its member,
its value, its path and the ID of the nearest element holding it, if any."""


def _owned(element: Any, owner: str | None) -> str | None:
    """The element's own ID where it holds a string one, else its holder's."""
    identifier = string_id(element)
    return owner if identifier is None else identifier


def _timeline_arrays(timeline: Any, path: _Path, owner: str | None) -> Iterator[_Array]:
    if not isinstance(timeline, Mapping):
        return
    owner = _owned(timeline, owner)
    if "links" in timeline:
        yield "Timeline", "links", timeline["links"], (*path, "links"), owner
    for index, region in enumerate(_entries(timeline, "regions")):
        if isinstance(region, Mapping) and "links" in region:
            at = (*path, "regions", index, "links")
            yield "Region", "links", region["links"], at, _owned(region, owner)
    for index, child in enumerate(_entries(timeline, "children")):
        yield from _timeline_arrays(child, (*path, "children", index), owner)


def description_arrays(manifest: Any) -> Iterator[_Array]:
    """Yield every array of the description layer that a manifest states.

    The manifest's ``schemes``, then its ``links``, then root by root each
    timeline's ``links``, its regions' ``links`` in array order and its
    children's, depth first, whatever their values; an element that is no
    object states none. Each comes with the schema definition declaring it
    (``Manifest``, ``Timeline`` or ``Region``) and the ID of the nearest
    element holding it, as the finite rule names an owner.
    """
    if not isinstance(manifest, Mapping):
        return
    owner = string_id(manifest)
    for member in ("schemes", "links"):
        if member in manifest:
            yield "Manifest", member, manifest[member], (member,), owner
    for index, root in enumerate(_entries(manifest, "timelines")):
        yield from _timeline_arrays(root, ("timelines", index), owner)


def _timeline_links(timeline: Mapping[str, Any], path: _Path) -> Iterator[_Found]:
    for index, link in enumerate(_entries(timeline, "links")):
        yield link, (*path, "links", index)
    for index, region in enumerate(_entries(timeline, "regions")):
        at = (*path, "regions", index)
        for number, link in enumerate(_entries(region, "links")):
            yield link, (*at, "links", number)
    for index, child in enumerate(_entries(timeline, "children")):
        yield from _timeline_links(child, (*path, "children", index))


def links_of(manifest: Mapping[str, Any]) -> Iterator[_Found]:
    """Yield every link of a manifest with its path, in document order.

    The manifest's own links, then root by root each timeline's links, its
    regions' links in array order and its children's, depth first.
    """
    for index, link in enumerate(_entries(manifest, "links")):
        yield link, ("links", index)
    for index, root in enumerate(_entries(manifest, "timelines")):
        yield from _timeline_links(root, ("timelines", index))


def _targets(manifest: Mapping[str, Any]) -> set[str]:
    """The IDs a part slot may name: every timeline's, at any depth, and region's."""
    found: set[str] = set()

    def visit(timeline: Any) -> None:
        found.update(
            identifier
            for identifier in (
                string_id(timeline),
                *(string_id(region) for region in _entries(timeline, "regions")),
            )
            if identifier is not None
        )
        for child in _entries(timeline, "children"):
            visit(child)

    for root in _entries(manifest, "timelines"):
        visit(root)
    return found


def scheme_problems(
    manifest: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """Yield the scheme IDs another ID of the manifest holds, as the identity rules do.

    Each scheme's ID against every ID before it in the order of the identity
    rules (the roots' trees, the groups, the MeasureMaps, the named
    timestamps, the earlier schemes), at the later ``id``; then the manifest
    ID where it is a scheme's ID. The schemes are taken as schema-checked;
    every other ID is read wherever it is a string.
    """
    first: dict[str, _Path] = {}
    for index, root in enumerate(_entries(manifest, "timelines")):
        for identifier, path in tree_ids(root, ("timelines", index)):
            first.setdefault(identifier, path)
    for key, entries in (
        (("groups",), _entries(manifest, "groups")),
        (("measure_maps",), _entries(manifest, "measure_maps")),
        (("graphical", "timestamps"), timestamps_of(manifest)),
    ):
        for index, entry in enumerate(entries):
            identifier = string_id(entry)
            if identifier is not None:
                first.setdefault(identifier, (*key, index, "id"))
    schemes: set[str] = set()
    for index, scheme in enumerate(_entries(manifest, "schemes")):
        identifier, path = scheme["id"], ("schemes", index, "id")
        schemes.add(identifier)
        if identifier in first:
            yield duplicate_problem(identifier, path, first[identifier])
        else:
            first[identifier] = path
    manifest_id = string_id(manifest)
    if manifest_id in schemes:
        yield duplicate_problem(manifest_id, ("id",), first[manifest_id], "manifest_id")


def _date_problems(
    owner: Mapping[str, Any], path: _Path
) -> Iterator[SchemaValidationError]:
    assertion = owner.get("assertion")
    date = assertion.get("asserted_on") if isinstance(assertion, Mapping) else None
    if isinstance(date, str):
        try:
            _calendar_date(date)
        except ValueError as error:
            yield SchemaValidationError(
                "calendar_date", (*path, "assertion", "asserted_on"), str(error)
            )


def _owner_problems(
    owner: Mapping[str, Any], path: _Path, schemes: set[str]
) -> Iterator[SchemaValidationError]:
    """The date of an owner's assertion, then its identifiers' schemes."""
    yield from _date_problems(owner, path)
    for index, identifier in enumerate(_entries(owner, "identifiers")):
        scheme = identifier["scheme"]
        if scheme not in schemes and not is_absolute_uri(scheme):
            yield SchemaValidationError(
                "dangling_target",
                (*path, "identifiers", index, "scheme"),
                f"'{scheme}' names no scheme of this manifest and is no absolute URI",
            )


def link_problems(
    manifest: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """Yield the impossible dates and dangling references of links, link by link.

    Within a link: its assertion's date and its identifiers' schemes, then
    each part slot's assertion's date, identifiers' schemes and
    ``represented_by`` entries, then each ``part_of`` entry's assertion's
    date and identifiers' schemes. The links and schemes are taken as
    schema-checked; the timelines and regions a slot may name are read
    wherever their ``id`` is a string.
    """
    schemes = {scheme["id"] for scheme in _entries(manifest, "schemes")}
    targets = _targets(manifest)
    for link, path in links_of(manifest):
        yield from _owner_problems(link, path, schemes)
        for index, slot in enumerate(_entries(link, "parts")):
            at = (*path, "parts", index)
            yield from _owner_problems(slot, at, schemes)
            for number, target in enumerate(slot.get("represented_by", [])):
                if target not in targets:
                    yield SchemaValidationError(
                        "dangling_target",
                        (*at, "represented_by", number),
                        f"'{target}' names no timeline or region of this manifest",
                    )
        for index, entry in enumerate(_entries(link, "part_of")):
            yield from _owner_problems(entry, (*path, "part_of", index), schemes)


def _term(
    owner: Mapping[str, Any], key: str, words: tuple[str, ...], path: _Path
) -> Iterator[tuple[_Path, str]]:
    term = owner.get(key)
    if isinstance(term, str) and ":" not in term and term not in words:
        yield (*path, key), term


def _method(owner: Mapping[str, Any], path: _Path) -> Iterator[tuple[_Path, str]]:
    assertion = owner.get("assertion")
    if isinstance(assertion, Mapping):
        yield from _term(assertion, "method", METHODS, (*path, "assertion"))


def unregistered_terms(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return every bare term outside the words registered for its key.

    A term holding a colon is an extension term and never listed. The keys
    read are a link's ``relation`` and ``parts_relation``, every assertion's
    ``method``, a part slot's ``absent`` and a ``part_of`` entry's
    ``parts_relation``. The entries ``{"path": [...], "term": ...}`` are
    sorted by path. The manifest is taken as valid.
    """
    found: list[tuple[_Path, str]] = []
    for link, path in links_of(manifest):
        found.extend(_term(link, "relation", RELATIONS, path))
        found.extend(_method(link, path))
        found.extend(_term(link, "parts_relation", PARTS_RELATIONS, path))
        for index, slot in enumerate(_entries(link, "parts")):
            at = (*path, "parts", index)
            found.extend(_term(slot, "absent", ABSENCE_REASONS, at))
            found.extend(_method(slot, at))
        for index, entry in enumerate(_entries(link, "part_of")):
            at = (*path, "part_of", index)
            found.extend(_term(entry, "parts_relation", PARTS_RELATIONS, at))
            found.extend(_method(entry, at))
    return [{"path": list(path), "term": term} for path, term in sorted(found)]
