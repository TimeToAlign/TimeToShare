"""The statement fixtures read by PyLD; see README "The RDF of the statements"."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import pytest
from pyld import jsonld

from timetoshare import (
    FORMAT_CONTEXT,
    NAMESPACE,
    expand_iri,
    fixture_paths,
    loads,
    rdf_expectation,
)

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
PROV = "http://www.w3.org/ns/prov#"
XSD = "http://www.w3.org/2001/XMLSchema#"
FORMAT_PREDICATES = {
    RDF + "type",
    RDFS + "label",
    RDF + "subject",
    RDF + "predicate",
    RDF + "object",
    PROV + "wasAttributedTo",
    "http://purl.org/dc/terms/date",
    PROV + "hadPrimarySource",
    RDFS + "comment",
    NAMESPACE + "method",
    NAMESPACE + "service",
    NAMESPACE + "match",
    NAMESPACE + "status",
}
SCHEMES = ("http:", "https:", "urn:", "tag:", "mailto:", "info:")
STATEMENTS = [path for path in fixture_paths() if path.parent.name == "statements"]
OTHERS = [path for path in fixture_paths() if path.parent.name != "statements"]


def _base(path: Path) -> str:
    name = path.name.removesuffix(".yaml").removesuffix(".minimal")
    return f"https://example.org/manifests/{name}.yaml"


def _refuse(url: str, options: Any = None) -> Any:
    raise AssertionError(f"the processor fetched {url}")


def _options(path: Path) -> dict[str, Any]:
    return {"base": _base(path), "documentLoader": _refuse}


def _document(path: Path) -> Any:
    return loads(path.read_text(encoding="utf-8"))


def _quads(path: Path) -> list[dict[str, Any]]:
    dataset = jsonld.to_rdf(_document(path), _options(path))
    return [quad for graph in dataset.values() for quad in graph]


def test_the_statement_fixtures_are_found() -> None:
    assert sorted(path.name for path in STATEMENTS) == sorted(
        f"{name}{suffix}"
        for name in (
            "djset_segment",
            "layerit_recording",
            "nielsen_record",
            "op106_work",
        )
        for suffix in (".yaml", ".minimal.yaml")
    )
    for path in STATEMENTS:
        name = path.name.removesuffix(".yaml").removesuffix(".minimal")
        assert rdf_expectation(path).name == f"{name}.nq"
        assert rdf_expectation(path).parent.parts[-2:] == ("rdf", "0.2.0")


@pytest.mark.parametrize("path", STATEMENTS, ids=lambda path: path.name)
def test_the_canonical_n_quads_are_the_expected_bytes(path: Path) -> None:
    options = {**_options(path), "algorithm": "URDNA2015"}
    options["format"] = "application/n-quads"
    text = jsonld.normalize(_document(path), options)
    assert text.encode("utf-8") == rdf_expectation(path).read_bytes()


def _terms(quad: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield quad["subject"]
    yield quad["predicate"]
    yield quad["object"]


@pytest.mark.parametrize("path", STATEMENTS, ids=lambda path: path.name)
def test_every_iri_is_expanded(path: Path) -> None:
    prefixes = [key for key in _document(path)["@context"] if key not in FORMAT_CONTEXT]
    quads = _quads(path)
    assert quads
    for quad in quads:
        for term in _terms(quad):
            if term["type"] != "IRI":
                continue
            assert term["value"].startswith(SCHEMES), term
            assert not any(term["value"].startswith(f"{p}:") for p in prefixes), term


def _subjects(value: Any) -> Iterator[dict[str, Any]]:
    """Every element and node carrying pairs or provenance, at any depth."""
    if isinstance(value, list):
        for item in value:
            yield from _subjects(item)
    elif isinstance(value, dict):
        if "statements" in value or "provenance" in value:
            yield value
        elif "id" in value and any(":" in key for key in value):
            yield value
        for key, item in value.items():
            if key != "@context":
                yield from _subjects(item)


def _keys(value: Any, inside: bool = False) -> Iterator[str]:
    """Every key holding a ``:`` within statements and provenance: the pair keys."""
    if isinstance(value, list):
        for item in value:
            yield from _keys(item, inside)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key == "@context":
                continue
            if inside and ":" in key:
                yield key
            yield from _keys(item, inside or key in ("statements", "provenance"))


@pytest.mark.parametrize("path", STATEMENTS, ids=lambda path: path.name)
def test_every_predicate_is_a_stated_property_or_the_formats(path: Path) -> None:
    document = _document(path)
    context = document["@context"]
    allowed = FORMAT_PREDICATES | {expand_iri(context, key) for key in _keys(document)}
    for quad in _quads(path):
        assert quad["predicate"]["value"] in allowed, quad


def _iri(path: Path, context: dict[str, Any], text: str) -> str:
    if text.startswith("#") or ":" not in text.split("/")[0]:
        return urljoin(_base(path), text)
    return expand_iri(context, text) or text


def _literal(value: Any) -> tuple[str, str] | None:
    if isinstance(value, bool):
        return ("true" if value else "false", XSD + "boolean")
    if isinstance(value, int):
        return (str(value), XSD + "integer")
    if isinstance(value, str):
        return (value, XSD + "string")
    return None


def _entries(path: Path) -> Iterator[tuple[str, dict[str, Any]]]:
    """Every provenance entry whose subject has an IRI, with that IRI."""
    document = _document(path)
    for holder in _subjects(document):
        identifier = holder.get("id")
        if not isinstance(identifier, str):
            continue
        for entry in holder.get("provenance", []):
            yield _iri(path, document["@context"], identifier), entry


@pytest.mark.parametrize("path", STATEMENTS, ids=lambda path: path.name)
def test_a_pair_that_is_not_stated_is_asserted_nowhere(path: Path) -> None:
    context = _document(path)["@context"]
    triples = {
        (
            quad["subject"]["value"],
            quad["predicate"]["value"],
            quad["object"]["value"],
            quad["object"].get("datatype"),
        )
        for quad in _quads(path)
    }
    for subject, entry in _entries(path):
        if entry["status"] == "confirmed":
            continue
        predicate = expand_iri(context, entry["property"])
        value = entry["value"]
        if isinstance(value, dict) and list(value) == ["id"]:
            target = (_iri(path, context, value["id"]), None)
        elif _literal(value) is not None:
            target = _literal(value)
        else:
            continue
        assert (subject, predicate, *target) not in triples


@pytest.mark.parametrize("path", STATEMENTS, ids=lambda path: path.name)
def test_each_entry_is_one_reified_statement(path: Path) -> None:
    entries = sum(
        len(holder.get("provenance", [])) for holder in _subjects(_document(path))
    )
    reified = {
        quad["subject"]["value"]
        for quad in _quads(path)
        if quad["predicate"]["value"] == RDF + "subject"
    }
    assert len(reified) == entries


@pytest.mark.parametrize("path", OTHERS, ids=lambda path: path.name)
def test_a_manifest_without_statements_says_nothing(path: Path) -> None:
    assert _quads(path) == []
