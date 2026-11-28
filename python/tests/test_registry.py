"""The registry: non-event rows, resolving an ID, the registry command and its hook.

The strategy is the README's section "The registry: non-event rows, resolving,
the registry command and version steps".
"""

from __future__ import annotations

import copy
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from timetoshare import dumps, with_file_ids  # noqa: E402
from timetoshare.cli import _parser, main  # noqa: E402
from timetoshare.tables import (  # noqa: E402
    PackageProblem,
    package_fixture_path,
    package_problems,
)
from timetoshare.tables.registry import (  # noqa: E402
    Resolution,
    non_event_rows,
    resolve,
    stale_non_event_rows,
    write_non_event_rows,
    write_registry,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

NUMBER = pa.struct(
    [("numerator", pa.int64()), ("denominator", pa.int64()), ("value", pa.float64())]
)
REGISTRY = pa.schema(
    [
        ("id", pa.string()),
        ("kind", pa.string()),
        ("location", pa.string()),
        ("timeline_id", pa.string()),
        ("unit", pa.string()),
        ("number_type", pa.string()),
        ("start", NUMBER),
        ("duration", NUMBER),
        ("parse_id", pa.string()),
        ("locator", pa.string()),
        ("vanished_in", pa.string()),
        (
            "projection_of",
            pa.struct([("timeline_id", pa.string()), ("event_id", pa.string())]),
        ),
    ]
)
"""The registry's columns as the format declares them."""

PARSE = pa.schema(
    [
        ("id", pa.string()),
        ("source", pa.string()),
        (
            "source_integrity",
            pa.struct([("algorithm", pa.string()), ("digest", pa.string())]),
        ),
        ("parser", pa.string()),
        ("parser_version", pa.string()),
        ("parameters", pa.string()),
        ("minter", pa.string()),
        ("id_length", pa.int64()),
        ("seed", pa.string()),
        ("date", pa.string()),
    ]
)
CLAIMS = pa.schema(
    [
        ("id", pa.string()),
        ("timeline_a_id", pa.string()),
        ("timeline_b_id", pa.string()),
    ]
)

BACH = "bach.tts.yaml"
HANDEL = "handel.tts.yaml"
REGISTRY_FILE = "registry.parquet"


def bach() -> dict[str, Any]:
    """Bach's manifest, IDs bare: an element of every kind."""
    return {
        "timetoshare": "0.2.0",
        "id": "bach",
        "name": "Bach",
        "timelines": [
            {
                "id": "score",
                "name": "Score",
                "unit": "quarters",
                "length": [8, 1],
                "children": [
                    {
                        "id": "movement",
                        "unit": "quarters",
                        "length": [4, 1],
                        "offset": [4, 1],
                    }
                ],
                "regions": [
                    {"id": "region_1", "name": "A", "start": [0, 1], "end": [4, 1]}
                ],
                "flow_control": [
                    {
                        "id": "fine",
                        "coordinate": [6, 1],
                        "role": "break",
                        "manifestation": "fine",
                    }
                ],
                "conversion_maps": [
                    {
                        "id": "tempo_chain",
                        "type": "ChainMap",
                        "source_unit": "quarters",
                        "target_unit": "seconds",
                        "maps": [
                            {
                                "id": "tempo",
                                "type": "LinearMap",
                                "scalar": [1, 2],
                                "offset": 0,
                                "source_unit": "quarters",
                                "target_unit": "seconds",
                            }
                        ],
                    }
                ],
            },
            {"id": "shared", "unit": "seconds", "length": 10.0},
        ],
        "groups": [{"id": "pair", "members": ["score", "shared"]}],
        "measure_maps": [
            {
                "id": "bars",
                "rows": [
                    {
                        "actual_length": [4, 1],
                        "count": 2,
                        "nominal_length": [4, 1],
                        "number": 1,
                        "qstamp": [0, 1],
                        "time_signature": "4/4",
                    }
                ],
            }
        ],
        "resources": [
            {
                "id": "registry",
                "type": "Registry",
                "url": "registry.parquet",
                "timelines": ["score", "movement", "shared"],
            },
            {
                "id": "claims",
                "type": "MatchClaim",
                "url": "tables/MatchClaim/",
                "timelines": ["score", "shared"],
            },
        ],
        "flow_maps": [{"id": "reading", "timeline": "score", "chunks": ["region_1"]}],
        "virtual_timelines": [
            {
                "id": "score_read",
                "map": "reading",
                "timeline": "score",
                "unit": "quarters",
                "number_type": "fraction",
                "length": [4, 1],
            }
        ],
        "graphical": {
            "timestamps": [
                {
                    "id": "ts_1",
                    "name": "start",
                    "timeline": "score",
                    "coordinate": [0, 1],
                },
                {
                    "id": "ts_m1",
                    "timeline": "score",
                    "coordinate": [4, 1],
                    "matchstamp": True,
                },
                {
                    "id": "ts_m2",
                    "timeline": "shared",
                    "coordinate": 2.0,
                    "matchstamp": True,
                },
            ],
            "elisions": [
                {"id": "elision_1", "timeline": "score", "start": [5, 1], "end": [6, 1]}
            ],
            "matchstamps": [
                {
                    "id": "ms_1",
                    "name": "Bar 1",
                    "match_claims": ["claim_1"],
                    "alignment_anchors": [
                        {"id": "anchor_1", "timestamps": ["ts_m1", "ts_m2"]}
                    ],
                }
            ],
        },
    }


def handel() -> dict[str, Any]:
    return {
        "timetoshare": "0.2.0",
        "timelines": [
            {"id": "shared", "unit": "seconds", "length": 10.0},
            {"id": "aria", "unit": "quarters", "length": [4, 1]},
        ],
        "resources": [
            {
                "id": "handel_registry",
                "type": "Registry",
                "url": "registry.parquet",
                "timelines": ["shared", "aria"],
            }
        ],
    }


def number(numerator: int | None, denominator: int | None, value: float | None):
    return {"numerator": numerator, "denominator": denominator, "value": value}


def event(
    id: str,
    kind: str,
    timeline: str,
    unit: str,
    number_type: str,
    start: dict,
    parse: str,
    location: str | None = None,
    locator: str | None = None,
    projection_of: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "id": id,
        "kind": kind,
        "location": location,
        "timeline_id": timeline,
        "unit": unit,
        "number_type": number_type,
        "start": start,
        "duration": None,
        "parse_id": parse,
        "locator": locator,
        "vanished_in": None,
        "projection_of": projection_of,
    }


NOTE_1 = event(
    "note_1",
    "MidiNote",
    "score",
    "quarters",
    "fraction",
    number(1, 2, None),
    "ext_1",
    locator="track 0 message 3",
)
PROJ_1 = event(
    "proj_1",
    "Projection",
    "shared",
    "seconds",
    "float",
    number(None, None, 1.5),
    "ext_1",
    projection_of={"timeline_id": "score", "event_id": "note_1"},
)
NOTE_2 = event(
    "note_2",
    "MidiNote",
    "aria",
    "quarters",
    "fraction",
    number(1, 1, None),
    "ext_2",
    locator="track 1 message 0",
)


def parse(id: str, source: str) -> dict[str, Any]:
    return {
        "id": id,
        "source": source,
        "source_integrity": {"algorithm": "SHA-256", "digest": "00" * 32},
        "parser": "mido",
        "parser_version": "1.3.3",
        "parameters": None,
        "minter": "1",
        "id_length": 8,
        "seed": None,
        "date": "2026-11-27T00:00:00Z",
    }


def parquet(path: Path, rows: list[dict], schema: Any, kind: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=schema).replace_schema_metadata(
        {"timetoshare:type": kind, "timetoshare:version": "0.2.0"}
    )
    pq.write_table(table, path)


def manifest(root: Path, url: str, value: dict[str, Any]) -> None:
    path = root / url
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(with_file_ids(value)), encoding="utf-8")


