"""Deterministic, immutable transport for a strict finished bundle.

The canonical product remains the closed ``minimal-v1`` directory.  This
module wraps its exact six files in a byte-deterministic ZIP for transport
through Finder and other file managers without relaxing directory verification.
"""

from __future__ import annotations

import errno
import hashlib
import os
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from veriformis.bundle.finished import (
    ATTESTATION_NAME,
    EVALUATION_PATH,
    MANIFEST_NAME,
    PROVENANCE_PATH,
    TRAIN_PATH,
    VALIDATION_PATH,
    BundleVerificationError,
    FinishedBundleManifest,
    VerificationResult,
    _emit_runtime_warning,
)
from veriformis.bundle.verifier import verify_finished_bundle
from veriformis.identity import sha256_digest, validate_sha256

_TRANSPORT_MEMBERS = tuple(
    sorted(
        (
            ATTESTATION_NAME,
            EVALUATION_PATH,
            MANIFEST_NAME,
            PROVENANCE_PATH,
            TRAIN_PATH,
            VALIDATION_PATH,
        )
    )
)
_FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_COPY_CHUNK_BYTES = 1024 * 1024
_MAX_METADATA_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class BundleArchiveReceipt:
    """Verification and publication facts for one transport archive."""

    archive_path: Path
    archive_sha256: str
    archive_size: int
    manifest_sha256: str
    member_count: int
    verification: VerificationResult
    durability_warning: str | None = None


def _zip_info(relative_path: str) -> zipfile.ZipInfo:
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


def _write_deterministic_archive(bundle: Path, archive_path: Path) -> None:
    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_STORED,
        allowZip64=True,
        strict_timestamps=True,
    ) as archive:
        archive.comment = b""
        for relative_path in _TRANSPORT_MEMBERS:
            source_path = bundle.joinpath(*relative_path.split("/"))
            info = _zip_info(relative_path)
            info.file_size = source_path.stat().st_size
            with source_path.open("rb") as source, archive.open(
                info,
                mode="w",
                force_zip64=True,
            ) as destination:
                while chunk := source.read(_COPY_CHUNK_BYTES):
                    destination.write(chunk)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_COPY_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _files_equal(first: Path, second: Path) -> bool:
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


