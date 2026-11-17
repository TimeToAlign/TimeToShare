"""Description rules: what a link's references name, and its unregistered terms.

The schema checks the shape of every link; two references reach beyond the
link and are checked here, link by link: an identifier's ``scheme`` names a
scheme of the manifest or is an absolute URI, and a part slot's
``represented_by`` names a timeline (at any depth) or a region of the
manifest. The open vocabularies are never refused: a bare term outside the
words registered for its key is listed as a warning.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from ..description import ABSENCE_REASONS, METHODS, PARTS_RELATIONS, RELATIONS
from ..registry import is_absolute_uri
from .diagnostics import SchemaValidationError, _entries, _Path

_Found = tuple[Mapping[str, Any], _Path]


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

    def visit(timeline: Mapping[str, Any]) -> None:
        found.add(timeline["id"])
        found.update(region["id"] for region in _entries(timeline, "regions"))
        for child in _entries(timeline, "children"):
            visit(child)

    for root in _entries(manifest, "timelines"):
        visit(root)
    return found


def _scheme_problems(
    owner: Mapping[str, Any], path: _Path, schemes: set[str]
) -> Iterator[SchemaValidationError]:
    for index, identifier in enumerate(_entries(owner, "identifiers")):
        scheme = identifier["scheme"]
        if scheme not in schemes and not is_absolute_uri(scheme):
            yield SchemaValidationError(
                "dangling_target",
                (*path, "identifiers", index, "scheme"),
                f"'{scheme}' names no scheme of this manifest and is no absolute URI",
            )


def description_problems(
    manifest: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """Yield the references of links that name nothing, link by link.

    Within a link: its identifiers' schemes, then each part slot's
    identifiers' schemes and its ``represented_by`` entries, then each
    ``part_of`` entry's identifiers' schemes.
    """
    schemes = {scheme["id"] for scheme in _entries(manifest, "schemes")}
    targets = _targets(manifest)
    for link, path in links_of(manifest):
        yield from _scheme_problems(link, path, schemes)
        for index, slot in enumerate(_entries(link, "parts")):
            at = (*path, "parts", index)
            yield from _scheme_problems(slot, at, schemes)
            for number, target in enumerate(slot.get("represented_by", [])):
                if target not in targets:
                    yield SchemaValidationError(
                        "dangling_target",
                        (*at, "represented_by", number),
                        f"'{target}' names no timeline or region of this manifest",
                    )
        for index, entry in enumerate(_entries(link, "part_of")):
            yield from _scheme_problems(entry, (*path, "part_of", index), schemes)


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
