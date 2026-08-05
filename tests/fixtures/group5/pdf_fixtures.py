"""Minimal digitally-born and empty-text PDF byte fixtures for Group 5 tests."""

from pathlib import Path

_FIXTURE_DIR = Path(__file__).resolve().parent

MINIMAL_TEXT_PDF = (_FIXTURE_DIR / "minimal-text.pdf").read_bytes()
EMPTY_TEXT_PDF = (_FIXTURE_DIR / "empty-text.pdf").read_bytes()