def package(root: Path, registry: str = "registry.parquet") -> Path:
    """The test package, its registry holding its three event rows, unsorted,
    and no non-event row yet."""
    manifest(root, BACH, bach())
    manifest(root, HANDEL, handel())
    (root / "package.yaml").write_text(
        dumps(
            {
                "timetoshare": "0.2.0",
                "manifests": [{"url": BACH}, {"url": HANDEL}],
                "tables": [
                    {"type": "Registry", "url": registry},
                    {"type": "Parse", "url": "parses.parquet"},
                    {"type": "MatchClaim", "url": "tables/MatchClaim/"},
                ],
            }
        ),
        encoding="utf-8",
    )
    parquet(root / REGISTRY_FILE, [NOTE_1, PROJ_1, NOTE_2], REGISTRY, "Registry")
    parquet(
        root / "parses.parquet",
        [parse("ext_1", "bach/take.mid"), parse("ext_2", "handel/aria.mid")],
        PARSE,
        "Parse",
    )
    parquet(
        root / "tables/MatchClaim/a.parquet",
        [{"id": "claim_1", "timeline_a_id": "score", "timeline_b_id": "shared"}],
        CLAIMS,
        "MatchClaim",
    )
    parquet(
        root / "tables/MatchClaim/b.parquet",
        [{"id": "claim_2", "timeline_a_id": "shared", "timeline_b_id": "score"}],
        CLAIMS,
        "MatchClaim",
    )
    return root


