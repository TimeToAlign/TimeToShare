from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from timetoshare import (
    BELIEFS,
    BLANK,
    DEFAULTS,
    FORMAT_CONTEXT,
    MATCHES,
    METHODS,
    SCHEMA_VERSION,
    TIMESTAMP_DISPLAY,
    load_schema,
    provenance_schema_path,
    schema_path,
)
from timetoshare.validate import UNIT_NUMBER_TYPES, bundle_schemas

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

PUBLIC = [
    "Manifest",
    "Timeline",
    "Group",
    "Graphical",
    "ConversionMap",
    "Coordinate",
    "Number",
    "Fraction",
    "TimeUnit",
    "NumberType",
    "Id",
    "MeasureMap",
    "MeasureMapRow",
    "Resource",
    "Timestamp",
    "MatchStamp",
    "AlignmentAnchor",
    "Context",
    "Statements",
    "StatementValue",
    "ProvenanceEntry",
]

MAP_TYPES = [
    "ChainMap",
    "CombinationMap",
    "ConstantMap",
    "FloatingMeasureMap",
    "LinearMap",
    "MeasureBeatMap",
    "MeasureNumberMap",
    "MeasureRecordMap",
    "PiecewiseMap",
    "TableMap",
]
MEASURE_VIEWS = {
    "FloatingMeasureMap": "floating_measures",
    "MeasureBeatMap": None,
    "MeasureNumberMap": None,
    "MeasureRecordMap": None,
}


def _defs() -> dict[str, Any]:
    return load_schema()["$defs"]


def _map_types() -> list[str]:
    """The conversion map types: the definitions ``ConversionMap`` chooses between."""
    return [
        branch["$ref"].removeprefix("#/$defs/")
        for branch in _defs()["ConversionMap"]["oneOf"]
    ]


def _target(node: dict) -> dict:
    """The definition a node refers to, else the node."""
    if "$ref" in node:
        return _defs()[node["$ref"].removeprefix("#/$defs/")]
    return node


def _custom_keys(node: Any) -> list[str]:
    """Every key of the document that begins with ``x-``."""
    if isinstance(node, list):
        return [key for item in node for key in _custom_keys(item)]
    if not isinstance(node, dict):
        return []
    found = [key for key in node if key.startswith("x-")]
    return found + [key for value in node.values() for key in _custom_keys(value)]


def _nodes(node: Any, inside: bool = False) -> Iterator[tuple[dict, bool]]:
    """Yield every schema node and whether it lies in a branch or an arm."""
    if isinstance(node, list):
        for item in node:
            yield from _nodes(item, inside)
    elif isinstance(node, dict):
        yield node, inside
        for key, value in node.items():
            if key in ("oneOf", "anyOf", "if", "then", "else"):
                yield from _nodes(value, True)
            elif key in ("properties", "$defs"):
                for child in value.values():
                    yield from _nodes(child, False)
            elif key not in ("default", "const", "enum"):
                yield from _nodes(value, inside)


