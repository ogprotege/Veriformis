from dataclasses import replace
import json

import pytest

from veriformis.bundle.writer import verify_bundle, write_bundle
from veriformis.chunkers.strategies import chunk_paragraph
from veriformis.errors import EvidenceError, GateFailure, RuleError
from veriformis.ir import Paragraph, Span, Text
from veriformis.rules.engine import RegexRule, apply_rules
from veriformis.sources import register_source
from veriformis.validate.gates import GateResult


def _source(logical_path="f.txt", text="hello world"):
    return register_source(
        logical_path,
        "text",
        text,
        logical_path=logical_path,
        parser_version="1",
        raw_bytes=text.encode("utf-8"),
    )


def _chunk(source):
    block = Paragraph(
        children=[Text(source.extracted_text)],
        span=Span(0, len(source.extracted_text)),
        block_index=0,
    )
    return chunk_paragraph([block], source=source)[0]


def _transform(source):
    return apply_rules(
        "hello  world",
        [RegexRule("whitespace", r" +", " ")],
        source_id=source.id,
    )[1][0]


def _inputs(passed=True):
    source = _source()
    chunk = _chunk(source)
    validations = [GateResult("schema", passed, [] if passed else ["bad record"])]
    return {
        "records": [{"text": chunk.text}],
        "chunks": [chunk],
        "sources": [source],
        "transforms": [_transform(source)],
        "validations": validations,
        "format": "completion",
        "template": None,
    }


def test_write_and_verify_bundle(tmp_path):
    out = write_bundle(tmp_path / "b.vfbundle", **_inputs())
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["dataset"]["record_count"] == 1
    assert manifest["sources"][0]["sha256"] == _inputs()["sources"][0].sha256
    assert manifest["files"]["dataset.jsonl"]
    assert verify_bundle(out) is True
    (out / "dataset.jsonl").write_text('{"text": "tampered"}\n')
    assert verify_bundle(out) is False


def test_seal_refuses_failed_gate(tmp_path):
    with pytest.raises(GateFailure):
        write_bundle(tmp_path / "b.vfbundle", **_inputs(passed=False))
    assert not (tmp_path / "b.vfbundle" / "manifest.json").exists()


def test_manifest_preserves_group1_integrity_identities(tmp_path):
    source = _source("corpus/input.txt")
    chunk = _chunk(source)
    transform = _transform(source)

    out = write_bundle(
        tmp_path / "integrity.vfbundle",
        records=[{"text": chunk.text}],
        chunks=[chunk],
        sources=[source],
        transforms=[transform],
        validations=[GateResult("schema", True, [])],
        format="completion",
        template=None,
    )
    manifest = json.loads((out / "manifest.json").read_text())

    source_entry = manifest["sources"][0]
    assert source_entry["id"] == source.id
    assert source_entry["logical_path"] == source.logical_path
    assert source_entry["parser_version"] == source.parser_version
    assert (
        source_entry["canonical_stream_contract_version"]
        == source.canonical_stream_contract_version
    )
    assert source_entry["stream_sha256"] == source.stream_sha256
    assert source_entry["artifact_id"] == source.artifact_id

    transform_entry = manifest["transforms"][0]
    assert transform_entry["schema_version"] == transform.schema_version
    assert transform_entry["id"] == transform.id
    assert transform_entry["source_id"] == source.id
    assert transform_entry["operation_ids"] == list(transform.operation_ids)
    assert transform_entry["input_sha256"] == transform.input_sha256
    assert transform_entry["output_sha256"] == transform.output_sha256

    chunk_entry = manifest["chunks"][0]
    assert chunk_entry["artifact_id"] == source.artifact_id
    assert chunk_entry["evidence_id"] == chunk.evidence.evidence_id
    assert chunk_entry["evidence_output_sha256"] == chunk.evidence.output_sha256


def test_manifest_never_persists_the_host_source_path(tmp_path):
    host_path = tmp_path / "private" / "source.txt"
    host_path.parent.mkdir()
    host_path.write_text("hello world", encoding="utf-8")
    source = register_source(
        host_path,
        "text",
        "hello world",
        logical_path="corpus/source.txt",
        parser_version="1",
    )
    chunk = _chunk(source)

    out = write_bundle(
        tmp_path / "portable.vfbundle",
        records=[{"text": chunk.text}],
        chunks=[chunk],
        sources=[source],
        transforms=[],
        validations=[GateResult("all", True, [])],
        format="completion",
        template=None,
    )
    source_entry = json.loads((out / "manifest.json").read_text())["sources"][0]

    assert source_entry["path"] == "corpus/source.txt"
    assert source_entry["logical_path"] == "corpus/source.txt"
    assert str(tmp_path) not in json.dumps(source_entry)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda source: replace(source, stream_sha256="0" * 64),
        lambda source: replace(source, artifact_id="art-v1-" + "0" * 64),
        lambda source: replace(source, id="src-v1-" + "0" * 64),
    ],
)
def test_bundle_refuses_tampered_source_before_writing(tmp_path, mutation):
    inputs = _inputs()
    inputs["sources"] = [mutation(inputs["sources"][0])]
    out = tmp_path / "invalid-source.vfbundle"

    with pytest.raises(EvidenceError):
        write_bundle(out, **inputs)

    assert not out.exists()


def test_bundle_refuses_tampered_transform_before_writing(tmp_path):
    inputs = _inputs()
    inputs["transforms"] = [replace(inputs["transforms"][0], output_sha256="0" * 64)]
    out = tmp_path / "invalid-transform.vfbundle"

    with pytest.raises(RuleError, match="identity mismatch"):
        write_bundle(out, **inputs)

    assert not out.exists()


def test_bundle_refuses_cross_source_transform_before_writing(tmp_path):
    inputs = _inputs()
    other = _source("other.txt")
    inputs["transforms"] = [_transform(other)]
    out = tmp_path / "cross-source-transform.vfbundle"

    with pytest.raises(RuleError, match="unregistered source"):
        write_bundle(out, **inputs)

    assert not out.exists()


def test_bundle_refuses_tampered_chunk_before_writing(tmp_path):
    inputs = _inputs()
    inputs["chunks"] = [replace(inputs["chunks"][0], text="fabricated")]
    out = tmp_path / "invalid-chunk.vfbundle"

    with pytest.raises(EvidenceError):
        write_bundle(out, **inputs)

    assert not out.exists()


def test_bundle_refuses_cross_source_chunk_before_writing(tmp_path):
    inputs = _inputs()
    other = _source("other.txt")
    inputs["chunks"] = [_chunk(other)]
    out = tmp_path / "cross-source-chunk.vfbundle"

    with pytest.raises(EvidenceError, match="unregistered source"):
        write_bundle(out, **inputs)

    assert not out.exists()
