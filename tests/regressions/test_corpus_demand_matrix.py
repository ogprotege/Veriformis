from __future__ import annotations

import builtins
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "docs/governance/corpus-demand-matrix.json"
SCHEMA_PATH = ROOT / "docs/governance/corpus-demand-matrix.schema.json"
SCANNER_PATH = ROOT / "scripts/scan_corpus_metadata.py"


def _matrix() -> dict[str, object]:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _scanner_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("scan_corpus_metadata", SCANNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_repository_fixture_aggregate_matches_committed_matrix() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCANNER_PATH),
            "tests/fixtures",
            "--source-id",
            "repository-test-fixtures",
            "--evidence-grade",
            "test-verified",
            "--portability",
            "repository-tracked",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    observed = json.loads(result.stdout)
    matrix = _matrix()
    assert observed == matrix["inventory_observations"][0]


def test_scanner_does_not_open_content_or_emit_identifiers(
    tmp_path: Path,
    monkeypatch,
) -> None:
    private_root = tmp_path / "customer-secret-root"
    private_root.mkdir()
    secret_name = "confidential-client-name.private"
    secret_content = "content-must-never-be-read-or-emitted"
    (private_root / secret_name).write_text(secret_content, encoding="utf-8")
    module = _scanner_module()

    def refuse_open(*args, **kwargs):
        raise AssertionError("scanner attempted to open file content")

    monkeypatch.setattr(builtins, "open", refuse_open)
    monkeypatch.setattr(Path, "open", refuse_open)
    monkeypatch.setattr(Path, "read_bytes", refuse_open)
    monkeypatch.setattr(Path, "read_text", refuse_open)
    observed = module.scan_source(
        private_root,
        source_id="sanitized-owner-corpus",
        evidence_grade="recorded-local",
        portability="local-only",
    )
    serialized = json.dumps(observed, sort_keys=True)

    assert observed["aggregate"]["file_count"] == 1
    assert observed["aggregate"]["extensions"][0]["extension"] == "[undeclared-other]"
    assert secret_name not in serialized
    assert secret_content not in serialized
    assert str(private_root) not in serialized
    assert observed["privacy"] == {
        "content_hashes_emitted": False,
        "file_content_read": False,
        "file_names_emitted": False,
        "source_paths_emitted": False,
        "timestamps_emitted": False,
        "undeclared_extensions_emitted": False,
    }


def test_demand_matrix_claims_preserve_evidence_limits() -> None:
    matrix = _matrix()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert matrix["schema_version"] == "veriformis.corpus-demand-matrix/v1"
    assert schema["properties"]["schema_version"]["const"] == matrix["schema_version"]

    observations = matrix["inventory_observations"]
    assert observations[0]["portability"] == "repository-tracked"
    local_observations = [item for item in observations if item["portability"] == "local-only"]
    assert local_observations
    assert all(item["evidence_grade"] == "recorded-local" for item in local_observations)

    priorities = matrix["format_priorities"] + matrix["trainer_priorities"]
    for priority in priorities:
        if priority["state"] == "unranked-insufficient-evidence":
            assert priority["rank"] is None
        else:
            assert isinstance(priority["rank"], int) and priority["rank"] > 0
        for basis in priority["basis"]:
            assert basis["limitation"]
            for source in basis["sources"]:
                assert (ROOT / source).is_file(), source

    named_profiles = next(
        item for item in matrix["trainer_priorities"]
        if item["work_item"] == "named-consumer-profile-order"
    )
    assert named_profiles["rank"] is None
    assert named_profiles["state"] == "unranked-insufficient-evidence"
    assert {gap["gap_id"] for gap in matrix["evidence_gaps"]} == {
        "actual-training-destinations",
        "owner-corpus-composition",
        "representative-scale",
        "required-physical-containers",
    }
