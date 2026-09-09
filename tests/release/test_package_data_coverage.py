"""Every packaged data file under ``src/veriformis`` must be declared.

Post-20 defect D-01: ``scale/support-v1.json`` was loaded through
``importlib.resources`` but no ``package-data`` glob covered it, so an installed
wheel raised ``FileNotFoundError`` from ``veriformis scale-support``. This test
compares the on-disk data files with the declared globs so the next stray data
file fails here instead of on a clean machine.
"""

from __future__ import annotations

import fnmatch
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "src" / "veriformis"
DATA_SUFFIXES = (".json", ".jinja", ".yaml", ".yml", ".txt")


def _declared_globs() -> tuple[str, ...]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]
    return tuple(package_data["veriformis"])


def _data_files() -> tuple[str, ...]:
    files = []
    for path in sorted(PACKAGE_ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in DATA_SUFFIXES:
            continue
        if "__pycache__" in path.parts:
            continue
        files.append(path.relative_to(PACKAGE_ROOT).as_posix())
    return tuple(files)


def test_every_packaged_data_file_matches_a_package_data_glob() -> None:
    globs = _declared_globs()
    files = _data_files()
    assert files, "expected packaged data files under src/veriformis"
    uncovered = [
        name for name in files if not any(fnmatch.fnmatch(name, glob) for glob in globs)
    ]
    assert uncovered == [], f"data files missing from package-data: {uncovered}"


def test_every_package_data_glob_matches_at_least_one_file() -> None:
    files = _data_files()
    for glob in _declared_globs():
        assert any(fnmatch.fnmatch(name, glob) for name in files), (
            f"package-data glob matches no file: {glob}"
        )


def test_scale_support_data_is_declared() -> None:
    assert "scale/support-v1.json" in _data_files()
    assert any(fnmatch.fnmatch("scale/support-v1.json", glob) for glob in _declared_globs())