def row(id: str, kind: str, location: str, timeline=None) -> dict:
    return {
        "id": id,
        "kind": kind,
        "location": location,
        "timeline_id": timeline,
        "unit": None,
        "number_type": None,
        "start": None,
        "duration": None,
        "parse_id": None,
        "locator": None,
        "vanished_in": None,
        "projection_of": None,
    }


NON_EVENTS = [
    row("anchor_1", "AlignmentAnchor", BACH),
    row("bach", "Manifest", BACH),
    row("bars", "MeasureMap", BACH),
    row("claims", "Resource", BACH),
    row("elision_1", "Elision", BACH, "score"),
    row("fine", "FlowControlElement", BACH, "score"),
    row("movement", "Timeline", BACH),
    row("ms_1", "MatchStamp", BACH),
    row("pair", "Group", BACH),
    row("reading", "FlowMap", BACH),
    row("region_1", "Region", BACH, "score"),
    row("registry", "Resource", BACH),
    row("score", "Timeline", BACH),
    row("score_read", "VirtualTimeline", BACH),
    row("shared", "Timeline", BACH),
    row("tempo", "ConversionMap", BACH),
    row("tempo_chain", "ConversionMap", BACH),
    row("ts_1", "Timestamp", BACH, "score"),
    row("ts_m1", "Timestamp", BACH, "score"),
    row("ts_m2", "Timestamp", BACH, "shared"),
    row("aria", "Timeline", HANDEL),
    row("handel_registry", "Resource", HANDEL),
    row("shared", "Timeline", HANDEL),
    row("ext_1", "Parse", "parses.parquet"),
    row("ext_2", "Parse", "parses.parquet"),
    row("claim_1", "MatchClaim", "tables/MatchClaim/"),
    row("claim_2", "MatchClaim", "tables/MatchClaim/"),
]
"""The non-event rows of the test package, by hand."""


def row_of(rows: list[dict], id: str, location: str = BACH) -> dict:
    (found,) = [r for r in rows if r["id"] == id and r["location"] == location]
    return found


# The non-event rows ----------------------------------------------------------------


def test_the_non_event_rows_of_every_kind(tmp_path: Path) -> None:
    table = non_event_rows(package(tmp_path))
    assert table.schema.names == REGISTRY.names
    assert [field.type for field in table.schema] == list(REGISTRY.types)
    assert table.to_pylist() == NON_EVENTS


def test_a_manifest_that_does_not_validate_gives_no_rows(tmp_path: Path) -> None:
    root = package(tmp_path)
    (root / HANDEL).write_text("timetoshare: '0.2.0'\n", encoding="utf-8")
    assert non_event_rows(root).to_pylist() == [
        r for r in NON_EVENTS if r["location"] != HANDEL
    ]


# Writing -------------------------------------------------------------------------


EVENTS = [NOTE_2, NOTE_1, PROJ_1]
"""The three event rows in the order of the format: by timeline, ``aria``,
``score``, ``shared``."""


