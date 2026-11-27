from __future__ import annotations

import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SPECIFICATIONS = {
    f"docs/{name}": (REPOSITORY_ROOT / "docs" / name).read_bytes()
    for name in ("description.md", "drawing.md")
}
"""The two specifications, sorted: all of ``docs/`` that the packages ship."""
LICENCE = (REPOSITORY_ROOT / "LICENSE").read_bytes()
DOCUMENTS = {
    **{
        f"schema/0.2.0/{name}": (
            REPOSITORY_ROOT / "schema" / "0.2.0" / name
        ).read_bytes()
        for name in (
            "package.schema.json",
            "provenance.schema.json",
            "tables.json",
            "timetoshare.schema.json",
        )
    },
    **{
        f"catalogue/{name}": (REPOSITORY_ROOT / "catalogue" / name).read_bytes()
        for name in ("catalogue.yaml", "catalogue.schema.json")
    },
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
def test_the_distributions_ship_the_specifications_schemas_catalogue_fonts_licences(
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
        for path, document in {**SPECIFICATIONS, **DOCUMENTS, **FONTS}.items():
            assert archive.read(f"timetoshare/{path}") == document
        for directory, files in (("fonts", FONTS), ("docs", SPECIFICATIONS)):
            assert sorted(
                name
                for name in archive.namelist()
                if name.startswith(f"timetoshare/{directory}/")
            ) == [f"timetoshare/{path}" for path in files]
        name, version = wheel.name.split("-")[:2]
        assert archive.read(f"{name}-{version}.dist-info/licenses/LICENSE") == LICENCE
    (sdist,) = tmp_path.glob("timetoshare-*.tar.gz")
    with tarfile.open(sdist) as archive:
        root = sdist.name.removesuffix(".tar.gz")
        for path, document in {**SPECIFICATIONS, **DOCUMENTS, **FONTS}.items():
            shipped = archive.extractfile(f"{root}/src/timetoshare/{path}")
            assert shipped is not None
            assert shipped.read() == document
        for directory, files in (("fonts", FONTS), ("docs", SPECIFICATIONS)):
            assert sorted(
                member.name
                for member in archive.getmembers()
                if member.isfile()
                and member.name.startswith(f"{root}/src/timetoshare/{directory}/")
            ) == [f"{root}/src/timetoshare/{path}" for path in files]
        licence = archive.extractfile(f"{sdist.name.removesuffix('.tar.gz')}/LICENSE")
        assert licence is not None
        assert licence.read() == LICENCE
