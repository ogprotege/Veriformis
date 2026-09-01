#!/usr/bin/env python3
"""Fail when independent-product tracking records drift from code or each other."""

from __future__ import annotations

import inspect
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

from typer.models import OptionInfo

from veriformis import __version__
from veriformis.bundle.finished import (
    ATTESTATION_NAME,
    EVALUATION_PATH,
    MANIFEST_NAME,
    PROVENANCE_PATH,
    TRAIN_PATH,
    VALIDATION_PATH,
)
from veriformis.cli import seal
from veriformis.datasets.serialization import PRODUCT_ROW_SCHEMAS, V1_ROW_SCHEMAS
from veriformis.goals import goal_catalog, preset_catalog, recipe_defaults
from veriformis.mapping import IMPLEMENTED_INPUT_MODES, PLANNED_INPUT_MODES
from veriformis.mcp.server import create_mcp_server
from veriformis.parsers.dispatch import DECLARED_V1_EXTENSIONS
from veriformis.recipes.library import list_named_recipes
from veriformis.taxonomy import (
    CANONICAL_CONSUMER_PROFILE,
    CANDIDATE_CONSUMER_PROFILES,
    EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES,
    EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES,
    IMPLEMENTED_INPUT_FAMILIES,
    INPUT_FAMILY_SUFFIXES,
    IMPLEMENTED_CONSUMER_PROFILES,
    IMPLEMENTED_EXPORT_CONSUMER_PROFILES,
    IMPLEMENTED_PHYSICAL_CONTAINERS,
    IMPLEMENTED_TRAINING_FAMILIES,
    LOSS_POLICY_IDS,
    PLANNED_CONSUMER_PROFILES,
    PLANNED_PHYSICAL_CONTAINERS,
    PLANNED_TRAINING_FAMILIES,
)
from veriformis.release import REQUIRED_EXCLUSIONS, support_matrix


ROOT = Path(__file__).resolve().parents[1]
PROGRAM_PATH = ROOT / "dev/active/independent-product/program.json"
SUPPORT_PATH = ROOT / "docs/governance/support-registry.json"
EVIDENCE_PATH = ROOT / "docs/evidence/index.json"
WIP_PATH = ROOT / "WIP.md"
PHASE_PACKET_FILES = {
    "README.md",
    "plan.md",
    "progress.md",
    "decisions.md",
    "risks.md",
    "evidence.md",
    "closeout.md",
}
PHASE_STATUS_DISPLAY = {
    "planned": "Planned",
    "in_progress": "In progress",
    "blocked": "Blocked",
    "deferred": "Deferred",
    "completed": "Completed",
}
LOCAL_REFERENCE_KEYS = {
    "claim_policy",
    "details",
    "evidence",
    "packet",
    "roadmap",
    "status_policy",
}


