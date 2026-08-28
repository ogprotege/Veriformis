"""Phase 16.9: missing extras do not block core; a broken optional fails closed."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.errors import ExtensionProtocolError
from veriformis.extensions.registry import BuiltinBinding
from veriformis.extensions.runtime import bound_split_jsonl_exporter, bound_text_parser
from veriformis.exports.service import ExportService
from veriformis.pipeline import PipelineService
from veriformis.workspace import Workspace


ROOT = Path(__file__).resolve().parents[2]
RUNNER = CliRunner()
_EMPTY_EXTRAS = (
    "trl",
    "mlx-lm",
    "columnar",
    "axolotl",
    "llama-factory",
    "unsloth",
    "ocr",
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


def _broken_optional_parser(*_args: object, **_kwargs: object) -> None:
    """Test-only extra=ocr stand-in. It must never run on a product path."""
    raise RuntimeError("broken optional extra ocr must not execute")


def test_optional_extras_remain_empty() -> None:
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["optional-dependencies"]
    for name in _EMPTY_EXTRAS:
        assert extras[name] == []


def test_core_surfaces_start_with_missing_optional_extras() -> None:
    script = (
        "from veriformis.cli import app\n"
        "from veriformis.mcp.server import create_mcp_server\n"
        "from veriformis.pipeline import PipelineService\n"
        "PipelineService()\n"
        "create_mcp_server()\n"
        "assert app is not None\n"
        "import sys\n"
        f"optional = {_OPTIONAL_IMPORT_ROOTS!r}\n"
        "loaded = sorted(name for name in optional if name in sys.modules)\n"
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
    result = RUNNER.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_production_registry_has_no_optional_extra_parser() -> None:
    registry = PipelineService().extension_registry
    assert all(item.extra is None for item in registry.parsers)
    assert registry.mapper.extra is None
    assert all(item.extra is None for item in registry.constructors)


def test_broken_optional_binding_cannot_run_through_migrated_exemplars(
    tmp_path: Path,
) -> None:
    workspace = Workspace.create(tmp_path / "workspace")
    head_before = workspace.head_id
    bundle_path = tmp_path / "must-not-exist.vfbundle"
    marker = tmp_path / "broken-ran"

    def broken_writer(*_args: object, **_kwargs: object) -> None:
        marker.write_text("ran", encoding="utf-8")
        bundle_path.write_text("tamper", encoding="utf-8")
        (workspace.root / "HEAD").write_text("rev-v1-deadbeef", encoding="ascii")
        raise RuntimeError("broken optional extra ocr must not execute")

    binding = BuiltinBinding(
        "source-parser",
        "ocr-image",
        "ocr",
        "builtin",
        broken_writer,
    )
    assert binding.extra == "ocr"
    text = SimpleNamespace(
        kind="source-parser",
        origin="builtin",
        extra="ocr",
        contract_version=1,
        discovery=SimpleNamespace(selector="text"),
    )
    with pytest.raises(
        ExtensionProtocolError,
        match="text parser requires extra null; requested extra 'ocr'",
    ):
        bound_text_parser(declaration=text)  # type: ignore[arg-type]
    exporter = SimpleNamespace(
        kind="container-exporter",
        origin="builtin",
        extra="ocr",
        contract_version=1,
        discovery=SimpleNamespace(selector="split-jsonl-directory"),
    )
    with pytest.raises(
        ExtensionProtocolError,
        match="split-jsonl-directory requires extra null; requested extra 'ocr'",
    ):
        bound_split_jsonl_exporter(
            catalog=ExportService()._catalog(),
            declaration=exporter,  # type: ignore[arg-type]
        )
    assert not marker.exists()
    assert not bundle_path.exists()
    assert workspace.head_id == head_before
    assert not list(workspace.root.glob("*.vfbundle"))
    with pytest.raises(RuntimeError, match="broken optional extra ocr must not execute"):
        _broken_optional_parser()
    assert workspace.head_id == head_before
    assert not bundle_path.exists()
