"""Discovery-closed Phase 6 goal acceptance matrix.

Every frozen cell starts from two exact, distinct raw sources and runs the
complete compiler through an externally pinned bundle verification. The safe
preset remains authoritative, so every compile must retain a non-empty train
and evaluation partition. Plain-text source A also contains an internal exact
duplicate plus unique evidence, making exclusion coverage non-vacuous without
leaving any selected source unrepresented.

``supervision_sha256`` binds the default product preview sample (the first
accepted record for each primary source).  The row-set digest independently
binds every formatted record emitted by the compile.
"""

from __future__ import annotations

import base64
import io
import json
import sys
import tempfile
import unicodedata
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest
import yaml
from docx import Document as DocxBuilder
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.datasets import row_set_from_json_bytes
from veriformis.goals import (
    goal_catalog,
    goal_catalog_json,
    preset_catalog_json,
)
from veriformis.identity import canonical_digest, sha256_digest
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.pipeline.service import _load_constructed_dataset
from veriformis.recipes import load_pipeline_spec, run_pipeline_spec
from veriformis.taxonomy import IMPLEMENTED_INPUT_FAMILIES
from veriformis.workspace import Workspace


ROOT = Path(__file__).parents[2]
FIXTURE = (
    ROOT
    / "tests"
    / "regressions"
    / "fixtures"
    / "phase6"
    / ("goal-acceptance-matrix.json")
)
PDF_FIXTURE = ROOT / "tests" / "fixtures" / "group5" / "minimal-text.pdf"
SCHEMA_ID = "veriformis.goal-acceptance-matrix/v1"
SERVICE = PipelineService()
RUNNER = CliRunner()

_TOP_LEVEL_KEYS = {
    "schema_id",
    "catalog_sha256",
    "preset_catalog_sha256",
    "source_fixtures",
    "cells",
}
_SOURCE_KEYS = {
    "source_fixture_id",
    "input_family",
    "logical_path",
    "raw_base64",
    "sha256",
    "size",
}
_CELL_KEYS = {
    "cell_id",
    "source_fixture_ids",
    "input_family",
    "goal_id",
    "preset_id",
    "representation_id",
    "instruction",
    "cleaning_rules",
    "cleaning_custom",
    "chunk_size",
    "chunk_overlap",
    "evaluation_required",
    "recipe_id",
    "row_set_sha256",
    "manifest_sha256",
    "loss_policy",
    "loss_boundary",
    "context_row_keys",
    "supervised_row_key",
    "supervision_sha256",
    "exclusions",
}
_OBSERVATION_KEYS = (
    "recipe_id",
    "row_set_sha256",
    "manifest_sha256",
    "loss_policy",
    "loss_boundary",
    "context_row_keys",
    "supervised_row_key",
    "supervision_sha256",
    "exclusions",
)
_SOURCE_LOGICAL_PATHS = {
    "plain-text": ("source-a.txt", "source-b.txt"),
    "source-code": ("source-a.py", "source-b.js"),
    "markdown": ("source-a.md", "source-b.md"),
    "word-document": ("source-a.docx", "source-b.docx"),
    "html": ("source-a.html", "source-b.html"),
    "pdf-text": ("source-a.pdf", "source-b.pdf"),
    "delimited-table": ("source-a.csv", "source-b.csv"),
    "json-records": ("source-a.jsonl", "source-b.jsonl"),
}
_BEFORE_AFTER_CUSTOM = {
    "plain-text": "REMOVE",
    "markdown": "REMOVE",
    "word-document": "REMOVE",
    "html": "REMOVE",
    "pdf-text": "PDF",
    "delimited-table": "alpha",
    "json-records": "first",
}
_INSTRUCTIONS = {
    "continue-a-passage": "Continue the passage with its exact source remainder.",
    "recover-a-section-from-its-heading": (
        "Produce the exact source section body for this heading."
    ),
    "reproduce-a-recorded-change": (
        "Apply the recorded cleaning change to this exact source text."
    ),
    "extract-a-structured-value": (
        "Produce the exact structural attribute recorded by this source."
    ),
}


