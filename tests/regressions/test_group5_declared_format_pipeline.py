"""Permanent Group 5 regression: every declared new format must compile perfectly.

These tests lock the fail-closed product path for HTML, digitally-born PDF, CSV,
JSON, and JSONL. A regression here is a product collapse, not a soft quality dip.

Coverage matrix:
- parse + exact IR stream validation (including Unicode)
- named refusal paths (OCR, invalid JSON/JSONL, empty HTML, unknown suffix)
- full PipelineService path: parse → clean → chunk → construct → curate →
  split → format → validate → seal → external_digest verify
- solo seal per format
- multi-source mix and continuation objective
- CLI parse for each format and CLI OCR refusal
- construction identity replay across independent workspaces
- YAML pipeline seal including a new Group 5 format
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.construction import construction_result_from_json_bytes
from veriformis.errors import UnsupportedInputError
from veriformis.ir import validate_document_against_stream
from veriformis.parsers.dispatch import parse_captured_source
from veriformis.parsers.html import parse_html_file
from veriformis.parsers.pdf import parse_pdf_file
from veriformis.parsers.structured import (
    parse_csv_file,
    parse_json_file,
    parse_jsonl_file,
)
from veriformis.pipeline import PipelineService
from veriformis.recipes import load_pipeline_spec, run_pipeline_spec
from veriformis.workspace import Workspace

runner = CliRunner()
_G5 = Path(__file__).resolve().parents[1] / "fixtures" / "group5"


def _pdf(name: str) -> bytes:
    return (_G5 / name).read_bytes()


def _assert_exact_stream(result) -> None:
    assert result.diagnostics.status in {"complete", "degraded"}
    assert result.source.extracted_text.strip()
    validate_document_against_stream(
        result.document,
        result.source.extracted_text,
        exact=True,
    )


def _write_corpus(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    paths["txt"] = root / "control.txt"
    paths["txt"].write_text(
        "Control paragraph with enough text for construction.\n\n"
        "Second control paragraph keeps multi-block structure.",
        encoding="utf-8",
    )

    paths["html"] = root / "page.html"
    paths["html"].write_text(
        """<!DOCTYPE html>
<html><head><title>T</title><style>.x{color:red}</style>
<script>var x=1</script></head>
<body><main>
  <h1>Main Title</h1>
  <p>First HTML paragraph with recoverable body text for fine-tuning.</p>
  <p>Second HTML paragraph continues the grounded content stream.</p>
