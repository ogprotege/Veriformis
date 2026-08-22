"""Deterministic transport archives for receipt-bound export packs.

An export-pack archive is a transport wrapper around an already published
verified-export tree.  It contains the tree's exact canonical receipt and every
file bound by that receipt; it does not create a new export plan, receipt,
container renderer, or source-trust grade.
"""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import BinaryIO

from veriformis._archive_transport import (
    CanonicalArchiveError,
    publish_deterministic_archive,
    require_canonical_archive_structure,
    write_deterministic_archive,
)
from veriformis.bundle.finished import _emit_runtime_warning
from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.exports._publication import (
    _inspect_export_directory,
    _verify_export_directory,
)
from veriformis.exports.models import (
    EXPORT_RECEIPT_PATH,
    ExportReceipt,
    SourceTrustGrade,
)
from veriformis.exports.paths import validate_export_path_set
from veriformis.identity import sha256_digest, validate_sha256

EXPORT_PACK_TRANSPORT_PROFILE = "deterministic-export-pack-zip-v1"
EXPORT_PACK_ARCHIVE_SUFFIX = ".vfexport.zip"

_COPY_CHUNK_BYTES = 1024 * 1024
_MAX_EXPORT_RECEIPT_BYTES = 64 * 1024 * 1024
_MAX_EXPORT_PACK_MEMBERS = 4096
_MAX_EXPORT_PACK_DEPTH = 128


@dataclass(frozen=True, slots=True)
class ExportPackArchiveReceipt:
    """Runtime verification/publication facts for one export-pack transport."""

    archive_path: Path
    archive_sha256: str
    archive_size: int
    export_receipt_sha256: str
    export_receipt_id: str
    export_plan_id: str
    output_content_root_sha256: str
    source_trust_grade: SourceTrustGrade
    member_count: int
    durability_warning: str | None = None


def _expected_digest(value: str) -> str:
    try:
        return validate_sha256(value)
    except (TypeError, ValueError) as exc:
        raise ExportVerificationError(
            f"invalid expected export receipt SHA-256: {exc}"
        ) from exc


def _members_from_receipt(receipt: ExportReceipt) -> tuple[str, ...]:
    members = tuple(sorted((*tuple(item.path for item in receipt.files), EXPORT_RECEIPT_PATH)))
    try:
        validate_export_path_set(members, label="export-pack archive members")
    except ValueError as exc:
        raise ExportVerificationError(
            f"invalid export-pack archive member set: {exc}"
        ) from exc
    if len(members) > _MAX_EXPORT_PACK_MEMBERS:
        raise ExportVerificationError("export-pack archive exceeds the member-count limit")
    if any(path.count("/") > _MAX_EXPORT_PACK_DEPTH for path in members):
        raise ExportVerificationError("export-pack archive exceeds the path-depth limit")
    return members


def _require_portable_exact_export(receipt: ExportReceipt) -> None:
    if (
        receipt.export_plan.container_profile.determinism_claim
        != "portable_exact_bytes"
    ):
        raise ExportVerificationError(
            "deterministic export-pack transport requires a "
            "portable_exact_bytes export plan"
        )


def _require_anchored_export_directory(
    export_dir: Path,
    *,
    expected_export_receipt_sha256: str,
) -> ExportReceipt:
    receipt = _inspect_export_directory(export_dir)
    observed_digest = sha256_digest(receipt.canonical_bytes())
    if observed_digest != expected_export_receipt_sha256:
        raise ExportVerificationError(
            "export receipt does not match the separately retained expected digest"
        )
    _require_portable_exact_export(receipt)
    verified_receipt, _ = _verify_export_directory(
        export_dir,
        expected_plan=receipt.export_plan,
    )
    if (
        verified_receipt != receipt
        or verified_receipt.canonical_bytes() != receipt.canonical_bytes()
    ):
        raise ExportVerificationError(
            "verified export directory differs from its anchored receipt"
        )
    _members_from_receipt(verified_receipt)
    return verified_receipt


def _copy_archive_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    destination: Path,
    *,
    expected_size: int,
) -> None:
    observed_size = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(info, mode="r") as source, destination.open("xb") as output:
        while chunk := source.read(_COPY_CHUNK_BYTES):
            observed_size += len(chunk)
            if observed_size > expected_size:
                raise ExportVerificationError(
                    f"export-pack member {info.filename!r} exceeds its receipt size"
                )
            output.write(chunk)
    if observed_size != expected_size:
        raise ExportVerificationError(
            f"export-pack member {info.filename!r} differs from its receipt size"
        )


