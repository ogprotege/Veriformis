"""Independent adversarial tests for receipt-anchored export-pack transport.

These tests deliberately exercise the public archive boundary rather than the
private ZIP helpers.  The canonical generic export remains a directory; the
``.vfexport.zip`` value is an immutable transport wrapper over that exact tree.
"""

from __future__ import annotations

import base64
import errno
import json
import os
import shutil
import stat
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from veriformis.bundle.transport import (
    BundleArchiveReceipt,
    verify_bundle_archive,
    write_bundle_archive,
)
from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.exports import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportDryRunRequest,
    ExportExecuteRequest,
    ExportPlan,
    ExportPublicationOutcome,
    ExportService,
)
from veriformis.exports.archive import (
    EXPORT_PACK_ARCHIVE_SUFFIX,
    EXPORT_PACK_TRANSPORT_PROFILE,
    ExportPackArchiveReceipt,
    verify_export_pack_archive,
    write_export_pack_archive,
)
from veriformis.exports import archive as archive_module
from veriformis.identity import sha256_digest


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "regressions"
    / "fixtures"
    / "phase3"
    / "pre-taxonomy-full-text.vfbundle.json"
)
EXPECTED_MANIFEST_SHA256 = (
    "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"
)
LEGACY_ARCHIVE_SHA256 = (
    "d17217ace8e8929ce4d41f88b3a2bca54b6976ed95b9c7dc42122e97bdfb9980"
)
LEGACY_ARCHIVE_SIZE = 26287
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FIXED_EXTERNAL_ATTR = (stat.S_IFREG | 0o444) << 16


@dataclass(frozen=True, slots=True)
class _PublishedExport:
    bundle: Path
    root: Path
    plan: ExportPlan
    publication: ExportPublicationOutcome
    receipt_bytes: bytes
    receipt_sha256: str


def _materialize_bundle(root: Path) -> Path:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bundle = root / "source.vfbundle"
    for relative_path, encoded in sorted(fixture["files_base64"].items()):
        data = base64.b64decode(encoded, validate=True)
        assert sha256_digest(data) == fixture["file_sha256"][relative_path]
        target = bundle.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return bundle


def _selection(
    bundle: Path,
    *,
    source_trust_policy: str,
) -> dict[str, object]:
    return {
        "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA,
        "bundle": str(bundle),
        "container_id": "split-jsonl-directory",
        "container_version": 1,
        "consumer_id": None,
        "consumer_profile_version": None,
        "source_trust_policy": source_trust_policy,
        "expected_manifest_sha256": (
            EXPECTED_MANIFEST_SHA256
            if source_trust_policy == "require_external_digest"
            else None
        ),
        "overwrite_policy": "refuse",
    }


def _publish_export(
    root: Path,
    *,
    source_trust_policy: str = "require_external_digest",
    destination_name: str = "generic-export",
) -> _PublishedExport:
    bundle = _materialize_bundle(root)
    service = ExportService()
    selection = _selection(bundle, source_trust_policy=source_trust_policy)
    plan = service.dry_run_export(
        ExportDryRunRequest(operation="dry_run", **selection)
    )
    destination = root / destination_name
    publication = service.execute_export(
        ExportExecuteRequest(
            operation="execute",
            destination_root=str(destination),
            expected_export_plan_id=plan.export_plan_id,
            **selection,
        )
    )
    receipt_bytes = (destination / "export-receipt.json").read_bytes()
    assert receipt_bytes == publication.receipt.canonical_bytes()
    return _PublishedExport(
        bundle=bundle,
        root=destination,
        plan=plan,
        publication=publication,
        receipt_bytes=receipt_bytes,
        receipt_sha256=sha256_digest(receipt_bytes),
    )


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _write_pack(
    published: _PublishedExport,
    target: Path,
) -> ExportPackArchiveReceipt:
    return write_export_pack_archive(
        published.root,
        target,
        expected_export_receipt_sha256=published.receipt_sha256,
    )