def test_writing_keeps_the_event_rows(tmp_path: Path) -> None:
    root = package(tmp_path)
    written = write_non_event_rows(root)
    assert written == root / REGISTRY_FILE
    table = pq.read_table(written)
    assert table.to_pylist() == [*NON_EVENTS, *EVENTS]
    assert table.schema.metadata == {
        b"timetoshare:type": b"Registry",
        b"timetoshare:version": b"0.2.0",
    }
    assert [p.name for p in root.iterdir() if p.name.startswith(".")] == []


def test_writing_a_missing_registry_file(tmp_path: Path) -> None:
    root = package(tmp_path)
    (root / REGISTRY_FILE).unlink()
    write_non_event_rows(root)
    assert pq.read_table(root / REGISTRY_FILE).to_pylist() == NON_EVENTS


def test_writing_replaces_a_stale_non_event_row(tmp_path: Path) -> None:
    root = package(tmp_path)
    stale = row("gone", "Region", BACH, "score")
    parquet(root / REGISTRY_FILE, [NOTE_1, stale, NOTE_2], REGISTRY, "Registry")
    write_non_event_rows(root)
    assert pq.read_table(root / REGISTRY_FILE).to_pylist() == [
        *NON_EVENTS,
        NOTE_2,
        NOTE_1,
    ]


def test_event_rows_keep_every_value(tmp_path: Path) -> None:
    root = package(tmp_path)
    respelled = {**NOTE_1, "start": number(2, 4, None)}
    unknown = event(
        "blob_1", "Blob", "score", "quarters", "fraction", number(3, 1, None), "ext_1"
    )
    rows = [
        {**respelled, "velocity": 64},
        {**unknown, "velocity": None},
        {**NOTE_2, "velocity": 80},
    ]
    parquet(
        root / REGISTRY_FILE,
        rows,
        REGISTRY.append(pa.field("velocity", pa.int64())),
        "Registry",
    )
    write_non_event_rows(root)
    with_velocity = [{**r, "velocity": None} for r in NON_EVENTS]
    assert pq.read_table(root / REGISTRY_FILE).to_pylist() == [
        *with_velocity,
        {**NOTE_2, "velocity": 80},
        {**respelled, "velocity": 64},
        {**unknown, "velocity": None},
    ]


def test_a_package_without_a_registry_is_refused(tmp_path: Path) -> None:
    root = package(tmp_path)
    text = (root / "package.yaml").read_text(encoding="utf-8")
    value = yaml.safe_load(text)
    value["tables"] = [t for t in value["tables"] if t["type"] != "Registry"]
    (root / "package.yaml").write_text(dumps(value), encoding="utf-8")
    with pytest.raises(
        ValueError, match="^package.yaml lists no table of the type Registry$"
    ):
        write_non_event_rows(root)


def folder_package(root: Path) -> Path:
    """The test package with its Registry entry and resources naming a folder."""
    package(root)
    value = yaml.safe_load((root / "package.yaml").read_text(encoding="utf-8"))
    value["tables"][0]["url"] = "registry/"
    (root / "package.yaml").write_text(dumps(value), encoding="utf-8")
    changed = bach()
    changed["resources"][0]["url"] = "registry/"
    manifest(root, BACH, changed)
    return root


FOLDER = "the registry 'registry/' names a folder; a registry is one Parquet file"


def test_a_registry_folder_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    root = folder_package(tmp_path)
    for call in (write_non_event_rows, stale_non_event_rows):
        with pytest.raises(ValueError) as raised:
            call(root)
        assert str(raised.value) == FOLDER
    with pytest.raises(ValueError) as raised:
        resolve(root, "note_1")
    assert str(raised.value) == FOLDER
    with pytest.raises(ValueError) as raised:
        resolve(root / BACH, "score")
    assert str(raised.value) == FOLDER
    assert run(capsys, str(root)) == (1, [], f"timetoshare: {FOLDER}\n")
    assert run(capsys, "--check", str(root)) == (1, [], f"timetoshare: {FOLDER}\n")


# The order of a registry file ---------------------------------------------------