def _canonical_docx_bytes(*, heading: str, level: int, body: str) -> bytes:
    raw = io.BytesIO()
    document = DocxBuilder()
    document.add_heading(heading, level=level)
    document.add_paragraph(body)
    document.save(raw)

    normalized = io.BytesIO()
    with (
        ZipFile(io.BytesIO(raw.getvalue()), "r") as source,
        ZipFile(
            normalized,
            "w",
            compression=ZIP_DEFLATED,
            compresslevel=9,
        ) as output,
    ):
        for name in sorted(source.namelist()):
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = 0
            output.writestr(
                info,
                source.read(name),
                compress_type=ZIP_DEFLATED,
                compresslevel=9,
            )
    return normalized.getvalue()


def _source_pairs() -> dict[str, tuple[bytes, bytes]]:
    duplicate_paragraph = (
        "Duplicate REMOVE café evidence. "
        + ("Faithful source-grounded words continue here. " * 13)
        + "A naïve ending remains exact."
    )
    unique_paragraph = (
        "Unique REMOVE café evidence. "
        + ("Distinct source-grounded words continue here. " * 13)
        + "Another naïve ending remains exact."
    )
    source_b_paragraph = (
        "Independent REMOVE café evidence. "
        + ("Separate source-grounded words continue here. " * 13)
        + "Its naïve ending also remains exact."
    )
    assert all(
        500 <= len(paragraph) <= 800
        for paragraph in (duplicate_paragraph, unique_paragraph, source_b_paragraph)
    )
    pdf_a = PDF_FIXTURE.read_bytes()
    assert pdf_a.count(b"Hello") == 1
    assert pdf_a.count(b"text") == 1
    pdf_a = pdf_a.replace(b"text", b"caf\xe9")
    pdf_b = pdf_a.replace(b"Hello", b"Other")
    assert len(pdf_b) == len(pdf_a)
    return {
        "plain-text": (
            (
                f"{duplicate_paragraph}\n\n{duplicate_paragraph}\n\n{unique_paragraph}\n"
            ).encode("utf-8"),
            f"{source_b_paragraph}\n".encode("utf-8"),
        ),
        "source-code": (
            'def exact_source_value(number):\n    return f"café {number + 1}"\n'.encode(
                "utf-8"
            ),
            (
                "function distinctSourceValue(number) {\n"
                "  return `naïve ${number + 2}`;\n"
                "}\n"
            ).encode("utf-8"),
        ),
        "markdown": (
            (
                "# Recovered heading\n\n"
                "Body REMOVE café text beneath the heading; naïve source remains exact.\n"
            ).encode("utf-8"),
            (
                "## Distinct recovered heading\n\n"
                "Distinct body REMOVE café text; naïve source remains exact.\n"
            ).encode("utf-8"),
        ),
        "word-document": (
            _canonical_docx_bytes(
                heading="Recovered heading",
                level=1,
                body=(
                    "Body REMOVE café text beneath the heading; naïve source remains exact."
                ),
            ),
            _canonical_docx_bytes(
                heading="Distinct recovered heading",
                level=2,
                body="Distinct body REMOVE café text; naïve source remains exact.",
            ),
        ),
        "html": (
            (
                "<!doctype html><html><body><h1>Recovered heading</h1>"
                "<p>Body REMOVE café text; naïve source remains exact.</p>"
                "</body></html>"
            ).encode("utf-8"),
            (
                "<!doctype html><html><body><h2>Distinct recovered heading</h2>"
                "<p>Distinct body REMOVE café text; naïve source remains exact.</p>"
                "</body></html>"
            ).encode("utf-8"),
        ),
        "pdf-text": (pdf_a, pdf_b),
        "delimited-table": (
            (
                "name,value\nalpha,café first exact source value\n"
                "beta,naïve second exact source value\n"
            ).encode("utf-8"),
            (
                "name,value\nalpha,café distinct exact source value\n"
                "gamma,another naïve distinct source value\n"
            ).encode("utf-8"),
        ),
        "json-records": (
            (
                '{"text":"first café exact source-grounded record"}\n'
                '{"text":"second naïve exact source-grounded record"}\n'
            ).encode("utf-8"),
            (
                '{"text":"first café distinct source-grounded record"}\n'
                '{"text":"third naïve distinct source-grounded record"}\n'
            ).encode("utf-8"),
        ),
    }