def _require_archive_structure(
    archive: zipfile.ZipFile,
) -> tuple[dict[str, zipfile.ZipInfo], FinishedBundleManifest, bytes]:
    if archive.comment:
        raise BundleVerificationError("transport archive comment is not allowed")
    infos = archive.infolist()
    names = tuple(info.filename for info in infos)
    if names != _TRANSPORT_MEMBERS:
        raise BundleVerificationError(
            "transport archive member set or order is not canonical: "
            f"expected={list(_TRANSPORT_MEMBERS)!r}, observed={list(names)!r}"
        )
    if len(set(names)) != len(names):
        raise BundleVerificationError("transport archive contains duplicate members")
    by_name = dict(zip(names, infos, strict=True))
    for info in infos:
        if info.is_dir():
            raise BundleVerificationError(
                f"transport archive contains directory member {info.filename!r}"
            )
        if info.compress_type != zipfile.ZIP_STORED:
            raise BundleVerificationError(
                "transport archive members must use deterministic stored encoding"
            )
        if info.flag_bits & 0x1:
            raise BundleVerificationError("transport archive encryption is not allowed")
        if info.file_size != info.compress_size:
            raise BundleVerificationError(
                "transport archive stored member sizes are inconsistent"
            )
        expected_info = _zip_info(info.filename)
        observed_mode = info.external_attr >> 16
        if not stat.S_ISREG(observed_mode):
            raise BundleVerificationError(
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
            raise BundleVerificationError(
                f"transport archive metadata is not canonical for {info.filename!r}"
            )

    manifest_info = by_name[MANIFEST_NAME]
    if manifest_info.file_size > _MAX_METADATA_BYTES:
        raise BundleVerificationError("transport manifest exceeds the metadata limit")
    manifest_bytes = archive.read(manifest_info)
    manifest = FinishedBundleManifest.from_json_bytes(manifest_bytes)
    expected_sizes = {file.path: file.size for file in manifest.files}
    expected_sizes[MANIFEST_NAME] = len(manifest_bytes)
    attestation_info = by_name[ATTESTATION_NAME]
    if attestation_info.file_size > _MAX_METADATA_BYTES:
        raise BundleVerificationError("transport attestation exceeds the metadata limit")
    for relative_path, expected_size in expected_sizes.items():
        if by_name[relative_path].file_size != expected_size:
            raise BundleVerificationError(
                f"transport archive size differs from the manifest for {relative_path!r}"
            )
    return by_name, manifest, manifest_bytes


def verify_bundle_archive(
    archive_path: str | os.PathLike[str],
    *,
    expected_manifest_sha256: str,
) -> BundleArchiveReceipt:
    """Verify canonical ZIP bytes and the exact externally anchored bundle."""
    try:
        expected_digest = validate_sha256(expected_manifest_sha256)
        source = Path(os.path.abspath(os.fspath(archive_path)))
        if not source.is_file() or source.is_symlink():
            raise BundleVerificationError(
                "transport archive must be a real regular file"
            )
        with tempfile.TemporaryDirectory(prefix="veriformis-transport-verify-") as raw:
            temporary = Path(raw)
            extracted = temporary / "bundle.vfbundle"
            extracted.mkdir()
            (extracted / "data").mkdir()
            (extracted / "metadata").mkdir()
            with zipfile.ZipFile(source, mode="r") as archive:
                by_name, _, manifest_bytes = _require_archive_structure(archive)
                if sha256_digest(manifest_bytes) != expected_digest:
                    raise BundleVerificationError(
                        "finished bundle manifest does not match the external digest"
                    )
                for relative_path in _TRANSPORT_MEMBERS:
                    destination = extracted.joinpath(*relative_path.split("/"))
                    with archive.open(by_name[relative_path], mode="r") as member, (
                        destination.open("xb")
                    ) as output:
                        while chunk := member.read(_COPY_CHUNK_BYTES):
                            output.write(chunk)

            verification = verify_finished_bundle(
                extracted,
                expected_manifest_sha256=expected_digest,
            )
            canonical = temporary / "canonical.vfbundle.zip"
            _write_deterministic_archive(extracted, canonical)
            if not _files_equal(source, canonical):
                raise BundleVerificationError(
                    "transport archive bytes are not in canonical deterministic form"
                )

        return BundleArchiveReceipt(
            archive_path=source,
            archive_sha256=_sha256_file(source),
            archive_size=source.stat().st_size,
            manifest_sha256=expected_digest,
            member_count=len(_TRANSPORT_MEMBERS),
            verification=verification,
        )
    except BundleVerificationError:
        raise
    except (OSError, TypeError, UnicodeError, ValueError, zipfile.BadZipFile) as exc:
        raise BundleVerificationError(
            f"transport archive verification failed: {exc}"
        ) from exc


def write_bundle_archive(
    bundle_dir: str | os.PathLike[str],
    target_path: str | os.PathLike[str],
    *,
    expected_manifest_sha256: str,
) -> BundleArchiveReceipt:
    """Externally verify, deterministically package, and publish without replace."""
    expected_digest = validate_sha256(expected_manifest_sha256)
    bundle = Path(os.path.abspath(os.fspath(bundle_dir)))
    verification = verify_finished_bundle(
        bundle,
        expected_manifest_sha256=expected_digest,
    )
    if verification.trust_grade != "external_digest":
        raise BundleVerificationError(
            "transport packaging requires external-digest bundle verification"
        )

    target = Path(os.path.abspath(os.fspath(target_path)))
    if not target.name.endswith(".vfbundle.zip"):
        raise ValueError("transport archive must end with '.vfbundle.zip'")
    parent = target.parent
    parent_status = parent.lstat()
    if not stat.S_ISDIR(parent_status.st_mode) or stat.S_ISLNK(parent_status.st_mode):
        raise ValueError("transport archive parent must be a real directory")
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
        _write_deterministic_archive(bundle, staged)
        with staged.open("rb") as handle:
            os.fsync(handle.fileno())
        staged_receipt = verify_bundle_archive(
            staged,
            expected_manifest_sha256=expected_digest,
        )
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
        # The archive is already visible: durability notes are advisory and
        # must never let a warnings filter unwind the successful publication.
        _emit_runtime_warning(durability_warning, stacklevel=2)

    return BundleArchiveReceipt(
        archive_path=target,
        archive_sha256=staged_receipt.archive_sha256,
        archive_size=staged_receipt.archive_size,
        manifest_sha256=staged_receipt.manifest_sha256,
        member_count=staged_receipt.member_count,
        verification=staged_receipt.verification,
        durability_warning=durability_warning,
    )


__all__ = [
    "BundleArchiveReceipt",
    "verify_bundle_archive",
    "write_bundle_archive",
]
