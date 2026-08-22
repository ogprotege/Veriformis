"""Private deterministic-ZIP codec and no-replace publication machinery.

The finished-bundle and export-pack transports have different trust anchors
and inner-tree verifiers, but they intentionally share one byte-level archive
contract.  This module owns that common contract without exposing a plugin or
registration boundary.
"""

from __future__ import annotations

import errno
import hashlib
import os
import stat
import tempfile
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

_FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_COPY_CHUNK_BYTES = 1024 * 1024

_VerifiedArchive = TypeVar("_VerifiedArchive")


class CanonicalArchiveError(Exception):
    """A ZIP is not the one canonical deterministic transport encoding."""


@dataclass(frozen=True, slots=True)
class ArchivePublication(Generic[_VerifiedArchive]):
    """One verified staged archive after atomic no-replace publication."""

    target_path: Path
    staged_verification: _VerifiedArchive
    durability_warning: str | None


def canonical_zip_info(relative_path: str) -> zipfile.ZipInfo:
    """Build the unique v1 metadata record for one regular-file member."""
    info = zipfile.ZipInfo(relative_path, date_time=_FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.create_version = 45
    info.extract_version = 45
    info.external_attr = (stat.S_IFREG | 0o444) << 16
    info.internal_attr = 0
    info.extra = b""
    info.comment = b""
    return info


def write_deterministic_archive(
    source_root: Path,
    archive_path: Path,
    *,
    members: Sequence[str],
) -> None:
    """Stream one exact sorted source tree into the canonical ZIP encoding."""
    checked_members = tuple(members)
    if (
        not checked_members
        or checked_members != tuple(sorted(checked_members))
        or len(checked_members) != len(set(checked_members))
    ):
        raise ValueError("transport archive members must be non-empty, sorted, and unique")
    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_STORED,
        allowZip64=True,
        strict_timestamps=True,
    ) as archive:
        archive.comment = b""
        for relative_path in checked_members:
            source_path = source_root.joinpath(*relative_path.split("/"))
            info = canonical_zip_info(relative_path)
            info.file_size = source_path.stat().st_size
            with source_path.open("rb") as source, archive.open(
                info,
                mode="w",
                force_zip64=True,
            ) as destination:
                while chunk := source.read(_COPY_CHUNK_BYTES):
                    destination.write(chunk)


def require_canonical_archive_structure(
    archive: zipfile.ZipFile,
    *,
    expected_members: Sequence[str] | None,
    maximum_members: int | None = None,
) -> tuple[dict[str, zipfile.ZipInfo], tuple[str, ...]]:
    """Validate common canonical ZIP structure without interpreting payloads."""
    if archive.comment:
        raise CanonicalArchiveError("transport archive comment is not allowed")
    infos = archive.infolist()
    if maximum_members is not None and len(infos) > maximum_members:
        raise CanonicalArchiveError("transport archive exceeds the member-count limit")
    names = tuple(info.filename for info in infos)
    if expected_members is not None:
        expected = tuple(expected_members)
        if names != expected:
            raise CanonicalArchiveError(
                "transport archive member set or order is not canonical: "
                f"expected={list(expected)!r}, observed={list(names)!r}"
            )
    elif names != tuple(sorted(names)):
        raise CanonicalArchiveError(
            "transport archive members are not in canonical sorted order"
        )
    if len(set(names)) != len(names):
        raise CanonicalArchiveError("transport archive contains duplicate members")
    by_name = dict(zip(names, infos, strict=True))
    for info in infos:
        if info.is_dir():
            raise CanonicalArchiveError(
                f"transport archive contains directory member {info.filename!r}"
            )
        if info.compress_type != zipfile.ZIP_STORED:
            raise CanonicalArchiveError(
                "transport archive members must use deterministic stored encoding"
            )
        if info.flag_bits & 0x1:
            raise CanonicalArchiveError(
                "transport archive encryption is not allowed"
            )
        if info.file_size != info.compress_size:
            raise CanonicalArchiveError(
                "transport archive stored member sizes are inconsistent"
            )
        expected_info = canonical_zip_info(info.filename)
        observed_mode = info.external_attr >> 16
        if not stat.S_ISREG(observed_mode):
            raise CanonicalArchiveError(
                f"transport archive member {info.filename!r} is not a regular file"
            )
        if (
            info.date_time != expected_info.date_time
            or info.create_system != expected_info.create_system
            or info.create_version != expected_info.create_version
            or info.extract_version != expected_info.extract_version
            or info.external_attr != expected_info.external_attr
            or info.internal_attr != expected_info.internal_attr
            or info.extra
            or info.comment
        ):
            raise CanonicalArchiveError(
                f"transport archive metadata is not canonical for {info.filename!r}"
            )
    return by_name, names


