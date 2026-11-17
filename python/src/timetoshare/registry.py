"""The registry of well-known identifier schemes, which turns URLs into links.

A link names the entity it points to by URIs and identifiers (``Link``). A
URL a user copies from a catalogue's web page is rarely the form a link
keeps: the registry recognises the URL of each scheme it knows and gives
either the entity URI the scheme mints or, for a scheme that mints none, an
identifier ``{scheme: <scheme URI>, value}``. Never both. An entity URI is
written as Wikidata's formatter URI for RDF resources (P1921) writes it,
where the scheme's Wikidata property has one, unless the issuer prescribes
the canonical form, as the DOI Foundation does with ``https://doi.org/``.

The registry is one data file, ``registry/schemes.json``, shipped with this
package and with the JavaScript package, which reads it the same way. Each
entry holds ``id``, ``name``, ``uri`` (the URI of the scheme), ``level`` (the
level of every entity the scheme identifies, or null where the address does
not tell), ``entity_uri`` (a template holding ``{value}``, or null),
``lowercase`` (whether the scheme's values are written in lower case) and
``patterns``: regular expressions, each matching a whole URL and capturing
the value in its one group. An entry added by a user may leave out
``level``, ``entity_uri`` and ``lowercase``, read as null, null and false.
The patterns use only the syntax Python's ``re`` and JavaScript's ``RegExp``
read alike: no named group, no lookbehind, no inline flag. A URL holding
white space or a control character is no absolute URI and is never
recognised, so ``.`` and the end of a match read the same in both. The value
captured for an entity URI is substituted as written; the value of an
identifier is percent-decoded as UTF-8 and written with underscores for
spaces, as a wiki writes a page name. Where ``lowercase`` is true, the value
is then written with its letters ``A`` to ``Z`` in lower case, so a scheme
whose values ignore case, as MusicBrainz's identifiers do, recognises a URL
in either case (its patterns accept both) and gives one value.
"""

from __future__ import annotations

import json
import re
import string
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote

if TYPE_CHECKING:
    from .description import Identifier

__all__ = [
    "BLANK",
    "LEVELS",
    "KnownScheme",
    "Recognition",
    "SchemeRegistry",
    "default_registry",
    "is_absolute_uri",
]

LEVELS = ("work", "expression", "manifestation", "item", "agent")
"""The levels of a link, the closed vocabulary of the schema's ``Level``.

Every scheme's level is one of them; ``timetoshare.description`` exports
the same tuple.
"""

BLANK = (
    "[\\u0000-\\u0020\\u007f-\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029"
    "\\u202f\\u205f\\u3000\\ufeff]"
)
"""White space and control characters, which no URI or term holds.

The class the schema's ``Term``, ``Uri`` and ``UriReference`` refuse, written
out because Python's ``\\s`` and JavaScript's ``\\s`` differ.
"""

_BLANK = re.compile(BLANK)
_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)
_SCHEME_NAME = re.compile("[A-Za-z][A-Za-z0-9+.-]*:.")
_OUTSIDE_SUBSET = re.compile(r"\(\?[^:=!]")


def is_absolute_uri(text: str) -> bool:
    """Whether ``text`` is an absolute URI as the schema's ``Uri`` reads one.

    A scheme name (a letter, then letters, digits, ``+``, ``.`` or ``-``), a
    colon and at least one more character, without white space or a control
    character.
    """
    return _SCHEME_NAME.match(text) is not None and _BLANK.search(text) is None


@dataclass(frozen=True)
class KnownScheme:
    """One entry of the registry: a scheme and the URLs it recognises.

    Attributes:
        id: The entry's ID, unique within a registry.
        name: The scheme's name, a label for people; the registry reads
            nothing from it.
        uri: The URI of the scheme, the ``scheme`` of the identifiers it gives.
        level: The level of every entity of the scheme, or ``None`` where the
            address does not tell.
        entity_uri: The template of the scheme's entity URIs, holding
            ``{value}``, or ``None`` where the scheme mints none.
        patterns: Regular expressions, each matching a whole URL and
            capturing the value in its one group.
        lowercase: Whether the scheme's values are written in lower case:
            the letters ``A`` to ``Z`` of a captured value are lowered.

    Raises:
        ValueError: If a pattern is no regular expression, has not exactly
            one capturing group or uses syntax outside the shared subset, if
            the level is no level, if the template holds no ``{value}``, or
            if ``lowercase`` is no boolean.
    """

    id: str
    name: str
    uri: str
    level: str | None
    entity_uri: str | None
    patterns: tuple[str, ...]
    lowercase: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "patterns", tuple(self.patterns))
        if not isinstance(self.lowercase, bool):
            raise ValueError(f"the lowercase of scheme '{self.id}' is no boolean")
        if self.level is not None and self.level not in LEVELS:
            raise ValueError(
                f"scheme '{self.id}' has the level '{self.level}', which is no level"
            )
        if self.entity_uri is not None and "{value}" not in self.entity_uri:
            raise ValueError(
                f"the entity URI template '{self.entity_uri}' of scheme "
                f"'{self.id}' holds no {{value}}"
            )
        for pattern in self.patterns:
            where = f"pattern '{pattern}' of scheme '{self.id}'"
            if _OUTSIDE_SUBSET.search(pattern) is not None:
                raise ValueError(
                    f"{where} uses syntax outside the shared subset; only (?:, (?= "
                    "and (?! may follow '(?'"
                )
            try:
                groups = re.compile(pattern).groups
            except re.error as error:
                raise ValueError(f"{where} is no regular expression") from error
            if groups != 1:
                raise ValueError(
                    f"{where} has {groups} capturing groups; it needs exactly one"
                )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> KnownScheme:
        """Read one entry as the registry file writes it.

        A missing ``level`` or ``entity_uri`` is read as ``None``, a missing
        ``lowercase`` as false.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            uri=data["uri"],
            level=data.get("level"),
            entity_uri=data.get("entity_uri"),
            patterns=tuple(data["patterns"]),
            lowercase=data.get("lowercase", False),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the entry as the registry file writes it."""
        return {
            "id": self.id,
            "name": self.name,
            "uri": self.uri,
            "level": self.level,
            "entity_uri": self.entity_uri,
            "lowercase": self.lowercase,
            "patterns": list(self.patterns),
        }


