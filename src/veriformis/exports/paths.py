"""Portable path rules shared by verified-export models and publication."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
_WINDOWS_RESERVED = frozenset(
    {"con", "prn", "aux", "nul", "conin$", "conout$"}
    | {f"com{number}" for number in range(1, 10)}
    | {f"lpt{number}" for number in range(1, 10)}
)
_WINDOWS_FORBIDDEN = frozenset('<>:"/\\|?*')


def portable_export_path_key(path: str) -> str:
    """Return the conservative case/Unicode-insensitive collision key."""
    return unicodedata.normalize("NFKC", path).casefold()


def _validate_path_form(value: str) -> None:
    if "\x00" in value:
        raise ValueError("export paths cannot contain NUL")
    if "\\" in value:
        raise ValueError("export paths must use POSIX separators")
    if value.startswith("/") or _WINDOWS_DRIVE.match(value):
        raise ValueError("export paths must be relative POSIX paths")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("export paths cannot contain empty, dot, or parent segments")
    for part in parts:
        if any(character in _WINDOWS_FORBIDDEN for character in part) or part.endswith(
            (" ", ".")
        ):
            raise ValueError("export paths cannot contain Windows path aliases")
        if any(
            unicodedata.category(character) in {"Cc", "Cf"}
            for character in part
        ):
            raise ValueError("export paths cannot contain control or format characters")
        device_name = part.split(".", 1)[0].rstrip(" ").casefold()
        if device_name in _WINDOWS_RESERVED:
            raise ValueError("export paths cannot use Windows device names")


def validate_export_relative_path(value: str) -> str:
    """Validate one NFC relative POSIX path without normalizing it silently."""
    if not isinstance(value, str) or not value:
        raise ValueError("export paths must be non-empty strings")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("export paths must contain valid Unicode") from exc
    if value != unicodedata.normalize("NFC", value):
        raise ValueError("export paths must use canonical NFC Unicode")
    _validate_path_form(value)
    compatibility_form = unicodedata.normalize("NFKC", value)
    if compatibility_form.count("/") != value.count("/"):
        raise ValueError("export paths cannot contain compatibility separators")
    _validate_path_form(compatibility_form)
    return value


def validate_export_path_set(
    paths: Sequence[str],
    *,
    label: str,
    require_sorted: bool = True,
) -> tuple[str, ...]:
    """Reject duplicates, aliases, and file/ancestor conflicts in one tree."""
    checked = tuple(validate_export_relative_path(path) for path in paths)
    if require_sorted and checked != tuple(sorted(checked)):
        raise ValueError(f"{label} must be sorted by exact path")
    if len(checked) != len(set(checked)):
        raise ValueError(f"{label} contain duplicate paths")

    portable_entries: dict[str, str] = {}
    exact_paths = set(checked)
    for path in checked:
        parts = path.split("/")
        for index in range(1, len(parts) + 1):
            entry = "/".join(parts[:index])
            key = portable_export_path_key(entry)
            previous = portable_entries.get(key)
            if previous is not None and previous != entry:
                raise ValueError(
                    f"{label} collide by case or Unicode: {previous!r} and {entry!r}"
                )
            portable_entries[key] = entry
        for index in range(1, len(parts)):
            parent = "/".join(parts[:index])
            if parent in exact_paths:
                raise ValueError(
                    f"export path {parent!r} is both a file and a directory"
                )
    return checked


__all__ = [
    "portable_export_path_key",
    "validate_export_path_set",
    "validate_export_relative_path",
]