</main></body></html>
""",
        encoding="utf-8",
    )

    paths["html_unicode"] = root / "unicode.html"
    paths["html_unicode"].write_text(
        "<html><body><p>Café résumé — 日本語と絵文字 🚀 grounded body.</p>"
        "<p>Second unicode paragraph for multi-block construction.</p></body></html>",
        encoding="utf-8",
    )

    paths["pdf"] = root / "born.pdf"
    paths["pdf"].write_bytes(_pdf("minimal-text.pdf"))
    paths["pdf_empty"] = root / "empty.pdf"
    paths["pdf_empty"].write_bytes(_pdf("empty-text.pdf"))

    paths["csv"] = root / "table.csv"
    paths["csv"].write_text(
        "name,age,city\nAda,36,London\nBob,41,Paris\n",
        encoding="utf-8",
    )
    paths["csv_ragged"] = root / "ragged.csv"
    paths["csv_ragged"].write_text("a,b,c\n1,2\n3,4,5,6\n", encoding="utf-8")
    paths["csv_unicode"] = root / "unicode.csv"
    paths["csv_unicode"].write_text(
        "term,note\nnaïve,accented café note with body\n",
        encoding="utf-8",
    )

    paths["json"] = root / "obj.json"
    paths["json"].write_text(
        json.dumps(
            {
                "prompt": "What is water?",
                "completion": "A molecule of H2O with enough grounded text.",
                "meta": {"id": 7},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    paths["json_unicode"] = root / "unicode.json"
    paths["json_unicode"].write_text(
        json.dumps(
            {
                "title": "東京",
                "body": "café grounded unicode body for construction records.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    paths["jsonl"] = root / "rows.jsonl"
    paths["jsonl"].write_text(
        "\n".join(
            [
                json.dumps(
                    {"q": "one", "a": "first answer with enough grounded text"}
                ),
                json.dumps(
                    {"q": "two", "a": "second answer with enough grounded text"}
                ),
                json.dumps({"q": "三", "a": "unicode answer 🚀 with body text"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return paths


def _compile_to_verified_bundle(
    service: PipelineService,
    paths: list[Path],
    *,
    workspace: Path,
    bundle: Path,
    source_root: Path,
    objective: str = "full_text",
    split_ratio_ppm: int = 500_000,
) -> str:
    """Run the complete compiler path and return the sealed manifest SHA-256."""
    parsed = service.parse(paths, workspace, source_root=source_root)
    assert parsed.source_count == len(paths)
    cleaned = service.clean(workspace)
    assert cleaned.document_count == len(paths)
    chunked = service.chunk(workspace)
    assert chunked.chunk_count >= 1
    constructed = service.construct(
        workspace,
        objective=objective,
        split_ratio_ppm=split_ratio_ppm,
    )
    assert constructed.record_count >= 1
    curated = service.curate(workspace, evaluation_required=False)
    assert curated.included_count >= 1
    split = service.split(workspace)
    assert split.train_record_count + split.evaluation_record_count >= 1
    formatted = service.format(workspace)
    assert formatted.train_row_count + formatted.evaluation_row_count >= 1
    validated = service.validate(workspace)
    assert validated.exit_status == 0
    assert validated.report is not None
    assert validated.report.status == "passed"
    sealed = service.seal(workspace, bundle)
    assert sealed.publication is not None
    verified = service.verify(
        bundle,
        manifest_sha256=sealed.publication.manifest_sha256,
    )
    assert verified.verification is not None
    assert verified.verification.trust_grade == "external_digest"
    assert (bundle / "data" / "train.jsonl").is_file()
    assert (bundle / "manifest.json").is_file()
    assert (bundle / "attestation.json").is_file()
    assert (bundle / "validation.json").is_file()
    return sealed.publication.manifest_sha256


# ---------------------------------------------------------------------------
# Parse + stream identity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "parser"),
    [
        ("html", parse_html_file),
        ("html_unicode", parse_html_file),
        ("pdf", parse_pdf_file),
        ("csv", parse_csv_file),
        ("csv_ragged", parse_csv_file),
        ("csv_unicode", parse_csv_file),
        ("json", parse_json_file),
        ("json_unicode", parse_json_file),
        ("jsonl", parse_jsonl_file),
    ],
)
def test_group5_parse_exact_stream_matrix(tmp_path, key, parser):
    paths = _write_corpus(tmp_path / "raw")
    result = parser(paths[key], logical_path=paths[key].name)
    _assert_exact_stream(result)


def test_group5_pdf_ocr_refusal_is_named(tmp_path):
    paths = _write_corpus(tmp_path / "raw")
    result = parse_pdf_file(paths["pdf_empty"], logical_path=paths["pdf_empty"].name)
    assert result.diagnostics.status == "refused"
    codes = {item.code for item in result.diagnostics.diagnostics}
    assert "pdf.ocr-required" in codes
    assert any(
        item.details.get("limitation") == "ocr-unsupported"
        for item in result.diagnostics.diagnostics
    )


def test_group5_invalid_json_and_jsonl_refuse(tmp_path):
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{not json", encoding="utf-8")
    json_result = parse_json_file(bad_json, logical_path=bad_json.name)
    assert json_result.diagnostics.status == "refused"
    assert json_result.diagnostics.diagnostics[0].code == "json.invalid"

    bad_jsonl = tmp_path / "bad.jsonl"
    bad_jsonl.write_text('{"ok": true}\nnot-json\n', encoding="utf-8")
    jsonl_result = parse_jsonl_file(bad_jsonl, logical_path=bad_jsonl.name)
    assert jsonl_result.diagnostics.status == "refused"
    assert jsonl_result.diagnostics.diagnostics[0].code == "jsonl.invalid-line"


def test_group5_empty_html_refuses(tmp_path):
    path = tmp_path / "empty.html"
    path.write_text(
        "<html><body><script>only()</script></body></html>",
        encoding="utf-8",
    )
    result = parse_html_file(path, logical_path=path.name)
    assert result.diagnostics.status == "refused"
    assert any(
        item.code == "html.empty-text" for item in result.diagnostics.diagnostics
    )


def test_group5_unknown_suffix_unsupported(tmp_path):
    path = tmp_path / "x.webp"
    path.write_bytes(b"not-a-supported-parser")
    with pytest.raises(UnsupportedInputError):
        parse_captured_source(
            path,
            logical_path=path.name,
            raw_bytes=path.read_bytes(),
        )


# ---------------------------------------------------------------------------
# Full compiler path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "html",
        "pdf",
        "csv",
        "json",
        "jsonl",
        "html_unicode",
        "csv_unicode",
        "json_unicode",
    ],
)
def test_group5_solo_format_seals_and_verifies(tmp_path, key):
    raw = tmp_path / "raw"
    paths = _write_corpus(raw)
    service = PipelineService()
    digest = _compile_to_verified_bundle(
        service,
        [paths[key]],
        workspace=tmp_path / f"ws-{key}",
        bundle=tmp_path / f"bundle-{key}.vfbundle",
        source_root=raw,
    )
    assert len(digest) == 64


def test_group5_mixed_formats_full_text_seals(tmp_path):
    raw = tmp_path / "raw"
    paths = _write_corpus(raw)
    service = PipelineService()
    digest = _compile_to_verified_bundle(
        service,
        [
            paths["html"],
            paths["pdf"],
            paths["csv"],
            paths["json"],
            paths["jsonl"],
            paths["txt"],
        ],
        workspace=tmp_path / "ws-mix",
        bundle=tmp_path / "bundle-mix.vfbundle",
        source_root=raw,
        objective="full_text",
    )
    assert len(digest) == 64


def test_group5_mixed_formats_continuation_seals(tmp_path):
    raw = tmp_path / "raw"
    paths = _write_corpus(raw)
    service = PipelineService()
    digest = _compile_to_verified_bundle(
        service,
        [paths["html"], paths["jsonl"], paths["txt"]],
        workspace=tmp_path / "ws-cont",
        bundle=tmp_path / "bundle-cont.vfbundle",
        source_root=raw,
        objective="continuation",
        split_ratio_ppm=400_000,
    )
    assert len(digest) == 64


def test_group5_construction_identity_replays_across_workspaces(tmp_path):
    raw = tmp_path / "raw"
    paths = _write_corpus(raw)
    service = PipelineService()
    result_ids: list[str] = []
    for name in ("a", "b"):
        workspace = tmp_path / f"ws-{name}"
        service.parse([paths["html"], paths["csv"]], workspace, source_root=raw)
        service.clean(workspace)
        service.chunk(workspace)
        service.construct(workspace, objective="full_text")
        store = Workspace.open(workspace)
        head = store.head()
        result = construction_result_from_json_bytes(
            store.read_artifact(
                head.stages["construct"].outputs["result"],
                revision=head,
            )
        )
        result_ids.append(result.result_id)
    assert result_ids[0] == result_ids[1]


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["html", "pdf", "csv", "json", "jsonl"])
def test_group5_cli_parse_each_format(tmp_path, key):
    raw = tmp_path / "raw"
    paths = _write_corpus(raw)
    workspace = tmp_path / f"cli-{key}"
    result = runner.invoke(
        app,
        [
            "parse",
            str(paths[key]),
            "-o",
            str(workspace),
            "--source-root",
            str(raw),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "parsed 1 source(s)" in result.output
    assert Workspace.open(workspace).head().stages["parse"].status == "complete"


def test_group5_cli_refuses_empty_text_pdf(tmp_path):
    raw = tmp_path / "raw"
    paths = _write_corpus(raw)
    workspace = tmp_path / "cli-empty-pdf"
    result = runner.invoke(
        app,
        [
            "parse",
            str(paths["pdf_empty"]),
            "-o",
            str(workspace),
            "--source-root",
            str(raw),
        ],
    )
    assert result.exit_code != 0
    combined = result.output
    assert "pdf.ocr-required" in combined or "OCR" in combined or "ocr" in combined


# ---------------------------------------------------------------------------
# YAML pipeline with a Group 5 format
# ---------------------------------------------------------------------------


def test_group5_yaml_pipeline_seals_html_source(tmp_path):
    raw = tmp_path / "raw"
    _write_corpus(raw)
    pipeline = tmp_path / "pipeline.yaml"
    pipeline.write_text(
        """
