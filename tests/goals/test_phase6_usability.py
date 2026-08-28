"""Phase 6 closeout: predeclared usability criteria U1–U6."""

from __future__ import annotations

from pathlib import Path

from veriformis.contracts import (
    PRODUCT_OBJECTIVE_KINDS,
    PRODUCT_ROW_SCHEMA_KINDS,
)
from veriformis.exports import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportDryRunRequest,
    SPLIT_JSONL_CONTAINER_ID,
    SPLIT_JSONL_CONTAINER_VERSION,
)
from veriformis.goals import goal_catalog
from veriformis.identity import sha256_digest
from veriformis.pipeline import PipelineService
from veriformis.recipes import RECIPE_LIBRARY_IDS
from veriformis.taxonomy import LOSS_POLICY_IDS, ROW_SCHEMA_UI_ALIASES

SERVICE = PipelineService()


def _machine_tokens() -> set[str]:
    return {
        token
        for token in {
            *PRODUCT_OBJECTIVE_KINDS,
            *PRODUCT_ROW_SCHEMA_KINDS,
            *LOSS_POLICY_IDS,
            *RECIPE_LIBRARY_IDS,
            *ROW_SCHEMA_UI_ALIASES,
        }
        if any(character in token for character in "_-.")
    }


def test_u1_plain_language_selection_has_no_machine_vocabulary() -> None:
    tokens = _machine_tokens()
    for goal in goal_catalog().goals:
        texts = [
            goal.title,
            goal.plain_language,
            goal.what_the_model_learns,
            goal.what_you_provide,
            *goal.not_this,
            goal.instruction_template,
            goal.instruction_task,
        ]
        for text in texts:
            lowered = text.lower()
            assert text.strip() == text and text
            for token in tokens:
                assert token not in lowered, (goal.goal_id, token)
        for text in (
            goal.title,
            goal.plain_language,
            goal.what_the_model_learns,
            goal.what_you_provide,
            goal.instruction_template,
            goal.instruction_task,
        ):
            lowered = text.lower()
            for fragment in ("summar", "answer", "translat"):
                assert fragment not in lowered, (goal.goal_id, fragment)


def test_u4_every_goal_surfaces_visible_non_claims() -> None:
    catalog = SERVICE.discover_goals()
    for goal, discovered in zip(goal_catalog().goals, catalog["goals"], strict=True):
        assert discovered["not_this"] == list(goal.not_this)
        assert discovered["non_claims"] == list(goal.non_claims)


def test_u5_and_u6_walkthrough_picks_preflights_compiles_previews_and_exports(
    tmp_path: Path,
) -> None:
    """Documented walkthrough: pick a goal, refuse bad input, then compile."""
    goal = next(
        item for item in goal_catalog().goals if item.goal_id == "continue-a-passage"
    )
    source_root = tmp_path / "sources"
    source_root.mkdir()
    paths = []
    for name in ("alpha.txt", "beta.txt"):
        path = source_root / name
        path.write_text(
            (
                f"{name} opening is long enough to split into context and target. "
                "The remainder stays in this same independent source.\n\n"
                f"{name} second paragraph keeps the leakage groups distinct."
            ),
            encoding="utf-8",
        )
        paths.append(path)
    ineligible = source_root / "plain.txt"
    ineligible.write_text("A headingless plain-text file.\n", encoding="utf-8")

    family_refused = SERVICE.preflight(
        [ineligible],
        source_root=source_root,
        goal="recover-a-section-from-its-heading",
    ).preflight
    assert family_refused is not None
    assert family_refused.admitted is False
    assert any(
        reason.code == "goal-input-family-ineligible"
        for source in family_refused.sources
        for reason in source.refusal_reasons
    )
    untruthful = SERVICE.preflight(
        paths,
        source_root=source_root,
        goal=goal.goal_id,
        representation="instruction-and-output",
        instruction="Summarize the supplied opening.",
    ).preflight
    assert untruthful is not None
    assert untruthful.admitted is False
    assert untruthful.sources == ()
    assert [item.code for item in untruthful.incompatibilities] == [
        "instruction-untruthful"
    ]

    admitted = SERVICE.preflight(
        paths,
        source_root=source_root,
        goal=goal.goal_id,
        representation="instruction-and-output",
    ).preflight
    assert admitted is not None
    assert admitted.admitted is True
    assert admitted.incompatibilities == ()

    workspace = tmp_path / "workspace"
    bundle = tmp_path / "dataset.vfbundle"
    SERVICE.parse(paths, workspace, source_root=source_root)
    SERVICE.clean(workspace)
    SERVICE.chunk(workspace, preset=f"{goal.goal_id}.safe")
    SERVICE.construct(
        workspace,
        goal=goal.goal_id,
        preset=f"{goal.goal_id}.safe",
        representation="instruction-and-output",
    )
    SERVICE.curate(workspace, preset=f"{goal.goal_id}.safe")
    SERVICE.split(workspace)
    SERVICE.format(workspace)
    assert SERVICE.validate(workspace).exit_status == 0
    sealed = SERVICE.seal(workspace, bundle)
    assert sealed.publication is not None

    preview = SERVICE.preview_goal(workspace).preview
    assert preview.goal_id == goal.goal_id
    assert preview.not_this == goal.not_this
    assert preview.non_claims == goal.non_claims
    assert preview.records
    for entry in preview.records:
        target = next(iter(entry.target.values()))
        assert entry.supervised.end == len(target)
        assert entry.rendered_row["instruction"] == goal.instruction_template
        assert entry.rendered_row["output"] == target

    digest = sha256_digest((bundle / "manifest.json").read_bytes())
    exported = SERVICE.dry_run_export(
        ExportDryRunRequest(
            operation="dry_run",
            schema_version=EXPORT_SURFACE_REQUEST_SCHEMA,
            bundle=str(bundle),
            container_id=SPLIT_JSONL_CONTAINER_ID,
            container_version=SPLIT_JSONL_CONTAINER_VERSION,
            consumer_id=None,
            consumer_profile_version=None,
            source_trust_policy="require_external_digest",
            expected_manifest_sha256=digest,
            overwrite_policy="refuse",
        )
    )
    assert exported.plan is not None
    assert exported.preview is not None