def _source_fixture_ids(family: str) -> list[str]:
    return [f"{family}-{variant}-v1" for variant in ("a", "b")]


def _source_descriptors() -> list[dict[str, object]]:
    descriptors: list[dict[str, object]] = []
    pairs = _source_pairs()
    for family in IMPLEMENTED_INPUT_FAMILIES:
        source_a, source_b = pairs[family]
        for fixture_id, logical_path, raw in zip(
            _source_fixture_ids(family),
            _SOURCE_LOGICAL_PATHS[family],
            (source_a, source_b),
            strict=True,
        ):
            descriptors.append(
                {
                    "source_fixture_id": fixture_id,
                    "input_family": family,
                    "logical_path": logical_path,
                    "raw_base64": base64.b64encode(raw).decode("ascii"),
                    "sha256": sha256_digest(raw),
                    "size": len(raw),
                }
            )
    return descriptors


def _cell_selections() -> list[dict[str, object]]:
    selections: list[dict[str, object]] = []
    for goal in goal_catalog().goals:
        if goal.objective in {"explicit_label", "preference_pair", "tool_call"}:
            continue
        for family in goal.eligible_input_families:
            for representation_id in goal.compatible_representations:
                selections.append(
                    {
                        "cell_id": (f"{goal.goal_id}__{family}__{representation_id}"),
                        "source_fixture_ids": _source_fixture_ids(family),
                        "input_family": family,
                        "goal_id": goal.goal_id,
                        "preset_id": f"{goal.goal_id}.safe",
                        "representation_id": representation_id,
                        "instruction": (
                            _INSTRUCTIONS[goal.goal_id]
                            if representation_id == "instruction-and-output"
                            else None
                        ),
                        "cleaning_rules": "",
                        "cleaning_custom": (
                            _BEFORE_AFTER_CUSTOM[family]
                            if goal.goal_id == "reproduce-a-recorded-change"
                            else ""
                        ),
                        "chunk_size": (
                            24
                            if goal.goal_id == "reproduce-a-recorded-change"
                            else None
                        ),
                        "chunk_overlap": (
                            0 if goal.goal_id == "reproduce-a-recorded-change" else None
                        ),
                        "evaluation_required": True,
                    }
                )
    return selections


def _load_fixture() -> dict[str, object]:
    text = FIXTURE.read_text(encoding="utf-8")
    value = json.loads(text)
    assert json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n" == text
    return value


def _source_map(fixture: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(item["source_fixture_id"]): item for item in fixture["source_fixtures"]}


def _materialize_sources(
    root: Path,
    cell: dict[str, object],
    sources: dict[str, dict[str, object]],
) -> tuple[Path, list[Path]]:
    source_root = root / "sources"
    source_root.mkdir(parents=True)
    paths = []
    for fixture_id in cell["source_fixture_ids"]:
        descriptor = sources[str(fixture_id)]
        raw = base64.b64decode(str(descriptor["raw_base64"]), validate=True)
        assert len(raw) == descriptor["size"]
        assert sha256_digest(raw) == descriptor["sha256"]
        source = source_root / str(descriptor["logical_path"])
        source.write_bytes(raw)
        paths.append(source)
    return source_root, paths


def _artifact_bytes(workspace: Workspace, stage: str, key: str) -> bytes:
    revision = workspace.head()
    artifact_id = revision.stages[stage].outputs[key]
    return workspace.read_artifact(artifact_id, revision=revision)


def _supervised_text(record) -> str:
    assert record.rendered_row is not None
    if record.supervised.row_key == "messages[1].content":
        return str(record.rendered_row["messages"][1]["content"])
    return str(record.rendered_row[record.supervised.row_key])


def _is_nfc_with_non_ascii(value: str) -> bool:
    return value == unicodedata.normalize("NFC", value) and any(
        ord(character) > 127 for character in value
    )