class TrackingError(RuntimeError):
    """One or more governance records are inconsistent."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TrackingError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise TrackingError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _roadmap_phases(roadmap_path: Path) -> list[tuple[int, str]]:
    text = roadmap_path.read_text(encoding="utf-8")
    matches = re.findall(r"^## Phase (\d+) — (.+)$", text, flags=re.MULTILINE)
    return [(int(number), title) for number, title in matches]


def _check_program(program: dict[str, Any], errors: list[str]) -> None:
    _require(
        program.get("schema_version") == "veriformis.program-tracker/v1",
        "program tracker schema_version is not veriformis.program-tracker/v1",
        errors,
    )
    phases = program.get("phases")
    if not isinstance(phases, list):
        errors.append("program phases must be a list")
        return

    numbers = [phase.get("number") for phase in phases if isinstance(phase, dict)]
    _require(numbers == list(range(21)), "program phases must be numbered 0 through 20", errors)

    roadmap_value = program.get("roadmap")
    if not isinstance(roadmap_value, str):
        errors.append("program roadmap must be a repository-relative path")
        return
    roadmap_path = ROOT / roadmap_value
    if not roadmap_path.is_file():
        errors.append(f"program roadmap does not exist: {roadmap_value}")
        return
    roadmap_phases = _roadmap_phases(roadmap_path)
    program_phases = [
        (phase.get("number"), phase.get("title"))
        for phase in phases
        if isinstance(phase, dict)
    ]
    _require(
        roadmap_phases == program_phases,
        "program phase numbers/titles do not exactly match roadmap headings",
        errors,
    )

    allowed = program.get("status_values")
    if not isinstance(allowed, list) or set(allowed) != set(PHASE_STATUS_DISPLAY):
        errors.append("program status_values do not match the tracking policy")
        allowed_set = set(PHASE_STATUS_DISPLAY)
    else:
        allowed_set = set(allowed)

    active_count = 0
    for phase in phases:
        if not isinstance(phase, dict):
            errors.append("every program phase must be an object")
            continue
        number = phase.get("number")
        status = phase.get("status")
        _require(status in allowed_set, f"phase {number} has invalid status {status!r}", errors)
        if status == "in_progress":
            active_count += 1
        dependencies = phase.get("depends_on")
        if not isinstance(dependencies, list) or any(
            type(item) is not int or item < 0 or item >= number
            for item in dependencies
        ):
            errors.append(f"phase {number} has invalid predecessor dependencies")
        packet = phase.get("packet")
        if status in {"in_progress", "completed"}:
            if not isinstance(packet, str):
                errors.append(f"phase {number} must name a packet while {status}")
                continue
            packet_path = ROOT / packet
            if not packet_path.is_dir():
                errors.append(f"phase {number} packet does not exist: {packet}")
                continue
            missing = sorted(
                name for name in PHASE_PACKET_FILES if not (packet_path / name).is_file()
            )
            if missing:
                errors.append(f"phase {number} packet is missing {missing!r}")
        if status == "completed":
            _require(
                isinstance(phase.get("completed_on"), str),
                f"completed phase {number} must have completed_on",
                errors,
            )
        elif phase.get("completed_on") is not None:
            errors.append(f"non-completed phase {number} cannot have completed_on")

    _require(active_count <= 1, "more than one critical-path phase is in progress", errors)
    _check_wip_phase_table(phases, errors)


def _check_wip_phase_table(phases: list[dict[str, Any]], errors: list[str]) -> None:
    text = WIP_PATH.read_text(encoding="utf-8")
    start = "<!-- INDEPENDENT-PROGRAM:START -->"
    end = "<!-- INDEPENDENT-PROGRAM:END -->"
    if start not in text or end not in text:
        errors.append("WIP is missing the independent-program marker block")
        return
    block = text.split(start, 1)[1].split(end, 1)[0]
    rows = re.findall(r"^\| (\d+) \| (.+?) \| (.+?) \|", block, flags=re.MULTILINE)
    parsed = [(int(number), title, status) for number, title, status in rows]
    expected = [
        (phase["number"], phase["title"], PHASE_STATUS_DISPLAY[phase["status"]])
        for phase in phases
    ]
    _require(parsed == expected, "WIP phase table does not match program.json", errors)


def _check_support(support: dict[str, Any], errors: list[str]) -> None:
    _require(
        support.get("schema_version") == "veriformis.support-registry/v1",
        "support registry schema_version is not veriformis.support-registry/v1",
        errors,
    )
    product = support.get("product")
    if not isinstance(product, dict):
        errors.append("support registry product must be an object")
        return
    _require(product.get("version") == __version__, "support version differs from package", errors)
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    classifiers = pyproject["project"]["classifiers"]
    _require(
        ("Development Status :: 3 - Alpha" in classifiers)
        == (product.get("maturity") == "development-alpha"),
        "support maturity differs from pyproject classifier",
        errors,
    )

    inputs = support.get("inputs")
    training = support.get("training")
    artifacts = support.get("artifacts")
    if not all(isinstance(value, dict) for value in (inputs, training, artifacts)):
        errors.append("support inputs, training, and artifacts must be objects")
        return
    _require(
        inputs.get("implemented_extensions") == sorted(DECLARED_V1_EXTENSIONS),
        "support input extensions differ from DECLARED_V1_EXTENSIONS",
        errors,
    )
    _require(
        inputs.get("implemented_families") == list(IMPLEMENTED_INPUT_FAMILIES),
        "support input families differ from IMPLEMENTED_INPUT_FAMILIES",
        errors,
    )
    _require(
        inputs.get("implemented_modes") == list(IMPLEMENTED_INPUT_MODES),
        "support implemented modes differ from executable input modes",
        errors,
    )
    _require(
        inputs.get("planned_modes") == list(PLANNED_INPUT_MODES),
        "support planned modes differ from named non-executable input modes",
        errors,
    )
    owned_suffixes = sorted(
        suffix for suffixes in INPUT_FAMILY_SUFFIXES.values() for suffix in suffixes
    )
    _require(
        owned_suffixes == sorted(DECLARED_V1_EXTENSIONS),
        "taxonomy input-family suffixes do not partition DECLARED_V1_EXTENSIONS",
        errors,
    )
    unsupported_inputs = inputs.get("explicitly_unsupported")
    if not isinstance(unsupported_inputs, list):
        errors.append("support inputs.explicitly_unsupported must be a list")
    else:
        _require(
            [entry.get("family") for entry in unsupported_inputs if isinstance(entry, dict)]
            == list(EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES),
            "support unsupported input families differ from "
            "EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES",
            errors,
        )
    objective_names = sorted(item["objective"] for item in list_named_recipes())
    _require(
        training.get("implemented_objectives") == objective_names,
        "support objectives differ from the named recipe library",
        errors,
    )
    goals = goal_catalog().goals
    _require(
        training.get("implemented_goals") == [goal.goal_id for goal in goals],
        "support goals differ from the versioned goal catalog",
        errors,
    )
    _require(
        sorted(goal.objective for goal in goals) == objective_names,
        "goal catalog objectives differ from the named recipe library",
        errors,
    )
    presets = preset_catalog().presets
    _require(
        training.get("implemented_presets") == [preset.preset_id for preset in presets],
        "support presets differ from the versioned recipe presets",
        errors,
    )
    _check_no_recipe_default_literals(errors)
    _require(
        training.get("implemented_row_schemas") == sorted(PRODUCT_ROW_SCHEMAS),
        "support row schemas differ from PRODUCT_ROW_SCHEMAS",
        errors,
    )
    _require(
        training.get("implemented_families")
        == list(IMPLEMENTED_TRAINING_FAMILIES),
        "support training families differ from IMPLEMENTED_TRAINING_FAMILIES",
        errors,
    )
    _require(
        training.get("planned_families") == list(PLANNED_TRAINING_FAMILIES),
        "support planned families differ from PLANNED_TRAINING_FAMILIES",
        errors,
    )
    unsupported_families = training.get("explicitly_unsupported_families")
    if not isinstance(unsupported_families, list):
        errors.append("support explicitly_unsupported_families must be a list")
    else:
        unsupported_ids = [
            entry.get("family")
            for entry in unsupported_families
            if isinstance(entry, dict)
        ]
        _require(
            len(unsupported_ids) == len(unsupported_families)
            and unsupported_ids
            == list(EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES),
            "support unsupported families differ from "
            "EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES",
            errors,
        )
    _require(
        training.get("implemented_loss_policies") == list(LOSS_POLICY_IDS),
        "support loss policies differ from LOSS_POLICY_IDS",
        errors,
    )
    _require(
        artifacts.get("implemented_physical_containers")
        == list(IMPLEMENTED_PHYSICAL_CONTAINERS),
        "support physical containers differ from IMPLEMENTED_PHYSICAL_CONTAINERS",
        errors,
    )
    profiles = artifacts.get("implemented_bundle_profiles")
    if not isinstance(profiles, list) or len(profiles) != 1:
        errors.append("support registry must contain exactly the implemented minimal-v1 bundle")
    else:
        expected_paths = sorted(
            {
                MANIFEST_NAME,
                ATTESTATION_NAME,
                TRAIN_PATH,
                EVALUATION_PATH,
                PROVENANCE_PATH,
                VALIDATION_PATH,
            }
        )
        _require(
            profiles[0].get("profile") == "minimal-v1"
            and profiles[0].get("state") == "implemented"
            and profiles[0].get("paths") == expected_paths,
            "minimal-v1 support entry differs from bundle constants",
            errors,
        )

    transport_profiles = artifacts.get("implemented_transport_profiles")
    if not isinstance(transport_profiles, list) or len(transport_profiles) != 2:
        errors.append(
            "support registry must contain exactly both deterministic transports"
        )
    else:
        transports = {
            entry.get("profile"): entry
            for entry in transport_profiles
            if isinstance(entry, dict)
        }
        bundle_transport = transports.get("deterministic-vfbundle-zip-v1", {})
        export_transport = transports.get(
            "deterministic-export-pack-zip-v1",
            {},
        )
        _require(
            set(transports)
            == {
                "deterministic-vfbundle-zip-v1",
                "deterministic-export-pack-zip-v1",
            }
            and bundle_transport.get("state") == "implemented"
            and bundle_transport.get("product_role") == "immutable-transport"
            and bundle_transport.get("requires_external_manifest_digest") is True
            and bundle_transport.get("is_trainer_export") is False
            and export_transport.get("state") == "implemented"
            and export_transport.get("product_role")
            == "immutable-export-pack-transport"
            and export_transport.get("requires_external_export_receipt_digest")
            is True
            and export_transport.get("is_trainer_export") is False,
            "deterministic transport support entries differ from taxonomy",
            errors,
        )

    generic_containers = artifacts.get("generic_export_containers")
    non_generic_containers = {
        "minimal-v1",
        "deterministic-vfbundle-zip-v1",
        "deterministic-export-pack-zip-v1",
    }
    implemented_generic_containers = tuple(
        container
        for container in IMPLEMENTED_PHYSICAL_CONTAINERS
        if container not in non_generic_containers
    )
    expected_generic_containers = [
        *((container, "implemented") for container in implemented_generic_containers),
        *((container, "planned") for container in PLANNED_PHYSICAL_CONTAINERS),
    ]
    if not isinstance(generic_containers, list):
        errors.append("support generic_export_containers must be a list")
    else:
        current_generic_containers = [
            (entry.get("container"), entry.get("state"))
            for entry in generic_containers
            if isinstance(entry, dict)
        ]
        _require(
            len(current_generic_containers) == len(generic_containers)
            and current_generic_containers == expected_generic_containers,
            "generic export containers differ from taxonomy container states",
            errors,
        )
        implemented_entries = {
            entry.get("container"): entry
            for entry in generic_containers
            if isinstance(entry, dict) and entry.get("state") == "implemented"
        }
        _require(
            set(implemented_entries) == set(implemented_generic_containers),
            "implemented generic export entries differ from taxonomy",
            errors,
        )
        split_jsonl = implemented_entries.get("split-jsonl-directory")
        if split_jsonl is not None:
            _require(
                split_jsonl.get("container_version") == 1
                and split_jsonl.get("determinism_claim")
                == "portable_exact_bytes"
                and split_jsonl.get("consumer_profile") is None
                and split_jsonl.get("supported_row_schemas")
                == sorted(V1_ROW_SCHEMAS),
                "split JSONL support evidence differs from its executable contract",
                errors,
            )
        canonical_json = implemented_entries.get("json")
        if canonical_json is not None:
            _require(
                canonical_json.get("container_version") == 1
                and canonical_json.get("determinism_claim")
                == "portable_exact_bytes"
                and canonical_json.get("consumer_profile") is None
                and canonical_json.get("supported_row_schemas")
                == sorted(V1_ROW_SCHEMAS),
                "canonical JSON support evidence differs from its executable contract",
                errors,
            )
        constrained_csv = implemented_entries.get("constrained-csv")
        if constrained_csv is not None:
            _require(
                constrained_csv.get("container_version") == 1
                and constrained_csv.get("determinism_claim")
                == "portable_exact_bytes"
                and constrained_csv.get("consumer_profile") is None
                and constrained_csv.get("supported_row_schemas")
                == ["instruction_output", "prompt_completion", "text"],
                "constrained CSV support evidence differs from its executable contract",
                errors,
            )
        for container_id in ("parquet", "arrow", "hugging-face-dataset"):
            columnar = implemented_entries.get(container_id)
            if columnar is not None:
                _require(
                    columnar.get("container_version") == 1
                    and columnar.get("determinism_claim")
                    == "semantic_content_only"
                    and columnar.get("consumer_profile") is None
                    and columnar.get("supported_row_schemas")
                    == sorted(V1_ROW_SCHEMAS),
                    f"{container_id} support evidence differs from its executable contract",
                    errors,
                )

    consumer_profiles = support.get("consumer_profiles")
    if not isinstance(consumer_profiles, list):
        errors.append("support consumer_profiles must be a list")
        consumer_profiles = []
    profile_states = {
        profile.get("profile"): profile.get("state")
        for profile in consumer_profiles
        if isinstance(profile, dict) and isinstance(profile.get("profile"), str)
    }
    expected_profile_states = {
        **{profile: "implemented" for profile in IMPLEMENTED_CONSUMER_PROFILES},
        **{profile: "planned" for profile in PLANNED_CONSUMER_PROFILES},
        **{profile: "candidate" for profile in CANDIDATE_CONSUMER_PROFILES},
    }
    _require(
        len(profile_states) == len(consumer_profiles)
        and profile_states == expected_profile_states,
        "support consumer profile states differ from the taxonomy registry",
        errors,
    )

    canonical_profiles = [
        profile
        for profile in consumer_profiles
        if isinstance(profile, dict)
        and profile.get("profile") == CANONICAL_CONSUMER_PROFILE
    ]
    if len(canonical_profiles) != 1:
        errors.append("support registry must contain exactly one canonical profile")
    else:
        canonical = canonical_profiles[0]
        _require(
            canonical.get("state") == "implemented"
            and canonical.get("product_role") == "canonical-product",
            "canonical profile must be recorded as the implemented product boundary",
            errors,
        )

    aptus_profiles = [
        profile
        for profile in consumer_profiles
        if isinstance(profile, dict) and profile.get("profile") == "aptus-handoff-v1"
    ]
    if len(aptus_profiles) != 1:
        errors.append("support registry must contain exactly one Aptus profile")
    else:
        aptus = aptus_profiles[0]
        _require(
            aptus.get("state") == "implemented"
            and aptus.get("product_role") == "optional-integration",
            "Aptus must be recorded as an implemented optional integration",
            errors,
        )
        cli_default = inspect.signature(seal).parameters["aptus_handoff"].default
        cli_current = (
            cli_default.default if isinstance(cli_default, OptionInfo) else cli_default
        )
        server = create_mcp_server()
        mcp_seal = next(
            tool.fn for tool in server._tool_manager.list_tools() if tool.name == "seal"
        )
        mcp_current = inspect.signature(mcp_seal).parameters["write_handoff"].default
        workbench_source = (
            ROOT / "macos/Sources/ViewModels/WorkbenchViewModel.swift"
        ).read_text(encoding="utf-8")
        workbench_match = re.search(
            r"defaultWriteAptusHandoff\s*=\s*(true|false)\b",
            workbench_source,
        )
        workbench_current = (
            workbench_match.group(1) == "true" if workbench_match is not None else None
        )
        defaults = aptus.get("default_handoff")
        _require(
            defaults
            == {
                "cli_seal": cli_current,
                "mcp_seal": mcp_current,
                "workbench": workbench_current,
            },
            "Aptus default_handoff differs from CLI, MCP, or workbench source",
            errors,
        )
        _require(
            cli_current is False
            and mcp_current is False
            and workbench_current is False,
            "CLI, MCP, and workbench handoff defaults must remain false",
            errors,
        )
        _require(
            "veriformis.handoff" not in sys.modules,
            "tracking imports and MCP server creation unexpectedly loaded handoff code",
            errors,
        )

    generic_export_gaps = [
        gap
        for gap in support.get("known_current_gaps", [])
        if isinstance(gap, dict) and gap.get("id") == "gap-generic-export-service"
    ]
    _require(
        not generic_export_gaps,
        "completed Phase 4 cannot retain the generic export service foundation gap",
        errors,
    )
    _check_support_matrix(support, errors)


def _check_support_matrix(support: dict[str, Any], errors: list[str]) -> None:
    matrix = support_matrix()
    product = support.get("product") if isinstance(support.get("product"), dict) else {}
    training = support.get("training") if isinstance(support.get("training"), dict) else {}
    inputs = support.get("inputs") if isinstance(support.get("inputs"), dict) else {}
    artifacts = support.get("artifacts") if isinstance(support.get("artifacts"), dict) else {}
    _require(
        matrix.product_version == __version__ == product.get("version") == "0.1.0",
        "support-matrix product_version differs from package or registry",
        errors,
    )
    _require(
        matrix.maturity == "development-alpha"
        and product.get("maturity") == "development-alpha",
        "support-matrix maturity is not development-alpha",
        errors,
    )
    _require(
        matrix.aptus_required is False and product.get("aptus_required") is False,
        "support-matrix cannot require Aptus",
        errors,
    )
    _require(
        matrix.inputs.modes == tuple(IMPLEMENTED_INPUT_MODES)
        and matrix.inputs.families == tuple(IMPLEMENTED_INPUT_FAMILIES)
        and matrix.inputs.extensions == tuple(sorted(DECLARED_V1_EXTENSIONS))
        and matrix.inputs.explicitly_unsupported
        == tuple(EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES),
        "support-matrix inputs differ from executable input registries",
        errors,
    )
    _require(
        matrix.inputs.modes == tuple(inputs.get("implemented_modes") or ())
        and matrix.inputs.families == tuple(inputs.get("implemented_families") or ()),
        "support-matrix inputs differ from the support registry",
        errors,
    )
    _require(
        matrix.training.families == tuple(IMPLEMENTED_TRAINING_FAMILIES)
        and matrix.training.planned_families == tuple(PLANNED_TRAINING_FAMILIES)
        and matrix.training.explicitly_unsupported_families
        == tuple(EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES)
        and matrix.training.goals == tuple(training.get("implemented_goals") or ())
        and matrix.training.objectives == tuple(training.get("implemented_objectives") or ())
        and matrix.training.presets == tuple(training.get("implemented_presets") or ())
        and matrix.training.row_schemas == tuple(training.get("implemented_row_schemas") or ())
        and matrix.training.loss_policies == tuple(LOSS_POLICY_IDS),
        "support-matrix training lists differ from the support registry",
        errors,
    )
    _require(
        matrix.containers == tuple(IMPLEMENTED_PHYSICAL_CONTAINERS)
        and matrix.containers == tuple(artifacts.get("implemented_physical_containers") or ()),
        "support-matrix containers differ from taxonomy or the support registry",
        errors,
    )
    _require(
        matrix.profiles.implemented == tuple(IMPLEMENTED_CONSUMER_PROFILES)
        and matrix.profiles.optional_export_adapters
        == tuple(IMPLEMENTED_EXPORT_CONSUMER_PROFILES)
        and matrix.profiles.candidate_not_executable == tuple(CANDIDATE_CONSUMER_PROFILES)
        and matrix.profiles.extras_required == (),
        "support-matrix profiles differ from taxonomy",
        errors,
    )
    _require(
        tuple(item.exclusion_id for item in matrix.exclusions) == REQUIRED_EXCLUSIONS
        and matrix.hub_execute is False
        and matrix.generator is False
        and matrix.plugin_loader is False
        and matrix.platforms.public_signed_mac is False
        and matrix.published_corpus_tiers == (),
        "support-matrix exclusions drifted from the frozen 1.0 non-claims",
        errors,
    )


_RECIPE_LITERAL_PATTERNS = (
    re.compile(r"\b500[_]?000\b"),
    re.compile(r"\"veriformis-v1\""),
)
_RECIPE_LITERAL_FREE_SOURCES = (
    "src/veriformis/cli.py",
    "src/veriformis/mcp/server.py",
    "src/veriformis/pipeline/service.py",
    "src/veriformis/recipes/runner.py",
    "src/veriformis/recipes/library.py",
    "macos/Sources/ViewModels/WorkbenchViewModel.swift",
    "macos/Sources/Views/CompileView.swift",
    "macos/Sources/Services/VeriformisCLI.swift",
)


def _check_no_recipe_default_literals(errors: list[str]) -> None:
    """Roadmap 6.4: recipe defaults are versioned data, not CLI/Swift constants."""
    defaults = recipe_defaults()
    _require(
        defaults.construction.split_ratio_ppm == 500_000
        and defaults.curation.split_seed == "veriformis-v1",
        "recipe preset defaults changed; update the literal scan and contracts together",
        errors,
    )
    for relative in _RECIPE_LITERAL_FREE_SOURCES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for pattern in _RECIPE_LITERAL_PATTERNS:
            _require(
                pattern.search(text) is None,
                f"{relative} holds a recipe default literal matching {pattern.pattern}",
                errors,
            )


def _check_evidence_index(evidence: dict[str, Any], errors: list[str]) -> None:
    _require(
        evidence.get("schema_version") == "veriformis.evidence-index/v1",
        "evidence index schema_version is not veriformis.evidence-index/v1",
        errors,
    )
    grades = evidence.get("evidence_grades")
    records = evidence.get("records")
    if not isinstance(grades, dict) or not isinstance(records, list):
        errors.append("evidence grades must be an object and records must be a list")
        return
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            errors.append("every evidence record must be an object")
            continue
        record_id = record.get("id")
        if not isinstance(record_id, str) or record_id in seen:
            errors.append(f"invalid or duplicate evidence id {record_id!r}")
        else:
            seen.add(record_id)
        _require(
            record.get("grade") in grades,
            f"evidence {record_id!r} uses an unknown grade",
            errors,
        )
        details = record.get("details")
        _require(
            isinstance(details, str) and (ROOT / details).is_file(),
            f"evidence {record_id!r} details path does not exist",
            errors,
        )


def _iter_references(value: Any, *, key: str | None = None) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for child_key, child in value.items():
            found.extend(_iter_references(child, key=child_key))
    elif isinstance(value, list):
        for child in value:
            found.extend(_iter_references(child, key=key))
    elif isinstance(value, str) and key in LOCAL_REFERENCE_KEYS:
        found.append(value)
    return found


def _check_local_references(records: list[dict[str, Any]], errors: list[str]) -> None:
    for record in records:
        for reference in _iter_references(record):
            if reference.startswith(("http://", "https://")):
                continue
            path_text = reference.split("#", 1)[0]
            if not path_text:
                continue
            _require(
                (ROOT / path_text).exists(),
                f"tracked local reference does not exist: {reference}",
                errors,
            )


def check() -> list[str]:
    """Return all detected tracking inconsistencies."""
    errors: list[str] = []
    program = _load_json(PROGRAM_PATH)
    support = _load_json(SUPPORT_PATH)
    evidence = _load_json(EVIDENCE_PATH)
    _check_program(program, errors)
    _check_support(support, errors)
    _check_evidence_index(evidence, errors)
    _check_local_references([program, support, evidence], errors)
    return errors


def main() -> int:
    try:
        errors = check()
    except TrackingError as exc:
        errors = [str(exc)]
    if errors:
        print("Project tracking check: FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Project tracking check: PASS")
    print("- 21 roadmap phases match program.json and WIP.md")
    print(
        "- implemented inputs, input families, input modes, taxonomy families, "
        "objectives, goals, presets, rows, loss policies, containers, profiles, "
        "and handoff defaults match code; surfaces hold no recipe default literal"
    )
    print("- governed phase packets and evidence references are structurally complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