def _archive_entries(path: Path) -> tuple[tuple[str, bytes], ...]:
    with zipfile.ZipFile(path, mode="r") as archive:
        return tuple((info.filename, archive.read(info)) for info in archive.infolist())


def _canonical_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.create_version = 45
    info.extract_version = 45
    info.external_attr = FIXED_EXTERNAL_ATTR
    info.internal_attr = 0
    info.extra = b""
    info.comment = b""
    return info


def _rewrite_archive(
    target: Path,
    entries: tuple[tuple[str, bytes], ...],
    *,
    mutate_info=None,
    archive_comment: bytes = b"",
) -> None:
    with zipfile.ZipFile(
        target,
        mode="w",
        compression=zipfile.ZIP_STORED,
        allowZip64=True,
        strict_timestamps=True,
    ) as archive:
        archive.comment = archive_comment
        for index, (name, data) in enumerate(entries):
            info = _canonical_info(name)
            if mutate_info is not None:
                mutate_info(index, info)
            info.file_size = len(data)
            with archive.open(info, mode="w", force_zip64=True) as output:
                output.write(data)


def _patch_first_zip_version_field(path: Path, *, field: str) -> None:
    """Mutate a version word that ``zipfile`` otherwise normalizes on write."""
    data = bytearray(path.read_bytes())
    local = data.index(b"PK\x03\x04")
    central = data.index(b"PK\x01\x02")
    replacement = (20).to_bytes(2, "little")
    if field == "create-version":
        # Central-directory "version made by" retains the canonical Unix
        # system byte while changing only the low version byte.
        data[central + 4] = 20
    else:
        assert field == "extract-version"
        data[local + 4 : local + 6] = replacement
        data[central + 6 : central + 8] = replacement
    path.write_bytes(data)


def _patch_first_zip_flag(path: Path, *, flag: int) -> None:
    """Set one general-purpose flag in the first local and central records."""
    data = bytearray(path.read_bytes())
    local = data.index(b"PK\x03\x04")
    central = data.index(b"PK\x01\x02")
    for offset in (local + 6, central + 8):
        observed = int.from_bytes(data[offset : offset + 2], "little")
        data[offset : offset + 2] = (observed | flag).to_bytes(2, "little")
    path.write_bytes(data)


def _patch_first_central_uncompressed_size(path: Path) -> None:
    """Make the first central-directory size disagree with its stored size."""
    data = bytearray(path.read_bytes())
    central = data.index(b"PK\x01\x02")
    offset = central + 24
    observed = int.from_bytes(data[offset : offset + 4], "little")
    data[offset : offset + 4] = (observed + 1).to_bytes(4, "little")
    path.write_bytes(data)


def _flip_stored_payload_byte_without_updating_crc(path: Path) -> None:
    """Corrupt one stored member body while retaining its declared CRC."""
    data = bytearray(path.read_bytes())
    with zipfile.ZipFile(path, mode="r") as archive:
        info = next(item for item in archive.infolist() if item.file_size)
    local = info.header_offset
    name_size = int.from_bytes(data[local + 26 : local + 28], "little")
    extra_size = int.from_bytes(data[local + 28 : local + 30], "little")
    payload = local + 30 + name_size + extra_size
    data[payload] ^= 1
    path.write_bytes(data)


def _valid_archive(tmp_path: Path) -> tuple[_PublishedExport, Path]:
    published = _publish_export(tmp_path)
    archive = tmp_path / f"pack{EXPORT_PACK_ARCHIVE_SUFFIX}"
    _write_pack(published, archive)
    return published, archive


