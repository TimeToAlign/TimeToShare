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
from timetoshare.validate import data_root

VERSIONS = data_root() / "fixtures" / "versions"
CASES = sorted(path.name for path in VERSIONS.iterdir() if path.is_dir())


def summary(report: StepReport) -> dict[str, Any]:
    """A report as ``expected.yaml`` writes it."""
    return {
        "step": report.step,
        "scope": report.scope,
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
        "belief_added",
        "belief_changed",
        "child_removed",
        "elision_removed",
        "graphical_rule_changed",
        "id_changed",
        "id_reused",
        "manifest_added",
        "manifest_removed",
        "member_added",
        "member_removed",
        "meta_changed",
        "minimal_to_complete",
        "name_changed",
        "offset_edited",
        "pair_added",
        "pair_removed",
        "pair_replaced",
        "region_added",
        "resource_moved",
        "timeline_removed",
        "timestamp_removed",
        "unit_edited",
        "yaml_to_json",
    ]


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
        "findings": [{"kind": "removed_row", "step": "major", "id": "claim_18"}],
    }


def test_an_added_row_is_minor(tmp_path: Path) -> None:
    rows = claim_rows()
    fewer = [row for row in rows if row["id"] != "claim_18"]
    report = table_trees(tmp_path, fewer, rows)
    assert summary(report) == {
        "step": "minor",
        "scope": "claims",
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
