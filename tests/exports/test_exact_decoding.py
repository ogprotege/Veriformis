"""D-15: a planner and renderer sharing bad bytes cannot bless those bytes."""
from __future__ import annotations

import base64
import csv
import importlib
import io
import json
from pathlib import Path

import pytest

from veriformis.errors import ExportVerificationError
from veriformis.exports import ExportDryRunRequest, ExportExecuteRequest, ExportService
from veriformis.identity import lossless_json_bytes, sha256_digest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"


def _bundle(root: Path) -> Path:
    fixture = json.loads((ROOT / "tests/regressions/fixtures/phase3/pre-taxonomy-full-text.vfbundle.json").read_bytes())
    bundle = root / "source.vfbundle"
    for name, encoded in fixture["files_base64"].items():
        raw = base64.b64decode(encoded, validate=True)
        assert sha256_digest(raw) == fixture["file_sha256"][name]
        path = bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return bundle


@pytest.mark.parametrize("module_name,container,consumer", [
    ("exports.split_jsonl", "split-jsonl-directory", None),
    ("exports.canonical_json", "json", None),
    ("exports.constrained_csv", "constrained-csv", None),
    ("profiles.trl", "split-jsonl-directory", "trl"),
    ("profiles.mlx_lm", "split-jsonl-directory", "mlx-lm"),
    ("profiles.axolotl", "split-jsonl-directory", "axolotl"),
    ("profiles.llama_factory", "split-jsonl-directory", "llama-factory"),
])
def test_shared_bad_rendering_refuses_before_publication(tmp_path, monkeypatch, module_name, container, consumer):
    bundle = _bundle(tmp_path)
    module = importlib.import_module("veriformis." + module_name)
    original = module._rendered_files

    def corrupted(*args, **kwargs):
        files = dict(original(*args, **kwargs))
        if container == "json":
            name = "dataset.json"
            payload = json.loads(files[name])
            payload["splits"]["train"][0]["text"] += " forged"
            files[name] = lossless_json_bytes(payload)
        elif container == "constrained-csv":
            name = "data/train.csv"
            rows = list(csv.reader(io.StringIO(files[name].decode(), newline="")))
            rows[1][0] += " forged"
            output = io.StringIO(newline="")
            csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="\n").writerows(rows)
            files[name] = output.getvalue().encode()
        else:
            name = "train.jsonl" if consumer == "mlx-lm" else "data/train.jsonl"
            payloads = [json.loads(line) for line in files[name].split(b"\n") if line]
            payloads[0]["text"] += " forged"
            files[name] = b"".join(lossless_json_bytes(row) + b"\n" for row in payloads)
        return tuple(sorted(files.items()))

    monkeypatch.setattr(module, "_rendered_files", corrupted)
    selection = dict(
        schema_version="veriformis.export-surface-request/v1",
        bundle=str(bundle), container_id=container, container_version=1,
        consumer_id=consumer, consumer_profile_version=1 if consumer else None,
        source_trust_policy="require_external_digest", expected_manifest_sha256=MANIFEST,
        overwrite_policy="refuse",
    )
    service = ExportService()
    plan = service.dry_run_export(ExportDryRunRequest(operation="dry_run", **selection))
    destination = tmp_path / "export"
    with pytest.raises(ExportVerificationError):
        service.execute_export(ExportExecuteRequest(
            operation="execute", destination_root=str(destination),
            expected_export_plan_id=plan.export_plan_id, **selection,
        ))
    assert not destination.exists()