def sha256_file(path: Path) -> str:
    """Hash a file without retaining it in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_COPY_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def files_equal(first: Path, second: Path) -> bool:
    """Compare two files exactly without retaining either complete file."""
    if first.stat().st_size != second.stat().st_size:
        return False
    with first.open("rb") as left, second.open("rb") as right:
        while True:
            left_chunk = left.read(_COPY_CHUNK_BYTES)
            right_chunk = right.read(_COPY_CHUNK_BYTES)
            if left_chunk != right_chunk:
                return False
            if not left_chunk:
                return True


def _target_outside_source(source_root: Path, parent: Path) -> bool:
    try:
        source = source_root.resolve(strict=True)
        destination_parent = parent.resolve(strict=True)
        return os.path.commonpath((destination_parent, source)) != os.fspath(source)
    except ValueError:
        return True


def publish_deterministic_archive(
    source_root: Path,
    target_path: str | os.PathLike[str],
    *,
    required_suffix: str,
    write_staged: Callable[[Path], None],
    verify_staged: Callable[[Path], _VerifiedArchive],
    emit_warning: Callable[[str], None],
    require_target_outside_source: bool = False,
) -> ArchivePublication[_VerifiedArchive]:
    """Stage, verify, and atomically publish one archive without replacement."""
    target = Path(os.path.abspath(os.fspath(target_path)))
    if not target.name.endswith(required_suffix):
        raise ValueError(f"transport archive must end with {required_suffix!r}")
    parent = target.parent
    parent_status = parent.lstat()
    if not stat.S_ISDIR(parent_status.st_mode) or stat.S_ISLNK(parent_status.st_mode):
        raise ValueError("transport archive parent must be a real directory")
    if require_target_outside_source and not _target_outside_source(
        source_root,
        parent,
    ):
        raise ValueError("transport archive target cannot be inside its source tree")
    if os.path.lexists(target):
        raise FileExistsError(
            errno.EEXIST,
            "transport archive target already exists",
            target,
        )

    descriptor, staged_name = tempfile.mkstemp(
        prefix=f".{target.name}.tmp-",
        dir=parent,
    )
    os.close(descriptor)
    staged = Path(staged_name)
    published = False
    publication_warnings: list[str] = []
    try:
        write_staged(staged)
        with staged.open("rb") as handle:
            os.fsync(handle.fileno())
        staged_verification = verify_staged(staged)
        os.link(staged, target, follow_symlinks=False)
        published = True
        try:
            staged.unlink()
        except OSError as exc:
            publication_warnings.append(
                f"transport archive {target} is visible, but its staging link "
                f"could not be removed: {exc}"
            )
    finally:
        if not published and os.path.lexists(staged):
            staged.unlink()

    try:
        descriptor = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        publication_warnings.append(
            f"transport archive {target} is visible, but its parent directory "
            f"could not be synced: {exc}"
        )

    durability_warning = "; ".join(publication_warnings) or None
    if durability_warning is not None:
        emit_warning(durability_warning)
    return ArchivePublication(
        target_path=target,
        staged_verification=staged_verification,
        durability_warning=durability_warning,
    )


__all__: list[str] = []
