#!/usr/bin/env python
"""Write the expected RDF of the statement fixtures: for each manifest under
``fixtures/<version>/statements/`` (its minimal twin aside), the canonical
N-Quads (RDFC-1.0, the algorithm PyLD names URDNA2015) of its JSON-LD reading
with the base ``https://example.org/manifests/<name>.yaml``, to
``fixtures/rdf/<version>/<name>.nq``. Nothing is fetched: every manifest
carries its context inline. A file is rewritten only when its bytes change; a
file whose fixture is gone is removed. The files of a released version, whose
tag ``v<version>`` exists, are never overwritten.

Run it from ``python/`` with ``uv run python ../scripts/emit_rdf.py`` after
the fixtures are emitted; PyLD is a development dependency of the package.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from pyld import jsonld

from timetoshare import SCHEMA_VERSION, loads

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPOSITORY_ROOT / "fixtures" / SCHEMA_VERSION / "statements"
RDF_DIR = REPOSITORY_ROOT / "fixtures" / "rdf" / SCHEMA_VERSION
BASE = "https://example.org/manifests/{name}.yaml"


def refuse(url: str, options: Any = None) -> Any:
    """The document loader: a manifest's context is inline, so nothing is fetched."""
    raise OSError(f"the expected RDF is read without fetching anything; refused {url}")


def canonical_nquads(text: str, name: str) -> str:
    """Return the canonical N-Quads of the manifest ``text`` named ``name``."""
    return jsonld.normalize(
        loads(text),
        {
            "algorithm": "URDNA2015",
            "format": "application/n-quads",
            "base": BASE.format(name=name),
            "documentLoader": refuse,
        },
    )


def main() -> int:
    """Write every changed ``.nq`` file and remove the stale ones."""
    tag = f"v{SCHEMA_VERSION}"
    tagged = subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "tag", "--list", tag],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    if tag in tagged:
        raise SystemExit(f"{tag} is released; its expected RDF in {RDF_DIR} is frozen.")
    manifests = sorted(
        path
        for path in FIXTURE_DIR.glob("*.yaml")
        if not path.name.endswith(".minimal.yaml")
    )
    if not manifests:
        raise SystemExit(f"no statement fixture under {FIXTURE_DIR}; emit them first.")
    RDF_DIR.mkdir(parents=True, exist_ok=True)
    expected = {path.stem for path in manifests}
    for stale in RDF_DIR.glob("*.nq"):
        if stale.stem not in expected:
            stale.unlink()
            print(f"{stale.relative_to(REPOSITORY_ROOT)}: removed")
    for path in manifests:
        target = RDF_DIR / f"{path.stem}.nq"
        quads = canonical_nquads(path.read_text(encoding="utf-8"), path.stem)
        data = quads.encode("utf-8")
        if target.is_file() and target.read_bytes() == data:
            print(f"{target.relative_to(REPOSITORY_ROOT)}: unchanged")
            continue
        target.write_bytes(data)
        print(f"{target.relative_to(REPOSITORY_ROOT)}: written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