@dataclass(frozen=True)
class Recognition:
    """What the registry recognises in a URL.

    Exactly one of ``uri`` and ``identifier`` is set: the entity URI where
    the scheme mints one, else the identifier.

    Attributes:
        scheme: The entry that recognised the URL.
        value: The value the entry's pattern captured, decoded for an
            identifier and written as the scheme writes its values.
        level: The level of the entity, or ``None`` where the scheme does
            not tell.
        uri: The entity URI, or ``None``.
        identifier: The identifier, or ``None``.
    """

    scheme: KnownScheme
    value: str
    level: str | None
    uri: str | None
    identifier: Identifier | None


def _written(scheme: KnownScheme, value: str) -> str:
    """A value as its scheme writes it: lowered where the scheme says so.

    Only the letters ``A`` to ``Z`` are lowered and no other character
    changes, so both packages give the same text.
    """
    return value.translate(_LOWER) if scheme.lowercase else value


def _identifier_value(captured: str) -> str | None:
    try:
        decoded = unquote(captured, encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        return None
    return decoded.replace(" ", "_")


@dataclass(frozen=True)
class SchemeRegistry:
    """An ordered, read-only set of known schemes.

    Attributes:
        schemes: The entries; a URL is recognised by the first entry, in this
            order, one of whose patterns matches it.
    """

    schemes: tuple[KnownScheme, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "schemes", tuple(self.schemes))

    def recognize(self, url: str) -> Recognition | None:
        """Return what the registry recognises in ``url``, or ``None``.

        A URL that is no absolute URI is never recognised, and neither is
        one whose identifier is not percent-encoded UTF-8.
        """
        from .description import Identifier

        if not is_absolute_uri(url):
            return None
        for scheme in self.schemes:
            for pattern in scheme.patterns:
                match = re.fullmatch(pattern, url)
                if match is None:
                    continue
                captured = match.group(1)
                if captured is None:
                    continue
                if scheme.entity_uri is not None:
                    value = _written(scheme, captured)
                    return Recognition(
                        scheme=scheme,
                        value=value,
                        level=scheme.level,
                        uri=scheme.entity_uri.replace("{value}", value),
                        identifier=None,
                    )
                decoded = _identifier_value(captured)
                if decoded is None:
                    return None
                value = _written(scheme, decoded)
                return Recognition(
                    scheme=scheme,
                    value=value,
                    level=scheme.level,
                    uri=None,
                    identifier=Identifier(scheme.uri, value),
                )
        return None

    def with_schemes(self, *entries: KnownScheme | Mapping[str, Any]) -> SchemeRegistry:
        """Return a new registry extended by ``entries``.

        An entry whose ID the registry holds replaces that entry in place;
        any other is appended. This registry is left as it is.
        """
        schemes = list(self.schemes)
        for entry in entries:
            scheme = (
                entry
                if isinstance(entry, KnownScheme)
                else KnownScheme.from_dict(entry)
            )
            ids = [known.id for known in schemes]
            if scheme.id in ids:
                schemes[ids.index(scheme.id)] = scheme
            else:
                schemes.append(scheme)
        return SchemeRegistry(tuple(schemes))


@cache
def default_registry() -> SchemeRegistry:
    """Return the registry of the shipped file ``registry/schemes.json``.

    It is read once; a registry cannot be changed, only extended into a new
    one with :meth:`SchemeRegistry.with_schemes`.
    """
    from .validate import _data_root

    path = _data_root() / "registry" / "schemes.json"
    with path.open(encoding="utf-8") as handle:
        return SchemeRegistry(()).with_schemes(*json.load(handle))