def test_export_pack_public_api_and_runtime_receipt_shape_are_frozen(tmp_path: Path):
    published, archive = _valid_archive(tmp_path)
    receipt = verify_export_pack_archive(
        archive,
        expected_export_receipt_sha256=published.receipt_sha256,
    )

    assert EXPORT_PACK_TRANSPORT_PROFILE == "deterministic-export-pack-zip-v1"
    assert EXPORT_PACK_ARCHIVE_SUFFIX == ".vfexport.zip"
    assert tuple(ExportPackArchiveReceipt.__dataclass_fields__) == (
        "archive_path",
        "archive_sha256",
        "archive_size",
        "export_receipt_sha256",
        "export_receipt_id",
        "export_plan_id",
        "output_content_root_sha256",
        "source_trust_grade",
        "member_count",
        "durability_warning",
    )
    assert receipt.archive_path == archive
    assert receipt.archive_sha256 == sha256_digest(archive.read_bytes())
    assert receipt.archive_size == archive.stat().st_size
    assert receipt.export_receipt_sha256 == published.receipt_sha256
    assert receipt.export_receipt_id == published.publication.receipt.export_receipt_id
    assert receipt.export_plan_id == published.plan.export_plan_id
    assert (
        receipt.output_content_root_sha256
        == published.publication.receipt.output_content_root_sha256
    )
    assert receipt.source_trust_grade == "external_digest"
    assert receipt.member_count == len(_tree_bytes(published.root))
    assert receipt.durability_warning is None


def test_packaging_preserves_exact_export_plan_receipt_and_directory(tmp_path: Path):
    published = _publish_export(tmp_path)
    before_tree = _tree_bytes(published.root)
    before_plan = published.plan.canonical_bytes()
    before_receipt = published.publication.receipt.canonical_bytes()
    before_verification = published.publication.verification.canonical_bytes()
    archive = tmp_path / f"preserved{EXPORT_PACK_ARCHIVE_SUFFIX}"

    written = _write_pack(published, archive)
    verified = verify_export_pack_archive(
        archive,
        expected_export_receipt_sha256=published.receipt_sha256,
    )

    assert _tree_bytes(published.root) == before_tree
    assert published.plan.canonical_bytes() == before_plan
    assert published.publication.receipt.canonical_bytes() == before_receipt
    assert published.publication.verification.canonical_bytes() == before_verification
    assert written.export_plan_id == published.plan.export_plan_id
    assert written.export_receipt_id == published.publication.receipt.export_receipt_id
    assert verified.export_plan_id == written.export_plan_id
    assert verified.export_receipt_id == written.export_receipt_id
    assert verified.archive_sha256 == written.archive_sha256


def test_archive_bytes_ignore_source_root_mode_mtime_and_enumeration(tmp_path: Path):
    published = _publish_export(tmp_path)
    copied = tmp_path / "copied-export"
    shutil.copytree(published.root, copied)
    for index, path in enumerate(sorted(copied.rglob("*"))):
        os.utime(path, ns=(1_000_000_000 + index, 2_000_000_000 + index))
        if path.is_file():
            path.chmod(0o600)

    first = tmp_path / f"first{EXPORT_PACK_ARCHIVE_SUFFIX}"
    second = tmp_path / f"second{EXPORT_PACK_ARCHIVE_SUFFIX}"
    _write_pack(published, first)
    second_receipt = write_export_pack_archive(
        copied,
        second,
        expected_export_receipt_sha256=published.receipt_sha256,
    )

    assert first.read_bytes() == second.read_bytes()
    assert sha256_digest(first.read_bytes()) == second_receipt.archive_sha256


def test_archive_has_exact_sorted_members_and_canonical_zip_metadata(tmp_path: Path):
    published, archive_path = _valid_archive(tmp_path)
    expected_tree = _tree_bytes(published.root)

    with zipfile.ZipFile(archive_path, mode="r") as archive:
        infos = archive.infolist()
        assert archive.comment == b""
        assert tuple(info.filename for info in infos) == tuple(sorted(expected_tree))
        for info in infos:
            assert info.filename in expected_tree
            assert info.date_time == FIXED_TIMESTAMP
            assert info.compress_type == zipfile.ZIP_STORED
            assert info.create_system == 3
            assert info.create_version == 45
            assert info.extract_version == 45
            assert info.external_attr == FIXED_EXTERNAL_ATTR
            assert info.internal_attr == 0
            assert info.flag_bits == 0
            assert info.extra == b""
            assert info.comment == b""
            assert not info.is_dir()
            assert info.file_size == len(expected_tree[info.filename])
            assert info.compress_size == info.file_size
            assert archive.read(info) == expected_tree[info.filename]