def _observe(
    workspace_path: Path,
    bundle: Path,
    *,
    surface_preview: dict[str, object] | None = None,
) -> dict[str, object]:
    workspace = Workspace.open(workspace_path)
    revision = workspace.head()
    recipe, _, _ = _load_constructed_dataset(workspace, revision)
    preview_outcome = SERVICE.preview_goal(workspace_path)
    assert preview_outcome.preview is not None
    preview = preview_outcome.preview
    if surface_preview is not None:
        assert surface_preview == preview.model_dump(mode="json")
    assert len(preview.records) == 2
    assert preview.omitted_exclusion_count == 0
    assert all(
        exclusion.status == "excluded"
        and exclusion.reason_codes == ("exact-duplicate",)
        for exclusion in preview.exclusions
    )
    boundaries = []
    for record in preview.records:
        supervised = _supervised_text(record)
        if preview.objective == "structured_field":
            assert record.context is not None
            assert any(
                _is_nfc_with_non_ascii(value) for value in record.context.values()
            )
        else:
            assert _is_nfc_with_non_ascii(supervised)
        assert record.supervised.start == 0
        assert record.supervised.end == len(supervised)
        boundaries.append(
            {
                "record_id": record.record_id,
                "context_row_keys": list(record.context_row_keys),
                "row_key": record.supervised.row_key,
                "start": record.supervised.start,
                "end": record.supervised.end,
                "target_sha256": sha256_digest(supervised),
            }
        )
    context_row_keys = (
        list(preview.records[0].context_row_keys) if preview.records else []
    )
    supervised_row_key = (
        preview.records[0].supervised.row_key if preview.records else ""
    )
    assert all(
        list(record.context_row_keys) == context_row_keys
        and record.supervised.row_key == supervised_row_key
        for record in preview.records
    )
    row_set_bytes = _artifact_bytes(workspace, "format", "row-set")
    row_set = row_set_from_json_bytes(row_set_bytes)
    assert row_set.train_row_count > 0
    assert row_set.evaluation_row_count > 0
    manifest = (bundle / "manifest.json").read_bytes()
    return {
        "recipe_id": recipe.recipe_id,
        "row_set_sha256": sha256_digest(row_set_bytes),
        "manifest_sha256": sha256_digest(manifest),
        "loss_policy": preview.loss_policy,
        "loss_boundary": preview.loss_boundary,
        "context_row_keys": context_row_keys,
        "supervised_row_key": supervised_row_key,
        "supervision_sha256": canonical_digest(boundaries),
        "exclusions": [
            {
                "record_id": exclusion.record_id,
                "status": exclusion.status,
                "reason_codes": list(exclusion.reason_codes),
            }
            for exclusion in preview.exclusions
        ],
    }


def _verify_external(bundle: Path, manifest_sha256: str) -> None:
    verified = SERVICE.verify(bundle, manifest_sha256=manifest_sha256)
    assert verified.verification is not None
    assert verified.verification.trust_grade == "external_digest"


def _manifest_sha_for_verify(cell: dict[str, object], bundle: Path) -> str:
    actual = sha256_digest((bundle / "manifest.json").read_bytes())
    expected = str(cell.get("manifest_sha256", actual))
    assert actual == expected
    return expected


def _finish_python(
    root: Path,
    cell: dict[str, object],
    sources: dict[str, dict[str, object]],
) -> dict[str, object]:
    source_root, source_paths = _materialize_sources(root, cell, sources)
    workspace = root / "workspace"
    bundle = root / "out.vfbundle"
    SERVICE.parse(source_paths, workspace, source_root=source_root)
    SERVICE.clean(
        workspace,
        rules=str(cell["cleaning_rules"]),
        custom=str(cell["cleaning_custom"]),
    )
    if cell["chunk_size"] is None:
        SERVICE.chunk(workspace, preset=str(cell["preset_id"]))
    else:
        SERVICE.chunk(
            workspace,
            preset=str(cell["preset_id"]),
            size=int(cell["chunk_size"]),
            overlap=int(cell["chunk_overlap"]),
        )
    construct_selection = {
        "goal": str(cell["goal_id"]),
        "representation": str(cell["representation_id"]),
    }
    if cell["chunk_size"] is None:
        construct_selection["preset"] = str(cell["preset_id"])
    constructed = SERVICE.construct(workspace, **construct_selection)
    SERVICE.curate(
        workspace,
        preset=str(cell["preset_id"]),
        instruction=cell["instruction"],
    )
    SERVICE.split(workspace)
    SERVICE.format(workspace)
    validated = SERVICE.validate(workspace)
    assert validated.exit_status == 0
    sealed = SERVICE.seal(workspace, bundle)
    assert sealed.publication is not None
    assert constructed.recipe_id is not None
    manifest_sha256 = _manifest_sha_for_verify(cell, bundle)
    assert sealed.publication.manifest_sha256 == manifest_sha256
    _verify_external(bundle, manifest_sha256)
    return _observe(workspace, bundle)