def test_write_registry_orders_the_rows(tmp_path: Path) -> None:
    near = 6004799503160661

    def at(id: str, timeline: str, number_type: str, start: dict) -> dict:
        return event(id, "MidiNote", timeline, "quarters", number_type, start, "ext_1")

    expected = [
        row("a", "Timeline", "m/a.yaml"),
        row("b", "Timeline", "m/a.yaml"),
        row("a", "Timeline", "m/b.yaml"),
        row("ext_1", "Parse", "parses.parquet"),
        at("e_near", "f", "fraction", number(near, 2**54, None)),
        at("e_third", "f", "fraction", number(1, 3, None)),
        at("e_half_b", "f", "fraction", number(1, 2, None)),
        at("e_half_c", "f", "fraction", number(2, 4, None)),
        at("e_two", "f", "fraction", number(2, 1, None)),
        at("e_low", "i", "int", number(2**53, None, None)),
        at("e_high", "i", "int", number(2**53 + 1, None, None)),
        at("e_float", "x", "float", number(None, None, -0.5)),
    ]
    written = write_registry(
        pa.Table.from_pylist(list(reversed(expected)), schema=REGISTRY),
        tmp_path / REGISTRY_FILE,
    )
    assert written == tmp_path / REGISTRY_FILE
    table = pq.read_table(written)
    assert table.to_pylist() == expected
    assert table.schema.metadata == {
        b"timetoshare:type": b"Registry",
        b"timetoshare:version": b"0.2.0",
    }


def test_a_registry_of_another_shape_is_written_whole(tmp_path: Path) -> None:
    texts = pa.schema([field for field in REGISTRY if field.name != "start"]).append(
        pa.field("start", pa.string())
    )
    rows = [
        {**event("e_2", "MidiNote", "t", "quarters", "int", None, "x"), "start": "1"},
        {**event("e_1", "MidiNote", "t", "quarters", "int", None, "x"), "start": "2"},
        {**row("a", "Timeline", "m.yaml"), "start": None},
    ]
    written = write_registry(pa.Table.from_pylist(rows, schema=texts), tmp_path / "r")
    assert pq.read_table(written).column("id").to_pylist() == ["a", "e_1", "e_2"]
    assert pq.read_table(written).column("start").to_pylist() == [None, "2", "1"]


def test_the_shared_registry_is_in_the_order_of_the_format(tmp_path: Path) -> None:
    held = pq.read_table(package_fixture_path("shared") / REGISTRY_FILE)
    reversed_rows = held.take(pa.array(range(len(held) - 1, -1, -1)))
    written = write_registry(reversed_rows, tmp_path / REGISTRY_FILE)
    assert pq.read_table(written).equals(held, check_metadata=True)
    root = _shared_copy(tmp_path / "copy")
    write_non_event_rows(root)
    assert pq.read_table(root / REGISTRY_FILE).equals(held, check_metadata=True)


# Stale non-event rows ----------------------------------------------------------

PART = REGISTRY_FILE


def stale_package(root: Path) -> Path:
    """The written package, then a region added, a group removed, a named
    timestamp moved to another timeline, the score renamed (which leaves its
    non-event row as it was: the registry holds no names) and a MatchClaim
    added."""
    package(root)
    write_non_event_rows(root)
    changed = bach()
    changed["timelines"][0]["regions"].append(
        {"id": "region_9", "start": [4, 1], "end": [8, 1]}
    )
    changed["groups"] = []
    changed["graphical"]["timestamps"][0].update(timeline="shared", coordinate=0.0)
    changed["timelines"][0]["name"] = "Partitur"
    manifest(root, BACH, changed)
    parquet(
        root / "tables/MatchClaim/c.parquet",
        [{"id": "claim_3", "timeline_a_id": "score", "timeline_b_id": "shared"}],
        CLAIMS,
        "MatchClaim",
    )
    return root


def test_written_non_event_rows_are_not_stale(tmp_path: Path) -> None:
    root = package(tmp_path)
    write_non_event_rows(root)
    assert stale_non_event_rows(root) == []


