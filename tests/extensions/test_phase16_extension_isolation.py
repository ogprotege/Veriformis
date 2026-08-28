"""Phase 16 isolation: protocol declarations exist; no loader or dispatch change."""

from __future__ import annotations

import importlib.util
import inspect
import subprocess
import sys
import tomllib
from pathlib import Path

from veriformis.cli import app
from veriformis.construction import constructors as constructor_module
from veriformis.contracts import V1_FINISHED_DATASET_GATES
from veriformis.exports import _implementation as implementation_module
from veriformis.exports._implementation import _ExportImplementation
from veriformis.exports.service import ExportService
from veriformis.mcp.server import create_mcp_server
from veriformis.parsers import dispatch as parser_dispatch
from veriformis.pipeline import PipelineService
from veriformis.quality.gates import V1_QUALITY_GATES
from veriformis.taxonomy import TAXONOMY_AXES


ROOT = Path(__file__).resolve().parents[2]
_FORBIDDEN_OPERATIONS = frozenset(
    {
        "extension",
        "extensions",
        "extension-load",
        "extension_load",
        "install-extension",
        "install_extension",
        "plugin",
        "plugins",
        "plugin-load",
        "plugin_load",
    }
)
_OPTIONAL_IMPORT_ROOTS = (
    "trl",
    "mlx",
    "torch",
    "pyarrow",
    "datasets",
    "transformers",
    "axolotl",
    "llamafactory",
    "unsloth",
    "pytesseract",
)


def test_extension_package_is_protocol_only() -> None:
    assert importlib.util.find_spec("veriformis.extensions") is not None
    assert importlib.util.find_spec("veriformis._extensions") is None
    assert not (ROOT / "src/veriformis/extensions.py").exists()
    assert not (ROOT / "src/veriformis/_extensions.py").exists()
    assert not (ROOT / "src/veriformis/_extensions").exists()
    assert (ROOT / "src/veriformis/extensions/registry.py").exists()
    assert not (ROOT / "src/veriformis/extensions/loader.py").exists()
    from veriformis.extensions import __all__ as exported

    assert "load_capability_declaration" in exported
    assert "builtin_registry" in exported
    assert "install" not in exported
    assert "load_entry_points" not in exported


def test_packaging_has_no_plugin_entry_points_and_empty_extras() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    assert project["scripts"] == {"veriformis": "veriformis.cli:main"}
    assert "entry-points" not in project
    assert project["optional-dependencies"] == {
        "test": ["pytest>=8.0", "ruff==0.16.0"],
        "trl": [],
        "mlx-lm": [],
        "columnar": [],
        "axolotl": [],
        "llama-factory": [],
        "unsloth": [],
        "ocr": [],
    }


def test_core_import_does_not_load_optional_runtime_packages() -> None:
    script = (
        "import sys\n"
        "import veriformis\n"
        f"optional_roots = {_OPTIONAL_IMPORT_ROOTS!r}\n"
        "loaded = sorted(name for name in optional_roots if name in sys.modules)\n"
        "if loaded:\n"
        "    raise SystemExit(f'optional runtime packages loaded: {loaded}')\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_public_surfaces_have_no_extension_operation() -> None:
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    assert mcp_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    service = PipelineService()
    for name in _FORBIDDEN_OPERATIONS:
        assert not hasattr(service, name.replace("-", "_"))


def test_parser_dispatch_is_still_the_suffix_chain() -> None:
    source = inspect.getsource(parser_dispatch.parse_captured_source)
    assert "extension = Path(logical_path).suffix.lower()" in source
    assert 'if extension == ".txt"' in source
    assert "if extension in CODE_EXTENSIONS" in source
    assert "parse_text_via_protocol" in source
    assert "parse_md_file" in source
    assert "registry" not in source
    assert "extension_protocol" not in source


def test_constructors_are_still_one_private_exact_lookup() -> None:
    constructors = constructor_module._CONSTRUCTORS
    assert isinstance(constructors, dict)
    assert len(constructors) == 6
    assert all(
        type(selector) is tuple
        and len(selector) == 2
        and all(type(item) is str for item in selector)
        for selector in constructors
    )
    assert "_CONSTRUCTORS" not in constructor_module.__all__


def test_exports_and_profiles_still_share_one_private_catalog() -> None:
    service = ExportService()
    catalog = service._catalog()
    assert catalog
    assert all(type(item) is _ExportImplementation for item in catalog)
    assert any(item.descriptor.consumer_profile is None for item in catalog)
    assert any(item.descriptor.consumer_profile is not None for item in catalog)
    assert implementation_module.__all__ == []
    source = inspect.getsource(ExportService._resolve_implementation)
    assert "bound_split_jsonl_exporter" in source
    assert "request.consumer_id is None" in source
    assert source.index("bound_split_jsonl_exporter") < source.index(
        "for implementation in self._catalog()"
    )


def test_quality_gates_remain_preview_only() -> None:
    assert V1_QUALITY_GATES
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)


def test_taxonomy_has_no_extension_axis() -> None:
    assert TAXONOMY_AXES == (
        "training_family",
        "objective",
        "semantic_row",
        "physical_container",
        "consumer_profile",
        "loss_policy",
        "input_family",
    )
    assert all("extension" not in axis and "plugin" not in axis for axis in TAXONOMY_AXES)


def test_phase47_hooks_remain_trusted_conformance_code() -> None:
    contract = (ROOT / "docs/product-contract.md").read_text(encoding="utf-8")
    assert (
        "The private Phase 4.7 hooks are trusted conformance code rather than an\n"
        "untrusted plugin boundary."
    ) in contract


def test_seventeen_finished_dataset_gates_are_unchanged() -> None:
    assert len(V1_FINISHED_DATASET_GATES) == 17
    assert V1_FINISHED_DATASET_GATES[-1] == "snapshot"


def test_compatibility_kit_is_test_only() -> None:
    assert (
        ROOT / "tests/regressions/fixtures/phase16/compatibility-kit.json"
    ).exists()
    assert not (ROOT / "src/veriformis/extensions/kit.py").exists()
    assert not (ROOT / "src/veriformis/extensions/loader.py").exists()