def _cli_ok(args: list[str]) -> str:
    result = RUNNER.invoke(app, args)
    assert result.exit_code == 0, result.output
    return result.output


def _finish_cli(
    root: Path,
    cell: dict[str, object],
    sources: dict[str, dict[str, object]],
) -> dict[str, object]:
    source_root, source_paths = _materialize_sources(root, cell, sources)
    workspace = root / "workspace"
    bundle = root / "out.vfbundle"
    _cli_ok(
        [
            "parse",
            *(str(source) for source in source_paths),
            "-o",
            str(workspace),
            "--source-root",
            str(source_root),
        ]
    )
    clean = ["clean", str(workspace)]
    if cell["cleaning_rules"]:
        clean.extend(["--rules", str(cell["cleaning_rules"])])
    if cell["cleaning_custom"]:
        clean.extend(["--custom", str(cell["cleaning_custom"])])
    _cli_ok(clean)
    chunk = ["chunk", str(workspace)]
    if cell["chunk_size"] is None:
        chunk.extend(["--preset", str(cell["preset_id"])])
    else:
        chunk.extend(
            [
                "--preset",
                str(cell["preset_id"]),
                "--size",
                str(cell["chunk_size"]),
                "--overlap",
                str(cell["chunk_overlap"]),
            ]
        )
    _cli_ok(chunk)
    construct = [
        "construct",
        str(workspace),
        "--goal",
        str(cell["goal_id"]),
        "--representation",
        str(cell["representation_id"]),
    ]
    if cell["chunk_size"] is None:
        construct.extend(["--preset", str(cell["preset_id"])])
    _cli_ok(construct)
    curate = [
        "curate",
        str(workspace),
        "--preset",
        str(cell["preset_id"]),
    ]
    if cell["instruction"] is not None:
        curate.extend(["--instruction", str(cell["instruction"])])
    _cli_ok(curate)
    for command in ("split", "format", "validate"):
        _cli_ok([command, str(workspace)])
    _cli_ok(["seal", str(workspace), "-o", str(bundle)])
    manifest_sha256 = _manifest_sha_for_verify(cell, bundle)
    verify_output = _cli_ok(
        ["verify", str(bundle), "--manifest-sha256", manifest_sha256]
    )
    assert "external_digest" in verify_output
    cli_preview = json.loads(_cli_ok(["goal-preview", str(workspace)]))
    return _observe(workspace, bundle, surface_preview=cli_preview)


def _mcp_tools() -> dict[str, object]:
    return {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }


def _mcp_json(tool, *args, **kwargs) -> dict[str, object]:
    return json.loads(tool(*args, **kwargs))