def test_each_stale_row_is_one_problem(tmp_path: Path) -> None:
    assert stale_non_event_rows(stale_package(tmp_path)) == [
        PackageProblem(
            "stale_non_event_row",
            PART,
            8,
            ("id",),
            "the registry holds the non-event row of the ID 'pair' at "
            "'bach.tts.yaml', which no manifest or table holds there",
        ),
        PackageProblem(
            "stale_non_event_row",
            PART,
            17,
            ("timeline_id",),
            "the non-event row of the ID 'ts_1' at 'bach.tts.yaml' has the "
            "timeline_id 'score', not 'shared'",
        ),
        PackageProblem(
            "stale_non_event_row",
            PART,
            None,
            ("id",),
            "the registry lacks the non-event row of the ID 'region_9' at "
            "'bach.tts.yaml'",
        ),
        PackageProblem(
            "stale_non_event_row",
            PART,
            None,
            ("id",),
            "the registry lacks the non-event row of the ID 'claim_3' at "
            "'tables/MatchClaim/'",
        ),
    ]


def test_a_registry_of_event_rows_alone_lacks_every_row(tmp_path: Path) -> None:
    problems = stale_non_event_rows(package(tmp_path))
    assert [(p.row, p.message) for p in problems] == [
        (
            None,
            f"the registry lacks the non-event row of the ID '{r['id']}' at "
            f"'{r['location']}'",
        )
        for r in NON_EVENTS
    ]


# One comparison of the non-event rows -----------------------------------------


def _package_fixtures() -> list[Path]:
    """Every package fixture whose package.yaml lists exactly one registry,
    a file."""
    base = package_fixture_path()
    roots = [base / "shared"] + [
        case
        for kind in ("acceptances", "rejections")
        for case in sorted((base / kind).iterdir())
    ]

    def registries(root: Path) -> list[str]:
        tables = yaml.safe_load((root / "package.yaml").read_text())["tables"]
        return [entry["url"] for entry in tables if entry["type"] == "Registry"]

    return [
        root
        for root in roots
        if len(found := registries(root)) == 1 and not found[0].endswith("/")
    ]


def _the_checks_stale(root: Path) -> list[PackageProblem]:
    return [
        problem
        for problem in package_problems(root / "package.yaml")
        if problem.code == "stale_non_event_row"
    ]


@pytest.mark.parametrize("root", _package_fixtures(), ids=lambda root: root.name)
def test_the_command_and_the_check_compare_alike(root: Path) -> None:
    assert stale_non_event_rows(root) == _the_checks_stale(root)


def _shared_copy(tmp_path: Path) -> Path:
    root = tmp_path / "shared"
    shutil.copytree(package_fixture_path("shared"), root)
    return root


def test_an_invalid_manifests_rows_are_not_compared(tmp_path: Path) -> None:
    root = _shared_copy(tmp_path)
    handel = root / HANDEL
    handel.write_text(
        handel.read_text(encoding="utf-8").replace("unit: quarters", "unit: quarter"),
        encoding="utf-8",
    )
    assert stale_non_event_rows(root) == _the_checks_stale(root) == []
    part = root / REGISTRY_FILE
    before = pq.read_table(part).to_pylist()
    write_non_event_rows(root)
    after = pq.read_table(part).to_pylist()
    assert [row for row in after if row["location"] == HANDEL] == [
        row for row in before if row["location"] == HANDEL
    ]
    assert after == before
    assert stale_non_event_rows(root) == _the_checks_stale(root) == []


def test_locations_are_compared_resolved(tmp_path: Path) -> None:
    root = _shared_copy(tmp_path)
    file = root / "package.yaml"
    value = yaml.safe_load(file.read_text(encoding="utf-8"))
    for member in ("manifests", "tables"):
        for entry in value[member]:
            entry["url"] = "./" + entry["url"]
    file.write_text(dumps(value), encoding="utf-8")
    assert stale_non_event_rows(root) == _the_checks_stale(root) == []


