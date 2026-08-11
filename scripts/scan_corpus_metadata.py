#!/usr/bin/env python3
"""Aggregate corpus filesystem metadata without reading or naming files.

The scanner deliberately uses directory entries and ``stat`` metadata only.
It does not open files, hash content, emit filenames, preserve source paths, or
attempt to infer document meaning from content.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from veriformis.parsers.dispatch import CODE_EXTENSIONS, DECLARED_V1_EXTENSIONS


SCHEMA_VERSION = "veriformis.corpus-metadata-aggregate/v1"
EVIDENCE_GRADES = {
    "source-verified",
    "test-verified",
    "recorded-local",
    "retained-artifact",
    "external-primary",
    "planned",
}
PORTABILITY_VALUES = {"repository-tracked", "local-only", "external"}
SOURCE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
NO_EXTENSION = "[no-extension]"
UNDECLARED_EXTENSION = "[undeclared-other]"

SIZE_BUCKETS = (
    ("zero", 0, 0),
    ("1b_to_1kib", 1, 1024),
    ("over_1kib_to_1mib", 1025, 1024 * 1024),
    ("over_1mib_to_100mib", 1024 * 1024 + 1, 100 * 1024 * 1024),
    ("over_100mib", 100 * 1024 * 1024 + 1, None),
)

EXTENSION_FAMILIES = {
    ".txt": "plain-text",
    ".md": "markup",
    ".markdown": "markup",
    ".html": "markup",
    ".htm": "markup",
    ".docx": "office-document",
    ".pdf": "portable-document",
    ".csv": "tabular",
    ".json": "structured-data",
    ".jsonl": "structured-data",
    **{extension: "source-code" for extension in CODE_EXTENSIONS},
}


@dataclass
class _Counters:
    files: int = 0
    directories: int = 0
    total_bytes: int = 0
    symlinks: int = 0
    other_entries: int = 0
    inaccessible_entries: int = 0
    hidden_entries: int = 0
    bundle_directories: int = 0
    bundle_context_files: int = 0
    extension_files: Counter[str] = field(default_factory=Counter)
    extension_bytes: Counter[str] = field(default_factory=Counter)
    family_files: Counter[str] = field(default_factory=Counter)
    family_bytes: Counter[str] = field(default_factory=Counter)
    size_files: Counter[str] = field(default_factory=Counter)
    size_bytes: Counter[str] = field(default_factory=Counter)


def _public_extension(name: str) -> str:
    extension = Path(name).suffix.lower()
    if not extension:
        return NO_EXTENSION
    if extension in DECLARED_V1_EXTENSIONS:
        return extension
    return UNDECLARED_EXTENSION


def _family(extension: str) -> str:
    if extension == NO_EXTENSION:
        return "no-extension"
    if extension == UNDECLARED_EXTENSION:
        return "undeclared-other"
    return EXTENSION_FAMILIES[extension]


def _size_bucket(size: int) -> str:
    for name, minimum, maximum in SIZE_BUCKETS:
        if size >= minimum and (maximum is None or size <= maximum):
            return name
    raise AssertionError(f"unclassified non-negative size: {size}")


def _scan_directory(
    directory: Path,
    *,
    counters: _Counters,
    inside_bundle: bool,
) -> None:
    try:
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
    except OSError:
        counters.inaccessible_entries += 1
        return

    for entry in entries:
        if entry.name.startswith("."):
            counters.hidden_entries += 1
        try:
            if entry.is_symlink():
                counters.symlinks += 1
                continue
            if entry.is_dir(follow_symlinks=False):
                counters.directories += 1
                is_bundle = Path(entry.name).suffix.lower() == ".vfbundle"
                if is_bundle:
                    counters.bundle_directories += 1
                _scan_directory(
                    Path(entry.path),
                    counters=counters,
                    inside_bundle=inside_bundle or is_bundle,
                )
                continue
            if not entry.is_file(follow_symlinks=False):
                counters.other_entries += 1
                continue
            size = entry.stat(follow_symlinks=False).st_size
        except OSError:
            counters.inaccessible_entries += 1
            continue

        extension = _public_extension(entry.name)
        family = _family(extension)
        size_bucket = _size_bucket(size)
        counters.files += 1
        counters.total_bytes += size
        counters.extension_files[extension] += 1
        counters.extension_bytes[extension] += size
        counters.family_files[family] += 1
        counters.family_bytes[family] += size
        counters.size_files[size_bucket] += 1
        counters.size_bytes[size_bucket] += size
        if inside_bundle:
            counters.bundle_context_files += 1


def scan_source(
    root: Path,
    *,
    source_id: str,
    evidence_grade: str,
    portability: str,
) -> dict[str, Any]:
    """Return deterministic, content-blind aggregate metadata for ``root``."""
    if not SOURCE_ID_PATTERN.fullmatch(source_id):
        raise ValueError(
            "source_id must contain only lowercase letters, digits, '.', '_', or '-'"
        )
    if evidence_grade not in EVIDENCE_GRADES:
        raise ValueError(f"unsupported evidence grade: {evidence_grade}")
    if portability not in PORTABILITY_VALUES:
        raise ValueError(f"unsupported portability: {portability}")
    if not root.is_dir():
        raise ValueError("scan root must be an existing directory")

    counters = _Counters()
    _scan_directory(root, counters=counters, inside_bundle=False)

    extensions = [
        {
            "extension": extension,
            "family": _family(extension),
            "file_count": counters.extension_files[extension],
            "total_bytes": counters.extension_bytes[extension],
            "declared_v1_input_suffix": extension in DECLARED_V1_EXTENSIONS,
        }
        for extension in sorted(counters.extension_files)
    ]
    families = [
        {
            "family": family,
            "file_count": counters.family_files[family],
            "total_bytes": counters.family_bytes[family],
        }
        for family in sorted(counters.family_files)
    ]
    size_buckets = [
        {
            "bucket": name,
            "file_count": counters.size_files[name],
            "total_bytes": counters.size_bytes[name],
        }
        for name, _, _ in SIZE_BUCKETS
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "evidence_grade": evidence_grade,
        "portability": portability,
        "observation_scope": "filesystem-metadata-only",
        "aggregate": {
            "file_count": counters.files,
            "directory_count": counters.directories,
            "total_bytes": counters.total_bytes,
            "symlink_count": counters.symlinks,
            "other_entry_count": counters.other_entries,
            "inaccessible_entry_count": counters.inaccessible_entries,
            "hidden_entry_count": counters.hidden_entries,
            "bundle_directory_count": counters.bundle_directories,
            "bundle_context_file_count": counters.bundle_context_files,
            "extensions": extensions,
            "families": families,
            "size_buckets": size_buckets,
        },
        "privacy": {
            "file_content_read": False,
            "file_names_emitted": False,
            "source_paths_emitted": False,
            "content_hashes_emitted": False,
            "timestamps_emitted": False,
            "undeclared_extensions_emitted": False,
        },
        "limitations": [
            "Suffix classification does not prove that a file is a user source or that parsing succeeds.",
            "Counts establish the observed root's composition, not customer-corpus prevalence or product demand.",
            "Undeclared suffixes are combined to avoid disclosing uncommon extension names.",
            "Symlink targets and file content are never followed or read.",
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="directory to scan")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--evidence-grade", required=True, choices=sorted(EVIDENCE_GRADES))
    parser.add_argument("--portability", required=True, choices=sorted(PORTABILITY_VALUES))
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = scan_source(
            args.root,
            source_id=args.source_id,
            evidence_grade=args.evidence_grade,
            portability=args.portability,
        )
    except ValueError as exc:
        print(f"corpus metadata scan failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