def _compare_and_hash_open_archive(
    source: BinaryIO,
    canonical: Path,
) -> tuple[str, int]:
    """Compare and hash one descriptor-bound archive in the same read pass."""
    source.seek(0)
    digest = hashlib.sha256()
    observed_size = 0
    with canonical.open("rb") as expected:
        while True:
            source_chunk = source.read(_COPY_CHUNK_BYTES)
            expected_chunk = expected.read(_COPY_CHUNK_BYTES)
            if source_chunk != expected_chunk:
                raise ExportVerificationError(
                    "transport archive bytes are not in canonical deterministic form"
                )
            if not source_chunk:
                break
            digest.update(source_chunk)
            observed_size += len(source_chunk)
    return digest.hexdigest(), observed_size


def _stable_archive_status(status: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _verify_export_pack_archive(
    source: Path,
    source_file: BinaryIO,
    source_status: os.stat_result,
    *,
    expected_export_receipt_sha256: str,
) -> ExportPackArchiveReceipt:
    with tempfile.TemporaryDirectory(prefix="veriformis-export-pack-verify-") as raw:
        temporary = Path(raw)
        extracted = temporary / "export-pack"
        extracted.mkdir()
        with zipfile.ZipFile(source_file, mode="r") as archive:
            try:
                by_name, names = require_canonical_archive_structure(
                    archive,
                    expected_members=None,
                    maximum_members=_MAX_EXPORT_PACK_MEMBERS,
                )
            except CanonicalArchiveError as exc:
                raise ExportVerificationError(str(exc)) from exc
            try:
                validate_export_path_set(
                    names,
                    label="export-pack archive members",
                )
            except ValueError as exc:
                raise ExportVerificationError(
                    f"invalid export-pack archive member set: {exc}"
                ) from exc
            if any(path.count("/") > _MAX_EXPORT_PACK_DEPTH for path in names):
                raise ExportVerificationError(
                    "export-pack archive exceeds the path-depth limit"
                )
            receipt_info = by_name.get(EXPORT_RECEIPT_PATH)
            if receipt_info is None:
                raise ExportVerificationError(
                    "export-pack archive is missing export-receipt.json"
                )
            if receipt_info.file_size > _MAX_EXPORT_RECEIPT_BYTES:
                raise ExportVerificationError(
                    "export-pack receipt exceeds the inspection size limit"
                )
            receipt_bytes = archive.read(receipt_info)
            observed_receipt_digest = sha256_digest(receipt_bytes)
            if observed_receipt_digest != expected_export_receipt_sha256:
                raise ExportVerificationError(
                    "export receipt does not match the separately retained expected digest"
                )
            receipt = ExportReceipt.from_json_bytes(receipt_bytes)
            _require_portable_exact_export(receipt)
            expected_members = _members_from_receipt(receipt)
            if names != expected_members:
                raise ExportVerificationError(
                    "transport archive member set or order is not canonical: "
                    f"expected={list(expected_members)!r}, observed={list(names)!r}"
                )

            expected_sizes = {item.path: item.byte_size for item in receipt.files}
            expected_sizes[EXPORT_RECEIPT_PATH] = len(receipt_bytes)
            for relative_path in expected_members:
                info = by_name[relative_path]
                expected_size = expected_sizes[relative_path]
                if info.file_size != expected_size:
                    raise ExportVerificationError(
                        "export-pack archive size differs from its receipt for "
                        f"{relative_path!r}"
                    )
                destination = extracted.joinpath(*relative_path.split("/"))
                _copy_archive_member(
                    archive,
                    info,
                    destination,
                    expected_size=expected_size,
                )

        observed_receipt, _ = _verify_export_directory(
            extracted,
            expected_plan=receipt.export_plan,
        )
        if (
            observed_receipt != receipt
            or observed_receipt.canonical_bytes() != receipt_bytes
        ):
            raise ExportVerificationError(
                "reconstructed export pack differs from its anchored receipt"
            )
        canonical = temporary / f"canonical{EXPORT_PACK_ARCHIVE_SUFFIX}"
        write_deterministic_archive(
            extracted,
            canonical,
            members=expected_members,
        )
        archive_sha256, archive_size = _compare_and_hash_open_archive(
            source_file,
            canonical,
        )
        final_status = os.fstat(source_file.fileno())
        path_status = os.stat(source, follow_symlinks=False)
        if (
            not stat.S_ISREG(path_status.st_mode)
            or (path_status.st_dev, path_status.st_ino)
            != (final_status.st_dev, final_status.st_ino)
        ):
            raise ExportVerificationError(
                "transport archive path changed during verification"
            )
        if (
            _stable_archive_status(final_status)
            != _stable_archive_status(source_status)
            or archive_size != final_status.st_size
        ):
            raise ExportVerificationError(
                "transport archive changed during verification"
            )

    return ExportPackArchiveReceipt(
        archive_path=source,
        archive_sha256=archive_sha256,
        archive_size=archive_size,
        export_receipt_sha256=expected_export_receipt_sha256,
        export_receipt_id=receipt.export_receipt_id,
        export_plan_id=receipt.export_plan_id,
        output_content_root_sha256=receipt.output_content_root_sha256,
        source_trust_grade=receipt.export_plan.source_trust_grade,
        member_count=len(expected_members),
    )


def verify_export_pack_archive(
    archive_path: str | os.PathLike[str],
    *,
    expected_export_receipt_sha256: str,
) -> ExportPackArchiveReceipt:
    """Verify canonical archive bytes against an external receipt digest."""
    expected_digest = _expected_digest(expected_export_receipt_sha256)
    try:
        source = Path(os.path.abspath(os.fspath(archive_path)))
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(
            os,
            "O_NOFOLLOW",
            0,
        )
        try:
            descriptor = os.open(source, flags)
        except OSError as exc:
            raise ExportVerificationError(
                "transport archive must be a readable real regular file"
            ) from exc
        try:
            source_status = os.fstat(descriptor)
            if not stat.S_ISREG(source_status.st_mode):
                raise ExportVerificationError(
                    "transport archive must be a real regular file"
                )
            with os.fdopen(descriptor, mode="rb", closefd=True) as source_file:
                descriptor = -1
                return _verify_export_pack_archive(
                    source,
                    source_file,
                    source_status,
                    expected_export_receipt_sha256=expected_digest,
                )
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    except ExportVerificationError:
        raise
    except (
        OSError,
        RecursionError,
        TypeError,
        UnicodeError,
        ValueError,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
    ) as exc:
        raise ExportVerificationError(
            f"export-pack archive verification failed: {exc}"
        ) from exc


def write_export_pack_archive(
    export_dir: str | os.PathLike[str],
    target_path: str | os.PathLike[str],
    *,
    expected_export_receipt_sha256: str,
) -> ExportPackArchiveReceipt:
    """Externally anchor, package, verify, and publish one export pack."""
    expected_digest = _expected_digest(expected_export_receipt_sha256)
    try:
        source = Path(os.path.abspath(os.fspath(export_dir)))
    except (TypeError, ValueError) as exc:
        raise ExportContractError(f"invalid export-pack source path: {exc}") from exc
    receipt = _require_anchored_export_directory(
        source,
        expected_export_receipt_sha256=expected_digest,
    )
    members = _members_from_receipt(receipt)
    try:
        publication = publish_deterministic_archive(
            source,
            target_path,
            required_suffix=EXPORT_PACK_ARCHIVE_SUFFIX,
            write_staged=lambda staged: write_deterministic_archive(
                source,
                staged,
                members=members,
            ),
            verify_staged=lambda staged: verify_export_pack_archive(
                staged,
                expected_export_receipt_sha256=expected_digest,
            ),
            emit_warning=lambda message: _emit_runtime_warning(
                message,
                stacklevel=2,
            ),
            require_target_outside_source=True,
        )
    except FileExistsError:
        raise
    except ValueError as exc:
        raise ExportContractError(f"invalid export-pack archive target: {exc}") from exc
    return replace(
        publication.staged_verification,
        archive_path=publication.target_path,
        durability_warning=publication.durability_warning,
    )


__all__ = [
    "EXPORT_PACK_ARCHIVE_SUFFIX",
    "EXPORT_PACK_TRANSPORT_PROFILE",
    "ExportPackArchiveReceipt",
    "verify_export_pack_archive",
    "write_export_pack_archive",
]
