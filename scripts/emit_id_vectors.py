#!/usr/bin/env python3
"""Write the test vectors of minted IDs to ``fixtures/ids/minted_ids.json``.

A tool that mints an ID for an element created without one writes the
element's type prefix, ``_`` and a suffix of random base-36 characters,
seeded so that it can mint the same IDs again. Two tools that mint from the
same seed must mint the same IDs; the vectors written here are the values
both check against. This script is the reference implementation of the
algorithm, all arithmetic modulo 2^64:

* ``mix64(x)``: ``x ^= x >> 30; x *= 0xbf58476d1ce4e5b9; x ^= x >> 27;
  x *= 0x94d049bb133111eb; x ^= x >> 31``, the finalizer of SplitMix64, a
  bijection on 64-bit integers.
* A minter is a seed, an integer taken modulo 2^64, and a length L,
  1 <= L <= 13; ``start = mix64(seed mod 2^64)``.
* The k-th ID it mints, k = 1, 2, ..., whatever its prefix, is
  ``prefix + "_" + base36(mix64(start + k) mod 36^L)``, the digits ``0-9a-z``
  left-padded with ``0`` to L characters. All prefixes share the one
  counter.

At L = 13 one minter never repeats a suffix, since 36^13 > 2^64 and
``mix64`` is a bijection; a shorter L guarantees nothing.

Integers that may exceed 2^53 (seeds, the inputs and outputs of ``mix64``)
are written as decimal strings, so that JavaScript reads them exactly, as
BigInt; lengths and counters are JSON integers. The file is written with
sorted keys, an indent of two spaces and a final line feed, and only when
its bytes change.

Usage::

    python scripts/emit_id_vectors.py

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VECTORS_PATH = REPOSITORY_ROOT / "fixtures" / "ids" / "minted_ids.json"

MASK = (1 << 64) - 1
"""All arithmetic is modulo 2^64."""

DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"
MAX_LENGTH = 13
"""The longest suffix, and the length a tool mints by default."""

MIX64_INPUTS = (0, 1, 2, 42, 1 << 63, MASK, 0x0123456789ABCDEF)
SEEDS = (0, 1, 42, 0x0123456789ABCDEF, MASK, -1)
LENGTHS = (13, 10, 7)
PREFIXES = ("note", "clt", "note", "claim", "score:clt")
"""Mixed prefixes, the counter being shared by all of them; a prefix led by a
role (``score:clt``) is a prefix like any other."""

LATER_SEED = 42
LATER_PREFIX = "note"
LATER_COUNTER = 1000

DESCRIPTION = (
    "Test vectors of minted IDs. All arithmetic is modulo 2^64. "
    "mix64(x): x ^= x >> 30; x *= 0xbf58476d1ce4e5b9; x ^= x >> 27; "
    "x *= 0x94d049bb133111eb; x ^= x >> 31 (the finalizer of SplitMix64). "
    "A minter of seed s and length L (1 to 13) starts at mix64(s mod 2^64); "
    "its k-th ID (k = 1, 2, ...), for any prefix, is prefix + '_' + "
    "base36(mix64(start + k) mod 36^L), digits 0-9a-z, left-padded with '0' "
    "to L characters; one counter is shared by all prefixes. Seeds and the "
    "inputs and outputs of mix64 are decimal strings; lengths and counters "
    "are integers. 'minters' lists the IDs a fresh minter mints with the "
    "given prefixes in order; 'later_ids' the ID a fresh minter mints at the "
    "given counter, every ID before it minted with the same prefix."
)


def mix64(value: int) -> int:
    """Return SplitMix64's finalizer of ``value`` modulo 2^64."""
    value &= MASK
    value ^= value >> 30
    value = (value * 0xBF58476D1CE4E5B9) & MASK
    value ^= value >> 27
    value = (value * 0x94D049BB133111EB) & MASK
    value ^= value >> 31
    return value


def base36(value: int, length: int) -> str:
    """Return ``value`` in base 36, left-padded with ``0`` to ``length`` digits."""
    digits = []
    while value:
        value, digit = divmod(value, 36)
        digits.append(DIGITS[digit])
    return "".join(reversed(digits)).rjust(length, "0")


def minted_id(seed: int, length: int, counter: int, prefix: str) -> str:
    """Return the ``counter``-th ID a minter of ``seed`` and ``length`` mints."""
    if not 1 <= length <= MAX_LENGTH:
        raise ValueError(f"the length {length} lies outside 1 to {MAX_LENGTH}")
    if counter < 1:
        raise ValueError(f"the counter {counter} is not positive")
    start = mix64(seed)
    suffix = mix64(start + counter) % 36**length
    return f"{prefix}_{base36(suffix, length)}"


def vectors() -> dict[str, Any]:
    """Return the content of the vectors file."""
    return {
        "description": DESCRIPTION,
        "mix64": [
            {"input": str(value), "output": str(mix64(value))} for value in MIX64_INPUTS
        ],
        "minters": [
            {
                "seed": str(seed),
                "length": length,
                "prefixes": list(PREFIXES),
                "ids": [
                    minted_id(seed, length, counter, prefix)
                    for counter, prefix in enumerate(PREFIXES, start=1)
                ],
            }
            for seed in SEEDS
            for length in LENGTHS
        ],
        "later_ids": [
            {
                "seed": str(LATER_SEED),
                "length": length,
                "prefix": LATER_PREFIX,
                "counter": LATER_COUNTER,
                "id": minted_id(LATER_SEED, length, LATER_COUNTER, LATER_PREFIX),
            }
            for length in LENGTHS
        ],
    }


def render(content: dict[str, Any]) -> str:
    """Return the text of the vectors file: sorted keys, indent 2, a final line feed."""
    return json.dumps(content, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write the vectors file when its bytes change."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.parse_args(argv)
    data = render(vectors()).encode("utf-8")
    target = VECTORS_PATH.relative_to(REPOSITORY_ROOT)
    if VECTORS_PATH.is_file() and VECTORS_PATH.read_bytes() == data:
        print(f"{target}: unchanged")
        return 0
    VECTORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    VECTORS_PATH.write_bytes(data)
    print(f"{target}: written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