def test_self_consistent_source_trust_is_preserved_not_upgraded(tmp_path: Path):
    published = _publish_export(
        tmp_path,
        source_trust_policy="allow_self_consistent",
    )
    assert published.plan.source_trust_grade == "self_consistent"
    archive = tmp_path / f"lower-trust{EXPORT_PACK_ARCHIVE_SUFFIX}"

    written = _write_pack(published, archive)
    verified = verify_export_pack_archive(
        archive,
        expected_export_receipt_sha256=published.receipt_sha256,
    )

    assert written.source_trust_grade == "self_consistent"
    assert verified.source_trust_grade == "self_consistent"


def test_wrong_external_receipt_anchor_refuses_write_without_target(tmp_path: Path):
    published = _publish_export(tmp_path)
    target = tmp_path / f"wrong-anchor{EXPORT_PACK_ARCHIVE_SUFFIX}"

    with pytest.raises(ExportVerificationError):
        write_export_pack_archive(
            published.root,
            target,
            expected_export_receipt_sha256=sha256_digest(b"wrong receipt"),
        )

    assert not target.exists()


def test_wrong_external_receipt_anchor_refuses_archive_verification(tmp_path: Path):
    _, archive = _valid_archive(tmp_path)

    with pytest.raises(ExportVerificationError):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=sha256_digest(b"wrong receipt"),
        )


@pytest.mark.parametrize(
    "malformed_anchor",
    (
        "",
        "0" * 63,
        "0" * 65,
        "A" * 64,
        "not-a-digest",
    ),
)
def test_malformed_external_anchor_fails_before_archive_target_access(
    tmp_path: Path,
    malformed_anchor: str,
):
    published = _publish_export(tmp_path)
    missing_parent = tmp_path / "missing-parent"
    target = missing_parent / f"pack{EXPORT_PACK_ARCHIVE_SUFFIX}"

    with pytest.raises(ExportVerificationError):
        write_export_pack_archive(
            published.root,
            target,
            expected_export_receipt_sha256=malformed_anchor,
        )

    assert not missing_parent.exists()


@pytest.mark.parametrize("mutation", ("missing", "extra", "duplicate", "reordered"))
def test_verifier_rejects_noncanonical_member_sets_and_order(
    tmp_path: Path,
    mutation: str,
):
    published, archive = _valid_archive(tmp_path)
    entries = _archive_entries(archive)
    if mutation == "missing":
        changed = entries[:-1]
    elif mutation == "extra":
        changed = (*entries, ("unexpected.txt", b"unexpected"))
    elif mutation == "duplicate":
        changed = (*entries, entries[0])
    else:
        changed = tuple(reversed(entries))

    if mutation == "duplicate":
        with pytest.warns(UserWarning):
            _rewrite_archive(archive, changed)
    else:
        _rewrite_archive(archive, changed)

    with pytest.raises(ExportVerificationError):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=published.receipt_sha256,
        )


def test_verifier_rejects_payload_tamper_under_canonical_zip_metadata(tmp_path: Path):
    published, archive = _valid_archive(tmp_path)
    entries = list(_archive_entries(archive))
    index = next(i for i, (name, _) in enumerate(entries) if name != "export-receipt.json")
    name, data = entries[index]
    assert data
    entries[index] = (name, bytes([data[0] ^ 1]) + data[1:])
    _rewrite_archive(archive, tuple(entries))

    with pytest.raises(ExportVerificationError):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=published.receipt_sha256,
        )


