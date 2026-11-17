"""The description layer: links from a manifest's elements to external entities.

A link (``Link``) is a typed relation from the element holding it (the
manifest, a timeline or a region) to an external entity at a stated level, a
work, an expression, a manifestation, an item or an agent. It never claims
that the element is the entity. One link is one attributed reading: where
sources disagree, each reading is a link of its own. A link names its entity
by URIs (``uri``, the first preferred) and by identifiers in schemes that mint
no URI (``identifiers``), may point to documents describing it (``records``),
may state who asserted it (``assertion``), the parts of the entity in its
reading (``parts``, each a ``PartSlot``) and the wholes the entity belongs to
(``part_of``). A manifest declares the schemes its identifiers name by ID
(``Scheme``).

Every class is a frozen dataclass read from and written to the manifest's
JSON form: ``from_dict`` keeps the keys the format does not declare, which
survive ``to_dict`` and take no part in equality; ``to_dict()`` writes the
complete form and ``to_dict(minimal=True)`` the minimal form, from the one
table of defaults (``DEFAULTS``). ``Link.from_urls`` and ``PartSlot.from_url``
build links from the URLs of catalogue pages through the registry of known
schemes (``timetoshare.registry``); the ``with_*`` methods return new links.
The JavaScript package offers the same functions over plain objects
(``linkFromUrls``, ``withUri``, …), with the same values and the same
messages.
"""

from __future__ import annotations

import copy
import datetime
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields, replace
from typing import Any, ClassVar, Self

from .defaults import _strip_one
from .registry import LEVELS, SchemeRegistry, default_registry, is_absolute_uri

__all__ = [
    "ABSENCE_REASONS",
    "LEVELS",
    "MATCHES",
    "METHODS",
    "PARTS_RELATIONS",
    "RELATIONS",
    "STATUSES",
    "Assertion",
    "Descriptor",
    "Identifier",
    "Link",
    "PartOf",
    "PartSlot",
    "Scheme",
]

RELATIONS = ("pertains_to",)
"""The registered words of a link's ``relation``.

An unregistered bare word is read as an unspecified relation at the stated
level.
"""

METHODS = ("manual", "reconciled", "imported", "inferred")
"""The registered words of an assertion's ``method``.

An unregistered bare word is read as a method not stated.
"""

PARTS_RELATIONS = ("has_part", "aggregates", "incorporates")
"""The registered words of a ``parts_relation``, on a link and on ``part_of``.

An unregistered bare word is read as an unspecified structural relation.
"""

ABSENCE_REASONS = ("not_represented", "lost", "unfinished", "unknown", "not_recorded")
"""The registered words of a part slot's ``absent``.

An unregistered bare word is read as ``not_represented``.
"""

MATCHES = ("exact", "close", "broad", "narrow", "related")
"""The words of an assertion's ``match``, a closed vocabulary."""

STATUSES = ("confirmed", "unconfirmed", "rejected")
"""The words of an assertion's ``status``, a closed vocabulary."""


