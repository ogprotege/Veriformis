"""Deterministic, immutable transport for a strict finished bundle.

The canonical product remains the closed ``minimal-v1`` directory.  This
module wraps its exact six files in a byte-deterministic ZIP for transport
through Finder and other file managers without relaxing directory verification.
"""

from __future__ import annotations

import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from veriformis._archive_transport import (
    CanonicalArchiveError,
    canonical_zip_info,
    files_equal,
    publish_deterministic_archive,
    require_canonical_archive_structure,
    sha256_file,
    write_deterministic_archive,
)

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
_MAX_METADATA_BYTES = 16 * 1024 * 1024
_COPY_CHUNK_BYTES = 1024 * 1024


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
    """Compatibility seam for the historical private metadata helper."""
    return canonical_zip_info(relative_path)


def _write_deterministic_archive(bundle: Path, archive_path: Path) -> None:
    """Compatibility seam used by existing transport fault-injection tests."""
    write_deterministic_archive(
        bundle,
        archive_path,
        members=_TRANSPORT_MEMBERS,
    )


def _sha256_file(path: Path) -> str:
    return sha256_file(path)


def _files_equal(first: Path, second: Path) -> bool:
    return files_equal(first, second)


def _require_archive_structure(
    archive: zipfile.ZipFile,
) -> tuple[dict[str, zipfile.ZipInfo], FinishedBundleManifest, bytes]:
    try:
        by_name, _ = require_canonical_archive_structure(
            archive,
            expected_members=_TRANSPORT_MEMBERS,
        )
    except CanonicalArchiveError as exc:
        raise BundleVerificationError(str(exc)) from exc

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

    publication = publish_deterministic_archive(
        bundle,
        target_path,
        required_suffix=".vfbundle.zip",
        write_staged=lambda staged: _write_deterministic_archive(bundle, staged),
        verify_staged=lambda staged: verify_bundle_archive(
            staged,
            expected_manifest_sha256=expected_digest,
        ),
        emit_warning=lambda message: _emit_runtime_warning(message, stacklevel=2),
    )
    target = publication.target_path
    staged_receipt = publication.staged_verification

    return BundleArchiveReceipt(
        archive_path=target,
        archive_sha256=staged_receipt.archive_sha256,
        archive_size=staged_receipt.archive_size,
        manifest_sha256=staged_receipt.manifest_sha256,
        member_count=staged_receipt.member_count,
        verification=staged_receipt.verification,
        durability_warning=publication.durability_warning,
    )


__all__ = [
    "BundleArchiveReceipt",
    "verify_bundle_archive",
    "write_bundle_archive",
]
