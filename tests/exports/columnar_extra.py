"""Shared extra-columnar isolation assertions."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COLUMNAR_EXTRA_PINS = [
    "pyarrow>=19.0.0,<26.0.0",
    "datasets>=3.0.0,<6.0.0",
]
EMPTY_EXTRAS = ("trl", "mlx-lm", "axolotl", "llama-factory", "unsloth", "ocr")
_PYARROW_MARKER = (
    '{ name = "pyarrow", marker = "extra == \'columnar\'", '
    'specifier = ">=19.0.0,<26.0.0" }'
)
_DATASETS_MARKER = (
    '{ name = "datasets", marker = "extra == \'columnar\'", '
    'specifier = ">=3.0.0,<6.0.0" }'
)


def assert_columnar_extra_lists_pins() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    extras = tomllib.loads(text)["project"]["optional-dependencies"]
    assert extras["columnar"] == COLUMNAR_EXTRA_PINS
    assert "columnar = []" not in text
    for name in EMPTY_EXTRAS:
        assert extras[name] == []
        assert f"{name} = []" in text


def assert_columnar_wheels_are_extra_only() -> None:
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "pyarrow"\n' in lock
    assert 'name = "datasets"\n' in lock
    assert _PYARROW_MARKER in lock
    assert _DATASETS_MARKER in lock
    default_requires = _veriformis_default_requires(lock)
    assert not any(item.startswith("pyarrow") for item in default_requires)
    assert not any(item.startswith("datasets") for item in default_requires)
    assert not any(item.startswith("pandas") for item in default_requires)
    extras = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["optional-dependencies"]
    assert "pandas" not in extras["columnar"]


def _veriformis_default_requires(lock: str) -> tuple[str, ...]:
    lines = lock.splitlines()
    in_package = False
    in_requires = False
    names: list[str] = []
    for line in lines:
        if line == 'name = "veriformis"':
            in_package = True
            continue
        if in_package and line.startswith("name = ") and line != 'name = "veriformis"':
            break
        if in_package and line == "[package.metadata]":
            in_requires = False
            continue
        if in_package and line == "requires-dist = [":
            in_requires = True
            continue
        if in_requires:
            if line == "]":
                break
            if "marker" in line:
                continue
            start = line.find('{ name = "')
            if start < 0:
                continue
            start += len('{ name = "')
            end = line.find('"', start)
            names.append(line[start:end])
    return tuple(names)
