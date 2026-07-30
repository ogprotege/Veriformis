import hashlib
import json

import pytest

from veriformis.bundle.writer import verify_bundle, write_bundle
from veriformis.chunkers.strategies import chunk_paragraph
from veriformis.errors import GateFailure
from veriformis.ir import Paragraph, Span, Text
from veriformis.sources import register_source
from veriformis.validate.gates import GateResult


def _valid_inputs() -> dict:
    source = register_source(
        "source.txt",
        "text",
        "alpha",
        logical_path="source.txt",
        parser_version="1",
        raw_bytes=b"alpha",
    )
    block = Paragraph(
        children=[Text("alpha")],
        span=Span(0, 5),
        block_index=0,
    )
    chunk = chunk_paragraph([block], source=source)[0]
    return {
        "records": [{"text": "alpha"}],
        "chunks": [chunk],
        "sources": [source],
        "transforms": [],
        "validations": [GateResult("schema", True, [])],
        "format": "completion",
        "template": None,
    }


def test_empty_dataset_cannot_seal(tmp_path):
    inputs = _valid_inputs()
    inputs.update(records=[], chunks=[])
    with pytest.raises(GateFailure, match="empty"):
        write_bundle(tmp_path / "empty.vfbundle", **inputs)


def test_manifest_mutation_fails_external_verification(tmp_path):
    bundle = write_bundle(tmp_path / "bundle.vfbundle", **_valid_inputs())
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["dataset"]["record_count"] = 999
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert verify_bundle(bundle) is False


def test_undeclared_file_fails_verification(tmp_path):
    bundle = write_bundle(tmp_path / "bundle.vfbundle", **_valid_inputs())
    (bundle / "undeclared.txt").write_text("not in manifest", encoding="utf-8")
    assert verify_bundle(bundle) is False


def test_parent_traversal_fails_verification(tmp_path):
    bundle = write_bundle(tmp_path / "bundle.vfbundle", **_valid_inputs())
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["../outside.txt"] = hashlib.sha256(
        outside.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert verify_bundle(bundle) is False