def test_verifier_rejects_crc_failure(tmp_path: Path):
    published, archive = _valid_archive(tmp_path)
    _flip_stored_payload_byte_without_updating_crc(archive)

    with pytest.raises(ExportVerificationError):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=published.receipt_sha256,
        )


def test_verifier_rejects_encrypted_member_flag(tmp_path: Path):
    published, archive = _valid_archive(tmp_path)
    _patch_first_zip_flag(archive, flag=0x1)

    with pytest.raises(ExportVerificationError, match="encryption"):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=published.receipt_sha256,
        )


def test_verifier_rejects_declared_size_disagreement(tmp_path: Path):
    published, archive = _valid_archive(tmp_path)
    _patch_first_central_uncompressed_size(archive)

    with pytest.raises(ExportVerificationError, match="sizes are inconsistent"):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=published.receipt_sha256,
        )


@pytest.mark.parametrize("corruption", ("non-zip", "truncated"))
def test_verifier_rejects_malformed_archive_bytes(
    tmp_path: Path,
    corruption: str,
):
    published, archive = _valid_archive(tmp_path)
    original = archive.read_bytes()
    archive.write_bytes(
        b"not a ZIP archive"
        if corruption == "non-zip"
        else original[: len(original) // 2]
    )

    with pytest.raises(ExportVerificationError):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=published.receipt_sha256,
        )


@pytest.mark.parametrize("position", ("prefix", "suffix"))
def test_verifier_rejects_noncanonical_bytes_outside_zip_records(
    tmp_path: Path,
    position: str,
):
    published, archive = _valid_archive(tmp_path)
    original = archive.read_bytes()
    archive.write_bytes(
        b"noncanonical" + original
        if position == "prefix"
        else original + b"noncanonical"
    )

    with pytest.raises(ExportVerificationError):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=published.receipt_sha256,
        )


@pytest.mark.parametrize(
    "unsafe_name",
    (
        "../escape",
        "/absolute",
        "C:/drive-path",
        "data\\backslash",
        "wrapper/",
        "DATA/TRAIN.JSONL",
    ),
)
def test_verifier_rejects_unsafe_extra_member_names(
    tmp_path: Path,
    unsafe_name: str,
):
    published, archive = _valid_archive(tmp_path)
    entries = (*_archive_entries(archive), (unsafe_name, b"unsafe"))
    _rewrite_archive(archive, entries)

    with pytest.raises(ExportVerificationError):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=published.receipt_sha256,
        )


@pytest.mark.parametrize(
    "metadata_mutation",
    (
        "timestamp",
        "compression",
        "create-system",
        "create-version",
        "extract-version",
        "mode",
        "internal-attr",
        "extra",
        "member-comment",
        "symlink",
    ),
)
def test_verifier_rejects_noncanonical_member_metadata(
    tmp_path: Path,
    metadata_mutation: str,
):
    published, archive = _valid_archive(tmp_path)
    entries = _archive_entries(archive)

    def mutate(index: int, info: zipfile.ZipInfo) -> None:
        if index != 0:
            return
        if metadata_mutation == "timestamp":
            info.date_time = (1981, 1, 1, 0, 0, 0)
        elif metadata_mutation == "compression":
            info.compress_type = zipfile.ZIP_DEFLATED
        elif metadata_mutation == "create-system":
            info.create_system = 0
        elif metadata_mutation in {"create-version", "extract-version"}:
            # Raw header mutation follows the canonical rewrite below because
            # ``zipfile`` forces both fields back to 45 for force-ZIP64 writes.
            pass
        elif metadata_mutation == "mode":
            info.external_attr = (stat.S_IFREG | 0o644) << 16
        elif metadata_mutation == "internal-attr":
            info.internal_attr = 1
        elif metadata_mutation == "extra":
            info.extra = b"\x00\x00\x00\x00"
        elif metadata_mutation == "member-comment":
            info.comment = b"comment"
        else:
            info.external_attr = (stat.S_IFLNK | 0o777) << 16

    _rewrite_archive(archive, entries, mutate_info=mutate)
    if metadata_mutation in {"create-version", "extract-version"}:
        _patch_first_zip_version_field(archive, field=metadata_mutation)

    with pytest.raises(ExportVerificationError):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=published.receipt_sha256,
        )


