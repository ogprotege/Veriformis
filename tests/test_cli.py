import json
import zipfile
from dataclasses import replace

import pytest
from typer.testing import CliRunner

from veriformis.chunkers.base import (
    chunk_from_dict,
    chunk_to_dict,
    flatten,
    refresh_chunk_id,
)
from veriformis.cli import app
from veriformis.diagnostics import DiagnosticLocation, make_diagnostic, make_parse_report
from veriformis.errors import RuleError, WorkspaceCorruptError
from veriformis.evidence import (
    EvidenceComponent,
    EvidenceEdit,
    derivation_to_dict,
    edits_derivation,
    make_evidence,
)
from veriformis.identity import lossless_json_bytes, sha256_digest
from veriformis.ir import document_from_dict, document_to_dict
from veriformis.parsers.text import parse_text
from veriformis.rules.cleaning import (
    cleaning_input_digest,
    cleaning_plan_from_dict,
    cleaning_plan_to_dict,
    plan_cleaning,
    replay_cleaning_plan,
)
from veriformis.rules.derivations import (
    block_derivations_to_dict,
    build_block_derivations,
)
from veriformis.rules.engine import transform_record_to_dict
from veriformis.rules.library import custom_regex, default_rules
from veriformis.workspace import Workspace, WorkspaceTransaction

runner = CliRunner()


def _output_bytes(workspace, revision, stage, key):
    state = revision.stages[stage]
    assert state.status == "complete"
    artifact_id = state.outputs[key]
    return workspace.read_artifact(artifact_id, revision=revision)


def _json_output(workspace, revision, stage, key):
    return json.loads(_output_bytes(workspace, revision, stage, key))


def _jsonl_output(workspace, revision, stage, key):
    return [
        json.loads(line)
        for line in _output_bytes(workspace, revision, stage, key)
        .decode("utf-8")
        .splitlines()
        if line.strip()
    ]


def _assert_command_succeeded(result):
    assert result.exit_code == 0, result.output


def _forged_chunk_payload(workspace, revision):
    chunks = [
        chunk_from_dict(value)
        for value in _json_output(workspace, revision, "chunk", "chunks")
    ]
    target = next(chunk for chunk in chunks if len(chunk.evidence.components) > 1)
    evidence = target.evidence
    first = evidence.components[0]
    forged_component = EvidenceComponent(
        source_range=replace(first.source_range, text_sha256="0" * 64),
        derivations=first.derivations,
    )
    forged_evidence = make_evidence(
        source_id=evidence.source_id,
        components=(forged_component, *evidence.components[1:]),
        output_text=target.text,
        join=evidence.join_derivation,
        derivations=evidence.derivations,
        context=target.identity_context,
    )
    forged = refresh_chunk_id(replace(target, evidence=forged_evidence))
    return lossless_json_bytes(
        [chunk_to_dict(forged if chunk.id == target.id else chunk) for chunk in chunks]
    )


def _mutated_chunk_payload(workspace, revision, mutation):
    chunks = [
        chunk_from_dict(value)
        for value in _json_output(workspace, revision, "chunk", "chunks")
    ]
    target = next(chunk for chunk in chunks if len(chunk.block_indexes) > 1)
    if mutation == "region":
        context = {**target.identity_context, "region_id": "footnote:missing"}
        components = tuple(
            EvidenceComponent(
                source_range=replace(
                    component.source_range,
                    region_id="footnote:missing",
                ),
                derivations=component.derivations,
            )
            for component in target.evidence.components
        )
        evidence = make_evidence(
            source_id=target.source_id,
            components=components,
            output_text=target.text,
            join=target.evidence.join_derivation,
            derivations=target.evidence.derivations,
            context=context,
        )
        mutated = replace(
            target,
            evidence=evidence,
            identity_context=context,
        )
    elif mutation == "heading":
        mutated = replace(target, heading_path=["invented heading"])
    elif mutation == "blocks":
        mutated = replace(target, block_indexes=target.block_indexes[:1])
    else:
        mutated = replace(target, transformed=not target.transformed)
    mutated = refresh_chunk_id(mutated)
    return lossless_json_bytes(
        [chunk_to_dict(mutated if chunk.id == target.id else chunk) for chunk in chunks]
    )


