"""Packages: ``package.yaml``, tables read from folders, and the package check.

The strategy is the README's section "Packages".
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from fractions import Fraction
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from timetoshare import (  # noqa: E402
    SchemaValidationError,
    UnsupportedVersionError,
    dumps,
    load_package_schema,
    load_schema,
    loads,
    package_schema_path,
    validate_package,
    with_bare_ids,
    with_file_ids,
)
from timetoshare.tables import (  # noqa: E402
    MATCH_CLAIM_SCHEMA,
    PROJECTION_SCHEMA,
    PROVENANCE_METADATA_KEY,
    TYPE_METADATA_KEY,
    VERSION_METADATA_KEY,
    TableError,
    check_match_claims,
    check_projections,
    package_fixture_path,
    package_problems,
    read_table,
    table_files,
)

bundle_package_schema = import_module("timetoshare.validate").bundle_package_schema
package_module = import_module("timetoshare.tables.package")

SHARED = package_fixture_path("shared")
CASES = sorted(path.name for path in package_fixture_path("rejections").iterdir())
ACCEPTED = sorted(path.name for path in package_fixture_path("acceptances").iterdir())


def _read(path: Path) -> Any:
    return loads(path.read_text(encoding="utf-8"))


def _problems(path: Path) -> list[dict[str, Any]]:
    return [
        {
            "code": problem.code,
            "file": problem.file,
            "row": problem.row,
            "path": list(problem.path),
            "message": problem.message,
        }
        for problem in package_problems(path / "package.yaml")
    ]


def _refusal(call: Any) -> tuple[Any, ...]:
    with pytest.raises(SchemaValidationError) as raised:
        call()
    return raised.value.code, raised.value.path, raised.value.message


# The package schema


def test_the_package_schema_lies_beside_the_manifest_schema() -> None:
    document = json.loads(package_schema_path().read_text(encoding="utf-8"))
    assert package_schema_path().name == "package.schema.json"
    assert package_schema_path().parent.name == "0.2.0"
    assert document["$id"] == (
        "https://timetoalign.github.io/timetoshare/0.2.0/package.schema.json"
    )
    assert document["required"] == ["timetoshare", "manifests", "tables"]
    assert list(document["properties"]) == [
        "timetoshare",
        "id",
        "name",
        "meta",
        "manifests",
        "tables",
    ]
    outside = sorted(
        {
            node["$ref"]
            for node in _nodes(document)
            if isinstance(node, dict) and not node.get("$ref", "#").startswith("#")
        }
    )
    assert outside == [
        "timetoshare.schema.json#/$defs/Descriptor",
        "timetoshare.schema.json#/$defs/IriReference",
        "timetoshare.schema.json#/$defs/Meta",
        "timetoshare.schema.json#/$defs/Name",
    ]


def _nodes(value: Any) -> list[Any]:
    found = [value]
    if isinstance(value, dict):
        for item in value.values():
            found.extend(_nodes(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_nodes(item))
    return found


def test_the_package_schema_is_bundled_with_what_it_reaches() -> None:
    document = json.loads(package_schema_path().read_text(encoding="utf-8"))
    bundled = load_package_schema()
    assert bundled == bundle_package_schema(document, load_schema())
    assert list(bundled["$defs"]) == [
        "Table",
        "Descriptor",
        "Name",
        "Meta",
        "IriReference",
    ]
    for name in ("Descriptor", "Name", "Meta", "IriReference"):
        assert bundled["$defs"][name] == load_schema()["$defs"][name]
    references = [
        node["$ref"]
        for node in _nodes(bundled)
        if isinstance(node, dict) and "$ref" in node
    ]
    assert references
    assert all(reference.startswith("#/$defs/") for reference in references)
    assert all(
        reference.removeprefix("#/$defs/") in bundled["$defs"]
        for reference in references
    )


def test_a_package_schema_reaching_elsewhere_or_redefining_is_refused() -> None:
    other = {"properties": {"a": {"$ref": "https://example.org/other.json"}}}
    with pytest.raises(ValueError) as raised:
        bundle_package_schema(other, load_schema())
    assert str(raised.value) == (
        "reference 'https://example.org/other.json' leads to no definition of the "
        "manifest schema"
    )
    clash = {
        "properties": {"a": {"$ref": "timetoshare.schema.json#/$defs/Descriptor"}},
        "$defs": {"Descriptor": {}},
    }
    with pytest.raises(ValueError) as raised:
        bundle_package_schema(clash, load_schema())
    assert str(raised.value) == "both schemas define 'Descriptor'"


def test_one_descriptor_for_resources_and_tables() -> None:
    definitions = load_schema()["$defs"]
    descriptor = definitions["Descriptor"]
    assert list(descriptor["properties"]) == ["url", "media_type", "size", "integrity"]
    assert descriptor["required"] == ["url"]
    resource = definitions["Resource"]
    assert resource["allOf"] == [{"$ref": "#/$defs/Descriptor"}]
    assert list(resource["properties"]) == ["id", "type", "timelines"]
    assert resource["required"] == ["id", "type", "timelines"]
    table = load_package_schema()["$defs"]["Table"]
    assert table["allOf"] == [{"$ref": "#/$defs/Descriptor"}]
    assert list(table["properties"]) == ["type"]
    assert table["required"] == ["type"]


# validate_package


def test_the_shared_and_the_smallest_package_validate() -> None:
    validate_package(_read(SHARED / "package.yaml"))
    validate_package({"timetoshare": "0.2.0", "manifests": [], "tables": []})


def _package(**members: Any) -> dict[str, Any]:
    return {
        "timetoshare": "0.2.0",
        "manifests": [{"url": "a.yaml"}],
        "tables": [],
        **members,
    }


FOLDER = {"type": "Projection", "url": "tables/Projection/"}
FILE = {"type": "MatchClaim", "url": "match_claims.parquet"}
DIGEST = {"algorithm": "SHA-256", "digest": "00ff"}

PACKAGE_REFUSALS = [
    (
        {"manifests": [], "tables": []},
        ("not_a_package", (), "not a TimeToShare package"),
    ),
    ([], ("not_a_package", (), "not a TimeToShare package")),
    (
        {"timetoshare": "0.2.0", "manifests": []},
        ("schema", (), "'tables' is a required property"),
    ),
    (
        _package(tables=[{"url": "x.parquet"}]),
        ("schema", ("tables", 0), "'type' is a required property"),
    ),
    (
        _package(manifests=[{"url": "a.yaml", "size": -1}]),
        ("schema", ("manifests", 0, "size"), "-1 is less than the minimum of 0"),
    ),
    (
        _package(manifests=[{"url": "a.yaml"}, {"url": "a.yaml"}]),
        (
            "duplicate_url",
            ("manifests", 1, "url"),
            "the manifest 'a.yaml' is listed twice, first at #/manifests/0/url",
        ),
    ),
    (
        _package(tables=[FOLDER, FOLDER]),
        (
            "duplicate_url",
            ("tables", 1, "url"),
            "the table 'tables/Projection/' of the type Projection is listed twice, "
            "first at #/tables/0/url",
        ),
    ),
    (
        _package(tables=[FILE, {**FOLDER, "size": 1024}]),
        (
            "folder_descriptor",
            ("tables", 1, "size"),
            "'tables/Projection/' names a folder, which has no size",
        ),
    ),
    (
        _package(tables=[{**FOLDER, "integrity": DIGEST}]),
        (
            "folder_descriptor",
            ("tables", 0, "integrity"),
            "'tables/Projection/' names a folder, which has no integrity",
        ),
    ),
    (
        _package(manifests=[{"url": "manifests/", "size": 3}]),
        (
            "folder_descriptor",
            ("manifests", 0, "size"),
            "'manifests/' names a folder, which has no size",
        ),
    ),
]


@pytest.mark.parametrize(("value", "expected"), PACKAGE_REFUSALS)
def test_each_package_refusal(value: Any, expected: tuple[Any, ...]) -> None:
    assert _refusal(lambda: validate_package(value)) == expected


def test_a_package_of_another_version() -> None:
    with pytest.raises(UnsupportedVersionError) as raised:
        validate_package(_package(timetoshare="0.1.0"))
    assert str(raised.value) == (
        'unsupported TimeToShare version "0.1.0"; this package reads 0.2.0 only'
    )


def test_a_file_with_size_and_integrity_validates() -> None:
    validate_package(_package(tables=[{**FILE, "size": 1024, "integrity": DIGEST}]))


def test_one_url_under_two_types_validates() -> None:
    validate_package(_package(tables=[FOLDER, {**FOLDER, "type": "Box"}]))


# read_table


def _resources() -> list[tuple[str, dict[str, Any]]]:
    return [
        (manifest, resource)
        for manifest in _read(SHARED / "expected.yaml")["read"]
        for resource in with_bare_ids(_read(SHARED / manifest))["resources"]
    ]


@pytest.mark.parametrize(
    ("manifest", "resource"),
    _resources(),
    ids=lambda value: value if isinstance(value, str) else value["id"],
)
def test_a_resource_reads_its_rows_from_a_shared_folder(
    manifest: str, resource: dict[str, Any]
) -> None:
    expected = _read(SHARED / "expected.yaml")["read"][manifest][resource["id"]]
    folder = (SHARED / manifest).parent / resource["url"]
    table = read_table(folder, timelines=resource["timelines"])
    assert sorted(table.column("id").to_pylist()) == expected
    assert table.schema.metadata == {
        TYPE_METADATA_KEY.encode(): resource["type"].encode()
    }
    check = (
        check_match_claims if resource["type"] == "MatchClaim" else check_projections
    )
    check(table, _read(SHARED / manifest))


def test_the_expected_reads_are_stated() -> None:
    assert _read(SHARED / "expected.yaml")["read"] == {
        "bach/manifest.yaml": {
            "resource_1": ["claim_1", "claim_2", "claim_5"],
            "resource_2": [
                "projection_1",
                "projection_2",
                "projection_7",
                "projection_9",
            ],
        },
        "handel/manifest.yaml": {
            "resource_1": ["claim_3", "claim_4"],
            "resource_2": [
                "projection_3",
                "projection_4",
                "projection_5",
                "projection_6",
                "projection_8",
            ],
        },
    }


def test_a_folder_fills_in_the_provenance_its_file_shares() -> None:
    table = read_table(SHARED / "tables" / "MatchClaim")
    assert (
        table.column("provenance").to_pylist()
        == [
            {
                "stated_by": None,
                "date": "2026-11-20",
                "method": "imported",
                "service": "https://example.org/aligner",
                "basis": None,
                "match": None,
                "note": None,
                "beliefs": None,
            }
        ]
        * 5
    )


def test_a_match_claim_with_either_timeline_listed_is_kept() -> None:
    table = read_table(SHARED / "tables" / "MatchClaim", timelines=["dpt_1"])
    assert sorted(table.column("id").to_pylist()) == ["claim_1", "claim_2", "claim_5"]


def test_without_timelines_every_row_and_with_none_no_row() -> None:
    assert len(read_table(SHARED / "tables" / "MatchClaim")) == 5
    assert len(read_table(SHARED / "tables" / "Projection")) == 9
    assert len(read_table(SHARED / "tables" / "Projection", timelines=[])) == 0


def test_a_folder_holds_its_parquet_files_alone(tmp_path: Path) -> None:
    source = SHARED / "tables" / "Projection"
    assert [file.name for file in table_files(source)] == [
        "part_a.parquet",
        "part_b.parquet",
    ]
    folder = tmp_path / "Projection"
    shutil.copytree(source, folder)
    for name in (".part_c.parquet", "_part_d.parquet"):
        shutil.copy(source / "part_a.parquet", folder / name)
    (folder / "notes.txt").write_text("not a table\n", encoding="utf-8")
    (folder / "sub").mkdir()
    shutil.copy(source / "part_a.parquet", folder / "sub" / "part_e.parquet")
    assert [file.name for file in table_files(folder)] == [
        "part_a.parquet",
        "part_b.parquet",
    ]
    assert read_table(folder).equals(read_table(source))
    single = read_table(source / "part_b.parquet")
    assert single.column("id").to_pylist() == [
        "projection_6",
        "projection_7",
        "projection_8",
        "projection_9",
    ]


def _copied(tmp_path: Path) -> Path:
    shutil.copytree(SHARED, tmp_path / "package")
    return tmp_path / "package"


def _rewrite(path: Path, change: Any = None, **metadata: str | None) -> None:
    """Rewrite a Parquet file with its table changed and its metadata merged
    (a ``None`` value drops a key)."""
    table = pq.read_table(path)
    merged = {
        key.decode(): value.decode()
        for key, value in (table.schema.metadata or {}).items()
    }
    if change is not None:
        table = change(table)
    merged.update(metadata)
    pq.write_table(
        table.replace_schema_metadata(
            {k: v for k, v in merged.items() if v is not None}
        ),
        path,
    )


def _table_refusal(call: Any) -> tuple[Any, ...]:
    with pytest.raises(TableError) as raised:
        call()
    problem = raised.value.problem
    return problem.code, problem.row, problem.column, problem.message


def _with_velocity(kind: Any) -> Any:
    def change(table: Any) -> Any:
        values = [64] * len(table) if kind == pa.int64() else ["mf"] * len(table)
        return table.append_column(pa.field("velocity", kind), pa.array(values, kind))

    return change


def test_a_column_of_two_types_in_one_folder_is_refused(tmp_path: Path) -> None:
    folder = _copied(tmp_path) / "tables" / "Projection"
    _rewrite(folder / "part_a.parquet", _with_velocity(pa.int64()))
    _rewrite(folder / "part_b.parquet", _with_velocity(pa.string()))
    assert _table_refusal(lambda: read_table(folder)) == (
        "column_type_mismatch",
        None,
        ("velocity",),
        "the column 'velocity' is int64 in 'part_a.parquet' and string in "
        "'part_b.parquet'",
    )


def test_a_column_a_file_lacks_reads_as_null(tmp_path: Path) -> None:
    folder = _copied(tmp_path) / "tables" / "Projection"
    _rewrite(folder / "part_a.parquet", _with_velocity(pa.int64()))
    assert read_table(folder).column("velocity").to_pylist() == [64] * 5 + [None] * 4


def test_the_type_of_a_table(tmp_path: Path) -> None:
    folder = _copied(tmp_path) / "tables" / "Projection"
    assert _table_refusal(lambda: read_table(folder, type="MatchClaim")) == (
        "table_type",
        None,
        (),
        "'part_a.parquet' holds the type Projection, not MatchClaim",
    )
    _rewrite(folder / "part_b.parquet", **{TYPE_METADATA_KEY: "MatchClaim"})
    assert _table_refusal(lambda: read_table(folder)) == (
        "table_type",
        None,
        (),
        "'part_a.parquet' holds the type Projection and 'part_b.parquet' the type "
        "MatchClaim",
    )
    for name in ("part_a.parquet", "part_b.parquet"):
        _rewrite(folder / name, **{TYPE_METADATA_KEY: None})
    assert _table_refusal(lambda: read_table(folder)) == (
        "table_type",
        None,
        (),
        "the table names no type: no file states 'timetoshare:type'",
    )
    table = read_table(folder, type="Projection", timelines=["dpt_1"])
    assert sorted(table.column("id").to_pylist()) == [
        "projection_1",
        "projection_2",
        "projection_7",
        "projection_9",
    ]


def test_a_row_stating_provenance_beside_its_file(tmp_path: Path) -> None:
    folder = _copied(tmp_path) / "tables" / "MatchClaim"

    def stated(table: Any) -> Any:
        rows = table.to_pylist()
        rows[0]["provenance"] = {**(rows[0]["provenance"] or {}), "method": "manual"}
        return pa.Table.from_pylist(rows, schema=MATCH_CLAIM_SCHEMA)

    _rewrite(folder / "part_a.parquet", stated)
    assert _table_refusal(lambda: read_table(folder)) == (
        "invalid_provenance",
        0,
        ("provenance",),
        "the provenance is stated in the file's metadata and in the row",
    )


def test_a_provenance_column_of_another_type_is_refused(tmp_path: Path) -> None:
    folder = _copied(tmp_path) / "tables" / "MatchClaim"

    def as_strings(table: Any) -> Any:
        index = table.schema.get_field_index("provenance")
        strings = pa.array(["manual"] * len(table), pa.string())
        return table.set_column(index, pa.field("provenance", pa.string()), strings)

    _rewrite(folder / "part_a.parquet", as_strings)
    declared = MATCH_CLAIM_SCHEMA.field("provenance").type
    assert _table_refusal(lambda: read_table(folder)) == (
        "schema_violation",
        None,
        ("provenance",),
        f"the column 'provenance' is string, not {declared}, in 'part_a.parquet'",
    )


def test_timelines_need_the_column_naming_a_rows_timeline(tmp_path: Path) -> None:
    folder = _copied(tmp_path) / "tables" / "Projection"
    for name in ("part_a.parquet", "part_b.parquet"):
        _rewrite(folder / name, lambda table: table.drop_columns(["timeline_id"]))
    assert len(read_table(folder)) == 9
    assert _table_refusal(lambda: read_table(folder, timelines=["dpt_1"])) == (
        "schema_violation",
        None,
        ("timeline_id",),
        "the table has no column 'timeline_id'",
    )


def test_a_missing_table_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_table(tmp_path / "missing")


_READ_IN_A_CHILD = """
import json, sys
from timetoshare.tables import read_table
timelines = json.loads(sys.argv[2])
table = read_table(sys.argv[1], timelines=timelines)
print(json.dumps({
    "rows": table.num_rows,
    "columns": table.schema.names,
    "metadata": {k.decode(): v.decode() for k, v in table.schema.metadata.items()},
}))
"""
"""Read a table in a child process and print what it holds, so that a crash
fails the test instead of ending the test run."""


def _read_in_a_child(path: Path, timelines: list[str] | None) -> Any:
    done = subprocess.run(
        [sys.executable, "-c", _READ_IN_A_CHILD, str(path), json.dumps(timelines)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (done.returncode, done.stderr) == (0, "")
    return json.loads(done.stdout)


_NO_MATCH_CLAIM = {
    "rows": 0,
    "columns": MATCH_CLAIM_SCHEMA.names,
    "metadata": {TYPE_METADATA_KEY: "MatchClaim"},
}


def test_a_filter_keeping_no_match_claim_of_a_shared_provenance() -> None:
    folder = SHARED / "tables" / "MatchClaim"
    assert (
        PROVENANCE_METADATA_KEY.encode()
        in pq.read_schema(folder / "part_a.parquet").metadata
    )
    assert _read_in_a_child(folder, ["clt_3"]) == _NO_MATCH_CLAIM


def test_a_match_claim_file_of_a_shared_provenance_without_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / "empty.parquet"
    metadata = pq.read_schema(SHARED / "tables" / "MatchClaim" / "part_a.parquet")
    pq.write_table(
        MATCH_CLAIM_SCHEMA.empty_table().replace_schema_metadata(metadata.metadata),
        path,
    )
    assert _read_in_a_child(path, None) == _NO_MATCH_CLAIM


# package_problems


def test_the_shared_package_has_no_problem() -> None:
    assert _problems(SHARED) == []


def test_every_acceptance_is_stated() -> None:
    assert ACCEPTED == ["recording_resource"]


@pytest.mark.parametrize("case", ACCEPTED)
def test_each_accepted_package(case: str) -> None:
    directory = package_fixture_path("acceptances", case)
    assert _read(directory / "expected.yaml")["problems"] == []
    assert _problems(directory) == []


def test_the_recording_is_the_one_change() -> None:
    directory = package_fixture_path("acceptances", "recording_resource")
    bach = _read(directory / "bach" / "manifest.yaml")
    assert (
        bach["resources"][:2] == _read(SHARED / "bach" / "manifest.yaml")["resources"]
    )
    assert bach["resources"][2:] == [
        {
            "id": "#resource_3",
            "type": "Audio",
            "timelines": ["#dpt_1"],
            "url": "recording.flac",
            "media_type": "audio/flac",
        }
    ]
    assert not (directory / "bach" / "recording.flac").exists()


def test_every_rejection_is_stated() -> None:
    assert CASES == [
        "axis_mismatch",
        "claim_across_manifests",
        "column_in_two_types",
        "file_in_a_listed_folder",
        "file_of_another_type",
        "folder_with_size",
        "projection_id_in_two_files",
        "resource_naming_no_table",
        "row_of_no_manifest",
        "table_listed_twice",
        "timeline_in_two_manifests",
        "timeline_unlisted",
        "version_mismatch",
    ]


@pytest.mark.parametrize("case", CASES)
def test_each_rejected_package(case: str) -> None:
    directory = package_fixture_path("rejections", case)
    assert _problems(directory) == _read(directory / "expected.yaml")["problems"]


EXPECTED = {
    "row_of_no_manifest": ("unknown_timeline", "tables/Projection/part_b.parquet", 4),
    "projection_id_in_two_files": (
        "duplicate_id",
        "tables/Projection/part_b.parquet",
        3,
    ),
    "timeline_in_two_manifests": ("duplicate_timeline", "handel/manifest.yaml", None),
    "claim_across_manifests": (
        "claim_across_manifests",
        "tables/MatchClaim/part_a.parquet",
        2,
    ),
    "column_in_two_types": ("column_type_mismatch", "tables/Projection/", None),
    "version_mismatch": ("version_mismatch", "tables/Projection/part_b.parquet", None),
    "resource_naming_no_table": ("unknown_table", "bach/manifest.yaml", None),
    "folder_with_size": ("folder_descriptor", "package.yaml", None),
    "axis_mismatch": ("axis_mismatch", "tables/Projection/part_b.parquet", 1),
    "file_of_another_type": ("table_type", "tables/Projection/part_b.parquet", None),
    "table_listed_twice": ("duplicate_url", "package.yaml", None),
    "file_in_a_listed_folder": ("duplicate_url", "package.yaml", None),
}
"""The one problem of each case but ``timeline_unlisted``, as the README's
table states it."""


@pytest.mark.parametrize("case", sorted(EXPECTED))
def test_each_case_is_the_readmes(case: str) -> None:
    found = _problems(package_fixture_path("rejections", case))
    assert [(p["code"], p["file"], p["row"]) for p in found] == [EXPECTED[case]]


def test_an_unlisted_timeline_is_reported_at_each_of_its_rows() -> None:
    found = _problems(package_fixture_path("rejections", "timeline_unlisted"))
    assert [(p["code"], p["file"], p["row"], p["path"]) for p in found] == [
        ("unlisted_timeline", "tables/Projection/part_a.parquet", 0, ["timeline_id"]),
        ("unlisted_timeline", "tables/Projection/part_b.parquet", 2, ["timeline_id"]),
    ]


def test_each_manifest_alone_passes_the_repeated_id() -> None:
    directory = package_fixture_path("rejections", "projection_id_in_two_files")
    for name in ("bach/manifest.yaml", "handel/manifest.yaml"):
        manifest = with_bare_ids(_read(directory / name))
        resource = manifest["resources"][1]
        table = read_table(
            directory / "tables" / "Projection", timelines=resource["timelines"]
        )
        check_projections(table, _read(directory / name))


def _write_yaml(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dumps(value).encode("utf-8"))


def _listing(directory: Path, change: Any) -> None:
    value = _read(directory / "package.yaml")
    change(value)
    _write_yaml(directory / "package.yaml", value)


def test_a_missing_manifest_and_a_missing_folder(tmp_path: Path) -> None:
    directory = _copied(tmp_path)
    _listing(
        directory,
        lambda value: (
            value["manifests"].append({"url": "gone.yaml"}),
            value["tables"].append({"type": "Box", "url": "tables/Box/"}),
        ),
    )
    assert _problems(directory) == [
        {
            "code": "missing_file",
            "file": "package.yaml",
            "row": None,
            "path": ["manifests", 2, "url"],
            "message": "no manifest lies at 'gone.yaml' in the package",
        },
        {
            "code": "missing_file",
            "file": "package.yaml",
            "row": None,
            "path": ["tables", 2, "url"],
            "message": "no folder lies at 'tables/Box/' in the package",
        },
    ]


def test_a_url_leaving_the_package_names_no_table(tmp_path: Path) -> None:
    directory = _copied(tmp_path)
    _listing(
        directory,
        lambda value: value["tables"].append({"type": "Box", "url": "../outside/"}),
    )
    bach = _read(directory / "bach" / "manifest.yaml")
    bach["resources"].append(
        {
            "id": "#resource_3",
            "type": "Box",
            "timelines": ["#clt_1"],
            "url": "../../outside/",
        }
    )
    _write_yaml(directory / "bach" / "manifest.yaml", bach)
    assert _problems(directory) == [
        {
            "code": "missing_file",
            "file": "package.yaml",
            "row": None,
            "path": ["tables", 2, "url"],
            "message": "no folder lies at '../outside/' in the package",
        },
        {
            "code": "unknown_table",
            "file": "bach/manifest.yaml",
            "row": None,
            "path": ["resources", 2, "url"],
            "message": "the resource 'resource_3' names '../../outside/', which is "
            "no table of the type Box in the package",
        },
    ]


def test_only_a_table_resource_names_a_table(tmp_path: Path) -> None:
    directory = _copied(tmp_path)
    bach = _read(directory / "bach" / "manifest.yaml")
    added = [
        ("Image", "#clt_1", "score.png", None),
        ("Text", "#dpt_1", "notes.txt", "text/plain"),
        ("Recording", "#dpt_1", "take.parquet", None),
        ("Scan", "#clt_1", "scans/", None),
        ("Sheet", "#dpt_1", "sheet.bin", "application/vnd.apache.parquet"),
        ("Projection", "#clt_1", "more.arrow", None),
    ]
    for number, (kind, timeline, url, media_type) in enumerate(added, start=3):
        resource = {
            "id": f"#resource_{number}",
            "type": kind,
            "timelines": [timeline],
            "url": url,
        }
        if media_type is not None:
            resource["media_type"] = media_type
        bach["resources"].append(resource)
    _write_yaml(directory / "bach" / "manifest.yaml", bach)
    assert _problems(directory) == [
        {
            "code": "unknown_table",
            "file": "bach/manifest.yaml",
            "row": None,
            "path": ["resources", index, "url"],
            "message": f"the resource 'resource_{index + 1}' names '{url}', which "
            f"is no table of the type {kind} in the package",
        }
        for index, (kind, url) in (
            (4, ("Recording", "take.parquet")),
            (5, ("Scan", "scans/")),
            (6, ("Sheet", "sheet.bin")),
            (7, ("Projection", "more.arrow")),
        )
    ]


def test_a_null_timeline_is_reported_at_its_row(tmp_path: Path) -> None:
    directory = _copied(tmp_path)

    def nulled(*columns: str) -> Any:
        def change(table: Any) -> Any:
            for column in columns:
                index = table.schema.get_field_index(column)
                values = table.column(column).to_pylist()
                values[0] = None
                table = table.set_column(
                    index, table.schema.field(index), pa.array(values, pa.string())
                )
            return table

        return change

    _rewrite(
        directory / "tables" / "Projection" / "part_b.parquet", nulled("timeline_id")
    )
    _rewrite(
        directory / "tables" / "MatchClaim" / "part_a.parquet",
        nulled("timeline_a_id", "timeline_b_id"),
    )
    assert _problems(directory) == [
        {
            "code": "schema_violation",
            "file": "tables/Projection/part_b.parquet",
            "row": 0,
            "path": ["timeline_id"],
            "message": "'timeline_id' is null",
        },
        {
            "code": "schema_violation",
            "file": "tables/MatchClaim/part_a.parquet",
            "row": 0,
            "path": ["timeline_a_id"],
            "message": "'timeline_a_id' is null",
        },
        {
            "code": "schema_violation",
            "file": "tables/MatchClaim/part_a.parquet",
            "row": 0,
            "path": ["timeline_b_id"],
            "message": "'timeline_b_id' is null",
        },
    ]


EXTRA = {
    "timetoshare": "0.2.0",
    "timelines": [{"id": "dlt_1", "unit": "ticks", "length": 960}],
}


def test_a_manifest_of_another_version_and_an_invalid_manifest(tmp_path: Path) -> None:
    directory = _copied(tmp_path)
    _write_yaml(
        directory / "old" / "manifest.yaml",
        with_file_ids({**EXTRA, "timetoshare": "0.1.0"}),
    )
    invalid = {
        **EXTRA,
        "resources": [
            {
                "id": "resource_1",
                "type": "Box",
                "timelines": ["dlt_9"],
                "url": "boxes.parquet",
            }
        ],
    }
    _write_yaml(directory / "invalid" / "manifest.yaml", with_file_ids(invalid))
    _listing(
        directory,
        lambda value: value["manifests"].extend(
            [{"url": "old/manifest.yaml"}, {"url": "invalid/manifest.yaml"}]
        ),
    )
    assert _problems(directory) == [
        {
            "code": "version_mismatch",
            "file": "old/manifest.yaml",
            "row": None,
            "path": ["timetoshare"],
            "message": "the manifest declares the version '0.1.0', the package '0.2.0'",
        },
        {
            "code": "resource_timeline",
            "file": "invalid/manifest.yaml",
            "row": None,
            "path": ["resources", 0, "timelines", 0],
            "message": "'dlt_9' names no timeline or virtual timeline of this manifest",
        },
    ]


def _write_table(
    path: Path, rows: list[dict[str, Any]], schema: Any, kind: str
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(
        table.replace_schema_metadata(
            {TYPE_METADATA_KEY: kind, VERSION_METADATA_KEY: "0.2.0"}
        ),
        path,
    )


def test_a_match_claim_id_twice_is_reported_once(tmp_path: Path) -> None:
    directory = _copied(tmp_path)
    claims = pq.read_table(directory / "tables" / "MatchClaim" / "part_a.parquet")
    _write_table(
        directory / "tables" / "MatchClaim" / "part_b.parquet",
        claims.slice(0, 1).to_pylist(),
        MATCH_CLAIM_SCHEMA,
        "MatchClaim",
    )
    assert _problems(directory) == [
        {
            "code": "duplicate_id",
            "file": "tables/MatchClaim/part_b.parquet",
            "row": 0,
            "path": ["id"],
            "message": "the MatchClaim ID 'claim_1' is given twice, first in "
            "'tables/MatchClaim/part_a.parquet' at row 0",
        }
    ]


BOX = pa.schema(
    [
        ("id", pa.string()),
        ("timeline_id", pa.string()),
        ("unit", pa.string()),
        ("number_type", pa.string()),
        ("start", PROJECTION_SCHEMA.field("start").type),
        ("duration", PROJECTION_SCHEMA.field("duration").type),
    ]
)


def test_an_event_id_is_unique_across_every_type(tmp_path: Path) -> None:
    directory = _copied(tmp_path)
    number = {"numerator": 0, "denominator": None, "value": None}
    _write_table(
        directory / "tables" / "Box" / "part_a.parquet",
        [
            {
                "id": "projection_1",
                "timeline_id": "dpt_1",
                "unit": "samples",
                "number_type": "int",
                "start": number,
                "duration": None,
            }
        ],
        BOX,
        "Box",
    )
    _listing(
        directory,
        lambda value: value["tables"].append({"type": "Box", "url": "tables/Box/"}),
    )
    bach = _read(directory / "bach" / "manifest.yaml")
    bach["resources"].append(
        {
            "id": "#resource_3",
            "type": "Box",
            "timelines": ["#dpt_1"],
            "url": "../tables/Box/",
        }
    )
    _write_yaml(directory / "bach" / "manifest.yaml", bach)
    assert _problems(directory) == [
        {
            "code": "duplicate_id",
            "file": "tables/Box/part_a.parquet",
            "row": 0,
            "path": ["id"],
            "message": "the event ID 'projection_1' is given twice, first in "
            "'tables/Projection/part_a.parquet' at row 1",
        }
    ]


def test_a_large_package_checks_each_row_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = _copied(tmp_path)
    folder = directory / "tables" / "Projection"
    for file in folder.iterdir():
        file.unlink()
    number = {"numerator": 0, "denominator": None, "value": None}
    rows = [
        {
            "id": f"projection_{index}",
            "timeline_id": "dpt_1" if index % 2 else "dpt_2",
            "unit": "samples",
            "number_type": "int",
            "start": {**number, "numerator": index},
            "duration": None,
            "projection_of": None,
        }
        for index in range(20000)
    ]
    rows[15000] = {**rows[15000], "id": "projection_11"}
    _write_table(folder / "part_a.parquet", rows, PROJECTION_SCHEMA, "Projection")
    checks = dict(package_module._CHECKED)
    calls: list[tuple[str, str | None, int, set[str]]] = []

    def recorded(kind: str) -> Any:
        def check(table: Any, manifest: Any) -> Any:
            timelines = (
                ["timeline_a_id", "timeline_b_id"]
                if kind == "MatchClaim"
                else ["timeline_id"]
            )
            seen = {
                value
                for column in timelines
                for value in table.column(column).to_pylist()
            }
            calls.append((kind, manifest.get("name"), len(table), seen))
            return checks[kind](table, manifest)

        return check

    for kind in ("MatchClaim", "Projection"):
        monkeypatch.setitem(package_module._CHECKED, kind, recorded(kind))
    found = _problems(directory)
    assert found == [
        {
            "code": "duplicate_id",
            "file": "tables/Projection/part_a.parquet",
            "row": 15000,
            "path": ["id"],
            "message": "the event ID 'projection_11' is given twice, first in "
            "'tables/Projection/part_a.parquet' at row 11",
        }
    ]
    assert calls == [
        ("MatchClaim", "Bach", 3, {"clt_1", "dpt_1"}),
        ("Projection", "Bach", 10000, {"dpt_1"}),
        ("MatchClaim", "Handel", 2, {"clt_2", "dpt_2"}),
        ("Projection", "Handel", 10000, {"dpt_2"}),
    ]


def test_the_fixture_files_are_the_scripts() -> None:
    package = _read(SHARED / "package.yaml")
    assert package["tables"] == [
        {
            "media_type": "application/vnd.apache.parquet",
            "type": "MatchClaim",
            "url": "tables/MatchClaim/",
        },
        {
            "media_type": "application/vnd.apache.parquet",
            "type": "Projection",
            "url": "tables/Projection/",
        },
    ]
    for name, kind in (
        ("MatchClaim/part_a.parquet", "MatchClaim"),
        ("Projection/part_a.parquet", "Projection"),
        ("Projection/part_b.parquet", "Projection"),
    ):
        metadata = pq.read_schema(SHARED / "tables" / name).metadata
        assert metadata[TYPE_METADATA_KEY.encode()] == kind.encode()
        assert metadata[VERSION_METADATA_KEY.encode()] == b"0.2.0"
        assert (PROVENANCE_METADATA_KEY.encode() in metadata) is (kind == "MatchClaim")
    part_a = pq.read_table(SHARED / "tables" / "Projection" / "part_a.parquet")
    order = [
        (
            row["timeline_id"],
            Fraction(row["start"]["numerator"], row["start"]["denominator"] or 1),
            row["id"],
        )
        for row in part_a.to_pylist()
    ]
    assert order == sorted(order)
    part_b = pq.read_table(SHARED / "tables" / "Projection" / "part_b.parquet")
    assert part_b.column("timeline_id").to_pylist() == [
        "dpt_2",
        "dpt_1",
        "clt_3",
        "dpt_1",
    ]
