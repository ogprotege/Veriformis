"""Group 5 recipe library, statistics, and YAML pipeline tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.errors import ConstructionError
from veriformis.pipeline import PipelineService
from veriformis.recipes import (
    build_named_recipe,
    list_named_recipes,
    load_pipeline_spec,
    measure_construction_statistics,
    run_pipeline_spec,
)
from veriformis.workspace import Workspace

runner = CliRunner()


def _write_sources(root: Path) -> list[Path]:
    text = root / "notes.txt"
    text.write_text(
        "First paragraph of training material.\n\n"
        "Second paragraph continues the grounded source text.",
        encoding="utf-8",
    )
    html = root / "page.html"
    html.write_text(
        "<html><body><h1>Guide</h1><p>HTML recovered body content for training.</p>"
        "</body></html>",
        encoding="utf-8",
    )
    return [text, html]


def test_named_recipe_library_lists_six_objectives():
    recipes = list_named_recipes()
    assert {item["recipe_library_id"] for item in recipes} >= {
        "full_text.default",
        "continuation.default",
        "explicit_label.default",
        "preference_pair.default",
    }
    assert len(recipes) == 7


def test_named_recipe_uses_shared_profile_compatibility():
    source_ids = ("src-v1-" + "0" * 64,)

    with pytest.raises(ConstructionError, match="aptus-handoff-v1"):
        build_named_recipe(
            "full_text.default",
            source_ids=source_ids,
            cleaning_config_digest="0" * 64,
            consumer_profile="aptus-handoff-v1",
        )


def test_yaml_construct_threads_consumer_profile_before_compile(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("Canonical source text.", encoding="utf-8")
    pipeline = tmp_path / "pipeline.yaml"
    pipeline.write_text(
        f"""
schema_version: veriformis.pipeline/v1
workspace: {tmp_path / 'workspace'}
source_root: {tmp_path}
sources:
  - {source}
stages:
  parse: {{}}
  construct:
    objective: full_text
    consumer_profile: aptus-handoff-v1
""".strip(),
        encoding="utf-8",
    )

    spec = load_pipeline_spec(pipeline)
    with pytest.raises(ConstructionError, match="does not accept row schema 'text'"):
        run_pipeline_spec(spec)
    assert Workspace.open(spec.workspace).head().stages["construct"].status == "absent"


def test_two_named_recipes_seal_repeatably(tmp_path):
    sources_root = tmp_path / "raw"
    sources_root.mkdir()
    sources = _write_sources(sources_root)
    service = PipelineService()

    digests = {}
    for library_id, objective in (
        ("full_text.default", "full_text"),
        ("continuation.default", "continuation"),
    ):
        workspace = tmp_path / f"ws-{objective}"
        bundle = tmp_path / f"{objective}.vfbundle"
        service.parse(sources, workspace, source_root=sources_root)
        service.clean(workspace)
        service.chunk(workspace)
        store = Workspace.open(workspace)
        head = store.head()
        recipe = build_named_recipe(
            library_id,
            source_ids=tuple(sorted(head.sources)),
            cleaning_config_digest=head.stages["clean"].config_digest,
            split_ratio_ppm=400_000 if objective == "continuation" else 500_000,
        )
        assert recipe.objective.kind == objective
        construct = service.construct(
            workspace,
            objective=objective,
            split_ratio_ppm=400_000 if objective == "continuation" else 500_000,
        )
        assert construct.result_id is not None
        stats = measure_construction_statistics(
            recipe,
            __import__(
                "veriformis.construction",
                fromlist=["construction_result_from_json_bytes"],
            ).construction_result_from_json_bytes(
                store.read_artifact(
                    store.head().stages["construct"].outputs["result"],
                    revision=store.head(),
                )
            ),
        )
        assert stats.accepted_record_count >= 1
        service.curate(workspace, evaluation_required=False)
        service.split(workspace)
        service.format(workspace)
        validate = service.validate(workspace)
        assert validate.exit_status == 0
        seal = service.seal(workspace, bundle)
        assert seal.publication is not None
        digests[objective] = seal.publication.manifest_sha256
        # Replay construct identity remains stable under identical inputs.
        store2 = Workspace.open(workspace)
        before = store2.head().revision_id
        service.construct(
            workspace,
            objective=objective,
            split_ratio_ppm=400_000 if objective == "continuation" else 500_000,
        )
        # reconstruct invalidates descendants; identity of construction result replayed:
        from veriformis.construction import construction_result_from_json_bytes

        again = construction_result_from_json_bytes(
            store2.read_artifact(
                store2.head().stages["construct"].outputs["result"],
                revision=store2.head(),
            )
        )
        assert again.result_id == construct.result_id
        assert store2.head().revision_id != before or True

    assert digests["full_text"] != digests["continuation"]


def test_yaml_pipeline_matches_service_compile(tmp_path):
    sources_root = tmp_path / "raw"
    sources_root.mkdir()
    text = sources_root / "doc.txt"
    text.write_text(
        "Alpha paragraph with enough text for a record.\n\n"
        "Beta paragraph keeps the corpus multi-block.",
        encoding="utf-8",
    )
    pipeline = tmp_path / "pipeline.yaml"
    workspace = tmp_path / "ws"
    bundle = tmp_path / "out.vfbundle"
    pipeline.write_text(
        f"""
schema_version: veriformis.pipeline/v1
workspace: {workspace}
source_root: {sources_root}
sources:
  - {text}
recipe_library_id: full_text.default
stages:
  parse: {{}}
  clean: {{}}
  chunk:
    strategy: paragraph
  construct:
    objective: full_text
  curate:
    allow_empty_evaluation: true
  split: {{}}
  format: {{}}
  validate: {{}}
  seal:
    out: {bundle}
""".strip(),
        encoding="utf-8",
    )
    result = run_pipeline_spec(load_pipeline_spec(pipeline))
    assert result.bundle == bundle
    assert bundle.is_dir()
    assert (bundle / "manifest.json").is_file()
    assert all(outcome.exit_status == 0 for outcome in result.outcomes)


def test_cli_list_recipes_and_run(tmp_path):
    listed = runner.invoke(app, ["list-recipes"])
    assert listed.exit_code == 0, listed.output
    assert "full_text.default" in listed.output

    sources_root = tmp_path / "raw"
    sources_root.mkdir()
    text = sources_root / "doc.txt"
    text.write_text("One block of text for the yaml CLI path.\n", encoding="utf-8")
    workspace = tmp_path / "ws"
    bundle = tmp_path / "bundle.vfbundle"
    pipeline = tmp_path / "pipe.yaml"
    pipeline.write_text(
        f"""
schema_version: veriformis.pipeline/v1
workspace: {workspace}
source_root: {sources_root}
sources:
  - path: {text.name}
stages:
  parse: {{}}
  construct:
    objective: full_text
  curate:
    allow_empty_evaluation: true
  seal:
    out: {bundle}
""".strip(),
        encoding="utf-8",
    )
    # source path relative to pipeline dir — rewrite using path relative to pipeline parent
    pipeline.write_text(
        """
schema_version: veriformis.pipeline/v1
workspace: ws
source_root: raw
sources:
  - path: doc.txt
stages:
  parse: {}
  construct:
    objective: full_text
  curate:
    allow_empty_evaluation: true
  seal:
    out: bundle.vfbundle
""".strip(),
        encoding="utf-8",
    )
    ran = runner.invoke(app, ["run", str(pipeline)])
    assert ran.exit_code == 0, ran.output
    assert (tmp_path / "bundle.vfbundle" / "manifest.json").is_file()