@dataclass(frozen=True)
class _Element:
    """What every object of the description layer shares: its JSON form.

    Attributes:
        extra: The keys the format does not declare, kept as read; they
            survive ``to_dict`` and take no part in equality.
    """

    _KIND: ClassVar[str | None] = None
    """The kind of the object in ``DEFAULTS``, or ``None`` for one without defaults."""
    _NESTED: ClassVar[Mapping[str, type[_Element]]] = {}
    """The members holding objects of the description layer, and their classes."""

    extra: Mapping[str, Any] = field(
        default_factory=dict, compare=False, repr=False, kw_only=True
    )

    def __post_init__(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if isinstance(value, list):
                object.__setattr__(self, item.name, tuple(value))
        object.__setattr__(self, "extra", dict(self.extra))

    @classmethod
    def _names(cls) -> list[str]:
        return [item.name for item in fields(cls) if item.name != "extra"]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Read the object from its JSON form, complete or minimal.

        Raises:
            ValueError: If the object breaks a rule its constructor checks.
        """
        names = cls._names()
        values = {name: cls._read(name, data[name]) for name in names if name in data}
        extra = {
            key: copy.deepcopy(value) for key, value in data.items() if key not in names
        }
        return cls(**values, extra=extra)

    @classmethod
    def _read(cls, name: str, value: Any) -> Any:
        nested = cls._NESTED.get(name)
        if nested is not None and isinstance(value, list):
            return tuple(nested.from_dict(entry) for entry in value)
        if nested is not None and isinstance(value, Mapping):
            return nested.from_dict(value)
        if isinstance(value, list):
            return tuple(copy.deepcopy(value))
        return value

    @staticmethod
    def _written(value: Any, minimal: bool) -> Any:
        if isinstance(value, _Element):
            return value.to_dict(minimal=minimal)
        if isinstance(value, tuple):
            return [_Element._written(entry, minimal) for entry in value]
        if isinstance(value, datetime.date):
            return value.isoformat()
        return copy.deepcopy(value)

    def to_dict(self, *, minimal: bool = False) -> dict[str, Any]:
        """Return the object's JSON form, complete or, if ``minimal``, minimal.

        The complete form writes every key, its default included; the minimal
        form leaves out every key whose value is its default, as
        ``timetoshare.minimal`` does in a manifest. Unknown keys are written
        as read.
        """
        result = {
            name: self._written(getattr(self, name), minimal) for name in self._names()
        }
        result.update((key, copy.deepcopy(value)) for key, value in self.extra.items())
        if minimal and self._KIND is not None:
            _strip_one(result, self._KIND)
        return result


@dataclass(frozen=True)
class Identifier(_Element):
    """An identifier of an external entity: its ``value`` in the scheme ``scheme``.

    Attributes:
        scheme: The ID of a ``Scheme`` of the manifest, or an absolute URI
            identifying the scheme.
        value: The identifier in its scheme.
    """

    scheme: str
    value: str


@dataclass(frozen=True)
class Scheme(_Element):
    """An identifier scheme a manifest declares, so identifiers may name it by ID.

    Attributes:
        id: The scheme ID, unique across every ID of the manifest.
        name: The scheme's name, or ``None``.
        uri: URIs that identify or describe the scheme, the first preferred.
        criteria: A document stating how the scheme assigns its values, or
            ``None``.
    """

    _KIND = "scheme"

    id: str
    name: str | None = None
    uri: tuple[str, ...] = ()
    criteria: str | None = None


@dataclass(frozen=True)
class Descriptor(_Element):
    """A document about a linked entity, such as its record in a catalogue.

    Attributes:
        url: Where the document lies, a URI reference.
        media_type: The document's media type, or ``None``.
        size: Its size in bytes, or ``None``.
        integrity: A Subresource Integrity digest of its bytes, or ``None``.
    """

    _KIND = "descriptor"

    url: str
    media_type: str | None = None
    size: int | None = None
    integrity: str | None = None


@dataclass(frozen=True)
class Assertion(_Element):
    """Who stated a link, a part slot or a ``part_of`` entry, when, how, how surely.

    Attributes:
        asserted_by: URIs of the agents who made the assertion.
        asserted_on: The date of the assertion, or ``None``. A date the
            format's ``YYYY-MM-DD`` spells but the calendar lacks
            (``2026-02-30``) is refused when read.
        method: How the assertion was reached (a term), or ``None``.
        service: The service that reached it, or ``None``.
        based_on: The sources it rests on.
        match: How closely the linked entity corresponds, one of
            :data:`MATCHES`, or ``None``.
        status: Whether it stands, one of :data:`STATUSES`, or ``None``.
    """

    _KIND = "assertion"

    asserted_by: tuple[str, ...] = ()
    asserted_on: datetime.date | None = None
    method: str | None = None
    service: str | None = None
    based_on: tuple[str, ...] = ()
    match: str | None = None
    status: str | None = None

    @classmethod
    def _read(cls, name: str, value: Any) -> Any:
        if name == "asserted_on" and isinstance(value, str):
            return datetime.date.fromisoformat(value)
        return super()._read(name, value)


def _unique(entries: Iterable[Any]) -> list[Any]:
    """The entries without repetitions, each kept where it first occurs."""
    found: list[Any] = []
    for entry in entries:
        if entry not in found:
            found.append(entry)
    return found


def _quoted(texts: Iterable[str]) -> str:
    return ", ".join(f"'{text}'" for text in texts)


def _normalised(
    urls: Iterable[str], registry: SchemeRegistry | None
) -> tuple[list[str], list[Identifier], list[tuple[str, str]]]:
    """Read URLs through the registry: their URIs, identifiers and levels.

    A recognised URL gives its entity URI or its identifier, and its level
    where the scheme tells one, with the URL; an absolute URI the registry
    does not recognise is kept as it is.

    Raises:
        ValueError: If a URL is neither recognised nor an absolute URI.
    """
    known = default_registry() if registry is None else registry
    uris: list[str] = []
    identifiers: list[Identifier] = []
    levels: list[tuple[str, str]] = []
    for url in urls:
        recognition = known.recognize(url)
        if recognition is None:
            if not is_absolute_uri(url):
                raise ValueError(f"'{url}' is no absolute URI")
            uris.append(url)
            continue
        if recognition.uri is not None:
            uris.append(recognition.uri)
        elif recognition.identifier is not None:
            identifiers.append(recognition.identifier)
        if recognition.level is not None:
            levels.append((recognition.level, url))
    return _unique(uris), _unique(identifiers), levels


def _checked_level(level: str) -> str:
    if level not in LEVELS:
        raise ValueError(f"'{level}' is no level")
    return level


def _level(stated: str | None, recognised: list[tuple[str, str]]) -> str | None:
    """The level of a link: the stated one, else the one the URLs tell.

    Raises:
        ValueError: If the stated level is no level or contradicts a
            recognised one, or if the URLs tell two levels.
    """
    if stated is not None:
        _checked_level(stated)
        for level, url in recognised:
            if level != stated:
                raise ValueError(
                    f"the level '{stated}' contradicts '{url}', recognised at the "
                    f"level '{level}'"
                )
        return stated
    if not recognised:
        return None
    first, first_url = recognised[0]
    for level, url in recognised[1:]:
        if level != first:
            raise ValueError(
                f"'{url}' is recognised at the level '{level}', '{first_url}' at "
                f"'{first}'"
            )
    return first


def _given_identifiers(
    identifiers: Mapping[str, str] | Iterable[Identifier] | None,
) -> list[Identifier]:
    if identifiers is None:
        return []
    if isinstance(identifiers, Mapping):
        return [Identifier(scheme, value) for scheme, value in identifiers.items()]
    return list(identifiers)


@dataclass(frozen=True)
class PartSlot(_Element):
    """One part of a linked entity in a link's reading.

    Its position is its place in the reading's ``parts``. Exactly one of
    ``represented_by`` and ``absent`` is stated.

    Attributes:
        uri: URIs of the part, the first preferred.
        identifiers: Identifiers of the part.
        label: A human-readable label of the part, or ``None``.
        represented_by: IDs of the timelines and regions representing it.
        absent: Why no element represents it (a term), or ``None``.
        assertion: Who stated the slot, or ``None``, where the link's holds.

    Raises:
        ValueError: If the slot is both represented and absent, or neither.
    """

    _KIND = "part_slot"
    _NESTED = {"identifiers": Identifier, "assertion": Assertion}

    uri: tuple[str, ...] = ()
    identifiers: tuple[Identifier, ...] = ()
    label: str | None = None
    represented_by: tuple[str, ...] = ()
    absent: str | None = None
    assertion: Assertion | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.represented_by and self.absent is not None:
            raise ValueError("a part slot is represented or absent, not both")
        if not self.represented_by and self.absent is None:
            raise ValueError("a part slot is represented by an element or absent")

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        absent: str | None = None,
        represented_by: Iterable[str] = (),
        label: str | None = None,
        assertion: Assertion | None = None,
        registry: SchemeRegistry | None = None,
    ) -> PartSlot:
        """Build a slot from the URL of the part, read through the registry.

        Raises:
            ValueError: If the URL is neither recognised nor an absolute
                URI, or the slot is both represented and absent, or neither.
        """
        uris, identifiers, _ = _normalised([url], registry)
        return cls(
            uri=tuple(uris),
            identifiers=tuple(identifiers),
            label=label,
            represented_by=tuple(represented_by),
            absent=absent,
            assertion=assertion,
        )


@dataclass(frozen=True)
class PartOf(_Element):
    """A whole a linked entity belongs to, with its position in it where stated.

    Attributes:
        parts_relation: How the whole holds the linked entity (a term).
        uri: URIs of the whole, the first preferred.
        identifiers: Identifiers of the whole.
        label: A human-readable label of the whole, or ``None``.
        position: The linked entity's position in the whole, from 1, or
            ``None``.
        assertion: Who stated the entry, or ``None``, where the link's holds.
    """

    _KIND = "part_of"
    _NESTED = {"identifiers": Identifier, "assertion": Assertion}

    parts_relation: str
    uri: tuple[str, ...] = ()
    identifiers: tuple[Identifier, ...] = ()
    label: str | None = None
    position: int | None = None
    assertion: Assertion | None = None


@dataclass(frozen=True)
class Link(_Element):
    """A typed relation from an element to an external entity at a level.

    One link is one attributed reading of the entity. Every ``with_*``
    method returns a new link and leaves this one as it is.

    Attributes:
        relation: How the element relates to the entity (a term):
            ``pertains_to`` at a bibliographic level, the agent's role at
            the level ``agent``.
        level: One of :data:`LEVELS`.
        uri: URIs of the entity, the first preferred.
        identifiers: Identifiers of the entity.
        records: Documents describing the entity.
        label: A human-readable label of the entity, or ``None``.
        assertion: Who stated the link, or ``None``.
        parts_relation: How the entity holds ``parts`` (a term), or ``None``.
        parts: The parts of the entity in this reading, in order.
        parts_ordered: Whether the order of ``parts`` is the entity's.
        part_of: The wholes the entity belongs to.

    Raises:
        ValueError: If the level is no level, an agent link uses
            ``pertains_to``, or parts lack a ``parts_relation``.
    """

    _KIND = "link"
    _NESTED = {
        "identifiers": Identifier,
        "records": Descriptor,
        "assertion": Assertion,
        "parts": PartSlot,
        "part_of": PartOf,
    }

    relation: str
    level: str
    uri: tuple[str, ...] = ()
    identifiers: tuple[Identifier, ...] = ()
    records: tuple[Descriptor, ...] = ()
    label: str | None = None
    assertion: Assertion | None = None
    parts_relation: str | None = None
    parts: tuple[PartSlot, ...] = ()
    parts_ordered: bool = True
    part_of: tuple[PartOf, ...] = ()

    def __post_init__(self) -> None:
        super().__post_init__()
        _checked_level(self.level)
        if self.level == "agent" and self.relation == "pertains_to":
            raise ValueError("an agent link never uses the relation 'pertains_to'")
        if self.parts and self.parts_relation is None:
            raise ValueError("a link with parts states its parts_relation")

    @classmethod
    def from_urls(
        cls,
        *urls: str,
        level: str | None = None,
        relation: str | None = None,
        identifiers: Mapping[str, str] | Iterable[Identifier] | None = None,
        label: str | None = None,
        assertion: Assertion | None = None,
        registry: SchemeRegistry | None = None,
    ) -> Link:
        """Build a link from the URLs of an entity, read through the registry.

        Each URL gives its entity URI, which joins ``uri``, or its identifier,
        which joins ``identifiers``; an absolute URI the registry does not
        recognise joins ``uri`` as it is. Repetitions collapse into the first.
        The identifiers from URLs come first, then the given ones (a mapping
        of scheme to value, or ``Identifier`` objects). The level is the given
        one, which no recognised level may contradict, else the one level the
        URLs tell. The relation is ``pertains_to`` unless the level is
        ``agent``, which needs the agent's role.

        Raises:
            ValueError: If no URL is given, a URL is neither recognised nor
                an absolute URI, the level is no level, contradicts a
                recognised one or is told by no URL, the URLs tell two
                levels, or an agent link names no relation.
        """
        if not urls:
            raise ValueError("a link from URLs needs one URL at least")
        uris, found, recognised = _normalised(urls, registry)
        resolved = _level(level, recognised)
        if resolved is None:
            raise ValueError(
                f"no level is recognised from {_quoted(urls)}; state the level"
            )
        if relation is None:
            if resolved == "agent":
                raise ValueError("an agent link states its relation, the agent's role")
            relation = "pertains_to"
        return cls(
            relation,
            resolved,
            uri=tuple(uris),
            identifiers=tuple(_unique([*found, *_given_identifiers(identifiers)])),
            label=label,
            assertion=assertion,
        )

    @classmethod
    def from_url(cls, url: str, **options: Any) -> Link:
        """Build a link from one URL, as :meth:`from_urls` does."""
        return cls.from_urls(url, **options)

    def with_uri(self, *urls: str, registry: SchemeRegistry | None = None) -> Link:
        """Return the link with URLs appended, read as :meth:`from_urls` reads them.

        Raises:
            ValueError: If a URL is neither recognised nor an absolute URI, or
                is recognised at another level than the link's.
        """
        uris, found, recognised = _normalised(urls, registry)
        _level(self.level, recognised)
        return replace(
            self,
            uri=tuple(_unique([*self.uri, *uris])),
            identifiers=tuple(_unique([*self.identifiers, *found])),
        )

    def with_identifier(self, scheme: str, value: str) -> Link:
        """Return the link with the identifier appended, unless it holds it."""
        identifiers = _unique([*self.identifiers, Identifier(scheme, value)])
        return replace(self, identifiers=tuple(identifiers))

    def with_record(self, descriptor: Descriptor) -> Link:
        """Return the link with a record appended."""
        return replace(self, records=(*self.records, descriptor))

    def with_label(self, label: str | None) -> Link:
        """Return the link with its label replaced."""
        return replace(self, label=label)

    def with_assertion(self, assertion: Assertion | None) -> Link:
        """Return the link with its assertion replaced."""
        return replace(self, assertion=assertion)

    def with_parts(
        self,
        parts_relation: str,
        slots: Iterable[PartSlot],
        *,
        ordered: bool = True,
        registry: SchemeRegistry | None = None,
    ) -> Link:
        """Return the link with its reading's parts replaced by ``slots``.

        Raises:
            ValueError: If a slot's URI is recognised at another level than
                the link's.
        """
        known = default_registry() if registry is None else registry
        slots = tuple(slots)
        for position, slot in enumerate(slots, start=1):
            for uri in slot.uri:
                recognition = known.recognize(uri)
                level = None if recognition is None else recognition.level
                if level is not None and level != self.level:
                    raise ValueError(
                        f"part slot {position} is recognised at the level '{level}', "
                        f"the link's level is '{self.level}'"
                    )
        return replace(
            self, parts_relation=parts_relation, parts=slots, parts_ordered=ordered
        )

    def with_part_of(self, entry: PartOf) -> Link:
        """Return the link with a ``part_of`` entry appended."""
        return replace(self, part_of=(*self.part_of, entry))

    def assertion_for(self, entry: PartSlot | PartOf) -> Assertion | None:
        """Return the assertion of a slot or ``part_of`` entry, else the link's."""
        return entry.assertion if entry.assertion is not None else self.assertion
