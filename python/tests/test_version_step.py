"""The version step a change of a repository of manifests requires."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from timetoshare import (
    STEPS,
    Finding,
    StepReport,
    dumps,
    fixture_paths,
    git_step,
    loads,
    manifest_step,
    tree_step,
)
from timetoshare.validate import data_root, validate

VERSIONS = data_root() / "fixtures" / "versions"
CASES = sorted(path.name for path in VERSIONS.iterdir() if path.is_dir())


def summary(report: StepReport) -> dict[str, Any]:
    """A report as ``expected.yaml`` writes it."""
    return {
        "step": report.step,
        "scope": report.scope,
        "refused": report.refused,
        "undetermined": report.undetermined,
        "findings": [
            {"kind": f.kind, "step": f.step, "id": f.id} for f in report.findings
        ],
    }


def base() -> dict[str, Any]:
    """The base manifest of the cases, as read from its file."""
    return loads((VERSIONS / "region_added" / "old" / "base.yaml").read_text())


def git_environment(home: Path) -> dict[str, str]:
    """An environment for git with no global or system configuration."""
    return {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.org",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.org",
        "HOME": str(home),
    }


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args],
        cwd=repo,
        env=git_environment(repo.parent),
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def test_the_steps_are_ordered() -> None:
    assert STEPS == ("none", "patch", "minor", "major")


@pytest.mark.parametrize("case", CASES)
def test_each_rule(case: str) -> None:
    directory = VERSIONS / case
    expected = loads((directory / "expected.yaml").read_text())
    assert summary(tree_step(directory / "old", directory / "new")) == expected


def test_the_cases_cover_the_table() -> None:
    assert CASES == [
        "anchor_removed",
        "belief_added",
        "belief_changed",
        "child_removed",
        "chunks_edited",
        "comments_only",
        "conversion_map_removed",
        "coordinate_edited",
        "elision_added",
        "elision_edited",
        "elision_removed",
        "flow_control_removed",
        "flow_map_removed",
        "graphical_rule_changed",
        "group_removed",
        "id_changed",
        "id_reused",
        "length_edited",
        "manifest_added",
        "manifest_removed",
        "map_numbers_edited",
        "matchstamp_removed",
        "measure_map_removed",
        "member_added",
        "member_removed",
        "meta_changed",
        "minimal_to_complete",
        "name_changed",
        "number_type_edited",
        "numbers_respelled",
        "offset_edited",
        "pair_added",
        "pair_removed",
        "pair_replaced",
        "prefix_added",
        "prefix_iri_edited",
        "prefix_removed",
        "projection_row_edited",
        "projection_row_removed",
        "region_added",
        "registry_non_event_rows_only",
        "registry_projection_moved",
        "registry_row_added",
        "registry_row_removed",
        "registry_row_vanished",
        "resource_moved",
        "resource_removed",
        "timeline_removed",
        "timestamp_display_edited",
        "timestamp_removed",
        "unit_edited",
        "virtual_timeline_removed",
        "yaml_to_json",
    ]


CASE_MANIFESTS = sorted(
    path
    for path in VERSIONS.rglob("*")
    if path.suffix in (".yaml", ".json")
    and path.name not in ("expected.yaml", "package.yaml")
)
PACKAGES = sorted(path.parent for path in VERSIONS.rglob("package.yaml"))


@pytest.mark.parametrize(
    "path", CASE_MANIFESTS, ids=lambda path: path.relative_to(VERSIONS).as_posix()
)
def test_every_case_manifest_validates(path: Path) -> None:
    assert validate(loads(path.read_text(encoding="utf-8"))) is None


@pytest.mark.parametrize(
    "root", PACKAGES, ids=lambda path: path.relative_to(VERSIONS).as_posix()
)
def test_every_case_package_has_fresh_non_event_rows(root: Path) -> None:
    pytest.importorskip("pyarrow")
    from timetoshare.tables.registry import stale_non_event_rows

    assert stale_non_event_rows(root) == []


def test_the_case_tables_are_the_scripts() -> None:
    pa = pytest.importorskip("pyarrow")
    pc = pytest.importorskip("pyarrow.compute")
    pq = pytest.importorskip("pyarrow.parquet")
    import importlib.util

    from timetoshare.tables import NON_EVENT_KINDS

    script_path = Path(__file__).resolve().parents[2] / "scripts" / "emit_versions.py"
    spec = importlib.util.spec_from_file_location("emit_versions", script_path)
    assert spec is not None and spec.loader is not None
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    assert sorted(script.CASES) == sorted(
        path.parent.name for path in PACKAGES if path.name == "old"
    )
    for name, change in script.CASES.items():
        for side in ("old", "new"):
            tree = script.Tree()
            if side == "new":
                change(tree)
            root = VERSIONS / name / side
            for file, (rows, schema, kind) in tree.tables.items():
                table = script.pa.Table.from_pylist(rows, schema=schema)
                table = table.replace_schema_metadata(
                    {"timetoshare:type": kind, "timetoshare:version": "0.2.0"}
                )
                held = pq.read_table(root / file)
                if kind == "Registry":
                    # The registry file holds the case's event rows after the
                    # non-event rows written from its manifest and tables.
                    held = held.filter(
                        pc.invert(
                            pc.is_in(held["kind"], value_set=pa.array(NON_EVENT_KINDS))
                        )
                    )
                assert held.equals(table, check_metadata=True), (
                    name,
                    side,
                    file,
                )


def tempo(manifest: dict[str, Any]) -> dict[str, Any]:
    (score,) = [t for t in manifest["timelines"] if t["id"] == "#score"]
    return score["conversion_maps"][0]


@pytest.mark.parametrize(
    ("scalar", "offset"), [(2, [1, 2]), ([2, 1], [2, 4]), ([4, 2], 0.5)]
)
def test_a_map_number_compares_by_value(scalar: Any, offset: Any) -> None:
    new = base()
    tempo(new).update(scalar=scalar, offset=offset)
    assert manifest_step(base(), new) == ()


def test_a_float_and_a_fraction_of_another_value_differ() -> None:
    new = base()
    tempo(new)["offset"] = 0.1
    old = base()
    tempo(old)["offset"] = [1, 10]
    assert manifest_step(old, new, "base.yaml") == (
        Finding(
            "edited", "minor", "base.yaml", "tempo", "ConversionMap #tempo: offset"
        ),
    )


def test_two_integers_where_no_pair_stands_are_two_numbers() -> None:
    old, new = base(), base()
    for manifest, passes in ((old, [1, 2]), (new, [2, 4])):
        (score,) = [t for t in manifest["timelines"] if t["id"] == "#score"]
        score["flow_control"][0]["ends"] = {"passes": passes}
    assert manifest_step(old, new, "base.yaml") == (
        Finding(
            "edited", "minor", "base.yaml", "fine", "FlowControlElement #fine: ends"
        ),
    )


def test_meta_and_statement_literals_compare_as_written() -> None:
    new = base()
    new["meta"] = {"source": "first edition", "pages": 1.0}
    old = base()
    old["meta"] = {"source": "first edition", "pages": 1}
    assert manifest_step(old, new, "base.yaml") == (
        Finding("meta", "patch", "base.yaml", None, "the meta of the manifest"),
    )


@pytest.mark.parametrize(
    "path",
    [path for path in fixture_paths() if not path.name.endswith(".minimal.yaml")],
    ids=lambda path: path.name,
)
def test_a_fixture_and_its_twin_are_one_state(path: Path) -> None:
    manifest = loads(path.read_text())
    twin_path = path.with_name(path.name[: -len(".yaml")] + ".minimal.yaml")
    twin = loads(twin_path.read_text())
    assert manifest_step(manifest, twin) == ()
    assert manifest_step(manifest, manifest) == ()


def test_another_format_version_is_undetermined() -> None:
    old = base()
    new = {**base(), "timetoshare": "0.1.0", "timelines": []}
    assert manifest_step(old, new, "base.yaml") == (
        Finding(
            "unsupported_version",
            "undetermined",
            "base.yaml",
            None,
            "a manifest declares the version '0.1.0'; this package reads 0.2.0",
        ),
    )
    report = StepReport.of(manifest_step(old, new, "base.yaml"))
    assert (report.step, report.undetermined, report.refused) == (
        "none",
        True,
        False,
    )


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(value), encoding="utf-8")


def renamed(value: dict[str, Any], name: str) -> dict[str, Any]:
    return {**value, "name": name}


def test_the_scope_is_one_directory(tmp_path: Path) -> None:
    for side in ("old", "new"):
        name = "Sonata" if side == "old" else "Sonata, revised"
        write(tmp_path / side / "bpsd" / "op106.yaml", renamed(base(), name))
        write(tmp_path / side / "bpsd" / "op110.yaml", renamed(base(), name))
    report = tree_step(tmp_path / "old", tmp_path / "new")
    assert report.scope == "bpsd"
    assert [(f.path, f.kind) for f in report.findings] == [
        ("bpsd/op106.yaml", "label"),
        ("bpsd/op110.yaml", "label"),
    ]


def renamed_trees(root: Path, *paths: str) -> StepReport:
    """The report of renaming the base manifest at each of ``paths``."""
    for side in ("old", "new"):
        name = "Sonata" if side == "old" else "Sonata, revised"
        for path in paths:
            write(root / side / path, renamed(base(), name))
    return tree_step(root / "old", root / "new")


@pytest.mark.parametrize(
    ("paths", "scope"),
    [
        (["bpsd/op106/manifest.yaml"], "op106"),
        (["bpsd/op106/manifest.json"], "op106"),
        (["manifest.yaml"], "manifest"),
        (["bpsd/op106/manifest.minimal.yaml"], "manifest.minimal"),
        (["bpsd/op106/manifest.yaml", "bpsd/op110/manifest.yaml"], "bpsd"),
        (["bpsd/op106/manifest.yaml", "mtd/manifest.yaml"], None),
    ],
)
def test_a_file_named_manifest_takes_its_folder_s_name(
    tmp_path: Path, paths: list[str], scope: str | None
) -> None:
    assert renamed_trees(tmp_path, *paths).scope == scope


def test_no_scope_over_two_top_level_manifests(tmp_path: Path) -> None:
    for side in ("old", "new"):
        name = "Sonata" if side == "old" else "Sonata, revised"
        write(tmp_path / side / "op106.yaml", renamed(base(), name))
        write(tmp_path / side / "op110.yaml", renamed(base(), name))
    assert tree_step(tmp_path / "old", tmp_path / "new").scope is None


def test_findings_are_sorted_by_path_kind_and_id() -> None:
    findings = [
        Finding("removed", "major", "b.yaml", "x", "x"),
        Finding("added", "minor", "b.yaml", "z", "z"),
        Finding("added", "minor", "b.yaml", "y", "y"),
        Finding("label", "patch", "a.yaml", None, "name"),
    ]
    report = StepReport.of(findings)
    assert [(f.path, f.kind, f.id) for f in report.findings] == [
        ("a.yaml", "label", None),
        ("b.yaml", "added", "y"),
        ("b.yaml", "added", "z"),
        ("b.yaml", "removed", "x"),
    ]
    assert (report.step, report.scope) == ("major", None)


def test_no_findings_is_no_step(tmp_path: Path) -> None:
    report = tree_step(tmp_path / "missing", tmp_path / "also_missing")
    assert report == StepReport("none", (), False, False, None)


# Tables --------------------------------------------------------------------


def table_manifest(kind: str = "MatchClaim", url: str = "match_claims.parquet") -> dict:
    return {
        "timetoshare": "0.2.0",
        "timelines": [{"id": "#clt_1", "unit": "quarters", "length": [8, 1]}],
        "resources": [
            {"id": "#claims", "type": kind, "timelines": ["#clt_1"], "url": url}
        ],
    }


def table_trees(tmp_path: Path, old_rows: Any, new_rows: Any) -> StepReport:
    pq = pytest.importorskip("pyarrow.parquet")
    pa = pytest.importorskip("pyarrow")
    from timetoshare.tables import fixture_path

    schema = pq.read_table(fixture_path("match_claims.parquet")).schema
    for side, rows in (("old", old_rows), ("new", new_rows)):
        write(tmp_path / side / "claims.yaml", table_manifest())
        table = pa.Table.from_pylist(rows, schema=schema)
        pq.write_table(table, tmp_path / side / "match_claims.parquet")
    return tree_step(tmp_path / "old", tmp_path / "new")


def claim_rows() -> list[dict[str, Any]]:
    pq = pytest.importorskip("pyarrow.parquet")
    from timetoshare.tables import fixture_path

    return pq.read_table(fixture_path("match_claims.parquet")).to_pylist()


def test_a_removed_row_is_major(tmp_path: Path) -> None:
    rows = claim_rows()
    fewer = [row for row in rows if row["id"] != "claim_18"]
    report = table_trees(tmp_path, rows, fewer)
    assert summary(report) == {
        "step": "major",
        "scope": "claims",
        "refused": False,
        "undetermined": False,
        "findings": [{"kind": "removed_row", "step": "major", "id": "claim_18"}],
    }


def test_an_added_row_is_minor(tmp_path: Path) -> None:
    rows = claim_rows()
    fewer = [row for row in rows if row["id"] != "claim_18"]
    report = table_trees(tmp_path, fewer, rows)
    assert summary(report) == {
        "step": "minor",
        "scope": "claims",
        "refused": False,
        "undetermined": False,
        "findings": [{"kind": "added_row", "step": "minor", "id": "claim_18"}],
    }


def test_a_belief_on_a_row_is_a_patch(tmp_path: Path) -> None:
    rows = claim_rows()
    changed = claim_rows()
    (row,) = [row for row in changed if row["id"] == "claim_6"]
    row["provenance"]["beliefs"][0]["belief"] = "false"
    report = table_trees(tmp_path, rows, changed)
    assert summary(report)["findings"] == [
        {"kind": "belief", "step": "patch", "id": "claim_6"}
    ]
    assert report.step == "patch"


def test_an_edited_row_is_minor(tmp_path: Path) -> None:
    rows = claim_rows()
    changed = claim_rows()
    (row,) = [row for row in changed if row["id"] == "claim_6"]
    row["event_a_name"] = "D4"
    report = table_trees(tmp_path, rows, changed)
    assert summary(report)["findings"] == [
        {"kind": "edited_row", "step": "minor", "id": "claim_6"}
    ]


def test_without_pyarrow_a_changed_table_is_undetermined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = claim_rows()
    fewer = [row for row in rows if row["id"] != "claim_18"]
    table_trees(tmp_path, rows, fewer)
    monkeypatch.setitem(sys.modules, "pyarrow.parquet", None)
    report = tree_step(tmp_path / "old", tmp_path / "new")
    assert report.findings == (
        Finding(
            "changed_table",
            "undetermined",
            "claims.yaml",
            "claims",
            "match_claims.parquet changed; comparing its rows needs pyarrow: pip "
            'install "timetoshare[tables]"',
        ),
    )
    assert (report.step, report.undetermined) == ("none", True)


def test_a_table_of_another_type_is_undetermined(tmp_path: Path) -> None:
    for side, data in (("old", b"one"), ("new", b"two")):
        write(tmp_path / side / "notes.yaml", table_manifest("Note", "notes.csv"))
        (tmp_path / side / "notes.csv").write_bytes(data)
    report = tree_step(tmp_path / "old", tmp_path / "new")
    assert report.findings == (
        Finding(
            "changed_table",
            "undetermined",
            "notes.yaml",
            "claims",
            "notes.csv changed; tables of the type Note are not compared",
        ),
    )


# Registries ----------------------------------------------------------------


def registry_case(tmp_path: Path, case: str) -> tuple[Path, Path]:
    """A copy of a registry case's two packages."""
    old, new = tmp_path / "old", tmp_path / "new"
    shutil.copytree(VERSIONS / case / "old", old)
    shutil.copytree(VERSIONS / case / "new", new)
    return old, new