def test_the_registry_names_are_public() -> None:
    from timetoshare import tables
    from timetoshare.tables import columns, registry

    for name in (
        "Resolution",
        "resolve",
        "non_event_rows",
        "write_non_event_rows",
        "stale_non_event_rows",
        "write_registry",
    ):
        assert name in tables.__all__
        assert getattr(tables, name) is getattr(registry, name)
    assert "ELEMENT_KINDS" in tables.__all__
    assert tables.ELEMENT_KINDS is columns.ELEMENT_KINDS
    assert tables.ELEMENT_KINDS == tuple(
        kind for kind in tables.NON_EVENT_KINDS if kind not in ("MatchClaim", "Parse")
    )


# Resolving -----------------------------------------------------------------------


@pytest.fixture
def written(tmp_path: Path) -> Path:
    root = package(tmp_path)
    write_non_event_rows(root)
    return root


def test_resolve_through_the_package(written: Path) -> None:
    assert resolve(written, "note_1") == [Resolution("MidiNote", None, None, NOTE_1)]
    assert resolve(written, "shared") == [
        Resolution("Timeline", BACH, BACH, row_of(NON_EVENTS, "shared")),
        Resolution("Timeline", HANDEL, HANDEL, row_of(NON_EVENTS, "shared", HANDEL)),
    ]
    assert resolve(written, "claim_1") == [
        Resolution(
            "MatchClaim",
            "tables/MatchClaim/",
            None,
            row_of(NON_EVENTS, "claim_1", "tables/MatchClaim/"),
        )
    ]
    assert resolve(written, "ext_2") == [
        Resolution(
            "Parse",
            "parses.parquet",
            None,
            row_of(NON_EVENTS, "ext_2", "parses.parquet"),
        )
    ]
    assert resolve(written, "nothing") == []


def test_resolve_through_a_manifest(written: Path) -> None:
    through_bach = written / BACH
    through_handel = written / HANDEL
    assert resolve(through_bach, "score") == [
        Resolution("Timeline", BACH, BACH, row_of(NON_EVENTS, "score"))
    ]
    assert resolve(through_bach, "shared") == [
        Resolution("Timeline", BACH, BACH, row_of(NON_EVENTS, "shared"))
    ]
    assert resolve(through_bach, "proj_1") == [
        Resolution("Projection", None, BACH, PROJ_1)
    ]
    assert resolve(through_handel, "proj_1") == [
        Resolution("Projection", None, HANDEL, PROJ_1)
    ]
    assert resolve(through_bach, "note_2") == []
    assert resolve(through_handel, "note_2") == [
        Resolution("MidiNote", None, HANDEL, NOTE_2)
    ]
    claim = row_of(NON_EVENTS, "claim_2", "tables/MatchClaim/")
    assert resolve(through_bach, "claim_2") == [
        Resolution("MatchClaim", "tables/MatchClaim/", BACH, claim)
    ]
    assert resolve(through_handel, "claim_2") == []
    first = row_of(NON_EVENTS, "ext_1", "parses.parquet")
    second = row_of(NON_EVENTS, "ext_2", "parses.parquet")
    assert resolve(through_bach, "ext_1") == [
        Resolution("Parse", "parses.parquet", BACH, first)
    ]
    assert resolve(through_bach, "ext_2") == []
    assert resolve(through_handel, "ext_2") == [
        Resolution("Parse", "parses.parquet", HANDEL, second)
    ]
    assert resolve(through_handel, "ext_1") == [
        Resolution("Parse", "parses.parquet", HANDEL, first)
    ]


