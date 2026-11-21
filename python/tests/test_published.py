"""The publication check of the release: ``scripts/check_published.py`` (see
"The publication check" in tests/README.md)."""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPOSITORY_ROOT / "scripts" / "check_published.py"
SITE = "https://timetoalign.github.io/timetoshare/"


def _script() -> Any:
    spec = importlib.util.spec_from_file_location("check_published", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = _script()


def _tree(documents: dict[str, Any]) -> dict[str, bytes]:
    return {path: json.dumps(document).encode() for path, document in documents.items()}


def _sound() -> dict[str, Any]:
    """A small sound tree: a reference to a member of another document and a
    ``tables.json`` naming a schema served beside it."""
    return {
        "0.2.0/a.json": {"$id": f"{SITE}0.2.0/a.json", "$ref": "b.json#/$defs/Kept"},
        "0.2.0/b.json": {"$id": f"{SITE}0.2.0/b.json", "$defs": {"Kept": {}}},
        "0.2.0/tables.json": {
            "$id": f"{SITE}0.2.0/tables.json",
            "types": {"provenance": {"schema": "b.json"}},
        },
    }


def test_the_repository_tree_is_published_whole_and_sound() -> None:
    files = check.published()
    assert sorted(files) == [
        "0.2.0/catalogue.schema.json",
        "0.2.0/provenance.schema.json",
        "0.2.0/tables.json",
        "0.2.0/timetoshare.schema.json",
    ]
    assert (
        files["0.2.0/catalogue.schema.json"]
        == (REPOSITORY_ROOT / "catalogue" / "catalogue.schema.json").read_bytes()
    )
    for name in ("provenance.schema.json", "tables.json", "timetoshare.schema.json"):
        assert (
            files[f"0.2.0/{name}"]
            == (REPOSITORY_ROOT / "schema" / "0.2.0" / name).read_bytes()
        )
    assert check.problems(files) == []


def test_the_small_tree_is_sound() -> None:
    assert check.problems(_tree(_sound())) == []


def _set(path: str, *keys: str, value: Any) -> Callable[[dict[str, Any]], None]:
    def change(documents: dict[str, Any]) -> None:
        holder = documents[path]
        for key in keys[:-1]:
            holder = holder[key]
        holder[keys[-1]] = value

    return change


def _drop_id(documents: dict[str, Any]) -> None:
    del documents["0.2.0/a.json"]["$id"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            _set("0.2.0/a.json", "$ref", value="c.json"),
            "0.2.0/a.json: c.json names a document not published",
        ),
        (
            _set("0.2.0/a.json", "$id", value=f"{SITE}0.1.0/a.json"),
            [
                f"0.2.0/a.json: its $id {SITE}0.1.0/a.json is not its address "
                f"{SITE}0.2.0/a.json",
                "0.2.0/a.json: b.json#/$defs/Kept names a document not published",
            ],
        ),
        (_drop_id, "0.2.0/a.json: no $id"),
        (
            _set("0.2.0/a.json", "$ref", value="b.json#/$defs/Missing"),
            "0.2.0/a.json: b.json#/$defs/Missing names no member",
        ),
        (
            _set("0.2.0/tables.json", "types", "provenance", "schema", value="c.json"),
            "0.2.0/tables.json: c.json names a document not published",
        ),
    ],
    ids=[
        "reference_unpublished",
        "id_not_address",
        "id_missing",
        "pointer_no_member",
        "tables_schema_unpublished",
    ],
)
def test_each_broken_tree_is_refused(
    change: Callable[[dict[str, Any]], None], message: str | list[str]
) -> None:
    documents = _sound()
    change(documents)
    expected = message if isinstance(message, list) else [message]
    assert check.problems(_tree(documents)) == expected


def test_a_document_missing_from_the_repository_tree_is_refused() -> None:
    files = check.published()
    del files["0.2.0/provenance.schema.json"]
    assert check.problems(files) == [
        "0.2.0/tables.json: provenance.schema.json names a document not published",
        "0.2.0/timetoshare.schema.json: provenance.schema.json names a document "
        "not published",
    ]