def test_verifier_rejects_archive_comment(tmp_path: Path):
    published, archive = _valid_archive(tmp_path)
    _rewrite_archive(
        archive,
        _archive_entries(archive),
        archive_comment=b"comment",
    )

    with pytest.raises(ExportVerificationError):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=published.receipt_sha256,
        )


@pytest.mark.parametrize(
    "source_mutation",
    ("extra-file", "extra-dir", "symlink", "hardlink"),
)
def test_packager_rejects_nonclosed_or_linked_source_exports(
    tmp_path: Path,
    source_mutation: str,
):
    published = _publish_export(tmp_path)
    if source_mutation == "extra-file":
        (published.root / ".DS_Store").write_bytes(b"finder mutation")
    elif source_mutation == "extra-dir":
        (published.root / "unexpected-empty-directory").mkdir()
    elif source_mutation == "symlink":
        source = published.root / "README.md"
        outside = tmp_path / "outside-readme"
        outside.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(outside)
    else:
        os.link(
            published.root / "README.md",
            published.root / "unexpected-hard-link.md",
        )
    target = tmp_path / f"must-not-exist{EXPORT_PACK_ARCHIVE_SUFFIX}"

    with pytest.raises(ExportVerificationError):
        _write_pack(published, target)

    assert not target.exists()


def test_packager_rejects_symlink_source_root(tmp_path: Path):
    published = _publish_export(tmp_path)
    linked = tmp_path / "linked-export"
    linked.symlink_to(published.root, target_is_directory=True)
    target = tmp_path / f"must-not-exist{EXPORT_PACK_ARCHIVE_SUFFIX}"

    with pytest.raises(ExportVerificationError):
        write_export_pack_archive(
            linked,
            target,
            expected_export_receipt_sha256=published.receipt_sha256,
        )

    assert not target.exists()


def test_archive_target_is_no_replace_and_preserves_existing_bytes(tmp_path: Path):
    published = _publish_export(tmp_path)
    target = tmp_path / f"occupied{EXPORT_PACK_ARCHIVE_SUFFIX}"
    sentinel = b"owner-controlled existing bytes"
    target.write_bytes(sentinel)

    with pytest.raises(FileExistsError) as caught:
        _write_pack(published, target)

    assert caught.value.errno == errno.EEXIST
    assert target.read_bytes() == sentinel


def test_packager_rejects_archive_target_inside_source_tree(tmp_path: Path):
    published = _publish_export(tmp_path)
    before = _tree_bytes(published.root)
    target = published.root / f"nested{EXPORT_PACK_ARCHIVE_SUFFIX}"

    with pytest.raises(ExportContractError):
        _write_pack(published, target)

    assert not target.exists()
    assert _tree_bytes(published.root) == before


def test_packager_rejects_wrong_suffix_without_writing(tmp_path: Path):
    published = _publish_export(tmp_path)
    target = tmp_path / "not-an-export-pack.zip"

    with pytest.raises(ExportContractError):
        _write_pack(published, target)

    assert not target.exists()


def test_packager_rejects_symlink_destination_parent(tmp_path: Path):
    published = _publish_export(tmp_path)
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)
    target = linked_parent / f"pack{EXPORT_PACK_ARCHIVE_SUFFIX}"

    with pytest.raises(ExportContractError):
        _write_pack(published, target)

    assert not target.exists()


