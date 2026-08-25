"""Deterministic collection plan for files and directories.

Collection is a first-class ingest contract. CLI, MCP, and the Mac bridge
must share this expander. Capture still pins accepted regular files; this
module only names membership.
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from veriformis.errors import CollectionError, CollectionLimitError, InvalidSourceLocatorError
from veriformis.identity import (
    canonical_digest,
    lossless_json_bytes,
    normalize_logical_path,
)
from veriformis.parsers.dispatch import DECLARED_V1_EXTENSIONS
from veriformis.sources import _absolute, _source_root

COLLECTION_PLAN_SCHEMA_ID = "veriformis.collection-plan/v1"
COLLECTION_PLAN_SCHEMA_VERSION = 1
DEFAULT_MAX_FILES = 10_000
DEFAULT_MAX_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_VISITED = 50_000
PACKAGE_DIRECTORY_SUFFIXES = frozenset(
    {".app", ".bundle", ".framework", ".plugin", ".lproj", ".xcodeproj", ".xcassets"}
)
MemberStatus = Literal["accepted", "degraded", "refused", "duplicate", "ignored"]
UnsupportedPolicy = Literal["ignore", "refuse"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class CollectionSettings(_StrictModel):
    recurse: bool = True
    include_hidden: bool = False
    include_package_contents: bool = False
    follow_symlinks: Literal[False] = False
    unsupported_policy: UnsupportedPolicy = "ignore"
    max_files: int = DEFAULT_MAX_FILES
    max_bytes: int = DEFAULT_MAX_BYTES
    max_visited: int = DEFAULT_MAX_VISITED
    include_globs: tuple[str, ...] = ()
    exclude_globs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _positive_limits(self) -> CollectionSettings:
        if self.max_files < 1 or self.max_bytes < 1 or self.max_visited < 1:
            raise CollectionError("collection limits must be positive")
        if self.follow_symlinks:
            raise CollectionError("collection must not follow symlinks")
        return self


class CollectionMember(_StrictModel):
    logical_path: str
    status: MemberStatus
    reason: str | None
    size: int
    sha256: str | None


class CollectionCounts(_StrictModel):
    accepted: int
    degraded: int
    refused: int
    duplicate: int
    ignored: int
    visited: int
    accepted_bytes: int


class CollectionPlan(_StrictModel):
    schema_id: Literal["veriformis.collection-plan/v1"] = COLLECTION_PLAN_SCHEMA_ID
    schema_version: Literal[1] = COLLECTION_PLAN_SCHEMA_VERSION
    plan_id: str
    source_root: str
    settings: CollectionSettings
    accepted_suffixes: tuple[str, ...]
    members: tuple[CollectionMember, ...]
    counts: CollectionCounts

    def transport_text(self) -> str:
        return lossless_json_bytes(self.model_dump(mode="json")).decode("utf-8")

    def accepted_logical_paths(self) -> tuple[str, ...]:
        return tuple(
            member.logical_path for member in self.members if member.status == "accepted"
        )


def default_collection_settings() -> CollectionSettings:
    return CollectionSettings()


def accepted_source_paths(plan: CollectionPlan, *, source_root: Path) -> list[Path]:
    """Resolve accepted members to regular files under the pinned root."""
    root = _absolute(source_root)
    paths: list[Path] = []
    for logical_path in plan.accepted_logical_paths():
        paths.append(root.joinpath(*PurePosixPath(logical_path).parts))
    return paths


def build_collection_plan(
    paths: list[Path],
    *,
    source_root: Path | None = None,
    settings: CollectionSettings | None = None,
    accepted_suffixes: tuple[str, ...] | None = None,
) -> CollectionPlan:
    """Build one deterministic membership plan without parsing content."""
    if not paths:
        raise CollectionError("collection requires at least one path")
    chosen = default_collection_settings() if settings is None else settings
    suffixes = tuple(
        sorted(
            suffix.lower() if suffix.startswith(".") else f".{suffix.lower()}"
            for suffix in (accepted_suffixes or tuple(sorted(DECLARED_V1_EXTENSIONS)))
        )
    )
    root, _root_identity = _source_root(source_root)
    records: list[CollectionMember] = []
    digest_owners: dict[str, str] = {}
    visited = 0
    accepted_bytes = 0

    for path in paths:
        absolute = _absolute(path)
        visited, records, digest_owners, accepted_bytes = _collect_entry(
            absolute,
            root=root,
            settings=chosen,
            suffixes=suffixes,
            records=records,
            digest_owners=digest_owners,
            visited=visited,
            accepted_bytes=accepted_bytes,
            allow_root=True,
        )

    members = tuple(sorted(records, key=lambda item: item.logical_path))
    counts = _counts(members, visited=visited, accepted_bytes=accepted_bytes)
    if counts.accepted > chosen.max_files:
        raise CollectionLimitError(
            f"collection accepted {counts.accepted} files; max_files is {chosen.max_files}"
        )
    if counts.accepted_bytes > chosen.max_bytes:
        raise CollectionLimitError(
            f"collection accepted {counts.accepted_bytes} bytes; max_bytes is {chosen.max_bytes}"
        )
    if counts.accepted == 0:
        raise CollectionError("collection accepted no sources")
    payload = {
        "schema_id": COLLECTION_PLAN_SCHEMA_ID,
        "schema_version": COLLECTION_PLAN_SCHEMA_VERSION,
        "source_root": root.as_posix(),
        "settings": chosen.model_dump(mode="json"),
        "accepted_suffixes": list(suffixes),
        "members": [member.model_dump(mode="json") for member in members],
        "counts": counts.model_dump(mode="json"),
    }
    plan_id = canonical_digest(payload)
    return CollectionPlan(
        plan_id=plan_id,
        source_root=root.as_posix(),
        settings=chosen,
        accepted_suffixes=suffixes,
        members=members,
        counts=counts,
    )


def _counts(
    members: tuple[CollectionMember, ...] | list[CollectionMember],
    *,
    visited: int,
    accepted_bytes: int,
) -> CollectionCounts:
    accepted = degraded = refused = duplicate = ignored = 0
    for member in members:
        if member.status == "accepted":
            accepted += 1
        elif member.status == "degraded":
            degraded += 1
        elif member.status == "refused":
            refused += 1
        elif member.status == "duplicate":
            duplicate += 1
        else:
            ignored += 1
    return CollectionCounts(
        accepted=accepted,
        degraded=degraded,
        refused=refused,
        duplicate=duplicate,
        ignored=ignored,
        visited=visited,
        accepted_bytes=accepted_bytes,
    )


def _collect_entry(
    absolute: Path,
    *,
    root: Path,
    settings: CollectionSettings,
    suffixes: tuple[str, ...],
    records: list[CollectionMember],
    digest_owners: dict[str, str],
    visited: int,
    accepted_bytes: int,
    allow_root: bool,
) -> tuple[int, list[CollectionMember], dict[str, str], int]:
    if visited >= settings.max_visited:
        raise CollectionLimitError(
            f"collection visited {visited} entries; max_visited is {settings.max_visited}"
        )
    visited += 1
    try:
        observed = os.lstat(absolute)
    except FileNotFoundError:
        if allow_root and absolute == root:
            raise CollectionError("source root does not exist") from None
        try:
            relative = absolute.relative_to(root)
            logical = normalize_logical_path(relative.as_posix())
        except (ValueError, InvalidSourceLocatorError):
            logical = normalize_logical_path(absolute.name or "missing")
        records.append(
            CollectionMember(
                logical_path=logical,
                status="refused",
                reason="missing",
                size=0,
                sha256=None,
            )
        )
        return visited, records, digest_owners, accepted_bytes
    except OSError as exc:
        raise CollectionError(f"collection path could not be inspected: {absolute}") from exc

    is_root_directory = allow_root and stat.S_ISDIR(observed.st_mode) and absolute == root
    if is_root_directory:
        logical = None
    else:
        try:
            relative = absolute.relative_to(root)
        except ValueError as exc:
            raise InvalidSourceLocatorError(
                "source is outside source root; pass --source-root explicitly"
            ) from exc
        if not relative.parts:
            raise InvalidSourceLocatorError("source path names the source root")
        logical = normalize_logical_path(relative.as_posix())

    if stat.S_ISLNK(observed.st_mode):
        if logical is None:
            raise CollectionError("source root must not be a symlink")
        records.append(
            CollectionMember(
                logical_path=logical,
                status="refused",
                reason="symlink",
                size=0,
                sha256=None,
            )
        )
        return visited, records, digest_owners, accepted_bytes

    if stat.S_ISDIR(observed.st_mode):
        if logical is not None:
            if _is_hidden(absolute.name) and not settings.include_hidden:
                records.append(
                    CollectionMember(
                        logical_path=logical,
                        status="ignored",
                        reason="hidden",
                        size=0,
                        sha256=None,
                    )
                )
                return visited, records, digest_owners, accepted_bytes
            if _is_package_directory(absolute) and not settings.include_package_contents:
                records.append(
                    CollectionMember(
                        logical_path=logical,
                        status="ignored",
                        reason="package-directory",
                        size=0,
                        sha256=None,
                    )
                )
                return visited, records, digest_owners, accepted_bytes
            if not settings.recurse:
                records.append(
                    CollectionMember(
                        logical_path=logical,
                        status="ignored",
                        reason="directory-not-recursed",
                        size=0,
                        sha256=None,
                    )
                )
                return visited, records, digest_owners, accepted_bytes
        try:
            with os.scandir(absolute) as entries:
                children = sorted(entries, key=lambda item: item.name)
        except OSError as exc:
            raise CollectionError(
                f"collection directory could not be read: {absolute}"
            ) from exc
        for child in children:
            visited, records, digest_owners, accepted_bytes = _collect_entry(
                Path(child.path),
                root=root,
                settings=settings,
                suffixes=suffixes,
                records=records,
                digest_owners=digest_owners,
                visited=visited,
                accepted_bytes=accepted_bytes,
                allow_root=False,
            )
        return visited, records, digest_owners, accepted_bytes

    if not stat.S_ISREG(observed.st_mode):
        if logical is None:
            raise CollectionError("source root must be a directory")
        records.append(
            CollectionMember(
                logical_path=logical,
                status="refused",
                reason="not-a-regular-file",
                size=0,
                sha256=None,
            )
        )
        return visited, records, digest_owners, accepted_bytes

    assert logical is not None
    size = observed.st_size
    suffix = Path(logical).suffix.lower()
    if _is_hidden(absolute.name) and not settings.include_hidden:
        records.append(
            CollectionMember(
                logical_path=logical,
                status="ignored",
                reason="hidden",
                size=size,
                sha256=None,
            )
        )
        return visited, records, digest_owners, accepted_bytes
    if not _glob_allowed(logical, settings):
        records.append(
            CollectionMember(
                logical_path=logical,
                status="ignored",
                reason="excluded-by-glob",
                size=size,
                sha256=None,
            )
        )
        return visited, records, digest_owners, accepted_bytes
    if suffix not in suffixes:
        if settings.unsupported_policy == "refuse":
            raise CollectionError(
                f"collection refused unsupported suffix {suffix or '<none>'} at {logical}"
            )
        records.append(
            CollectionMember(
                logical_path=logical,
                status="ignored",
                reason="unsupported-suffix",
                size=size,
                sha256=None,
            )
        )
        return visited, records, digest_owners, accepted_bytes

    digest = _file_digest(absolute)
    owner = digest_owners.get(digest)
    if owner is not None:
        records.append(
            CollectionMember(
                logical_path=logical,
                status="duplicate",
                reason=f"duplicate-bytes:{owner}",
                size=size,
                sha256=digest,
            )
        )
        return visited, records, digest_owners, accepted_bytes
    digest_owners[digest] = logical
    records.append(
        CollectionMember(
            logical_path=logical,
            status="accepted",
            reason=None,
            size=size,
            sha256=digest,
        )
    )
    return visited, records, digest_owners, accepted_bytes + size


def _is_hidden(name: str) -> bool:
    return name.startswith(".")


def _is_package_directory(path: Path) -> bool:
    return path.suffix.lower() in PACKAGE_DIRECTORY_SUFFIXES


def _glob_allowed(logical_path: str, settings: CollectionSettings) -> bool:
    if settings.exclude_globs and any(
        fnmatch.fnmatch(logical_path, pattern) for pattern in settings.exclude_globs
    ):
        return False
    if not settings.include_globs:
        return True
    return any(fnmatch.fnmatch(logical_path, pattern) for pattern in settings.include_globs)


def _file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()