def _finish_mcp(
    root: Path,
    cell: dict[str, object],
    sources: dict[str, dict[str, object]],
) -> dict[str, object]:
    source_root, source_paths = _materialize_sources(root, cell, sources)
    workspace = root / "workspace"
    bundle = root / "out.vfbundle"
    tools = _mcp_tools()
    _mcp_json(
        tools["parse"],
        [str(source) for source in source_paths],
        str(workspace),
        str(source_root),
    )
    _mcp_json(
        tools["clean"],
        str(workspace),
        str(cell["cleaning_rules"]),
        str(cell["cleaning_custom"]),
    )
    if cell["chunk_size"] is None:
        _mcp_json(
            tools["chunk"],
            str(workspace),
            preset=str(cell["preset_id"]),
        )
    else:
        _mcp_json(
            tools["chunk"],
            str(workspace),
            size=int(cell["chunk_size"]),
            overlap=int(cell["chunk_overlap"]),
            preset=str(cell["preset_id"]),
        )
    construct_selection = {
        "goal": str(cell["goal_id"]),
        "representation": str(cell["representation_id"]),
    }
    if cell["chunk_size"] is None:
        construct_selection["preset"] = str(cell["preset_id"])
    construct_payload = _mcp_json(
        tools["construct"], str(workspace), **construct_selection
    )
    assert isinstance(construct_payload.get("recipe_id"), str)
    _mcp_json(
        tools["curate"],
        str(workspace),
        instruction=cell["instruction"],
        preset=str(cell["preset_id"]),
    )
    for tool_name in ("split", "format_rows"):
        _mcp_json(tools[tool_name], str(workspace))
    validate_payload = _mcp_json(tools["validate"], str(workspace))
    assert validate_payload["exit_status"] == 0
    seal_payload = _mcp_json(tools["seal"], str(workspace), str(bundle))
    manifest_sha256 = _manifest_sha_for_verify(cell, bundle)
    assert seal_payload["publication"]["manifest_sha256"] == manifest_sha256
    verify_payload = _mcp_json(tools["verify"], str(bundle), manifest_sha256)
    assert verify_payload["verification"]["trust_grade"] == "external_digest"
    mcp_preview = _mcp_json(tools["goal_preview"], str(workspace))
    observed = _observe(workspace, bundle, surface_preview=mcp_preview)
    assert construct_payload["recipe_id"] == observed["recipe_id"]
    return observed


