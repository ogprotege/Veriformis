"""Compile preflight contract, bounded transport, and surface parity."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

import veriformis.sources as source_module
from veriformis.cli import app
from veriformis.errors import ConstructionError, InvalidSourceLocatorError
from veriformis.goals import (
    COMPILE_PREFLIGHT_SCHEMA_ID,
    PREFLIGHT_MAX_RESPONSE_BYTES,
    PREFLIGHT_MAX_SOURCE_BYTES,
    CurationDefaults,
)
from veriformis.identity import derive_source_id
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.sources import derive_logical_paths
from veriformis.workspace import Workspace


RUNNER = CliRunner()
SERVICE = PipelineService()


def _sources(root: Path, *, count: int = 2) -> tuple[Path, list[Path]]:
    source_root = root / "sources"
    source_root.mkdir(parents=True)
    paths: list[Path] = []
    for index in range(count):
        path = source_root / f"source-{index}.txt"
        path.write_text(
            (
                f"Source {index} begins with exact retained wording for preflight. "
                "This independent document contains enough text to survive curation.\n\n"
                f"Source {index} ends with a second exact paragraph for training."
            ),
            encoding="utf-8",
        )
        paths.append(path)
    return source_root, paths


def _tool(name: str):
    return {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }[name]


def test_preflight_replays_through_split_without_mutating_sources(tmp_path) -> None:
    source_root, paths = _sources(tmp_path)
    before = {
        path.relative_to(source_root): path.read_bytes()
        for path in source_root.rglob("*")
        if path.is_file()
    }

    outcome = SERVICE.preflight(
        paths,
        source_root=source_root,
        goal="learn-the-text",
    )

    assert outcome.exit_status == 0
    assert outcome.preflight is not None
    report = outcome.preflight
    assert report.schema_id == COMPILE_PREFLIGHT_SCHEMA_ID
    assert report.evaluated_through == "split"
    assert report.admitted is True
    assert report.counts.source_count == 2
    assert report.counts.admitted_source_count == 2
    assert all(source.parser_eligible for source in report.sources)
    assert all(source.goal_family_eligible for source in report.sources)
    assert all(source.evidence_status == "available" for source in report.sources)
    assert not (tmp_path / "workspace").exists()
    after = {
        path.relative_to(source_root): path.read_bytes()
        for path in source_root.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_missing_selection_is_a_complete_negative_report_without_source_access(
    tmp_path,
) -> None:
    missing = tmp_path / "does-not-exist.txt"

    outcome = SERVICE.preflight([missing], source_root=tmp_path)

    assert outcome.exit_status == 2
    assert outcome.preflight is not None
    report = outcome.preflight
    assert report.admitted is False
    assert report.evaluated_through == "selection"
    assert report.sources == ()
    assert [item.code for item in report.incompatibilities] == ["selection-required"]


@pytest.mark.parametrize(
    ("selection", "expected_code", "expected_fields"),
    [
        ({"goal": "not-a-goal"}, "goal-invalid", ("goal",)),
        (
            {
                "goal": "learn-the-text",
                "preset": "continue-a-passage.safe",
            },
            "preset-incompatible",
            ("goal", "preset"),
        ),
        (
            {"goal": "learn-the-text", "size": 0},
            "override-invalid",
            ("overrides",),
        ),
    ],
)
def test_closed_selection_refusals_are_typed_before_source_access(
    tmp_path: Path,
    selection: dict[str, object],
    expected_code: str,
    expected_fields: tuple[str, ...],
) -> None:
    report = SERVICE.preflight(
        [tmp_path / "not-read.txt"],
        source_root=tmp_path,
        **selection,
    ).preflight

    assert report is not None
    assert report.evaluated_through == "selection"
    assert report.sources == ()
    assert [(item.code, item.fields) for item in report.incompatibilities] == [
        (expected_code, expected_fields)
    ]


def test_preflight_limitations_include_the_catalog_non_claims(tmp_path: Path) -> None:
    report = SERVICE.preflight(
        [tmp_path / "not-read.txt"],
        source_root=tmp_path,
        goal="learn-the-text",
        evaluation_required=False,
    ).preflight

    assert report is not None
    codes = {item.code for item in report.known_limitations}
    assert {
        "no-trainer-compatibility",
        "no-generated-text",
        "no-invented-target",
        "no-fine-tuning-suitability-judgment",
    } <= codes


def test_cli_and_mcp_emit_identical_ascii_safe_preflight(tmp_path) -> None:
    source_root, paths = _sources(tmp_path)
    outcome = SERVICE.preflight(
        paths,
        source_root=source_root,
        goal="learn-the-text",
    )
    assert outcome.preflight is not None
    expected = outcome.preflight.transport_text()
    assert expected.isascii()

    result = RUNNER.invoke(
        app,
        [
            "preflight",
            *(str(path) for path in paths),
            "--source-root",
            str(source_root),
            "--goal",
            "learn-the-text",
        ],
    )
    assert result.exit_code == 0, result.output
    assert result.output == expected + "\n"

    actual = _tool("preflight")(
        [str(path) for path in paths],
        str(source_root),
        "learn-the-text",
    )
    assert actual == expected
    assert json.loads(actual)["admitted"] is True


def test_negative_cli_report_is_printed_before_exit_two(tmp_path) -> None:
    source_root, paths = _sources(tmp_path, count=1)

    result = RUNNER.invoke(
        app,
        [
            "preflight",
            str(paths[0]),
            "--source-root",
            str(source_root),
            "--goal",
            "learn-the-text",
        ],
    )

    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["schema_id"] == COMPILE_PREFLIGHT_SCHEMA_ID
    assert payload["admitted"] is False
    assert payload["sources"][0]["refusal_reasons"][0]["code"] == (
        "evaluation-partition-unavailable"
    )


def test_preflight_executes_the_selected_cleaning_rules_for_transform_evidence(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.txt"
    source.write_text(
        "Alpha XXX beta remains exact source-grounded text.", encoding="utf-8"
    )

    without_change = SERVICE.preflight(
        [source],
        source_root=tmp_path,
        goal="reproduce-a-recorded-change",
        evaluation_required=False,
    ).preflight
    with_change = SERVICE.preflight(
        [source],
        source_root=tmp_path,
        goal="reproduce-a-recorded-change",
        custom="XXX",
        evaluation_required=False,
    ).preflight

    assert without_change is not None and with_change is not None
    assert without_change.admitted is False
    assert {item.code for item in without_change.missing_evidence} == {
        "transformation-pair-unavailable"
    }
    assert with_change.admitted is True
    assert with_change.counts.record_count == 1
    assert (
        without_change.selection.resolved.cleaning_config_digest
        != with_change.selection.resolved.cleaning_config_digest
    )


def test_instruction_and_review_configuration_fail_before_source_access(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "not-read.txt"

    instruction_empty = SERVICE.preflight(
        [missing],
        source_root=tmp_path,
        goal="continue-a-passage",
        representation="instruction-and-output",
        instruction="",
    ).preflight
    instruction_untruthful = SERVICE.preflight(
        [missing],
        source_root=tmp_path,
        goal="continue-a-passage",
        representation="instruction-and-output",
        instruction="Summarize the supplied opening.",
    ).preflight
    instruction_not_applicable = SERVICE.preflight(
        [missing],
        source_root=tmp_path,
        goal="continue-a-passage",
        instruction="Continue this exact source passage.",
    ).preflight
    review_unavailable = SERVICE.preflight(
        [missing],
        source_root=tmp_path,
        goal="continue-a-passage",
        require_review=True,
    ).preflight

    assert instruction_empty is not None
    assert [item.code for item in instruction_empty.incompatibilities] == [
        "instruction-required"
    ]
    assert instruction_untruthful is not None
    assert [item.code for item in instruction_untruthful.incompatibilities] == [
        "instruction-untruthful"
    ]
    assert instruction_not_applicable is not None
    assert [item.code for item in instruction_not_applicable.incompatibilities] == [
        "instruction-not-applicable"
    ]
    assert review_unavailable is not None
    assert [item.code for item in review_unavailable.incompatibilities] == [
        "review-evidence-unavailable"
    ]
    assert instruction_empty.sources == instruction_not_applicable.sources == ()
    assert review_unavailable.sources == ()


def test_incompatible_representation_has_the_representation_code(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "not-read.txt"

    report = SERVICE.preflight(
        [missing],
        source_root=tmp_path,
        goal="learn-the-text",
        representation="instruction-and-output",
    ).preflight

    assert report is not None
    assert report.evaluated_through == "selection"
    assert report.sources == ()
    assert [(item.code, item.fields) for item in report.incompatibilities] == [
        ("representation-incompatible", ("representation",))
    ]


def test_unknown_consumer_profile_has_the_consumer_profile_code(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "not-read.txt"

    report = SERVICE.preflight(
        [missing],
        source_root=tmp_path,
        goal="continue-a-passage",
        consumer_profile="bogus-profile",
    ).preflight

    assert report is not None
    assert report.evaluated_through == "selection"
    assert report.sources == ()
    assert [(item.code, item.fields) for item in report.incompatibilities] == [
        ("consumer-profile-incompatible", ("consumer_profile",))
    ]


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO is POSIX-only")
def test_preflight_refuses_a_fifo_without_reading_it(tmp_path: Path) -> None:
    fifo = tmp_path / "source.txt"
    os.mkfifo(fifo)

    report = SERVICE.preflight(
        [fifo],
        source_root=tmp_path,
        goal="learn-the-text",
    ).preflight

    assert report is not None
    assert report.admitted is False
    assert report.evaluated_through == "capture"
    assert report.sources[0].parser_status == "error"
    assert [item.code for item in report.sources[0].refusal_reasons] == [
        "source-read-failed"
    ]
    assert report.sources[0].refusal_reasons[0].detail_codes == (
        "invalid-source-locator",
    )


def test_large_parser_refusal_is_aggregated_and_bounded(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text(
        "# Heading\n\nBody.\n\n"
        + "".join(f"[^{index}]: unused {index}\n" for index in range(400)),
        encoding="utf-8",
    )

    report = SERVICE.preflight(
        [source],
        source_root=tmp_path,
        goal="learn-the-text",
        evaluation_required=False,
    ).preflight

    assert report is not None
    verdict = report.sources[0]
    assert verdict.parser_status == "refused"
    assert len(verdict.refusal_reasons) == 1
    assert verdict.refusal_reasons[0].detail_codes == (
        "markdown.unused-footnote-definition-refused",
    )
    assert verdict.omitted_diagnostic_count == 400
    assert verdict.omission_reason == "exact-source-exceeds-preflight-limit"
    assert verdict.exact_size_bytes > PREFLIGHT_MAX_SOURCE_BYTES
    assert len(report.transport_text().encode("utf-8")) <= PREFLIGHT_MAX_RESPONSE_BYTES


def test_admitted_source_preserves_unredacted_size_after_diagnostic_omission(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.md"
    source.write_text(
        "# Heading\n\nExact source-grounded body text.\n\n"
        + "".join(
            f"[unused-reference-{index}]: https://example.com/{index}\n"
            for index in range(600)
        ),
        encoding="utf-8",
    )

    report = SERVICE.preflight(
        [source],
        source_root=tmp_path,
        goal="learn-the-text",
        evaluation_required=False,
    ).preflight

    assert report is not None
    assert report.admitted is True
    verdict = report.sources[0]
    assert verdict.admitted is True
    assert verdict.diagnostic_counts[0].code == (
        "markdown.unused-reference-definition-omitted"
    )
    assert verdict.diagnostic_counts[0].count == 600
    assert verdict.diagnostics == ()
    assert verdict.omitted_diagnostic_count == 600
    assert verdict.omission_reason == "exact-source-exceeds-preflight-limit"
    assert verdict.exact_size_bytes > PREFLIGHT_MAX_SOURCE_BYTES


def test_duplicate_absolute_inputs_do_not_leak_host_paths_in_preflight(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "private-source-root"
    source_root.mkdir()
    source = source_root / "same.txt"
    source.write_text("Exact source text.", encoding="utf-8")

    report = SERVICE.preflight(
        [source, source],
        source_root=source_root,
        goal="learn-the-text",
        evaluation_required=False,
    ).preflight

    assert report is not None
    transport = report.transport_text()
    assert report.evaluated_through == "capture"
    assert [item.logical_path for item in report.sources] == ["same.txt", "same.txt"]
    assert str(source_root) not in transport
    assert str(source) not in transport
    assert "source inputs 'same.txt' and 'same.txt'" in transport

    cli = RUNNER.invoke(
        app,
        [
            "preflight",
            str(source),
            str(source),
            "--source-root",
            str(source_root),
            "--goal",
            "learn-the-text",
            "--allow-empty-evaluation",
        ],
    )
    assert cli.exit_code == 2, cli.output
    assert str(source_root) not in cli.output
    assert str(source) not in cli.output
    assert json.loads(cli.output)["sources"][0]["logical_path"] == "same.txt"


def test_request_digest_uses_logical_source_arguments_across_path_spellings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.txt"
    source.write_text(
        "Exact source wording with enough retained content for one continuation row.",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    absolute = SERVICE.preflight(
        [source],
        source_root=tmp_path,
        goal="learn-the-text",
        evaluation_required=False,
    ).preflight
    relative = SERVICE.preflight(
        [Path("source.txt")],
        source_root=Path("."),
        goal="learn-the-text",
        evaluation_required=False,
    ).preflight

    assert absolute is not None and relative is not None
    assert absolute.request_digest == relative.request_digest
    assert absolute.captured_source_digest == relative.captured_source_digest
    assert [item.logical_path for item in absolute.sources] == ["source.txt"]
    assert [item.logical_path for item in relative.sources] == ["source.txt"]

    absolute_cli = RUNNER.invoke(
        app,
        [
            "preflight",
            str(source),
            "--source-root",
            str(tmp_path),
            "--goal",
            "learn-the-text",
            "--allow-empty-evaluation",
        ],
    )
    relative_cli = RUNNER.invoke(
        app,
        [
            "preflight",
            "source.txt",
            "--source-root",
            ".",
            "--goal",
            "learn-the-text",
            "--allow-empty-evaluation",
        ],
    )
    assert absolute_cli.exit_code == relative_cli.exit_code
    assert (
        json.loads(absolute_cli.output)["request_digest"]
        == json.loads(relative_cli.output)["request_digest"]
    )


def test_mixed_capture_failure_retains_identity_for_captured_sibling(
    tmp_path: Path,
) -> None:
    captured = tmp_path / "captured.txt"
    captured.write_text("Exact captured sibling bytes.", encoding="utf-8")
    missing = tmp_path / "missing.txt"

    report = SERVICE.preflight(
        [captured, missing],
        source_root=tmp_path,
        goal="learn-the-text",
        evaluation_required=False,
    ).preflight

    assert report is not None
    assert report.evaluated_through == "capture"
    captured_verdict = next(
        item for item in report.sources if item.logical_path == "captured.txt"
    )
    assert captured_verdict.sha256 is not None
    assert captured_verdict.source_id == derive_source_id(
        "captured.txt",
        captured_verdict.sha256,
    )
    assert captured_verdict.size == len(captured.read_bytes())


@pytest.mark.parametrize("surface", ["preflight", "parse"])
def test_source_root_ancestor_symlink_race_is_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
) -> None:
    container = tmp_path / "container"
    trusted_ancestor = container / "movable"
    source_root = trusted_ancestor / "root"
    source_root.mkdir(parents=True)
    source = source_root / "source.txt"
    source.write_text("trusted exact bytes", encoding="utf-8")

    evil_ancestor = container / "evil"
    evil_root = evil_ancestor / "root"
    evil_root.mkdir(parents=True)
    (evil_root / "source.txt").write_text("evil substituted bytes", encoding="utf-8")
    moved_ancestor = container / "trusted-moved"
    real_open = os.open
    raced = False

    def racing_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal raced
        if path == "movable" and dir_fd is not None and not raced:
            raced = True
            trusted_ancestor.rename(moved_ancestor)
            trusted_ancestor.symlink_to(evil_ancestor, target_is_directory=True)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(source_module.os, "open", racing_open)
    workspace = tmp_path / "workspace"
    if surface == "preflight":
        report = SERVICE.preflight(
            [source],
            source_root=source_root,
            goal="learn-the-text",
            evaluation_required=False,
        ).preflight
        assert report is not None
        assert report.evaluated_through == "capture"
        assert report.captured_source_digest is None
        assert report.sources[0].sha256 is None
        assert report.sources[0].size is None
    else:
        with pytest.raises(
            InvalidSourceLocatorError,
            match="source root contains a symlink during capture",
        ):
            SERVICE.parse([source], workspace, source_root=source_root)
        assert not workspace.exists()
    assert raced is True


@pytest.mark.parametrize("surface", ["preflight", "parse"])
@pytest.mark.parametrize("retarget", ["root", "ancestor"])
def test_source_root_retarget_during_resolution_is_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
    retarget: str,
) -> None:
    container = tmp_path / "container"
    trusted_ancestor = container / "selected-parent"
    source_root = trusted_ancestor if retarget == "root" else trusted_ancestor / "root"
    source_root.mkdir(parents=True)
    source = source_root / "source.txt"
    source.write_text("trusted exact bytes", encoding="utf-8")

    evil_ancestor = container / "evil-parent"
    evil_root = evil_ancestor if retarget == "root" else evil_ancestor / "root"
    evil_root.mkdir(parents=True)
    (evil_root / "source.txt").write_text(
        "evil replacement bytes must never be captured",
        encoding="utf-8",
    )
    moved_ancestor = container / "trusted-moved"
    real_resolve = Path.resolve
    raced = False

    def racing_resolve(path: Path, *args, **kwargs) -> Path:
        nonlocal raced
        if path == source_root and not raced:
            raced = True
            trusted_ancestor.rename(moved_ancestor)
            trusted_ancestor.symlink_to(evil_ancestor, target_is_directory=True)
        return real_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", racing_resolve)
    workspace = tmp_path / "workspace"
    if surface == "preflight":
        report = SERVICE.preflight(
            [source],
            source_root=source_root,
            goal="learn-the-text",
            evaluation_required=False,
        ).preflight
        assert report is not None
        assert report.evaluated_through == "capture"
        assert report.captured_source_digest is None
        assert report.sources[0].logical_path == "source.txt"
        assert report.sources[0].sha256 is None
        assert report.sources[0].size is None
        assert "source root changed during capture" in report.transport_text()
        assert str(source_root) not in report.transport_text()
        assert str(evil_root) not in report.transport_text()
    else:
        with pytest.raises(
            InvalidSourceLocatorError,
            match="source root changed during capture",
        ):
            SERVICE.parse([source], workspace, source_root=source_root)
        assert not workspace.exists()
    assert raced is True


def test_parse_refusal_retains_known_family_and_is_not_a_family_verdict(
    tmp_path: Path,
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not-json", encoding="utf-8")

    report = SERVICE.preflight(
        [malformed],
        source_root=tmp_path,
        goal="learn-the-text",
        evaluation_required=False,
    ).preflight

    assert report is not None
    assert report.evaluated_through == "parse"
    verdict = report.sources[0]
    assert verdict.input_family == "json-records"
    assert verdict.parser_id == "json"
    assert verdict.parser_status == "refused"
    assert verdict.goal_family_eligible is None
    assert [item.code for item in verdict.refusal_reasons] == ["parser-refused"]


def test_unsupported_suffix_is_a_parse_refusal_not_a_family_rejection(
    tmp_path: Path,
) -> None:
    unsupported = tmp_path / "source.epub"
    unsupported.write_bytes(b"captured but unsupported")

    report = SERVICE.preflight(
        [unsupported],
        source_root=tmp_path,
        goal="learn-the-text",
        evaluation_required=False,
    ).preflight

    assert report is not None
    assert report.evaluated_through == "parse"
    verdict = report.sources[0]
    assert verdict.input_family is None
    assert verdict.parser_id is None
    assert verdict.parser_status == "refused"
    assert verdict.goal_family_eligible is None
    assert [item.code for item in verdict.refusal_reasons] == ["unsupported-input"]


def test_source_membership_refuses_duplicate_and_resolved_alias_inputs(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.txt"
    source.write_text("Exact source text.", encoding="utf-8")

    with pytest.raises(InvalidSourceLocatorError, match="resolve to the same file"):
        derive_logical_paths([source, source], source_root=tmp_path)

    alias = tmp_path / "alias.txt"
    alias.symlink_to(source)
    with pytest.raises(InvalidSourceLocatorError, match="symlinks are not allowed"):
        derive_logical_paths([source, alias], source_root=tmp_path)


def test_hard_link_aliases_are_refused_by_preflight_and_parse(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "sources"
    source_root.mkdir()
    first = source_root / "first.txt"
    first.write_text("One exact underlying source file.", encoding="utf-8")
    alias = source_root / "alias.txt"
    os.link(first, alias)

    report = SERVICE.preflight(
        [first, alias],
        source_root=source_root,
        goal="learn-the-text",
        evaluation_required=False,
    ).preflight

    assert report is not None
    assert report.evaluated_through == "capture"
    assert report.captured_source_digest is None
    assert report.counts.source_count == 2
    assert all(
        "hard-link and case aliases are not allowed" in reason.message
        for verdict in report.sources
        for reason in verdict.refusal_reasons
    )
    workspace = tmp_path / "workspace"
    with pytest.raises(
        InvalidSourceLocatorError,
        match="hard-link and case aliases are not allowed",
    ):
        SERVICE.parse([first, alias], workspace, source_root=source_root)
    assert not workspace.exists()


@pytest.mark.parametrize("surface", ["preflight", "parse"])
def test_hard_link_aliases_are_refused_before_any_body_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
) -> None:
    source_root = tmp_path / "sources"
    source_root.mkdir()
    first = source_root / "first.txt"
    first.write_text("One exact underlying source file.", encoding="utf-8")
    alias = source_root / "alias.txt"
    os.link(first, alias)
    body_reads = 0
    real_capture = source_module._capture_at

    def counting_capture(*args, **kwargs):
        nonlocal body_reads
        body_reads += 1
        return real_capture(*args, **kwargs)

    monkeypatch.setattr(source_module, "_capture_at", counting_capture)
    workspace = tmp_path / "workspace"
    if surface == "preflight":
        report = SERVICE.preflight(
            [first, alias],
            source_root=source_root,
            goal="learn-the-text",
            evaluation_required=False,
        ).preflight
        assert report is not None
        assert report.evaluated_through == "capture"
        assert report.captured_source_digest is None
    else:
        with pytest.raises(
            InvalidSourceLocatorError,
            match="hard-link and case aliases are not allowed",
        ):
            SERVICE.parse([first, alias], workspace, source_root=source_root)
        assert not workspace.exists()
    assert body_reads == 0


@pytest.mark.parametrize("ratio", [0, 1_000_000])
def test_curation_defaults_close_over_split_policy_endpoints(ratio: int) -> None:
    with pytest.raises(ValidationError, match="1..999999"):
        CurationDefaults(
            minimum_target_characters=1,
            balance_mode="none",
            maximum_records_per_primary_source=None,
            evaluation_ratio_ppm=ratio,
            evaluation_required=True,
            split_seed="veriformis-v1",
        )


def test_real_construct_uses_the_same_family_gate_as_preflight(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "group5" / "minimal-text.pdf"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    source = source_root / "source.pdf"
    source.write_bytes(fixture.read_bytes())
    workspace = tmp_path / "workspace"
    SERVICE.parse([source], workspace, source_root=source_root)
    SERVICE.clean(workspace)
    SERVICE.chunk(workspace, goal="recover-a-section-from-its-heading")
    before = Workspace.open(workspace).head().revision_id

    with pytest.raises(
        ConstructionError,
        match="goal input-family admission failed.*does not accept input family 'pdf-text'",
    ):
        SERVICE.construct(
            workspace,
            goal="recover-a-section-from-its-heading",
        )

    assert Workspace.open(workspace).head().revision_id == before
