"""The TimeToShare schema, its validator and its public diagnostics.

A manifest is validated in its file form, every ID written ``#`` followed by
the ID: the schema check and the search for unknown keys read the value as
given. Every other check reads the manifest with bare IDs (``with_bare_ids``),
the finite rule, which runs first, included: their messages quote IDs bare
(``'clt_1'``) and the paths of the checks after the schema name the keys of
``graphical.order`` bare too. The rules run in one order: the version
marker, the finite rule, the schema, the representation of own-axis values,
the identity rules, then the statement rules
(``timetoshare.validation.statements``).
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Mapping
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from .ids import FileIdError, leniently_bare_ids, with_bare_ids
from .serialization import spell
from .statements import subjects
from .validation.containment import child_ends as child_ends
from .validation.diagnostics import UNIT_NUMBER_TYPES as UNIT_NUMBER_TYPES
from .validation.diagnostics import ManifestWarning as ManifestWarning
from .validation.diagnostics import (
    SchemaValidationError,
    _entries,
    _Path,
    duplicate_problem,
    listed_ids,
    string_id,
    timestamps_of,
    tree_ids,
)
from .validation.diagnostics import ValidationCode as ValidationCode
from .validation.diagnostics import WarningCode as WarningCode
from .validation.diagnostics import json_pointer as json_pointer
from .validation.diagnostics import number_type_of as number_type_of
from .validation.identity import identity_problems as _semantic_problems
from .validation.representation import (
    finite_number_problems,
    representation_problems,
)
from .validation.statements import statement_rule_problems, statement_warnings
from .validation.timestamps import matchstamp_problems as _matchstamp_rule_problems

SCHEMA_VERSION = "0.2.0"
"""The schema version this package reads and writes, the only one it supports."""


class UnsupportedVersionError(ValueError):
    """Raised when a manifest's version marker names another version."""

    def __init__(self, version: object) -> None:
        self.version = version
        super().__init__(
            f"unsupported TimeToShare version {spell(version)}; this package reads "
            f"{SCHEMA_VERSION} only"
        )


def _data_root() -> Path:
    package = Path(str(files("timetoshare")))
    if (package / "schema").is_dir():
        return package
    return Path(__file__).resolve().parents[3]


def schema_path() -> Path:
    """Return the path of the schema document."""
    return _data_root() / "schema" / SCHEMA_VERSION / "timetoshare.schema.json"


def provenance_schema_path() -> Path:
    """Return the path of the provenance schema, the one provenance entry."""
    return _data_root() / "schema" / SCHEMA_VERSION / PROVENANCE_DOCUMENT


PROVENANCE_DOCUMENT = "provenance.schema.json"
"""The file name of the provenance schema beside the manifest schema."""

PROVENANCE_DEFINITION = "ProvenanceRecord"
"""The name of the provenance schema's root among the bundled definitions."""