def test_one_document_with_one_root() -> None:
    schema = load_schema()
    assert SCHEMA_VERSION == "0.2.0"
    assert (
        schema_path()
        == REPOSITORY_ROOT / "schema" / "0.2.0" / "timetoshare.schema.json"
    )
    assert sorted(p.name for p in (REPOSITORY_ROOT / "schema").iterdir()) == ["0.2.0"]
    assert sorted(p.name for p in (REPOSITORY_ROOT / "schema" / "0.2.0").iterdir()) == [
        "provenance.schema.json",
        "timetoshare.schema.json",
    ]
    assert schema["$id"] == (
        "https://timetoalign.github.io/timetoshare/0.2.0/timetoshare.schema.json"
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$ref"] == "#/$defs/Manifest"


def test_references_are_local_and_resolve_without_anchors() -> None:
    defs = _defs()
    references = [node["$ref"] for node, _ in _nodes(load_schema()) if "$ref" in node]
    assert references
    for reference in references:
        assert reference.startswith("#/$defs/")
        assert reference.removeprefix("#/$defs/") in defs
    assert not [node for node, _ in _nodes(load_schema()) if "$anchor" in node]


def test_the_public_definitions() -> None:
    defs = _defs()
    assert set(PUBLIC) <= set(defs)
    (named,) = re.findall(
        r"The definitions (.+?) are public:", load_schema()["description"]
    )
    assert named == ", ".join(PUBLIC[:-1]) + " and " + PUBLIC[-1]


def test_the_ten_map_types() -> None:
    defs = _defs()
    assert _map_types() == MAP_TYPES
    classes = defs["Selector"]["properties"]["class"]["enum"]
    assert classes == [
        "ContinuousLogicalTimeline",
        "ContinuousPhysicalTimeline",
        "ContinuousGraphicalTimeline",
        "DiscreteLogicalTimeline",
        "DiscretePhysicalTimeline",
        "DiscreteGraphicalTimeline",
        *MAP_TYPES,
    ]
    facets = ["markers", "conversion_maps", "children", "regions", "flow_control"]
    assert defs["Facet"]["enum"] == facets
    assert defs["Part"]["enum"] == [
        "start",
        "end",
        "name",
        "label",
        "card",
        "line",
        "id",
        "coordinate",
    ]
    display = defs["Timestamp"]["properties"]["display"]
    assert display["items"]["enum"] == list(TIMESTAMP_DISPLAY)
    assert TIMESTAMP_DISPLAY == ("wedge", "name", "id", "coordinate", "cross_section")
    assert display["uniqueItems"] is True
    assert defs["Selector"]["properties"]["facet"]["$ref"] == "#/$defs/Facet"
    assert defs["ElementType"]["enum"] == [
        "block",
        "timeline",
        "child",
        "band",
        "map",
        "region",
        "flow_marker",
        "jump_from",
        "wedge",
        "name",
        "label",
        "boundary",
        "ancestor",
        "frame",
        "card",
        "cross_section",
        "alignment_anchor",
    ]
    assert defs["MeasureView"]["properties"]["source_unit"]["const"] == "quarters"
    for name, target in MEASURE_VIEWS.items():
        assert defs[name]["allOf"] == [{"$ref": "#/$defs/MeasureView"}], name
        assert defs[name]["properties"]["target_unit"]["const"] == target, name


def test_the_unit_table_states_the_default_number_types() -> None:
    unit = _defs()["TimeUnit"]
    assert unit["type"] == "string"
    assert "enum" not in unit
    assert [entry["const"] for entry in unit["oneOf"]] == list(UNIT_NUMBER_TYPES)
    pattern = re.compile(
        r"^(Logical|Physical|Graphical), (continuous|discrete); "
        r"default number type (int|float|fraction)\.(?: \S.*\.)?$"
    )
    for entry in unit["oneOf"]:
        assert sorted(entry) == ["const", "description"]
        match = pattern.match(entry["description"])
        assert match is not None, entry["const"]
        assert match[3] == UNIT_NUMBER_TYPES[entry["const"]], entry["const"]


def test_repeated_shapes_are_shared_definitions() -> None:
    defs = _defs()
    assert defs["Name"] == {
        "type": ["string", "null"],
        "description": "Human-readable name, or null when none was given.",
        "default": None,
    }
    assert defs["Meta"] == {
        "type": "object",
        "additionalProperties": True,
        "description": "Free-form metadata.",
        "default": {},
    }
    names = [
        defs[owner]["properties"]["name"]
        for owner in (
            "Manifest",
            "Timeline",
            "Group",
            "Region",
            "FlowControlElement",
            "MeasureMap",
            "MapBase",
        )
    ]
    metas = [
        defs[owner]["properties"]["meta"]
        for owner in (
            "Manifest",
            "Timeline",
            "Group",
            "Region",
            "FlowControlElement",
            "MeasureMap",
        )
    ]
    for node in names:
        assert node["$ref"] == "#/$defs/Name"
    for node in metas:
        assert node["$ref"] == "#/$defs/Meta"
    for node, _ in _nodes(load_schema()):
        properties = node.get("properties", {})
        if "meta" in properties:
            assert properties["meta"]["$ref"] == "#/$defs/Meta"
        if properties.get("name", {}).get("type") == ["string", "null"]:
            raise AssertionError(f"an inline name: {properties['name']}")


def test_every_conversion_map_extends_the_map_base() -> None:
    defs = _defs()
    base = defs["MapBase"]
    assert list(base["properties"]) == [
        "type",
        "id",
        "name",
        "source_unit",
        "target_unit",
    ]
    assert base["required"] == ["type", "id", "source_unit", "target_unit"]
    view = defs["MeasureView"]
    assert view["type"] == "object"
    assert view["allOf"] == [{"$ref": "#/$defs/MapBase"}]
    assert list(view["properties"]) == ["source_unit", "measure_map"]
    assert view["properties"]["source_unit"]["const"] == "quarters"
    assert view["required"] == ["measure_map"]
    for name in _map_types():
        definition = defs[name]
        assert definition["type"] == "object"
        parent = "MeasureView" if name in MEASURE_VIEWS else "MapBase"
        assert definition["allOf"] == [{"$ref": f"#/$defs/{parent}"}], name
        bases = set(base["properties"]) | set(view["properties"])
        own = set(definition["properties"]) & bases
        units = {"target_unit"} if name in MEASURE_VIEWS else set()
        assert own == {"type"} | units, name
        for key in units:
            assert "const" in definition["properties"][key], name
        assert definition["properties"]["type"] == {"const": name}
        assert "type" in definition["required"]
        assert not set(definition["required"]) & {"id", "source_unit", "target_unit"}


def test_references_are_ids_and_addresses() -> None:
    defs = _defs()
    selector = defs["Selector"]["properties"]
    assert selector["within"]["$ref"] == "#/$defs/Id"
    assert selector["addresses"]["items"] == {"$ref": "#/$defs/Address"}
    assert defs["FlowControlElement"]["properties"]["target"]["$ref"] == "#/$defs/Id"
    assert defs["MeasureView"]["properties"]["measure_map"]["$ref"] == "#/$defs/Id"
    identifier = Draft202012Validator({"$ref": "#/$defs/Id", "$defs": defs})
    for accepted in (
        "#score",
        "#Bass Kick",
        "#perf/take 2",
        "#https://example.org/piece/score#exposition",
        "#start",
        "#regions_1",
        "##x",
        "# ",
    ):
        assert identifier.is_valid(accepted), accepted
    for refused in ("", "#", "score", "score#", "#score\t", "#score\n", "#\u001f"):
        assert not identifier.is_valid(refused), refused
    address = Draft202012Validator({"$ref": "#/$defs/Address", "$defs": defs})
    for accepted in (
        {},
        {"part": ["name"]},
        {"id": "#score"},
        {"id": "#perf/take 2"},
        {"id": "#score", "facet": "regions"},
        {"id": "#score", "part": ["card"]},
        {"id": "#score", "part": ["end", "label"]},
        {"id": "#timestamp_1", "part": ["line"]},
        {"id": "#timestamp_1", "part": ["name"]},
        {"id": "#timestamp_1", "part": ["id"]},
        {"id": "#timestamp_1", "part": ["coordinate"]},
        {"id": "#score", "root": "score"},
    ):
        assert address.is_valid(accepted), accepted
    for refused in (
        "score",
        {"facet": "regions"},
        {"id": "#score", "facet": "regions", "part": ["label"]},
        {"id": "#score", "part": []},
        {"id": "#score", "part": ["wedge"]},
        {"id": "#score", "facet": "regions_1"},
    ):
        assert not address.is_valid(refused), refused


ANCHORED = {
    ("Timestamp", "properties", "id"): "#timestamp_1",
    ("Paint",): "none",
    ("Declaration", "properties", "stroke-dasharray"): "4 2",
    ("CalendarDate",): "2026-11-17",
    ("Resource", "properties", "id"): "#resource_1",
    ("Resource", "properties", "media_type"): "application/vnd.apache.parquet",
    ("Resource", "properties", "integrity", "properties", "digest"): "00ff",
    ("MatchStamp", "properties", "id"): "#matchstamp_1",
    ("AlignmentAnchor", "properties", "id"): "#anchor_1",
}
"""Every node whose pattern ends in ``$``, with a value its pattern accepts."""


def _anchored(node: Any, path: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
    if isinstance(node, list):
        for item in node:
            yield from _anchored(item, path)
    elif isinstance(node, dict):
        if str(node.get("pattern", "")).endswith("$"):
            yield path
        for key, value in node.items():
            yield from _anchored(value, (*path, key))


def _node(path: tuple[str, ...]) -> dict[str, Any]:
    node: Any = _defs()
    for key in path:
        node = node[key]
    return node


def test_no_pattern_lets_a_trailing_newline_through() -> None:
    assert sorted(_anchored(_defs(), ())) == sorted(ANCHORED)
    for path, value in ANCHORED.items():
        validator = Draft202012Validator({**_node(path), "$defs": _defs()})
        assert validator.is_valid(value), path
        assert not validator.is_valid(f"{value}\n"), path
    order = Draft202012Validator({"$ref": "#/$defs/Order", "$defs": _defs()})
    assert order.is_valid(["line", "markers"])
    assert not order.is_valid(["line\n", "markers"])
    assert not order.is_valid([""])


def test_objects_are_open_without_a_custom_keyword() -> None:
    defs = _defs()
    nodes = list(_nodes(load_schema()))
    assert not [node for node, _ in nodes if node.get("additionalProperties") is False]
    assert not [node for node, _ in nodes if "unevaluatedProperties" in node]
    assert not _custom_keys(load_schema())
    free = [node for node, _ in nodes if node.get("additionalProperties") is True]
    assert free == [defs["Meta"]]
    assert "properties" not in defs["Meta"]


def _declared(node: dict) -> set[str]:
    """The keys a node declares, its ``allOf`` bases' included, at any depth."""
    declared = set(node.get("properties", {}))
    for entry in node.get("allOf", []):
        declared |= _declared(_target(entry))
    return declared


def test_every_object_declares_what_its_branches_declare() -> None:
    for node, inside in _nodes(load_schema()):
        if inside or node.get("type") != "object" or "properties" not in node:
            continue
        declared = _declared(node)
        assert "patternProperties" not in node
        for key in ("oneOf", "anyOf"):
            for branch in node.get(key, []):
                assert set(branch.get("properties", {})) <= declared
        for key in ("if", "then", "else"):
            assert set(node.get(key, {}).get("properties", {})) <= declared


def test_every_discriminated_union_tags_each_branch_with_a_distinct_constant() -> None:
    unions = [node for node, _ in _nodes(load_schema()) if "discriminator" in node]
    assert sorted(node["discriminator"]["propertyName"] for node in unions) == [
        "number_type",
        "type",
    ]
    for node in unions:
        key = node["discriminator"]["propertyName"]
        tags = [_target(branch)["properties"][key]["const"] for branch in node["oneOf"]]
        assert all(isinstance(tag, str) for tag in tags)
        assert len(set(tags)) == len(tags)
        for branch in node["oneOf"]:
            assert key in _target(branch).get("required", node.get("required", []))


def _defaults(definition: dict) -> dict[str, Any]:
    """The defaults a definition declares, through references and its bases."""
    members = dict(definition.get("properties", {}))
    for entry in definition.get("allOf", []):
        base = _target(entry)
        members |= {
            key: {"default": value}
            for key, value in _defaults(base).items()
            if key not in members
        }
    return {
        key: (member if "default" in member else _target(member))["default"]
        for key, member in members.items()
        if "default" in member or "default" in _target(member)
    }


def test_the_defaults_are_the_table() -> None:
    defs = _defs()
    kinds = {
        "manifest": ["Manifest"],
        "timeline": ["Timeline"],
        "region": ["Region"],
        "measure_map": ["MeasureMap"],
        "group": ["Group"],
        "graphical": ["Graphical"],
        "timestamp": ["Timestamp"],
        "alignment_anchor": ["AlignmentAnchor"],
    }
    own = {"LinearMap": "linear_map", "TableMap": "table_map"}
    element = ["flow_control_element", "repeat_end"]
    assert sorted(
        [*kinds, "conversion_map", "match_timestamp", *own.values(), *element]
    ) == sorted(DEFAULTS)
    matched = defs["Timestamp"]
    assert matched["if"] == {
        "properties": {"matchstamp": {"const": True}},
        "required": ["matchstamp"],
    }
    assert _defaults(matched["then"]) == DEFAULTS["match_timestamp"]
    assert matched["else"] == {"required": ["name"]}
    covered = {"MapBase", "MeasureView", "FlowControlElement"}
    element_defs = defs["FlowControlElement"]
    assert _defaults(element_defs) == DEFAULTS["flow_control_element"]
    repeat_end = element_defs["then"]["else"]
    assert repeat_end["if"]["properties"]["manifestation"] == {"const": "repeat_end"}
    assert _defaults(repeat_end["then"]) == DEFAULTS["repeat_end"]
    for kind, names in kinds.items():
        for name in names:
            covered.add(name)
            assert _defaults(defs[name]) == DEFAULTS[kind], name
    for name in _map_types():
        covered.add(name)
        expected = DEFAULTS["conversion_map"] | DEFAULTS.get(own.get(name, ""), {})
        assert _defaults(defs[name]) == expected, name
    for name, definition in defs.items():
        if name not in covered:
            assert _defaults(definition) == {}, name
    assert "default" not in defs["Timeline"]["properties"]["number_type"]


def test_statements_provenance_and_the_context() -> None:
    defs = _defs()
    expected = {
        "statements": ["Manifest", "Region", "Timeline"],
        "provenance": ["Manifest", "Region", "Timeline", "ValueNode"],
        "@context": ["Manifest"],
    }
    for member, holders in expected.items():
        assert (
            sorted(
                name
                for name, definition in defs.items()
                if name != "Context" and member in definition.get("properties", {})
            )
            == holders
        ), member
    for name in ("Manifest", "Timeline", "Region"):
        for member in ("links", "schemes"):
            assert member not in defs[name]["properties"]
    removed = ("Link", "PartSlot", "PartOf", "Assertion", "Descriptor", "Identifier")
    for name in (*removed, "Scheme", "Level", "Term", "Uri", "UriReference"):
        assert name not in defs, name
    assert defs["ProvenanceEntry"]["allOf"] == [{"$ref": "#/$defs/ProvenanceRecord"}]
    assert defs["ProvenanceEntry"]["required"] == ["property", "value"]
    entry = defs["ProvenanceRecord"]["properties"]
    assert sorted(entry) == [
        "basis",
        "beliefs",
        "date",
        "match",
        "method",
        "note",
        "service",
        "stated_by",
    ]
    assert "required" not in defs["ProvenanceRecord"]
    assert defs["Belief"]["properties"]["belief"]["enum"] == list(BELIEFS)
    assert defs["Belief"]["required"] == ["actor", "belief", "date"]
    assert entry["method"]["anyOf"][0]["enum"] == list(METHODS)
    assert entry["match"]["enum"] == list(MATCHES)
    context = defs["Context"]
    consts = {term: rule["const"] for term, rule in context["properties"].items()}
    assert consts == FORMAT_CONTEXT
    assert context["required"] == list(FORMAT_CONTEXT)
    assert context["propertyNames"]["anyOf"][0]["enum"] == list(FORMAT_CONTEXT)
    for name in ("Iri", "PrefixIri"):
        assert defs[name]["not"] == {"pattern": BLANK}, name
    assert defs["IriReference"]["not"]["anyOf"][0] == {"pattern": BLANK}


def _accepts(name: str, value: Any) -> bool:
    return Draft202012Validator({"$ref": f"#/$defs/{name}", "$defs": _defs()}).is_valid(
        value
    )


def test_iris_prefixes_and_language_tags() -> None:
    for value in (
        "schema:MusicRecording",
        "http://musicbrainz.org/work/x",
        "urn:isbn:0451450523",
        "mailto:a@example.org",
        "wdt:P175",
    ):
        assert _accepts("Iri", value), value
    for value in (
        "MusicRecording",
        "1http://x",
        "http:",
        "schema:a b",
        "schema:a\n",
        "schema:a\u00a0b",
        "schema:a\ufeff",
    ):
        assert not _accepts("Iri", value), value
    for value in ("#clt_1", "other.yaml#clt_1", "wd:Q1", "records/op106.json"):
        assert _accepts("IriReference", value), value
    for value in ("", "a b", "_:b0", "@id"):
        assert not _accepts("IriReference", value), value
    for value in ("http://schema.org/", "https://d-nb.info/standards/elementset/gnd#"):
        assert _accepts("PrefixIri", value), value
    for value in ("http://www.wikidata.org/entity", "http://a/\n", "schema/"):
        assert not _accepts("PrefixIri", value), value
    for value in ("schema", "melodTerms", "wd", "a_b-1"):
        assert _accepts("PrefixName", value), value
    for value in ("unit", "http", "urn", "1a", "a:b", "a.b", ""):
        assert not _accepts("PrefixName", value), value
    for value in ("en", "de-CH", "zh-Hant-TW"):
        assert _accepts("LanguageTag", value), value
    for value in ("", "en_GB", "en\n", "toolongtag"):
        assert not _accepts("LanguageTag", value), value


def test_the_provenance_schema_is_bundled() -> None:
    directory = REPOSITORY_ROOT / "schema" / "0.2.0"
    provenance = json.loads((directory / "provenance.schema.json").read_text("utf-8"))
    manifest = json.loads((directory / "timetoshare.schema.json").read_text("utf-8"))
    assert provenance_schema_path() == directory / "provenance.schema.json"
    assert provenance["$id"] == (
        "https://timetoalign.github.io/timetoshare/0.2.0/provenance.schema.json"
    )
    assert manifest["$defs"]["ProvenanceEntry"]["allOf"] == [
        {"$ref": "provenance.schema.json"}
    ]
    assert sorted(provenance["$defs"]) == ["Belief", "CalendarDate"]
    references = sorted(
        {node["$ref"] for node, _ in _nodes(provenance) if "$ref" in node}
    )
    assert references == [
        "#/$defs/Belief",
        "#/$defs/CalendarDate",
        "timetoshare.schema.json#/$defs/Iri",
        "timetoshare.schema.json#/$defs/IriReference",
    ]
    bundled = load_schema()
    assert bundled == bundle_schemas(manifest, provenance)
    record = bundled["$defs"]["ProvenanceRecord"]
    assert record["properties"]["stated_by"]["items"] == {
        "$ref": "#/$defs/IriReference"
    }
    assert set(record) == set(provenance) - {"$schema", "$id", "$defs", "title"}
    with pytest.raises(ValueError) as raised:
        bundle_schemas(manifest, {**provenance, "$defs": {"Timeline": {}}})
    assert str(raised.value) == "both schemas define 'Timeline'"