def _finish_yaml(
    root: Path,
    cell: dict[str, object],
    sources: dict[str, dict[str, object]],
) -> dict[str, object]:
    source_root, source_paths = _materialize_sources(root, cell, sources)
    workspace = root / "workspace"
    bundle = root / "out.vfbundle"
    clean: dict[str, object] = {}
    if cell["cleaning_rules"]:
        clean["rules"] = cell["cleaning_rules"]
    if cell["cleaning_custom"]:
        clean["custom"] = cell["cleaning_custom"]
    curate: dict[str, object] = {"preset": cell["preset_id"]}
    if cell["instruction"] is not None:
        curate["instruction"] = cell["instruction"]
    spec_path = root / "pipeline.yaml"
    spec_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "veriformis.pipeline/v1",
                "workspace": str(workspace),
                "source_root": str(source_root),
                "sources": [str(source) for source in source_paths],
                "stages": {
                    "parse": {},
                    "clean": clean,
                    "chunk": (
                        {"preset": cell["preset_id"]}
                        if cell["chunk_size"] is None
                        else {
                            "preset": cell["preset_id"],
                            "size": cell["chunk_size"],
                            "overlap": cell["chunk_overlap"],
                        }
                    ),
                    "construct": {
                        **(
                            {"preset": cell["preset_id"]}
                            if cell["chunk_size"] is None
                            else {}
                        ),
                        "goal": cell["goal_id"],
                        "representation": cell["representation_id"],
                    },
                    "curate": curate,
                    "split": {},
                    "format": {},
                    "validate": {},
                    "seal": {"out": str(bundle)},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    result = run_pipeline_spec(load_pipeline_spec(spec_path))
    assert result.bundle == bundle
    assert all(outcome.exit_status == 0 for outcome in result.outcomes)
    manifest_sha256 = _manifest_sha_for_verify(cell, bundle)
    _verify_external(bundle, manifest_sha256)
    return _observe(workspace, bundle)


_SURFACES = {
    "python": _finish_python,
    "cli": _finish_cli,
    "mcp": _finish_mcp,
    "yaml": _finish_yaml,
}


def _expected(cell: dict[str, object]) -> dict[str, object]:
    return {key: cell[key] for key in _OBSERVATION_KEYS}


def _case_ids() -> list[str]:
    if not FIXTURE.exists():
        return []
    return [str(cell["cell_id"]) for cell in _load_fixture()["cells"]]


def test_frozen_matrix_is_canonical_discovery_closed_and_path_independent() -> None:
    fixture = _load_fixture()
    assert set(fixture) == _TOP_LEVEL_KEYS
    assert fixture["schema_id"] == SCHEMA_ID
    assert fixture["catalog_sha256"] == sha256_digest(goal_catalog_json())
    assert fixture["preset_catalog_sha256"] == sha256_digest(preset_catalog_json())
    assert len(fixture["source_fixtures"]) == len(IMPLEMENTED_INPUT_FAMILIES) * 2 == 16
    assert [item["input_family"] for item in fixture["source_fixtures"]] == [
        family for family in IMPLEMENTED_INPUT_FAMILIES for _ in range(2)
    ]
    generated_sources = {
        item["source_fixture_id"]: item for item in _source_descriptors()
    }
    for source in fixture["source_fixtures"]:
        assert set(source) == _SOURCE_KEYS
        assert source == generated_sources[source["source_fixture_id"]]
        logical_path = Path(source["logical_path"])
        assert not logical_path.is_absolute() and ".." not in logical_path.parts
    for family in IMPLEMENTED_INPUT_FAMILIES:
        source_a, source_b = (
            generated_sources[fixture_id] for fixture_id in _source_fixture_ids(family)
        )
        assert source_a["raw_base64"] != source_b["raw_base64"]
        assert source_a["logical_path"] != source_b["logical_path"]

    expected_selections = _cell_selections()
    # These small before/after windows are explicit evidence-shape controls.
    # They prove the goal's contract without claiming that the safe preset's
    # default segmentation happens to isolate every cleaning edit.
    for selection in expected_selections:
        if selection["goal_id"] == "reproduce-a-recorded-change":
            assert selection["chunk_size"] == 24
            assert selection["chunk_overlap"] == 0
        else:
            assert selection["chunk_size"] is None
            assert selection["chunk_overlap"] is None
    observed_selections = [
        {key: cell[key] for key in expected_selections[0]} for cell in fixture["cells"]
    ]
    assert observed_selections == expected_selections
    assert len(fixture["cells"]) == len(expected_selections) == 74
    for cell in fixture["cells"]:
        assert set(cell) == _CELL_KEYS
        assert cell["source_fixture_ids"] == _source_fixture_ids(cell["input_family"])
        assert cell["evaluation_required"] is True
        assert all(
            set(exclusion) == {"record_id", "status", "reason_codes"}
            and exclusion["status"] == "excluded"
            and exclusion["reason_codes"] == ["exact-duplicate"]
            for exclusion in cell["exclusions"]
        )
        assert all(
            not Path(value).is_absolute()
            for key, value in cell.items()
            if key.endswith("_id") and isinstance(value, str)
        )
        assert all(
            not Path(value).is_absolute() for value in cell["source_fixture_ids"]
        )
    assert any(
        cell["exclusions"]
        for cell in fixture["cells"]
        if cell["input_family"] == "plain-text"
    )


@pytest.mark.parametrize("surface", tuple(_SURFACES))
@pytest.mark.parametrize("cell_id", _case_ids())
def test_every_surface_seals_each_frozen_matrix_cell(
    tmp_path: Path,
    surface: str,
    cell_id: str,
) -> None:
    fixture = _load_fixture()
    cells = {cell["cell_id"]: cell for cell in fixture["cells"]}
    cell = cells[cell_id]
    observed = _SURFACES[surface](tmp_path, cell, _source_map(fixture))
    assert observed == _expected(cell)


def _generate_fixture() -> dict[str, object]:
    fixture: dict[str, object] = {
        "schema_id": SCHEMA_ID,
        "catalog_sha256": sha256_digest(goal_catalog_json()),
        "preset_catalog_sha256": sha256_digest(preset_catalog_json()),
        "source_fixtures": _source_descriptors(),
        "cells": [],
    }
    sources = _source_map(fixture)
    cells = []
    with tempfile.TemporaryDirectory(prefix="veriformis-phase6-matrix-") as temporary:
        temporary_root = Path(temporary)
        for cell in _cell_selections():
            try:
                observed = _finish_python(
                    temporary_root / str(cell["cell_id"]), cell, sources
                )
            except Exception as exc:
                raise RuntimeError(
                    f"matrix generation failed for {cell['cell_id']}"
                ) from exc
            cells.append({**cell, **observed})
    fixture["cells"] = cells
    return fixture


if __name__ == "__main__":
    if sys.argv[1:] != ["--generate"]:
        raise SystemExit("usage: test_phase6_goal_acceptance_matrix.py --generate")
    print(json.dumps(_generate_fixture(), ensure_ascii=True, indent=2, sort_keys=True))
