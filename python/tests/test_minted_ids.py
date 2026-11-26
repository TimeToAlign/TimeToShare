"""The test vectors of minted IDs; see README "Minted ID vectors"."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any

import pytest

from timetoshare.validate import data_root

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPOSITORY_ROOT / "scripts" / "emit_id_vectors.py"

_spec = importlib.util.spec_from_file_location("emit_id_vectors", SCRIPT)
assert _spec is not None and _spec.loader is not None
emitter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(emitter)

MASK = (1 << 64) - 1
GOLDEN_GAMMA = 0x9E3779B97F4A7C15
PREFIXES = ["note", "clt", "note", "claim", "score:clt"]


def vectors_path() -> Path:
    return data_root() / "fixtures" / "ids" / "minted_ids.json"


def vectors() -> dict[str, Any]:
    return json.loads(vectors_path().read_text(encoding="utf-8"))


def unmix64(value: int) -> int:
    """The inverse of SplitMix64's finalizer, written apart from the script."""
    value ^= value >> 31 ^ value >> 62
    value = (value * pow(0x94D049BB133111EB, -1, 1 << 64)) & MASK
    value ^= value >> 27 ^ value >> 54
    value = (value * pow(0xBF58476D1CE4E5B9, -1, 1 << 64)) & MASK
    value ^= value >> 30 ^ value >> 60
    return value


def test_the_file_is_the_scripts_output() -> None:
    expected = emitter.render(emitter.vectors()).encode("utf-8")
    assert vectors_path().read_bytes() == expected


def test_mix64_reproduces_splitmix64() -> None:
    state = 1234567
    outputs = []
    for _ in range(5):
        state = (state + GOLDEN_GAMMA) & MASK
        outputs.append(emitter.mix64(state))
    assert outputs == [
        6457827717110365317,
        3203168211198807973,
        9817491932198370423,
        4593380528125082431,
        16408922859458223821,
    ]


def test_mix64_pairs_invert() -> None:
    for pair in vectors()["mix64"]:
        assert unmix64(int(pair["output"])) == int(pair["input"])


def test_the_content_is_what_the_file_promises() -> None:
    content = vectors()
    assert sorted(content) == ["description", "later_ids", "minters", "mix64"]
    assert [pair["input"] for pair in content["mix64"]] == [
        "0",
        "1",
        "2",
        "42",
        "9223372036854775808",
        "18446744073709551615",
        "81985529216486895",
    ]
    assert all(isinstance(pair["output"], str) for pair in content["mix64"])
    seeds = ["0", "1", "42", "81985529216486895", "18446744073709551615", "-1"]
    assert [(entry["seed"], entry["length"]) for entry in content["minters"]] == [
        (seed, length) for seed in seeds for length in (13, 10, 7)
    ]
    for entry in content["minters"]:
        assert sorted(entry) == ["ids", "length", "prefixes", "seed"]
        assert entry["prefixes"] == PREFIXES
        assert len(entry["ids"]) == 5
    assert content["later_ids"] == [
        {
            "counter": 1000,
            "id": entry["id"],
            "length": length,
            "prefix": "note",
            "seed": "42",
        }
        for entry, length in zip(content["later_ids"], (13, 10, 7), strict=True)
    ]


def minted(seed: str, length: int) -> list[tuple[int, str, str]]:
    """Every ID the file states for the minter, with its counter and prefix."""
    content = vectors()
    found = []
    for entry in content["minters"]:
        if (entry["seed"], entry["length"]) == (seed, length):
            found += [
                (counter, prefix, identifier)
                for counter, (prefix, identifier) in enumerate(
                    zip(entry["prefixes"], entry["ids"], strict=True), start=1
                )
            ]
    for entry in content["later_ids"]:
        if (entry["seed"], entry["length"]) == (seed, length):
            found.append((entry["counter"], entry["prefix"], entry["id"]))
    return found


MINTERS = [
    (entry["seed"], entry["length"])
    for entry in json.loads(
        (data_root() / "fixtures" / "ids" / "minted_ids.json").read_text("utf-8")
    )["minters"]
]


@pytest.mark.parametrize(("seed", "length"), MINTERS)
def test_each_id_decodes_to_its_counter(seed: str, length: int) -> None:
    pattern = re.compile(rf"^.+_[0-9a-z]{{{length}}}$")
    start = emitter.mix64(int(seed) & MASK)
    for counter, prefix, identifier in minted(seed, length):
        assert pattern.fullmatch(identifier), identifier
        head, _, suffix = identifier.rpartition("_")
        assert head == prefix
        assert int(suffix, 36) == emitter.mix64(start + counter) % 36**length


def test_a_seed_is_taken_modulo_2_64() -> None:
    by_seed = {
        (entry["seed"], entry["length"]): entry["ids"] for entry in vectors()["minters"]
    }
    for length in (13, 10, 7):
        assert by_seed[("-1", length)] == by_seed[("18446744073709551615", length)]


def test_the_counter_is_shared_by_the_prefixes() -> None:
    for entry in vectors()["minters"]:
        assert entry["ids"][0] != entry["ids"][2]


def test_pinned_values() -> None:
    content = vectors()
    assert emitter.mix64(0) == 0
    first = next(
        entry
        for entry in content["minters"]
        if (entry["seed"], entry["length"]) == ("42", 13)
    )
    assert first["ids"][0] == "note_26vx31m84xkac"
    assert content["later_ids"][0]["id"] == "note_3cu6welhit32x"