def _workspace_with_chunks(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("first   paragraph\n\nsecond paragraph", encoding="utf-8")
    workspace_path = tmp_path / "workspace"
    _assert_command_succeeded(
        runner.invoke(
            app,
            [
                "parse",
                str(source),
                "-o",
                str(workspace_path),
                "--source-root",
                str(tmp_path),
            ],
        )
    )
    _assert_command_succeeded(runner.invoke(app, ["clean", str(workspace_path)]))
    _assert_command_succeeded(runner.invoke(app, ["chunk", str(workspace_path)]))
    return Workspace.open(workspace_path)


def test_full_pipeline_on_text_file(tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text("First paragraph here.\n\n37\n\nSecond paragraph here.", encoding="utf-8")
    ws = tmp_path / "ws"

    result = runner.invoke(
        app,
        ["parse", str(src), "-o", str(ws), "--source-root", str(tmp_path)],
    )
    _assert_command_succeeded(result)

    workspace = Workspace.open(ws)
    parsed = workspace.head()
    assert (ws / "HEAD").read_text(encoding="ascii").strip() == parsed.revision_id
    assert (ws / "revisions" / parsed.revision_id / "revision.json").is_file()
    assert parsed.committed_stage == "parse"
    assert parsed.stages["parse"].status == "complete"
    assert "registry" in parsed.stages["parse"].outputs
    source_id = next(iter(parsed.sources))
    for key in (
        f"source/{source_id}/raw",
        f"source/{source_id}/canonical",
        f"source/{source_id}/document",
        f"source/{source_id}/diagnostics",
    ):
        assert key in parsed.stages["parse"].outputs

    result = runner.invoke(app, ["clean", str(ws)])
    _assert_command_succeeded(result)
    cleaned = workspace.head()
    assert cleaned.committed_stage == "clean"
    for key in (
        "transforms",
        f"source/{source_id}/document",
        f"source/{source_id}/cleaning-plan",
        f"source/{source_id}/block-derivations",
    ):
        assert key in cleaned.stages["clean"].outputs

    result = runner.invoke(app, ["chunk", str(ws), "--strategy", "paragraph"])
    _assert_command_succeeded(result)
    chunked = workspace.head()
    chunk_values = _json_output(workspace, chunked, "chunk", "chunks")
    chunks = [chunk_from_dict(value) for value in chunk_values]
    assert chunks
    assert all(chunk.evidence is not None for chunk in chunks)

    result = runner.invoke(
        app,
        ["construct", str(ws), "--objective", "full_text"],
    )
    _assert_command_succeeded(result)
    constructed = workspace.head()
    assert constructed.committed_stage == "construct"
    assert set(constructed.stages["construct"].outputs) == {"recipe", "result"}

    result = runner.invoke(app, ["curate", str(ws), "--allow-empty-evaluation"])
    _assert_command_succeeded(result)
    curated = workspace.head()
    assert curated.committed_stage == "curate"
    assert set(curated.stages["curate"].outputs) == {"plan", "result"}

    result = runner.invoke(app, ["split", str(ws)])
    _assert_command_succeeded(result)
    split = workspace.head()
    assert split.committed_stage == "split"
    assert set(split.stages["split"].outputs) == {"result"}

    result = runner.invoke(app, ["format", str(ws)])
    _assert_command_succeeded(result)
    formatted = workspace.head()
    assert formatted.committed_stage == "format"
    assert set(formatted.stages["format"].outputs) == {
        "row-set",
        "train",
        "evaluation",
        "provenance",
    }
    records = _jsonl_output(workspace, formatted, "format", "train")
    assert records
    assert all(set(record) == {"text"} for record in records)
    row_set = _json_output(workspace, formatted, "format", "row-set")
    assert row_set["row_schema"] == "text"
    assert row_set["train_row_count"] == len(records)
    assert row_set["evaluation_row_count"] == 0

    result = runner.invoke(app, ["validate", str(ws)])
    _assert_command_succeeded(result)
    validated = workspace.head()
    assert validated.committed_stage == "validate"
    assert set(validated.stages["validate"].outputs) == {"snapshot", "report"}
    report = _json_output(workspace, validated, "validate", "report")
    assert report["status"] == "passed"
    assert report["gate_results"]
    assert all(item["status"] == "passed" for item in report["gate_results"])

    bundle = tmp_path / "out.vfbundle"
    result = runner.invoke(app, ["seal", str(ws), "-o", str(bundle)])
    _assert_command_succeeded(result)
    sealed = workspace.head()
    assert sealed.committed_stage == "seal"
    assert set(sealed.stages["seal"].outputs) == {"manifest", "attestation"}
    assert (bundle / "manifest.json").exists()
    assert (bundle / "attestation.json").exists()
    assert (bundle / "data" / "train.jsonl").exists()
    assert (bundle / "data" / "evaluation.jsonl").exists()
    assert (bundle / "metadata" / "row-provenance.jsonl").exists()
    assert (bundle / "validation.json").exists()

    result = runner.invoke(app, ["verify", str(bundle)])
    _assert_command_succeeded(result)
    assert "verification grade:" in result.output
    assert "dataset rows:" in result.output

    manifest_sha256 = sha256_digest((bundle / "manifest.json").read_bytes())
    archive = tmp_path / "out.vfbundle.zip"
    result = runner.invoke(
        app,
        [
            "package",
            str(bundle),
            "-o",
            str(archive),
            "--manifest-sha256",
            manifest_sha256,
        ],
    )
    _assert_command_succeeded(result)
    assert archive.is_file()
    assert "transport archive:" in result.output
    assert "verification grade: external_digest" in result.output

    result = runner.invoke(
        app,
        ["package-verify", str(archive), "--manifest-sha256", manifest_sha256],
    )
    _assert_command_succeeded(result)
    assert "transport archive status: accepted" in result.output


def test_chunk_commit_rejects_self_consistent_but_false_source_evidence(tmp_path):
    workspace = _workspace_with_chunks(tmp_path)
    before = workspace.head()
    payload = _forged_chunk_payload(workspace, before)

    with workspace.begin("chunk") as transaction:
        artifact = transaction.put_artifact(
            payload,
            kind="chunks",
            media_type="application/json",
            source_ids=tuple(sorted(before.sources)),
            producer_id=(
                f"veriformis.chunker.{before.stages['chunk'].config['strategy']}"
            ),
            producer_version="1",
            config=before.stages["chunk"].config,
        )
        with pytest.raises(WorkspaceCorruptError, match="registered clean state"):
            transaction.commit(
                outputs={"chunks": artifact},
                config=before.stages["chunk"].config,
            )

    assert workspace.head_id == before.revision_id


@pytest.mark.parametrize("mutation", ("region", "heading", "blocks", "transformed"))
def test_chunk_commit_rejects_self_consistent_false_ir_attribution(
    tmp_path, mutation
):
    workspace = _workspace_with_chunks(tmp_path)
    before = workspace.head()
    payload = _mutated_chunk_payload(workspace, before, mutation)

    with workspace.begin("chunk") as transaction:
        artifact = transaction.put_artifact(
            payload,
            kind="chunks",
            media_type="application/json",
            source_ids=tuple(sorted(before.sources)),
            producer_id=(
                f"veriformis.chunker.{before.stages['chunk'].config['strategy']}"
            ),
            producer_version="1",
            config=before.stages["chunk"].config,
        )
        with pytest.raises(WorkspaceCorruptError, match="registered clean state"):
            transaction.commit(
                outputs={"chunks": artifact},
                config=before.stages["chunk"].config,
            )

    assert workspace.head_id == before.revision_id


def test_downstream_chunk_loader_resolves_evidence_against_source(
    tmp_path, monkeypatch
):
    workspace = _workspace_with_chunks(tmp_path)
    base = workspace.head()
    payload = _forged_chunk_payload(workspace, base)
    real_validator = WorkspaceTransaction._validate_stage_semantics
    monkeypatch.setattr(
        WorkspaceTransaction,
        "_validate_stage_semantics",
        lambda self, revision: None,
    )
    with workspace.begin("chunk") as transaction:
        artifact = transaction.put_artifact(
            payload,
            kind="chunks",
            media_type="application/json",
            source_ids=tuple(sorted(base.sources)),
            producer_id=(
                f"veriformis.chunker.{base.stages['chunk'].config['strategy']}"
            ),
            producer_version="1",
            config=base.stages["chunk"].config,
        )
        transaction.commit(
            outputs={"chunks": artifact},
            config=base.stages["chunk"].config,
        )
    monkeypatch.setattr(
        WorkspaceTransaction,
        "_validate_stage_semantics",
        real_validator,
    )

    result = runner.invoke(
        app,
        ["construct", str(workspace.root), "--objective", "full_text"],
    )

    assert result.exit_code == 2
    assert "source range digest mismatch" in result.output


def test_same_stem_sources_survive_parse_without_collisions(tmp_path):
    alpha_dir = tmp_path / "alpha"
    beta_dir = tmp_path / "beta"
    alpha_dir.mkdir()
    beta_dir.mkdir()
    alpha = alpha_dir / "notes.txt"
    beta = beta_dir / "notes.txt"
    alpha.write_text("Alpha source", encoding="utf-8")
    beta.write_text("Beta source", encoding="utf-8")
    ws = tmp_path / "ws"

    result = runner.invoke(
        app,
        [
            "parse",
            str(alpha),
            str(beta),
            "-o",
            str(ws),
            "--source-root",
            str(tmp_path),
        ],
    )
    _assert_command_succeeded(result)

    workspace = Workspace.open(ws)
    revision = workspace.head()
    assert len(revision.sources) == 2
    assert len({source.id for source in revision.sources.values()}) == 2
    assert len({source.logical_path for source in revision.sources.values()}) == 2

    outputs = revision.stages["parse"].outputs
    canonical = {
        _output_bytes(workspace, revision, "parse", f"source/{source_id}/canonical")
        for source_id in revision.sources
    }
    assert canonical == {b"Alpha source", b"Beta source"}
    assert all(f"source/{source_id}/document" in outputs for source_id in revision.sources)
    assert len({outputs[f"source/{source_id}/document"] for source_id in revision.sources}) == 2


def test_parse_rejects_unknown_extension(tmp_path):
    bad = tmp_path / "data.xyz"
    bad.write_text("x")
    result = runner.invoke(
        app,
        [
            "parse",
            str(bad),
            "-o",
            str(tmp_path / "ws2"),
            "--source-root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 2
    assert "unsupported" in result.output.lower()


@pytest.mark.parametrize("package_kind", ("not-zip", "missing-document"))
def test_parse_rejects_malformed_docx_without_creating_workspace(
    tmp_path, package_kind
):
    source = tmp_path / "broken.docx"
    if package_kind == "not-zip":
        source.write_bytes(b"not a ZIP package")
    else:
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr("placeholder.txt", "missing word/document.xml")
    workspace = tmp_path / "workspace"

    result = runner.invoke(
        app,
        [
            "parse",
            str(source),
            "-o",
            str(workspace),
            "--source-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 2
    assert "error[parse-error]" in result.output
    assert "malformed or incomplete" in result.output
    assert not workspace.exists()


def test_preview_writes_nothing(tmp_path):
    src = tmp_path / "doc.txt"
    src.write_text("line\n\n42\n\nmore")
    before = set(tmp_path.iterdir())

    result = runner.invoke(
        app,
        ["preview", str(src), "--source-root", str(tmp_path)],
    )

    _assert_command_succeeded(result)
    assert "page-numbers" in result.output
    assert set(tmp_path.iterdir()) == before


def test_workspace_preview_and_clean_share_the_exact_durable_plan(tmp_path):
    src = tmp_path / "doc.txt"
    src.write_text("line   one\n\n42\n\nmore   text", encoding="utf-8")
    expected = plan_cleaning(
        parse_text(src, logical_path=src.name).document, default_rules()
    )
    expected_text = flatten(expected.document.children)

    preview_result = runner.invoke(
        app,
        ["preview", str(src), "--source-root", str(tmp_path)],
    )
    _assert_command_succeeded(preview_result)
    assert "--- after ---" in preview_result.output
    preview_text = preview_result.output.partition("--- after ---")[2].strip()
    assert preview_text == expected_text
    standalone_plan_id = next(
        line.removeprefix("plan: ")
        for line in preview_result.output.splitlines()
        if line.startswith("plan: ")
    )

    ws = tmp_path / "ws"
    _assert_command_succeeded(
        runner.invoke(
            app,
            ["parse", str(src), "-o", str(ws), "--source-root", str(tmp_path)],
        )
    )
    bound_preview = runner.invoke(app, ["preview", str(ws)])
    _assert_command_succeeded(bound_preview)
    preview_plan_id = next(
        line.removeprefix("plan: ")
        for line in bound_preview.output.splitlines()
        if line.startswith("plan: ")
    )
    _assert_command_succeeded(runner.invoke(app, ["clean", str(ws)]))

    workspace = Workspace.open(ws)
    revision = workspace.head()
    source_id = next(iter(revision.sources))
    base_document = document_from_dict(
        _json_output(workspace, revision, "parse", f"source/{source_id}/document")
    )
    cleaned_document = document_from_dict(
        _json_output(workspace, revision, "clean", f"source/{source_id}/document")
    )
    plan = cleaning_plan_from_dict(
        _json_output(workspace, revision, "clean", f"source/{source_id}/cleaning-plan")
    )

    assert replay_cleaning_plan(base_document, plan) == cleaned_document
    assert flatten(cleaned_document.children) == expected_text
    assert plan.id == preview_plan_id == standalone_plan_id


def test_preview_after_projection_includes_note_bodies(tmp_path):
    source = tmp_path / "notes.md"
    source.write_text("Body[^n]\n\n[^n]: note   body", encoding="utf-8")

    result = runner.invoke(
        app,
        ["preview", str(source), "--source-root", str(tmp_path)],
    )

    _assert_command_succeeded(result)
    after = result.output.partition("--- after ---")[2]
    assert "Body" in after
    assert "note body" in after


def test_nested_default_preview_and_parse_share_exact_plan(tmp_path, monkeypatch):
    nested = tmp_path / "nested"
    nested.mkdir()
    source = nested / "doc.txt"
    source.write_text("alpha   beta\n\n42\n\nomega", encoding="utf-8")
    workspace_path = tmp_path / "workspace"
    monkeypatch.chdir(tmp_path)

    raw_preview = runner.invoke(app, ["preview", "nested/doc.txt"])
    _assert_command_succeeded(raw_preview)
    raw_plan_id = next(
        line.removeprefix("plan: ")
        for line in raw_preview.output.splitlines()
        if line.startswith("plan: ")
    )

    parsed = runner.invoke(
        app,
        ["parse", "nested/doc.txt", "-o", str(workspace_path)],
    )
    _assert_command_succeeded(parsed)
    workspace_preview = runner.invoke(app, ["preview", str(workspace_path)])
    _assert_command_succeeded(workspace_preview)
    workspace_plan_id = next(
        line.removeprefix("plan: ")
        for line in workspace_preview.output.splitlines()
        if line.startswith("plan: ")
    )

    assert raw_plan_id == workspace_plan_id


def test_preview_outside_default_root_requires_explicit_source_root(
    tmp_path, monkeypatch
):
    working = tmp_path / "working"
    sources = tmp_path / "sources"
    working.mkdir()
    sources.mkdir()
    source = sources / "doc.txt"
    source.write_text("text", encoding="utf-8")
    monkeypatch.chdir(working)

    refused = runner.invoke(app, ["preview", str(source)])
    assert refused.exit_code == 2
    assert "outside source root" in refused.output

    accepted = runner.invoke(
        app,
        ["preview", str(source), "--source-root", str(sources)],
    )
    _assert_command_succeeded(accepted)


def test_code_parse_clean_chunk_preserves_semantic_whitespace(tmp_path):
    source = tmp_path / "program.py"
    original = "def f():\n    x =  1\n\treturn x\n"
    source.write_text(original, encoding="utf-8")
    workspace_path = tmp_path / "code-ws"

    for command in (
        [
            "parse",
            str(source),
            "-o",
            str(workspace_path),
            "--source-root",
            str(tmp_path),
        ],
        ["clean", str(workspace_path)],
        ["chunk", str(workspace_path), "--strategy", "paragraph"],
    ):
        _assert_command_succeeded(runner.invoke(app, command))

    workspace = Workspace.open(workspace_path)
    revision = workspace.head()
    source_id = next(iter(revision.sources))
    cleaned = document_from_dict(
        _json_output(
            workspace,
            revision,
            "clean",
            f"source/{source_id}/document",
        )
    )
    plan = cleaning_plan_from_dict(
        _json_output(
            workspace,
            revision,
            "clean",
            f"source/{source_id}/cleaning-plan",
        )
    )
    chunks = [
        chunk_from_dict(value)
        for value in _json_output(workspace, revision, "chunk", "chunks")
    ]

    assert cleaned.children[0].text == original
    assert plan.operations == ()
    assert "".join(chunk.text for chunk in chunks) == original


def test_nfd_unicode_survives_parse_clean_chunk_without_normalization(tmp_path):
    source = tmp_path / "unicode.txt"
    original = "Cafe\u0301   source"
    cleaned_text = "Cafe\u0301 source"
    source.write_text(original, encoding="utf-8")
    workspace_path = tmp_path / "unicode-ws"

    for command in (
        [
            "parse",
            str(source),
            "-o",
            str(workspace_path),
            "--source-root",
            str(tmp_path),
        ],
        ["clean", str(workspace_path)],
        ["chunk", str(workspace_path), "--strategy", "paragraph"],
    ):
        _assert_command_succeeded(runner.invoke(app, command))

    workspace = Workspace.open(workspace_path)
    revision = workspace.head()
    source_id = next(iter(revision.sources))
    descriptor = revision.sources[source_id]
    canonical = workspace.read_artifact(
        descriptor.extracted_artifact_id, revision=revision
    ).decode("utf-8")
    cleaned = document_from_dict(
        _json_output(
            workspace,
            revision,
            "clean",
            f"source/{source_id}/document",
        )
    )
    chunks = [
        chunk_from_dict(value)
        for value in _json_output(workspace, revision, "chunk", "chunks")
    ]

    assert canonical == original
    assert cleaned.children[0].children[0].value == cleaned_text
    assert chunks[0].text == cleaned_text
    assert "é" not in canonical
    assert "é" not in chunks[0].text


def test_chunk_stage_covers_body_and_note_regions_separately(tmp_path):
    source = tmp_path / "notes.md"
    source.write_text("Body[^n]\n\n[^n]: note   body", encoding="utf-8")
    workspace_path = tmp_path / "notes-ws"
    commands = [
        [
            "parse",
            str(source),
            "-o",
            str(workspace_path),
            "--source-root",
            str(tmp_path),
        ],
        ["clean", str(workspace_path)],
        ["chunk", str(workspace_path), "--strategy", "paragraph"],
    ]
    for command in commands:
        _assert_command_succeeded(runner.invoke(app, command))

    workspace = Workspace.open(workspace_path)
    revision = workspace.head()
    chunks = [
        chunk_from_dict(value)
        for value in _json_output(workspace, revision, "chunk", "chunks")
    ]
    by_region = {item.identity_context["region_id"]: item for item in chunks}

    assert set(by_region) == {"body", "footnote:n"}
    assert "Body" in by_region["body"].text
    assert by_region["footnote:n"].text == "note body"
    assert all(
        component.source_range.region_id == region_id
        for region_id, item in by_region.items()
        for component in item.evidence.components
    )


def test_semantic_inline_content_survives_parse_clean_chunk(tmp_path):
    source = tmp_path / "semantic.md"
    source.write_text(
        "Before ![critical diagram](image.png) [@smith2020]. Note[^n]\n\n"
        "[^n]: note detail",
        encoding="utf-8",
    )
    workspace_path = tmp_path / "semantic-ws"
    for command in (
        [
            "parse",
            str(source),
            "-o",
            str(workspace_path),
            "--source-root",
            str(tmp_path),
        ],
        ["clean", str(workspace_path)],
        ["chunk", str(workspace_path), "--strategy", "paragraph"],
    ):
        _assert_command_succeeded(runner.invoke(app, command))

    workspace = Workspace.open(workspace_path)
    revision = workspace.head()
    source_id = next(iter(revision.sources))
    canonical = workspace.read_artifact(
        revision.sources[source_id].extracted_artifact_id,
        revision=revision,
    ).decode("utf-8")
    chunks = [
        chunk_from_dict(value)
        for value in _json_output(workspace, revision, "chunk", "chunks")
    ]
    body = next(
        chunk
        for chunk in chunks
        if chunk.identity_context["region_id"] == "body"
    )

    assert "critical diagram" in canonical
    assert "[@smith2020]" in canonical
    assert "[^n]" in canonical
    assert "critical diagram" in body.text
    assert "[@smith2020]" in body.text
    assert "[^n]" in body.text


def test_format_and_validate_expose_no_row_format_override():
    format_help = runner.invoke(app, ["format", "--help"])
    validate_help = runner.invoke(app, ["validate", "--help"])

    _assert_command_succeeded(format_help)
    _assert_command_succeeded(validate_help)
    assert "--format" not in format_help.output
    assert "--format" not in validate_help.output


def test_source_identity_is_independent_of_parse_batch(tmp_path):
    primary = tmp_path / "corpus" / "primary.txt"
    unrelated = tmp_path / "other" / "extra.txt"
    primary.parent.mkdir()
    unrelated.parent.mkdir()
    primary.write_text("stable source", encoding="utf-8")
    unrelated.write_text("unrelated source", encoding="utf-8")

    first_ws = tmp_path / "first-ws"
    second_ws = tmp_path / "second-ws"
    first = runner.invoke(
        app,
        [
            "parse",
            str(primary),
            "-o",
            str(first_ws),
            "--source-root",
            str(tmp_path),
        ],
    )
    second = runner.invoke(
        app,
        [
            "parse",
            str(primary),
            str(unrelated),
            "-o",
            str(second_ws),
            "--source-root",
            str(tmp_path),
        ],
    )

    _assert_command_succeeded(first)
    _assert_command_succeeded(second)
    primary_id = next(iter(Workspace.open(first_ws).head().sources))
    sources = Workspace.open(second_ws).head().sources
    assert primary_id in sources
    assert sources[primary_id].logical_path == "corpus/primary.txt"


def test_identical_bytes_remain_source_scoped_through_clean_and_chunk(tmp_path):
    first = tmp_path / "alpha" / "same.txt"
    second = tmp_path / "beta" / "same.txt"
    first.parent.mkdir()
    second.parent.mkdir()
    payload = "identical   source text"
    first.write_text(payload, encoding="utf-8")
    second.write_text(payload, encoding="utf-8")
    workspace_path = tmp_path / "scoped-ws"
    for command in (
        [
            "parse",
            str(first),
            str(second),
            "-o",
            str(workspace_path),
            "--source-root",
            str(tmp_path),
        ],
        ["clean", str(workspace_path)],
        ["chunk", str(workspace_path), "--strategy", "paragraph"],
    ):
        _assert_command_succeeded(runner.invoke(app, command))

    workspace = Workspace.open(workspace_path)
    revision = workspace.head()
    source_ids = sorted(revision.sources)
    plans = [
        cleaning_plan_from_dict(
            _json_output(
                workspace,
                revision,
                "clean",
                f"source/{source_id}/cleaning-plan",
            )
        )
        for source_id in source_ids
    ]
    transforms = _json_output(workspace, revision, "clean", "transforms")
    chunks = [
        chunk_from_dict(value)
        for value in _json_output(workspace, revision, "chunk", "chunks")
    ]

    assert len({item.sha256 for item in revision.sources.values()}) == 1
    assert len(set(source_ids)) == 2
    assert len({plan.id for plan in plans}) == 2
    assert all(
        plan.source_id == source_id
        for plan, source_id in zip(plans, source_ids, strict=True)
    )
    assert set(plans[0].transform_record_ids).isdisjoint(
        plans[1].transform_record_ids
    )
    assert {record["source_id"] for record in transforms} == set(source_ids)
    assert len({chunk.id for chunk in chunks}) == len(chunks) == 2
    assert {chunk.source_id for chunk in chunks} == set(source_ids)


def test_absolute_source_outside_default_root_fails_closed(tmp_path):
    source = tmp_path / "outside.txt"
    source.write_text("outside", encoding="utf-8")

    result = runner.invoke(
        app,
        ["parse", str(source), "-o", str(tmp_path / "ws")],
    )

    assert result.exit_code == 2
    assert "invalid-source-locator" in result.output
    assert "--source-root" in result.output


def test_parse_refusal_never_commits_a_workspace(tmp_path, monkeypatch):
    source_path = tmp_path / "refused.txt"
    source_path.write_text("refused source", encoding="utf-8")
    parsed = parse_text(
        source_path,
        logical_path="refused.txt",
        raw_bytes=source_path.read_bytes(),
    )
    diagnostic = make_diagnostic(
        source_id=parsed.source.id,
        parser_name=parsed.source.parser,
        parser_version=parsed.source.parser_version,
        code="text.fixture-refused",
        severity="error",
        disposition="refused",
        loss_kind="unknown",
        location=DiagnosticLocation(kind="text", line_start=1, line_end=1),
        message="Fixture parser refusal.",
    )
    refused = replace(
        parsed,
        diagnostics=make_parse_report(
            source_id=parsed.source.id,
            parser_name=parsed.source.parser,
            parser_version=parsed.source.parser_version,
            diagnostics=[diagnostic],
        ),
    )
    monkeypatch.setattr(
        "veriformis.pipeline.service._parse_one",
        lambda *args, **kwargs: refused,
    )
    workspace = tmp_path / "refused-ws"

    result = runner.invoke(
        app,
        [
            "parse",
            str(source_path),
            "-o",
            str(workspace),
            "--source-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 2
    assert "error[parse-error]" in result.output
    assert "text.fixture-refused" in result.output
    assert not workspace.exists()


def test_multi_source_clean_failure_rolls_back_without_advancing_head(
    tmp_path, monkeypatch
):
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("first   source", encoding="utf-8")
    second.write_text("second   source", encoding="utf-8")
    workspace_path = tmp_path / "workspace"
    _assert_command_succeeded(
        runner.invoke(
            app,
            [
                "parse",
                str(first),
                str(second),
                "-o",
                str(workspace_path),
                "--source-root",
                str(tmp_path),
            ],
        )
    )
    before = Workspace.open(workspace_path).head()
    from veriformis.pipeline import service as pipeline_service

    real_plan = pipeline_service.plan_cleaning
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuleError("injected second-source failure")
        return real_plan(*args, **kwargs)

    monkeypatch.setattr(pipeline_service, "plan_cleaning", fail_second)

    result = runner.invoke(app, ["clean", str(workspace_path)])

    assert result.exit_code == 2
    assert "injected second-source failure" in result.output
    assert Workspace.open(workspace_path).head().revision_id == before.revision_id
    assert list((workspace_path / ".txn").iterdir()) == []


def test_clean_commit_replans_rules_and_enforces_removal_limit(tmp_path):
    source_path = tmp_path / "source.txt"
    raw = b"remove every character in this deliberately long source paragraph"
    source_path.write_bytes(raw)
    workspace_path = tmp_path / "workspace"
    _assert_command_succeeded(
        runner.invoke(
            app,
            [
                "parse",
                str(source_path),
                "-o",
                str(workspace_path),
                "--source-root",
                str(tmp_path),
            ],
        )
    )
    workspace = Workspace.open(workspace_path)
    base = workspace.head()
    source_id = next(iter(base.sources))
    descriptor = base.sources[source_id]
    parsed = parse_text(
        source_path,
        logical_path=descriptor.logical_path,
        raw_bytes=raw,
    )
    input_digest = cleaning_input_digest(
        parsed.document,
        source_id=source_id,
        raw_sha256=descriptor.sha256,
        canonical_artifact_id=descriptor.extracted_artifact_id,
        canonical_stream_sha256=parsed.source.stream_sha256,
        parser=descriptor.parser_id,
        parser_version=descriptor.parser_version,
        canonical_stream_contract_version=(
            descriptor.canonical_stream_contract_version
        ),
    )
    unsafe = plan_cleaning(
        parsed.document,
        [custom_regex(r".+")],
        max_remove_frac=1.0,
        base_input_sha256=input_digest,
    )
    assert unsafe.plan.max_remove_ppm == 1_000_000
    config = {"rules": [], "custom": r".+", "max_remove_ppm": 300_000}
    derivations = build_block_derivations(
        parsed.source,
        unsafe.document,
        cleaning_plan_id=unsafe.plan.id,
    )

    with workspace.begin("clean") as transaction:
        document_artifact = transaction.put_artifact(
            lossless_json_bytes(document_to_dict(unsafe.document)),
            kind="cleaned-document-ir",
            media_type="application/json",
            source_ids=(source_id,),
            producer_id="veriformis.cleaning",
            producer_version="1",
            config=config,
        )
        plan_artifact = transaction.put_artifact(
            lossless_json_bytes(cleaning_plan_to_dict(unsafe.plan)),
            kind="cleaning-plan",
            media_type="application/json",
            source_ids=(source_id,),
            producer_id="veriformis.cleaning",
            producer_version="1",
            config=config,
        )
        derivation_artifact = transaction.put_artifact(
            lossless_json_bytes(block_derivations_to_dict(derivations)),
            kind="block-derivations",
            media_type="application/json",
            source_ids=(source_id,),
            producer_id="veriformis.cleaning",
            producer_version="1",
            config={**config, "cleaning_plan_id": unsafe.plan.id},
        )
        transforms_artifact = transaction.put_artifact(
            lossless_json_bytes(
                [transform_record_to_dict(record) for record in unsafe.records]
            ),
            kind="transform-records",
            media_type="application/json",
            source_ids=(source_id,),
            producer_id="veriformis.cleaning",
            producer_version="1",
            config=config,
        )
        with pytest.raises(WorkspaceCorruptError, match="configured replay"):
            transaction.commit(
                outputs={
                    "transforms": transforms_artifact,
                    f"source/{source_id}/document": document_artifact,
                    f"source/{source_id}/cleaning-plan": plan_artifact,
                    f"source/{source_id}/block-derivations": derivation_artifact,
                },
                config=config,
            )

    assert workspace.head_id == base.revision_id


def test_clean_commit_rejects_alternate_noncanonical_derivation(tmp_path):
    workspace = _workspace_with_chunks(tmp_path)
    base = workspace.head()
    source_id = next(iter(base.sources))
    plan = cleaning_plan_from_dict(
        _json_output(
            workspace,
            base,
            "clean",
            f"source/{source_id}/cleaning-plan",
        )
    )
    raw_derivations = _json_output(
        workspace,
        base,
        "clean",
        f"source/{source_id}/block-derivations",
    )
    alternate = edits_derivation(
        "first   paragraph",
        [EvidenceEdit(5, 8, "   ", " ")],
        context={
            "cleaning_plan_id": plan.id,
            "source_id": source_id,
            "block_index": 0,
        },
    )
    raw_derivations["0"] = [derivation_to_dict(alternate)]
    outputs = dict(base.stages["clean"].outputs)

    with workspace.begin("clean") as transaction:
        replacement = transaction.put_artifact(
            lossless_json_bytes(raw_derivations),
            kind="block-derivations",
            media_type="application/json",
            source_ids=(source_id,),
            producer_id="veriformis.cleaning",
            producer_version="1",
            config={**base.stages["clean"].config, "cleaning_plan_id": plan.id},
        )
        outputs[f"source/{source_id}/block-derivations"] = replacement.id
        with pytest.raises(WorkspaceCorruptError, match="canonical cleaning replay"):
            transaction.commit(
                outputs=outputs,
                config=base.stages["clean"].config,
            )

    assert workspace.head_id == base.revision_id


def test_identical_pipeline_runs_have_identical_semantic_outputs(tmp_path):
    snapshots = []
    for name in ("machine-a", "machine-b"):
        root = tmp_path / name
        root.mkdir()
        source = root / "source.txt"
        source.write_text("Alpha   beta. Second sentence.", encoding="utf-8")
        workspace_path = root / "workspace"
        stage_states = []
        commands = [
            [
                "parse",
                str(source),
                "-o",
                str(workspace_path),
                "--source-root",
                str(root),
            ],
            ["clean", str(workspace_path)],
            ["chunk", str(workspace_path), "--strategy", "sentence"],
        ]
        for command in commands:
            _assert_command_succeeded(runner.invoke(app, command))
            revision = Workspace.open(workspace_path).head()
            stage_states.append((revision.revision_id, revision.state_digest))

        workspace = Workspace.open(workspace_path)
        final = workspace.head()
        source_id = next(iter(final.sources))
        plan_id = final.stages["clean"].outputs[
            f"source/{source_id}/cleaning-plan"
        ]
        chunks = [
            chunk_from_dict(value)
            for value in _json_output(workspace, final, "chunk", "chunks")
        ]
        snapshots.append(
            {
                "revision_ids": [item[0] for item in stage_states],
                "state_digests": [item[1] for item in stage_states],
                "plan_artifact_id": plan_id,
                "chunk_ids": [item.id for item in chunks],
                "evidence_ids": [item.evidence.evidence_id for item in chunks],
            }
        )

    assert snapshots[0]["revision_ids"] != snapshots[1]["revision_ids"]
    assert snapshots[0]["state_digests"] == snapshots[1]["state_digests"]
    assert snapshots[0]["plan_artifact_id"] == snapshots[1]["plan_artifact_id"]
    assert snapshots[0]["chunk_ids"] == snapshots[1]["chunk_ids"]
    assert snapshots[0]["evidence_ids"] == snapshots[1]["evidence_ids"]


def test_reconfigured_cleaning_converges_to_fresh_semantic_outputs(tmp_path):
    source = tmp_path / "history.txt"
    source.write_text(
        "Alpha   https://example.test/value   omega",
        encoding="utf-8",
    )
    fresh_path = tmp_path / "fresh-ws"
    reconfigured_path = tmp_path / "reconfigured-ws"

    for workspace_path in (fresh_path, reconfigured_path):
        _assert_command_succeeded(
            runner.invoke(
                app,
                [
                    "parse",
                    str(source),
                    "-o",
                    str(workspace_path),
                    "--source-root",
                    str(tmp_path),
                ],
            )
        )
    _assert_command_succeeded(runner.invoke(app, ["clean", str(fresh_path)]))
    _assert_command_succeeded(runner.invoke(app, ["chunk", str(fresh_path)]))

    _assert_command_succeeded(
        runner.invoke(
            app,
            ["clean", str(reconfigured_path), "--rules", "urls"],
        )
    )
    _assert_command_succeeded(
        runner.invoke(app, ["clean", str(reconfigured_path)])
    )
    _assert_command_succeeded(
        runner.invoke(app, ["chunk", str(reconfigured_path)])
    )

    fresh = Workspace.open(fresh_path)
    reconfigured = Workspace.open(reconfigured_path)
    first = fresh.head()
    second = reconfigured.head()
    source_id = next(iter(first.sources))
    first_plan = cleaning_plan_from_dict(
        _json_output(
            fresh,
            first,
            "clean",
            f"source/{source_id}/cleaning-plan",
        )
    )
    second_plan = cleaning_plan_from_dict(
        _json_output(
            reconfigured,
            second,
            "clean",
            f"source/{source_id}/cleaning-plan",
        )
    )
    first_chunks = [
        chunk_from_dict(value)
        for value in _json_output(fresh, first, "chunk", "chunks")
    ]
    second_chunks = [
        chunk_from_dict(value)
        for value in _json_output(reconfigured, second, "chunk", "chunks")
    ]

    assert first.revision_id != second.revision_id
    assert first.state_digest == second.state_digest
    assert first_plan.id == second_plan.id
    assert first_plan.base_input_sha256 == second_plan.base_input_sha256
    assert [chunk.id for chunk in first_chunks] == [
        chunk.id for chunk in second_chunks
    ]
    assert [chunk.evidence.evidence_id for chunk in first_chunks] == [
        chunk.evidence.evidence_id for chunk in second_chunks
    ]


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0 and "0.1.0" in result.output
