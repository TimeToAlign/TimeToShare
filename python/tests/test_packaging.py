from __future__ import annotations

import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SPECIFICATION = (REPOSITORY_ROOT / "docs" / "drawing.md").read_bytes()
LICENCE = (REPOSITORY_ROOT / "LICENSE").read_bytes()
DOCUMENTS = {
    "schema/0.2.0/timetoshare.schema.json": (
        REPOSITORY_ROOT / "schema" / "0.2.0" / "timetoshare.schema.json"
    ).read_bytes(),
    "registry/schemes.json": (
        REPOSITORY_ROOT / "registry" / "schemes.json"
    ).read_bytes(),
}
FONT_FILES = (
    "DejaVuSans-LICENSE",
    "DejaVuSans.ttf",
    "NotoMusic-LICENSE",
    "NotoMusic-Regular.ttf",
    "dejavu-sans-2.37+noto-music-2.004.metrics.json",
)
"""Both TrueType files, their licences and the metrics table, sorted."""
FONTS = {
    f"fonts/{name}": (REPOSITORY_ROOT / "fonts" / name).read_bytes()
    for name in FONT_FILES
}


@pytest.mark.parametrize(
    "arguments",
    [["--sdist", "--wheel"], []],
    ids=["wheel from the checkout", "wheel from the sdist"],
)
def test_the_distributions_ship_the_specification_schemas_registry_fonts_licences(
    arguments: list[str], tmp_path: Path
) -> None:
    uv = shutil.which("uv")
    assert uv is not None, "building the distributions needs uv"
    subprocess.run(
        [uv, "build", *arguments, "--out-dir", str(tmp_path)],
        cwd=REPOSITORY_ROOT / "python",
        check=True,
        capture_output=True,
    )
    (wheel,) = tmp_path.glob("timetoshare-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        assert archive.read("timetoshare/docs/drawing.md") == SPECIFICATION
        for path, document in {**DOCUMENTS, **FONTS}.items():
            assert archive.read(f"timetoshare/{path}") == document
        assert sorted(
            name for name in archive.namelist() if name.startswith("timetoshare/fonts/")
        ) == [f"timetoshare/{path}" for path in FONTS]
        name, version = wheel.name.split("-")[:2]
        assert archive.read(f"{name}-{version}.dist-info/licenses/LICENSE") == LICENCE
    (sdist,) = tmp_path.glob("timetoshare-*.tar.gz")
    with tarfile.open(sdist) as archive:
        member = archive.extractfile(
            f"{sdist.name.removesuffix('.tar.gz')}/src/timetoshare/docs/drawing.md"
        )
        assert member is not None
        assert member.read() == SPECIFICATION
        root = sdist.name.removesuffix(".tar.gz")
        for path, document in {**DOCUMENTS, **FONTS}.items():
            shipped = archive.extractfile(f"{root}/src/timetoshare/{path}")
            assert shipped is not None
            assert shipped.read() == document
        assert sorted(
            member.name
            for member in archive.getmembers()
            if member.isfile()
            and member.name.startswith(f"{root}/src/timetoshare/fonts/")
        ) == [f"{root}/src/timetoshare/{path}" for path in FONTS]
        licence = archive.extractfile(f"{sdist.name.removesuffix('.tar.gz')}/LICENSE")
        assert licence is not None
        assert licence.read() == LICENCE
