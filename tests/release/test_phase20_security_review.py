"""Phase 20.4: license, secret, parser-threat, and provenance review."""

from __future__ import annotations

import ast
import json
import re
import tomllib
from pathlib import Path

import pytest

from veriformis.cli import app
from veriformis.errors import UnsupportedInputError
from veriformis.mcp.server import create_mcp_server
from veriformis.parsers.dispatch import parse_captured_source
from veriformis.pipeline import PipelineService
from veriformis.publication import create_publication_adapter
from veriformis.recipes.pipeline_spec import PIPELINE_SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "docs/security.md"
_LIVE_SECRET_VALUES = re.compile(
    r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"
    r"|AKIA[0-9A-Z]{16}"
    r"|ghp_[A-Za-z0-9]{20,}"
    r"|hf_[A-Za-z0-9]{20,}",
)
_SCAN_ROOTS = ("src", "scripts", "examples")
_NETWORK_MODULES = frozenset({"httpx", "huggingface_hub", "openai", "requests"})
_COMPILE_SOURCES = (
    ROOT / "src/veriformis/recipes/runner.py",
    ROOT / "src/veriformis/recipes/pipeline_spec.py",
    ROOT / "src/veriformis/pipeline/service.py",
)


def _cli_names() -> set[str]:
    return {command.name for command in app.registered_commands}


def test_security_review_names_required_sections() -> None:
    text = REVIEW.read_text(encoding="utf-8")
    for required in (
        "License inventory",
        "Vulnerability review",
        "Parser threat model",
        "Secret scan",
        "Artifact reproducibility",
        "Provenance",
        "Privacy",
        "MIT",
        "resolve_entities=False",
        "no_network=True",
        "This review does not subscribe to an external vulnerability database",
        "Public signed, notarized, or stapled Mac",
    ):
        assert required in text, required


def test_first_party_license_is_mit() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("MIT License")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["license"] == "MIT"
    dependencies = project["project"]["dependencies"]
    assert dependencies
    extras = project["project"]["optional-dependencies"]
    for name in ("trl", "mlx-lm", "columnar", "axolotl", "llama-factory", "unsloth", "ocr"):
        assert extras[name] == []
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert lock
    assert "huggingface_hub" not in " ".join(dependencies)


def test_source_tree_has_no_live_credentials() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "HF_TOKEN" not in pyproject
    workflows = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / ".github/workflows").glob("*.yml")
    )
    assert "secrets:" not in workflows.lower()
    hits: list[str] = []
    for folder in _SCAN_ROOTS:
        root = ROOT / folder
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix in {".png", ".pdf", ".docx", ".zip"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            if _LIVE_SECRET_VALUES.search(text):
                hits.append(str(path.relative_to(ROOT)))
    assert hits == [], hits


def test_compile_path_has_no_network_client_and_no_hub() -> None:
    assert PIPELINE_SCHEMA_VERSION == "veriformis.pipeline/v1"
    for path in _COMPILE_SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        assert imported.isdisjoint(_NETWORK_MODULES), path
    assert "hub-upload" not in _cli_names()
    assert "hub_upload" not in {
        tool.name for tool in create_mcp_server()._tool_manager.list_tools()
    }
    pin = create_publication_adapter(repository="ogprotege/example", revision="main")
    assert pin.execute_allowed is False
    assert not hasattr(PipelineService(), "hub_upload")


def test_unknown_suffix_fails_closed(tmp_path: Path) -> None:
    payload = b"not a supported capture"
    with pytest.raises(UnsupportedInputError):
        parse_captured_source(
            tmp_path / "x.bin",
            logical_path="x.bin",
            raw_bytes=payload,
        )


def test_ooxml_xml_parser_disables_entities_and_network() -> None:
    source = (ROOT / "src/veriformis/diagnostics.py").read_text(encoding="utf-8")
    assert "resolve_entities=False" in source
    assert "no_network=True" in source
    html = (ROOT / "src/veriformis/parsers/html.py").read_text(encoding="utf-8")
    assert "No network fetch is performed." in html
    golden = (ROOT / "scripts/release/golden_compile.sh").read_text(encoding="utf-8")
    assert "no integration dependency" in golden
    smoke = (ROOT / "scripts/release/smoke_install.sh").read_text(encoding="utf-8")
    assert "uv lock --check" in smoke


def test_golden_example_fingerprint_is_retained() -> None:
    fingerprint = json.loads(
        (ROOT / "examples/project-spec/expected-fingerprint.json").read_text(encoding="utf-8")
    )
    assert fingerprint["manifest_sha256"]
    assert len(fingerprint["manifest_sha256"]) == 64