def listing(root: Path, name: str, timelines: list[str]) -> None:
    """Write a manifest holding the timeline score whose Registry resource
    lists ``timelines``."""
    manifest = loads((root / "score.yaml").read_text(encoding="utf-8"))
    manifest["resources"][0]["timelines"] = timelines
    write(root / name, manifest)


def test_a_row_listed_by_no_manifest_lies_at_the_package(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    old, new = registry_case(tmp_path, "registry_row_removed")
    for root in (old, new):
        listing(root, "score.yaml", [])
    assert tree_step(old, new).findings == (
        Finding(
            "removed_row",
            "major",
            "package.yaml",
            "note_2",
            "row note_2 of registry.parquet",
        ),
    )


def test_a_row_two_manifests_list_lies_at_both(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    old, new = registry_case(tmp_path, "registry_row_removed")
    for root in (old, new):
        listing(root, "other.yaml", ["#score"])
    assert tree_step(old, new).findings == (
        Finding(
            "removed_row",
            "major",
            "other.yaml",
            "note_2",
            "row note_2 of registry.parquet",
        ),
        Finding(
            "removed_row",
            "major",
            "score.yaml",
            "note_2",
            "row note_2 of registry.parquet",
        ),
    )


def test_a_vanished_row_names_the_extraction(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    case = VERSIONS / "registry_row_vanished"
    assert tree_step(case / "old", case / "new").findings == (
        Finding(
            "vanished_row",
            "minor",
            "score.yaml",
            "note_2",
            "row note_2 of registry.parquet, vanished in the extraction ext_2",
        ),
    )


def test_without_pyarrow_a_changed_registry_is_undetermined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old, new = registry_case(tmp_path, "registry_row_removed")
    monkeypatch.setitem(sys.modules, "pyarrow.parquet", None)
    report = tree_step(old, new)
    assert report.findings == (
        Finding(
            "changed_table",
            "undetermined",
            "package.yaml",
            None,
            "registry.parquet changed; comparing its rows needs pyarrow: pip install "
            '"timetoshare[tables]"',
        ),
    )
    assert (report.step, report.undetermined) == ("none", True)


@pytest.mark.parametrize(
    ("case", "header"),
    [
        ("registry_row_removed", "remove(score)!: "),
        ("registry_row_added", "feat(score): "),
        ("registry_projection_moved", "feat(score): "),
        ("registry_row_vanished", "feat(score): "),
        ("projection_row_edited", "feat(score): "),
    ],
)
def test_the_commit_type_of_a_registry_change(case: str, header: str) -> None:
    pytest.importorskip("pyarrow")
    from timetoshare.commit_types import suggest_header, suggest_hints

    report = tree_step(VERSIONS / case / "old", VERSIONS / case / "new")
    assert (suggest_header(report), suggest_hints(report)) == (header, [])


# Git -----------------------------------------------------------------------


def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "--quiet")
    return repo


def test_a_repository_without_commits_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = repository(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    shutil.copy(VERSIONS / "region_added" / "old" / "base.yaml", repo / "base.yaml")
    git(repo, "add", "base.yaml")
    assert summary(git_step("HEAD", None, repo)) == {
        "step": "minor",
        "scope": "base",
        "refused": False,
        "undetermined": False,
        "findings": [{"kind": "added_manifest", "step": "minor", "id": None}],
    }


def test_two_commits_and_the_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = repository(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    case = VERSIONS / "timeline_removed"
    shutil.copy(case / "old" / "base.yaml", repo / "base.yaml")
    git(repo, "add", "base.yaml")
    git(repo, "commit", "--quiet", "-m", "first")
    shutil.copy(case / "new" / "base.yaml", repo / "base.yaml")
    assert git_step("HEAD", None, repo).findings == ()
    git(repo, "add", "base.yaml")
    expected = loads((case / "expected.yaml").read_text())
    assert summary(git_step("HEAD", None, repo)) == expected
    git(repo, "commit", "--quiet", "-m", "second")
    assert summary(git_step("HEAD~1", "HEAD", repo)) == expected
    assert summary(git_step("HEAD~1", "HEAD", repo / ".git" / "..")) == expected
    with pytest.raises(ValueError, match="'v9.9.9' names no commit"):
        git_step("v9.9.9", "HEAD", repo)


def test_a_manifest_that_no_longer_reads_is_undetermined(tmp_path: Path) -> None:
    write(tmp_path / "old" / "base.yaml", base())
    (tmp_path / "new").mkdir()
    (tmp_path / "new" / "base.yaml").write_text("timelines: [\n", encoding="utf-8")
    report = tree_step(tmp_path / "old", tmp_path / "new")
    assert [(f.kind, f.step, f.path, f.id) for f in report.findings] == [
        ("unreadable_manifest", "undetermined", "base.yaml", None)
    ]
    assert report.findings[0].detail.startswith(
        "the manifest cannot be read in the later tree: "
    )
    assert (report.step, report.refused, report.undetermined) == ("none", False, True)
    reverse = tree_step(tmp_path / "new", tmp_path / "old")
    assert [(f.kind, f.step, f.path) for f in reverse.findings] == [
        ("unreadable_manifest", "undetermined", "base.yaml")
    ]
    assert reverse.findings[0].detail.startswith(
        "the manifest cannot be read in the earlier tree: "
    )


def test_only_manifests_and_their_tables_are_read_from_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = repository(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    shutil.copy(VERSIONS / "region_added" / "old" / "base.yaml", repo / "base.yaml")
    (repo / ".gitattributes").write_text("*.yaml export-ignore\n", encoding="utf-8")
    (repo / "take_1.flac").write_bytes(b"one")
    (repo / "notes.txt").write_text("notes\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", "first")
    (repo / "take_1.flac").write_bytes(b"two")
    git(repo, "add", "take_1.flac")
    written: list[set[str]] = []
    real = tree_step

    def recording(old_root: Path, new_root: Path) -> StepReport:
        written.extend(
            {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
            for root in (old_root, new_root)
        )
        return real(old_root, new_root)

    monkeypatch.setattr("timetoshare.version_step.tree_step", recording)
    report = git_step("HEAD", None, repo)
    assert written == [{"base.yaml", "take_1.flac"}, {"base.yaml", "take_1.flac"}]
    assert [(f.kind, f.step, f.id) for f in report.findings] == [
        ("changed_table", "undetermined", "recording")
    ]


def test_a_registry_and_its_tables_are_read_from_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("pyarrow")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    for case in ("registry_row_removed", "projection_row_edited"):
        repo = tmp_path / case
        repo.mkdir()
        git(repo, "init", "--quiet")
        shutil.copytree(VERSIONS / case / "old", repo, dirs_exist_ok=True)
        # The pre-parsed table is reached through the registry's rows alone.
        package = loads((repo / "package.yaml").read_text(encoding="utf-8"))
        package["tables"] = [t for t in package["tables"] if t["type"] != "Projection"]
        write(repo / "package.yaml", package)
        git(repo, "add", ".")
        git(repo, "commit", "--quiet", "-m", "first")
        for part in ("registry.parquet", "tables/Projection/part.parquet"):
            shutil.copy(VERSIONS / case / "new" / part, repo / part)
        git(repo, "add", ".")
        expected = loads((VERSIONS / case / "expected.yaml").read_text())
        assert summary(git_step("HEAD", None, repo)) == expected


def test_a_table_is_read_through_the_filters_of_its_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A filter that stores the table as base64 text stands in for Git LFS,
    which stores a pointer: unfiltered, the stored text is no Parquet file."""
    pq = pytest.importorskip("pyarrow.parquet")
    pa = pytest.importorskip("pyarrow")
    from timetoshare.tables import fixture_path

    repo = repository(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    git(repo, "config", "filter.b64.clean", "base64 -w0")
    git(repo, "config", "filter.b64.smudge", "base64 -d")
    (repo / ".gitattributes").write_text("*.parquet filter=b64\n", encoding="utf-8")
    write(repo / "claims.yaml", table_manifest())
    rows = claim_rows()
    schema = pq.read_table(fixture_path("match_claims.parquet")).schema
    table = repo / "match_claims.parquet"
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), table)
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", "first")
    assert git(repo, "cat-file", "-p", "HEAD:match_claims.parquet").startswith("UEFS")
    fewer = [row for row in rows if row["id"] != "claim_18"]
    pq.write_table(pa.Table.from_pylist(fewer, schema=schema), table)
    git(repo, "add", "match_claims.parquet")
    assert [(f.kind, f.step, f.id) for f in git_step("HEAD", None, repo).findings] == [
        ("removed_row", "major", "claim_18")
    ]


def tagged(repo: Path, case: str, side: str, tag: str) -> None:
    shutil.copy(VERSIONS / case / side / "base.yaml", repo / "base.yaml")
    git(repo, "add", "base.yaml")
    git(repo, "commit", "--quiet", "--allow-empty", "-m", tag)
    git(repo, "tag", tag)


def test_history_refuses_an_id_given_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = repository(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    tagged(repo, "timeline_removed", "old", "v1.0.0")
    tagged(repo, "timeline_removed", "new", "v2.0.0")
    shutil.copy(VERSIONS / "timeline_removed" / "old" / "base.yaml", repo / "base.yaml")
    git(repo, "add", "base.yaml")
    plain = git_step("v2.0.0", None, repo)
    assert [(f.kind, f.step, f.id) for f in plain.findings] == [
        ("added", "minor", "sketch")
    ]
    report = git_step("v2.0.0", None, repo, history=True)
    assert summary(report) == {
        "step": "minor",
        "scope": "base",
        "refused": True,
        "undetermined": False,
        "findings": [
            {"kind": "added", "step": "minor", "id": "sketch"},
            {"kind": "reused_id", "step": "refused", "id": "sketch"},
        ],
    }
    assert report.findings[1].detail == (
        "#sketch was a Timeline in v1.0.0, is gone in v2.0.0 and is now a "
        "Timeline again"
    )
    git(repo, "commit", "--quiet", "-m", "restore")
    assert summary(git_step("v2.0.0", "HEAD", repo, history=True)) == summary(report)


def test_history_refuses_an_id_of_another_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = repository(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    tagged(repo, "id_reused", "old", "v1.0.0")
    without = base()
    (score,) = [t for t in without["timelines"] if t["id"] == "#score"]
    score["regions"] = [r for r in score["regions"] if r["id"] != "#region_1"]
    write(repo / "base.yaml", without)
    git(repo, "commit", "--quiet", "-am", "v1.1.0")
    git(repo, "tag", "v1.1.0")
    tagged(repo, "id_reused", "new", "v2.0.0")
    report = git_step("v1.1.0", "v2.0.0", repo, history=True)
    assert summary(report) == {
        "step": "major",
        "scope": "base",
        "refused": True,
        "undetermined": False,
        "findings": [
            {"kind": "added", "step": "minor", "id": "region_1"},
            {"kind": "removed", "step": "major", "id": "sketch"},
            {"kind": "reused_id", "step": "refused", "id": "region_1"},
        ],
    }
    assert report.findings[2].detail == (
        "#region_1 was a Region in v1.0.0 and is now a Timeline"
    )
    assert summary(git_step("v1.0.0", "v1.1.0", repo, history=True)) == {
        "step": "major",
        "scope": "base",
        "refused": False,
        "undetermined": False,
        "findings": [{"kind": "removed", "step": "major", "id": "region_1"}],
    }


def test_the_command_checks_the_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    from timetoshare.cli import main

    repo = repository(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    tagged(repo, "timeline_removed", "old", "v1.0.0")
    tagged(repo, "timeline_removed", "new", "v2.0.0")
    tagged(repo, "timeline_removed", "old", "v2.1.0")
    assert main(["step", "--repo", str(repo), "v2.0.0", "v2.1.0"]) == 0
    assert main(["step", "--history", "--repo", str(repo), "v2.0.0", "v2.1.0"]) == 2
    out = capsys.readouterr().out.splitlines()
    assert out[-1] == (
        "refused\treused_id\tbase.yaml\t#sketch\t#sketch was a Timeline in v1.0.0, "
        "is gone in v2.0.0 and is now a Timeline again"
    )
    old, new = VERSIONS / "region_added" / "old", VERSIONS / "region_added" / "new"
    assert main(["step", "--history", str(old), str(new)]) == 1
    assert capsys.readouterr().err == (
        "timetoshare step: --history compares git references, not directories\n"
    )


def test_the_command_compares_with_the_empty_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    from timetoshare.cli import main

    repo = repository(tmp_path)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    tagged(repo, "timeline_removed", "old", "v1.0.0")
    expected = [
        "step: minor",
        "scope: base",
        "minor\tadded_manifest\tbase.yaml\t-\tthe manifest base.yaml",
    ]
    for history in ([], ["--history"]):
        assert main(["step", "--repo", str(repo), *history, "-", "HEAD"]) == 0
        assert capsys.readouterr().out.splitlines() == expected
    new = VERSIONS / "region_added" / "new"
    assert main(["step", "-", str(new)]) == 1
    assert capsys.readouterr().err == (
        "timetoshare step: OLD and NEW are both directories or both git references\n"
    )