def test_resolving_reads_filtered(
    written: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from timetoshare.tables import registry

    calls: list[dict[str, Any]] = []
    original = registry.read_table

    def recorded(*arguments: Any, **keywords: Any) -> Any:
        calls.append(keywords)
        return original(*arguments, **keywords)

    monkeypatch.setattr(registry, "read_table", recorded)
    first = row_of(NON_EVENTS, "ext_1", "parses.parquet")
    claim = row_of(NON_EVENTS, "claim_2", "tables/MatchClaim/")
    assert resolve(written, "note_1") == [Resolution("MidiNote", None, None, NOTE_1)]
    assert resolve(written, "claim_2") == [
        Resolution("MatchClaim", "tables/MatchClaim/", None, claim)
    ]
    assert resolve(written / BACH, "ext_1") == [
        Resolution("Parse", "parses.parquet", BACH, first)
    ]
    assert resolve(written / BACH, "claim_2") == [
        Resolution("MatchClaim", "tables/MatchClaim/", BACH, claim)
    ]
    assert resolve(written / HANDEL, "note_2") == [
        Resolution("MidiNote", None, HANDEL, NOTE_2)
    ]
    assert [sorted(call) for call in calls] == [
        ["ids", "type"],
        ["ids", "type"],
        ["ids", "type"],
        ["columns", "timelines", "type"],
        ["ids", "type"],
        ["ids", "type"],
    ]
    assert [call.get("ids") for call in calls] == [
        ["note_1"],
        ["claim_2"],
        ["ext_1"],
        None,
        ["claim_2"],
        ["note_2"],
    ]
    assert calls[3]["columns"] == ["parse_id"]


def test_a_written_id_is_read_bare(written: Path) -> None:
    assert resolve(written, "#shared") == resolve(written, "shared")
    assert resolve(written / BACH, "#score") == resolve(written / BACH, "score")


def test_a_manifest_without_a_registry(tmp_path: Path) -> None:
    lone = copy.deepcopy(bach())
    lone["resources"] = []
    manifest(tmp_path, "lone.yaml", lone)
    assert resolve(tmp_path / "lone.yaml", "score") == [
        Resolution("Timeline", "lone.yaml", "lone.yaml", None)
    ]
    assert resolve(tmp_path / "lone.yaml", "note_1") == []


# The command and the hook -------------------------------------------------------


def run(capsys: pytest.CaptureFixture, *arguments: str) -> tuple[int, list[str], str]:
    status = main(["registry", *arguments])
    captured = capsys.readouterr()
    return status, captured.out.splitlines(), captured.err


def test_the_command_writes_the_non_event_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    root = package(tmp_path)
    assert run(capsys, str(root)) == (
        0,
        [f"wrote {PART}"],
        "",
    )
    assert pq.read_table(root / PART).to_pylist() == [*NON_EVENTS, *EVENTS]


def test_the_command_takes_the_current_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = package(tmp_path)
    monkeypatch.chdir(root)
    assert run(capsys)[0] == 0
    assert run(capsys, "--check") == (0, [], "")


def test_the_check_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    root = stale_package(tmp_path)
    before = (root / PART).read_bytes()
    assert run(capsys, "--check", str(root)) == (
        1,
        [
            f"{PART}: row 8: stale_non_event_row: the registry holds the non-event "
            "row of the ID 'pair' at 'bach.tts.yaml', which no manifest or "
            "table holds there",
            f"{PART}: row 17: stale_non_event_row: the non-event row of the ID "
            "'ts_1' at 'bach.tts.yaml' has the timeline_id 'score', not 'shared'",
            f"{PART}: stale_non_event_row: the registry lacks the non-event row of "
            "the ID 'region_9' at 'bach.tts.yaml'",
            f"{PART}: stale_non_event_row: the registry lacks the non-event row of "
            "the ID 'claim_3' at 'tables/MatchClaim/'",
        ],
        "",
    )
    assert (root / PART).read_bytes() == before


def test_a_folder_without_a_package(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    status, out, err = run(capsys, "--check", str(tmp_path))
    assert (status, out) == (1, [])
    assert err.splitlines() == [f"timetoshare: no package.yaml lies in '{tmp_path}'"]


def test_the_registry_hook() -> None:
    hooks = yaml.safe_load(
        (REPOSITORY_ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
    )
    (hook,) = [h for h in hooks if h["id"] == "timetoshare-registry"]
    assert {
        key: hook.get(key)
        for key in (
            "entry",
            "language",
            "additional_dependencies",
            "stages",
            "pass_filenames",
            "always_run",
        )
    } == {
        "entry": "timetoshare registry --check",
        "language": "python",
        "additional_dependencies": ["./python[tables]"],
        "stages": ["pre-commit"],
        "pass_filenames": False,
        "always_run": True,
    }
    command, *arguments = hook["entry"].split()
    assert command == "timetoshare"
    parsed = _parser().parse_args(arguments)
    assert (parsed.run.__name__, parsed.check, parsed.package) == (
        "_registry",
        True,
        ".",
    )
