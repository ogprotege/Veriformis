# tests/bundle/test_writer.py
import json

import pytest

from veriformis.bundle.writer import verify_bundle, write_bundle
from veriformis.chunkers.base import Chunk
from veriformis.errors import GateFailure
from veriformis.ir import Span
from veriformis.rules.engine import TransformRecord
from veriformis.sources import SourceRef
from veriformis.validate.gates import GateResult


def _inputs(passed=True):
    source = SourceRef(id="s1", path="f.txt", sha256="ab", size=5, parser="text", extracted_text="hello world")
    chunk = Chunk(id="chk-0001", source_id="s1", block_index=0, span=Span(0, 5),
                  heading_path=[], text="hello", tokens_est=2, transformed=False)
    transforms = [TransformRecord(rule="whitespace", params={}, block_index=0, edits=1, bytes_removed=2, warned=False)]
    validations = [GateResult("schema", passed, [] if passed else ["bad record"])]
    return dict(
        records=[{"text": "hello"}], chunks=[chunk], sources=[source],
        transforms=transforms, validations=validations, format="completion", template=None,
    )


def test_write_and_verify_bundle(tmp_path):
    out = write_bundle(tmp_path / "b.vfbundle", **_inputs())
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["dataset"]["record_count"] == 1
    assert manifest["sources"][0]["sha256"] == "ab"
    assert manifest["files"]["dataset.jsonl"]
    assert verify_bundle(out) is True
    (out / "dataset.jsonl").write_text('{"text": "tampered"}\n')
    assert verify_bundle(out) is False


def test_seal_refuses_failed_gate(tmp_path):
    with pytest.raises(GateFailure):
        write_bundle(tmp_path / "b.vfbundle", **_inputs(passed=False))
    assert not (tmp_path / "b.vfbundle" / "manifest.json").exists()