@pytest.mark.parametrize(
    ("error_number", "message"),
    (
        (errno.ENOSPC, "No space left on device"),
        (errno.EACCES, "Permission denied"),
    ),
)
def test_archive_write_failure_leaves_no_target_or_staging_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_number: int,
    message: str,
):
    published = _publish_export(tmp_path)
    target = tmp_path / f"failed{EXPORT_PACK_ARCHIVE_SUFFIX}"

    def fail_write(source_root, archive_path, *, members):
        del source_root, members
        raise OSError(error_number, message, archive_path)

    monkeypatch.setattr(archive_module, "write_deterministic_archive", fail_write)

    with pytest.raises(OSError) as caught:
        _write_pack(published, target)

    assert caught.value.errno == error_number
    assert not target.exists()
    assert not list(tmp_path.glob(f".{target.name}.tmp-*"))


def test_post_visibility_cleanup_warning_cannot_unwind_valid_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    published = _publish_export(tmp_path)
    target = tmp_path / f"warned{EXPORT_PACK_ARCHIVE_SUFFIX}"
    original_unlink = Path.unlink

    def fail_staging_unlink(path: Path, *args, **kwargs):
        if path.name.startswith(f".{target.name}.tmp-"):
            raise OSError(errno.EACCES, "Permission denied", path)
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_staging_unlink)
    with pytest.warns(RuntimeWarning, match="staging link could not be removed"):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            written = _write_pack(published, target)

    assert target.is_file()
    assert written.archive_path == target
    assert written.durability_warning is not None
    assert "staging link could not be removed" in written.durability_warning
    verified = verify_export_pack_archive(
        target,
        expected_export_receipt_sha256=published.receipt_sha256,
    )
    assert verified.archive_sha256 == written.archive_sha256


@pytest.mark.parametrize("archive_kind", ("directory", "symlink"))
def test_verifier_requires_a_real_regular_archive(
    tmp_path: Path,
    archive_kind: str,
):
    published, archive = _valid_archive(tmp_path)
    invalid = tmp_path / f"invalid{EXPORT_PACK_ARCHIVE_SUFFIX}"
    if archive_kind == "directory":
        invalid.mkdir()
    else:
        invalid.symlink_to(archive)

    with pytest.raises(ExportVerificationError):
        verify_export_pack_archive(
            invalid,
            expected_export_receipt_sha256=published.receipt_sha256,
        )


def test_verifier_rejects_archive_path_replacement_during_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    published, archive = _valid_archive(tmp_path)
    moved = tmp_path / "original-open-inode.vfexport.zip"
    original_write = archive_module.write_deterministic_archive

    def replace_archive_path_after_canonical_rerender(
        source_root: Path,
        archive_path: Path,
        *,
        members,
    ) -> None:
        original_write(source_root, archive_path, members=members)
        archive.replace(moved)
        archive.write_bytes(moved.read_bytes())

    monkeypatch.setattr(
        archive_module,
        "write_deterministic_archive",
        replace_archive_path_after_canonical_rerender,
    )

    with pytest.raises(ExportVerificationError, match="path changed"):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=published.receipt_sha256,
        )


def test_legacy_bundle_archive_bytes_and_public_api_remain_unchanged(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    archive = tmp_path / "legacy.vfbundle.zip"

    written = write_bundle_archive(
        bundle,
        archive,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    verified = verify_bundle_archive(
        archive,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )

    assert tuple(BundleArchiveReceipt.__dataclass_fields__) == (
        "archive_path",
        "archive_sha256",
        "archive_size",
        "manifest_sha256",
        "member_count",
        "verification",
        "durability_warning",
    )
    assert written.archive_sha256 == LEGACY_ARCHIVE_SHA256
    assert verified.archive_sha256 == LEGACY_ARCHIVE_SHA256
    assert sha256_digest(archive.read_bytes()) == LEGACY_ARCHIVE_SHA256
    assert archive.stat().st_size == LEGACY_ARCHIVE_SIZE
    assert written.member_count == 6
    assert written.manifest_sha256 == EXPECTED_MANIFEST_SHA256
    assert written.verification.trust_grade == "external_digest"