def _read(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _with_references(node: Any, rename: Callable[[str], str]) -> Any:
    """Copy ``node`` with every ``$ref`` renamed."""
    if isinstance(node, list):
        return [_with_references(item, rename) for item in node]
    if not isinstance(node, Mapping):
        return node
    return {
        key: rename(value)
        if key == "$ref" and isinstance(value, str)
        else _with_references(value, rename)
        for key, value in node.items()
    }


def bundle_schemas(
    manifest: Mapping[str, Any], provenance: Mapping[str, Any]
) -> dict[str, Any]:
    """Return the manifest schema with the provenance schema bundled into it.

    The provenance schema's root joins ``$defs`` as ``ProvenanceRecord`` and
    its own definitions join under their names; every reference between
    the two documents becomes a local ``#/$defs/...`` reference, so the
    bundle is one document whose references are all local. The JavaScript
    package's generated ``schema`` is the same bundle.

    Raises:
        ValueError: If a definition of the provenance schema has the name of
            one of the manifest schema.
    """
    definitions = "#/$defs/"

    def from_manifest(reference: str) -> str:
        document, _, pointer = reference.partition("#")
        if document != PROVENANCE_DOCUMENT:
            return reference
        return pointer and "#" + pointer or definitions + PROVENANCE_DEFINITION

    def from_provenance(reference: str) -> str:
        document, _, pointer = reference.partition("#")
        if document in ("", "timetoshare.schema.json") and pointer:
            return "#" + pointer
        return definitions + PROVENANCE_DEFINITION

    bundled = _with_references(manifest, from_manifest)
    root = _with_references(provenance, from_provenance)
    added = {
        PROVENANCE_DEFINITION: {
            key: value
            for key, value in root.items()
            if key not in ("$schema", "$id", "$defs", "title")
        },
        **root.get("$defs", {}),
    }
    for name, definition in added.items():
        if name in bundled["$defs"]:
            raise ValueError(f"both schemas define '{name}'")
        bundled["$defs"][name] = definition
    return bundled


@cache
def load_schema() -> dict[str, Any]:
    """Return the cached schema, the provenance schema bundled into it.

    The manifest schema with the provenance schema bundled
    (:func:`bundle_schemas`); treat it as read-only.
    """
    return bundle_schemas(_read(schema_path()), _read(provenance_schema_path()))


_BRANCHES = ("oneOf", "anyOf", "if", "then", "else")


def _allof_bases(node: Any) -> Iterator[str]:
    """Yield the definitions some ``allOf`` refers to: shared bases, not objects."""
    if isinstance(node, list):
        for item in node:
            yield from _allof_bases(item)
    elif isinstance(node, Mapping):
        for entry in node.get("allOf", ()):
            yield entry["$ref"].removeprefix("#/$defs/")
        for value in node.values():
            yield from _allof_bases(value)


def _close(node: Any, inside: bool, bases: frozenset[str]) -> Any:
    """Copy ``node`` with every declared object outside a branch closed."""
    if isinstance(node, list):
        return [_close(item, inside, bases) for item in node]
    if not isinstance(node, Mapping):
        return node
    closed: dict[str, Any] = {}
    for key, value in node.items():
        if key in _BRANCHES:
            closed[key] = _close(value, True, bases)
        elif key == "$defs":
            closed[key] = {
                name: member if name in bases else _close(member, False, bases)
                for name, member in value.items()
            }
        elif key == "properties":
            closed[key] = {
                name: _close(member, False, bases) for name, member in value.items()
            }
        elif key in ("default", "const", "enum"):
            closed[key] = value
        else:
            closed[key] = _close(value, inside, bases)
    if not inside and node.get("type") == "object" and "properties" in node:
        closed["unevaluatedProperties"] = False
    return closed


def _closed_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Return the schema with every object closed, the walk that finds unknown keys.

    The document keeps its objects open; this variant, built in memory only,
    sets ``unevaluatedProperties: false`` on every object node with
    ``properties`` outside a ``oneOf``/``anyOf`` branch or an
    ``if``/``then``/``else`` arm, except the bases an ``allOf`` shares, so a
    key no definition declares fails where it stands.
    """
    return _close(schema, False, frozenset(_allof_bases(schema)))


@cache
def _closed_document() -> dict[str, Any]:
    schema = load_schema()
    Draft202012Validator.check_schema(schema)
    return _closed_schema(schema)


@cache
def _marking_validator() -> Any:
    return Draft202012Validator(_closed_document())


@cache
def _member_validator(definition: str, member: str) -> Any:
    """The validator of one member of a definition, as the whole walk checks it."""
    document = _closed_document()
    declared = document["$defs"][definition]["properties"][member]
    return Draft202012Validator({"$defs": document["$defs"], **declared})


def _branch_tag(candidate: Mapping[str, Any], tag: str) -> Any:
    reference = candidate.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/$defs/"):
        candidate = load_schema()["$defs"][reference.removeprefix("#/$defs/")]
    return candidate.get("properties", {}).get(tag, {}).get("const")


def _candidate_leaves(error: ValidationError) -> Iterable[ValidationError]:
    if (
        error.validator in ("oneOf", "anyOf")
        and error.context
        and any(
            all(_key_failures_only(child) for child in branch)
            for branch in _branches(error)
        )
    ):
        return
    children = list(error.context or ())
    tag = error.schema.get("discriminator", {}).get("propertyName")
    if (
        error.validator == "oneOf"
        and tag is not None
        and isinstance(error.instance, Mapping)
    ):
        value = error.instance.get(tag)
        branch = next(
            (
                index
                for index, candidate in enumerate(error.schema["oneOf"])
                if value is not None and _branch_tag(candidate, tag) == value
            ),
            None,
        )
        children = [
            child
            for child in children
            if branch is not None
            and child.schema_path
            and child.schema_path[0] == branch
        ]
    if not children:
        if error.validator != "unevaluatedProperties":
            yield error
        return
    for child in children:
        yield from _candidate_leaves(child)


def _select(errors: Iterable[ValidationError]) -> ValidationError | None:
    best: ValidationError | None = None
    for error in errors:
        for leaf in _candidate_leaves(error):
            if best is None or len(leaf.absolute_path) > len(best.absolute_path):
                best = leaf
    return best


def _key_failures_only(error: ValidationError) -> bool:
    if error.validator == "unevaluatedProperties":
        return True
    if error.validator in ("oneOf", "anyOf") and error.context:
        return any(
            all(_key_failures_only(child) for child in branch)
            for branch in _branches(error)
        )
    return False


def _branches(error: ValidationError) -> Iterable[list[ValidationError]]:
    grouped: dict[Any, list[ValidationError]] = defaultdict(list)
    for child in error.context or ():
        grouped[child.relative_schema_path[0]].append(child)
    return grouped.values()


def _declared(node: Mapping[str, Any]) -> set[str]:
    """The keys an object node declares, its ``allOf`` bases' included, at any depth."""
    declared = set(node["properties"])
    for entry in node.get("allOf", ()):
        declared |= _declared(
            load_schema()["$defs"][entry["$ref"].removeprefix("#/$defs/")]
        )
    return declared


def _keys(errors: Iterable[ValidationError]) -> Iterator[tuple[_Path, str]]:
    for error in errors:
        if error.validator == "unevaluatedProperties":
            declared = _declared(error.schema)
            path = tuple(error.absolute_path)
            for key in error.instance:
                if key not in declared:
                    yield path, key
        elif error.validator in ("oneOf", "anyOf"):
            for branch in _branches(error):
                if all(_key_failures_only(child) for child in branch):
                    yield from _keys(branch)


def _check(value: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Check ``value`` through every rule; return its unknown keys and warnings."""
    if not isinstance(value, Mapping) or "timetoshare" not in value:
        raise SchemaValidationError("not_a_manifest", (), "not a TimeToShare manifest")
    if value["timetoshare"] != SCHEMA_VERSION:
        raise UnsupportedVersionError(value["timetoshare"])

    finite = next(finite_number_problems(leniently_bare_ids(value)), None)
    if finite is not None:
        raise finite

    errors = list(_marking_validator().iter_errors(value))
    error = _select(errors)
    if error is not None:
        raise SchemaValidationError("schema", tuple(error.absolute_path), error.message)

    bare = _bare_manifest(value)
    representation = next(representation_problems(bare), None)
    if representation is not None:
        raise representation
    semantic = next(_semantic_problems(bare), None)
    if semantic is not None:
        raise semantic
    statement = next(statement_rule_problems(bare), None)
    if statement is not None:
        raise statement

    found = set(_keys(errors))
    keys = [
        {"path": list(path), "key": key}
        for path, key in sorted(found, key=lambda entry: (entry[0], entry[1]))
    ]
    return keys, statement_warnings(bare)


def _bare_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    """The manifest with bare IDs; an ID the schema cannot see unwritten is refused.

    The schema types every position but one: a group's entry in
    ``graphical.order`` holds member IDs where a timeline's holds band words.
    """
    try:
        return with_bare_ids(value)
    except FileIdError as error:
        raise SchemaValidationError("schema", error.path, str(error)) from None


def validate(value: Mapping[str, Any]) -> None:
    """Check ``value`` and raise the first schema or semantic violation."""
    _check(value)


def unknown_keys(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return sorted unknown keys from the same schema walk used for validation."""
    return _check(value)[0]


def manifest_warnings(value: Mapping[str, Any]) -> list[ManifestWarning]:
    """Return the warnings of a valid manifest, sorted by path, then code.

    Validates ``value`` as :func:`validate` does, then lists
    ``context_absent`` at the root for a manifest without ``@context`` and
    ``bundle_blank`` at ``statements`` (else ``provenance``) for a manifest
    stating pairs or provenance without an ``id``, whose subject is a blank
    node, each as ``{"code": ..., "path": [...], "message": ...}``.

    Raises:
        SchemaValidationError: If the manifest violates a rule.
        UnsupportedVersionError: If it names another version.
    """
    return _check(value)[1]


def _statement_members(
    value: Mapping[str, Any], bare: Mapping[str, Any]
) -> Iterator[tuple[str, str, Any, _Path, str | None]]:
    """``@context``, then each ``statements`` and ``provenance`` in subject order.

    Each with the definition declaring it, its value, its path and the bare
    ID of the element holding it, as the finite rule names an owner.
    """
    if "@context" in value:
        yield "Manifest", "@context", value["@context"], ("@context",), string_id(bare)
    definitions = {"manifest": "Manifest", "timeline": "Timeline", "region": "Region"}
    for (path, element, kind), (_, plain, _) in zip(
        subjects(value), subjects(bare), strict=True
    ):
        for member in ("provenance", "statements"):
            if member in element:
                yield (
                    definitions[kind],
                    member,
                    element[member],
                    (*path, member),
                    string_id(plain),
                )


def statement_problems(value: Mapping[str, Any]) -> list[SchemaValidationError]:
    """Return the problems of the statements of ``value`` alone.

    First, member by member, the manifest's ``@context`` and every
    ``statements`` and ``provenance`` member of the manifest, a timeline at
    any depth or a region (subject order: the manifest, then root by root
    the timeline, its regions and its children, depth first; within an
    element ``provenance`` before ``statements``) checked as
    :func:`validate` checks them, each member's first problem at its path:
    a number that is not finite (``finite_number``), else the schema
    (``schema``), reported by the one path rule. Where no member has a
    problem, every problem of the statement rules follows, not only the
    first: ``context``, ``reserved_key``, then subject by subject ``iri``,
    ``dangling_target``, ``element_value``, ``representation``,
    ``calendar_date``, ``provenance_duplicate`` and ``belief_actor``.

    Nothing outside the statements is refused, and the version marker is not
    read: a manifest whose timelines break other rules but whose statements
    are sound has no problem here. A library that reads only part of a
    manifest checks its statements with this function. The messages are
    those of :func:`validate`. ``value`` is in the file form; the rules read
    its IDs bare, and an ID written without ``#`` is read as it stands.
    """
    if not isinstance(value, Mapping):
        return []
    problems: list[SchemaValidationError] = []
    bare = leniently_bare_ids(value)
    for definition, member, content, path, owner in _statement_members(value, bare):
        finite = next(finite_number_problems(content, path, owner, member), None)
        if finite is not None:
            problems.append(finite)
            continue
        error = _select(_member_validator(definition, member).iter_errors(content))
        if error is not None:
            at = (*path, *error.absolute_path)
            problems.append(SchemaValidationError("schema", at, error.message))
    if problems:
        return problems
    return list(statement_rule_problems(bare))


@cache
def _definition_validator(definition: str) -> Any:
    """The validator of one definition, as the whole walk checks it."""
    document = _closed_document()
    return Draft202012Validator(
        {"$defs": document["$defs"], "$ref": f"#/$defs/{definition}"}
    )


_MATCHSTAMPS: _Path = ("graphical", "matchstamps")


def _match_timestamps(value: Mapping[str, Any]) -> Iterator[tuple[_Path, Any]]:
    """Each match timestamp (``matchstamp: true``) with its path."""
    for index, timestamp in enumerate(timestamps_of(value)):
        if isinstance(timestamp, Mapping) and timestamp.get("matchstamp") is True:
            yield ("graphical", "timestamps", index), timestamp


def _matchstamp_id_problems(
    bare: Mapping[str, Any],
) -> Iterator[SchemaValidationError]:
    """The repeated IDs a named MatchStamp or an alignment anchor holds.

    IDs are compared as ``validate`` compares them (each root's tree, an ID
    repeated within one tree counted once, then the listed elements, then
    the manifest's ID); a repetition is reported where ``validate`` reports
    it when the ID at it or its first occurrence belongs to a MatchStamp.
    """

    def concerned(*paths: _Path) -> bool:
        return any(path[: len(_MATCHSTAMPS)] == _MATCHSTAMPS for path in paths)

    first: dict[str, _Path] = {}
    for index, root in enumerate(_entries(bare, "timelines")):
        seen: dict[str, _Path] = {}
        for identifier, path in tree_ids(root, ("timelines", index)):
            seen.setdefault(identifier, path)
        for identifier, path in seen.items():
            first.setdefault(identifier, path)
    for identifier, path in listed_ids(bare):
        if identifier not in first:
            first[identifier] = path
        elif concerned(path, first[identifier]):
            yield duplicate_problem(identifier, path, first[identifier])
    manifest_id = string_id(bare)
    if manifest_id in first and concerned(first[manifest_id]):
        yield duplicate_problem(manifest_id, ("id",), first[manifest_id], "manifest_id")


def matchstamp_problems(value: Mapping[str, Any]) -> list[SchemaValidationError]:
    """Return the problems of the named MatchStamps and their match timestamps alone.

    First, each match timestamp (a named timestamp with ``matchstamp:
    true``) and then ``graphical.matchstamps`` checked as :func:`validate`
    checks them, each one's first problem at its path: a number that is not
    finite (``finite_number``), else the schema (``schema``), reported by
    the one path rule. Where none has a problem, every problem beyond the
    schema follows, not only the first: an ID of a MatchStamp or an
    alignment anchor that the manifest holds twice (``duplicate_id``, or
    ``manifest_id`` where the manifest's ID repeats one), then the rules of
    the MatchStamps and their match timestamps (``alignment_anchor``,
    ``matchstamp``, ``groupstamp``, ``match_timestamp``), in
    :func:`identity_problems`' order.

    Nothing else is refused: an ordinary timestamp, the styles and rules,
    the timelines and the statements are not read beyond what the
    MatchStamps name. A library that keeps the rest of ``graphical`` unread
    checks its MatchStamps with this function. The messages are those of
    :func:`validate`. ``value`` is in the file form; the rules read its IDs
    bare, and an ID written without ``#`` is read as it stands.
    """
    if not isinstance(value, Mapping):
        return []
    graphical = value.get("graphical")
    flagged = list(_match_timestamps(value))
    if not flagged and not (
        isinstance(graphical, Mapping) and "matchstamps" in graphical
    ):
        return []
    bare = leniently_bare_ids(value)
    owner = string_id(bare)
    problems: list[SchemaValidationError] = []
    read = [timestamp for _, timestamp in _match_timestamps(bare)]
    for (path, timestamp), bare_timestamp in zip(flagged, read, strict=True):
        finite = next(finite_number_problems(bare_timestamp, path, owner), None)
        if finite is not None:
            problems.append(finite)
            continue
        error = _select(_definition_validator("Timestamp").iter_errors(timestamp))
        if error is not None:
            at = (*path, *error.absolute_path)
            problems.append(SchemaValidationError("schema", at, error.message))
    if isinstance(graphical, Mapping) and "matchstamps" in graphical:
        content = bare["graphical"]["matchstamps"]
        finite = next(
            finite_number_problems(content, _MATCHSTAMPS, owner, "matchstamps"), None
        )
        if finite is not None:
            problems.append(finite)
        else:
            validator = _member_validator("Graphical", "matchstamps")
            error = _select(validator.iter_errors(graphical["matchstamps"]))
            if error is not None:
                at = (*_MATCHSTAMPS, *error.absolute_path)
                problems.append(SchemaValidationError("schema", at, error.message))
    if problems:
        return problems
    return [*_matchstamp_id_problems(bare), *_matchstamp_rule_problems(bare)]


def identity_problems(value: Mapping[str, Any]) -> list[SchemaValidationError]:
    """Return all semantic violations in the established identity order.

    Root by root: duplicates, dangling targets, conversion maps, containment
    and segment lines; then the IDs unique across the manifest (the roots'
    trees, the group IDs, the MeasureMap IDs, the named timestamps' IDs, the
    named MatchStamps' IDs each followed by its alignment anchors' IDs, the
    resources' IDs, and last the manifest ID); then group members, graphical
    orders, named timestamps, named MatchStamps and resources. ``value`` is in
    the file form; the rules read its IDs bare.

    Raises:
        SchemaValidationError: If an ID is not written in the file form.
    """
    return list(_semantic_problems(_bare_manifest(value)))
