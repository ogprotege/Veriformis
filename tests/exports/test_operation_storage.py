"""Source reuse and spooled comparison retain export corruption boundaries."""
from pathlib import Path
import tracemalloc

import pytest

from support.bundles import _materialize_bundle
from support.export_api import _dry_run_request, _execute_request, _service, _verify_request
from veriformis.errors import ExportVerificationError
from veriformis.exports import service as module
from veriformis.exports import _publication as publication
from veriformis.exports._spool import SpooledTree


def test_execution_inspects_source_once_and_next_operation_inspects_again(tmp_path, monkeypatch):
    bundle = _materialize_bundle(tmp_path)
    service, runtime = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    inspections = 0
    original = module.inspect_finished_bundle

    def inspect(*args, **kwargs):
        nonlocal inspections
        inspections += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "inspect_finished_bundle", inspect)
    destination = tmp_path / "export"
    service.execute_export(_execute_request(bundle, destination, plan))
    assert inspections == 1 and runtime.render_calls == 2
    service.verify_export(_verify_request(bundle, destination, plan))
    assert inspections == 2


@pytest.mark.parametrize("mutation", ["file", "extra", "directory"])
def test_final_source_guard_refuses_changes_before_promotion(tmp_path, monkeypatch, mutation):
    bundle = _materialize_bundle(tmp_path)
    service, _ = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    original = publication._rename_no_replace
    destination = tmp_path / "export"

    def rename(staging, **kwargs):
        if mutation == "file":
            path = bundle / "data/train.jsonl"
            path.write_bytes(b"x" + path.read_bytes()[1:])
        elif mutation == "extra":
            (bundle / "metadata/extra").write_bytes(b"x")
        else:
            (bundle / "data").rename(bundle / "old-data")
            (bundle / "data").mkdir()
        return original(staging, **kwargs)

    monkeypatch.setattr(publication, "_rename_no_replace", rename)
    with pytest.raises(ExportVerificationError, match="source changed"):
        service.execute_export(_execute_request(bundle, destination, plan))
    assert not destination.exists()
    assert not list(tmp_path.glob(".veriformis-export-*"))


def test_spooled_comparison_does_not_retain_another_whole_tree():
    payload = b"x" * (16 * 1024 * 1024)
    with SpooledTree((("payload", payload),)) as tree:
        tracemalloc.start()
        try:
            assert tree.matches((("payload", payload),))
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert peak < 4 * 1024 * 1024
        assert not tree.matches((("payload", b"y" + payload[1:]),))
        assert not tree.matches((("different-path", payload),))


def test_spool_resources_close_on_refusal(tmp_path: Path):
    tree = SpooledTree((("payload", b"exact"),))
    with pytest.raises(RuntimeError):
        with tree:
            raise RuntimeError("cancel")
    assert tree._file.closed