schema_version: veriformis.pipeline/v1
workspace: ws
source_root: raw
sources:
  - path: page.html
recipe_library_id: full_text.default
stages:
  parse: {}
  construct:
    objective: full_text
  curate:
    allow_empty_evaluation: true
  seal:
    out: out.vfbundle
""".strip(),
        encoding="utf-8",
    )
    # corpus lives next to pipeline under raw/
    # _write_corpus already wrote raw/page.html under tmp_path/raw
    # pipeline expects raw relative to pipeline parent
    result = run_pipeline_spec(load_pipeline_spec(pipeline))
    assert result.bundle is not None
    assert result.bundle.is_dir()
    assert (result.bundle / "manifest.json").is_file()
    assert all(outcome.exit_status == 0 for outcome in result.outcomes)


def test_group5_yaml_pipeline_seals_jsonl_source(tmp_path):
    raw = tmp_path / "raw"
    _write_corpus(raw)
    pipeline = tmp_path / "pipeline.yaml"
    pipeline.write_text(
        """
schema_version: veriformis.pipeline/v1
workspace: ws
source_root: raw
sources:
  - path: rows.jsonl
stages:
  parse: {}
  construct:
    objective: full_text
  curate:
    allow_empty_evaluation: true
  seal:
    out: jsonl.vfbundle
""".strip(),
        encoding="utf-8",
    )
    result = run_pipeline_spec(load_pipeline_spec(pipeline))
    assert result.bundle is not None
    assert (result.bundle / "data" / "train.jsonl").is_file()
    assert all(outcome.exit_status == 0 for outcome in result.outcomes)
