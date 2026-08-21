"""Defect closure: post-publication transport warnings must not unwind success.

Once the ``.vfbundle.zip`` archive is visible, durability notes are advisory.
Under a ``warnings`` filter of ``error`` the naked ``warnings.warn`` used to
raise after the archive was already published, making the caller report
failure for a valid visible archive whose retry then hit the no-replace guard.
"""

from __future__ import annotations

import errno
import warnings
from pathlib import Path

from veriformis.bundle.transport import verify_bundle_archive, write_bundle_archive
from veriformis.pipeline import PipelineService


def _sealed_bundle(tmp_path: Path) -> tuple[Path, str]:
    source = tmp_path / "source.txt"
    source.write_text(
        "First paragraph with enough grounded text for one record.\n\n"
        "Second paragraph keeps the corpus multi-block.",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace"
    bundle = tmp_path / "sealed.vfbundle"
    service = PipelineService()
    service.parse([source], workspace, source_root=tmp_path)
    service.clean(workspace)
    service.chunk(workspace)
    service.construct(workspace, objective="full_text")
    service.curate(workspace, evaluation_required=False)
    service.split(workspace)
    service.format(workspace)
    assert service.validate(workspace).exit_status == 0
    sealed = service.seal(workspace, bundle)
    assert sealed.publication is not None
    return bundle, sealed.publication.manifest_sha256


def test_durability_warning_cannot_unwind_publication_under_error_filter(
    tmp_path,
    monkeypatch,
):
    bundle, digest = _sealed_bundle(tmp_path)
    target = tmp_path / "warned.vfbundle.zip"
    original_unlink = Path.unlink

    def fail_staging_unlink(path, *args, **kwargs):
        if path.name.startswith(".warned.vfbundle.zip.tmp-"):
            raise OSError(errno.EACCES, "Permission denied", path)
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_staging_unlink)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        receipt = write_bundle_archive(
            bundle,
            target,
            expected_manifest_sha256=digest,
        )

    assert target.is_file()
    assert receipt.archive_path == target
    assert receipt.durability_warning is not None
    assert "staging link could not be removed" in receipt.durability_warning
    assert (
        verify_bundle_archive(target, expected_manifest_sha256=digest).archive_sha256
        == receipt.archive_sha256
    )
