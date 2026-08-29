"""Phase 18.9: accessibility, keyboard, CLI equivalents, skip records."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MACOS = ROOT / "macos/Sources"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_primary_actions_have_accessibility_labels() -> None:
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    sources = _read("macos/Sources/Views/SourceDropView.swift")
    exports = _read("macos/Sources/Views/ExportsView.swift")
    review = _read("macos/Sources/Views/ReviewView.swift")
    run_sheet = _read("macos/Sources/Views/RunSheetView.swift")
    app = _read("macos/Sources/VeriformisApp.swift")
    assert 'accessibilityLabel("Compile to sealed bundle")' in compile_view
    assert 'accessibilityLabel("Goal")' in compile_view
    assert 'accessibilityLabel("Copy mapping CLI equivalent")' in compile_view
    assert 'accessibilityLabel("Browse source files")' in sources
    assert 'accessibilityLabel("Clear sources")' in sources
    assert 'accessibilityLabel("Execute confirmed export")' in exports
    assert 'accessibilityLabel("Submit confirmed review packet")' in review
    assert 'accessibilityLabel("Cancel compile")' in run_sheet
    assert 'accessibilityLabel("Copy compile error")' in run_sheet
    assert 'CommandMenu("Go")' in app
    assert 'keyboardShortcut("1", modifiers: .command)' in app
    assert "keyboardShortcut(.return, modifiers: .command)" in app
    assert 'keyboardShortcut(".", modifiers: .command)' in app


def test_cli_equivalents_cover_map_compile_export_review() -> None:
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    assert "var currentCompileCLIEquivalent: String?" in model
    assert "var currentMappingCLIEquivalent: String?" in model
    assert "var currentExportCLIEquivalent: String?" in model
    assert "var currentReviewCLIEquivalent: String?" in model
    assert "Copy mapping CLI equivalent" in compile_view
    assert '"mapping-detect"' in model
    assert '"mapping-preview"' in model


def test_english_v1_locale_and_no_github_xcodebuild() -> None:
    pbx = _read("macos/Veriformis.xcodeproj/project.pbxproj")
    assert "developmentRegion = en;" in pbx
    workflows = ROOT / ".github/workflows"
    texts = "\n".join(path.read_text(encoding="utf-8") for path in workflows.glob("*.yml"))
    assert "xcodebuild" not in texts


def test_source_list_is_not_virtualized() -> None:
    sources = _read("macos/Sources/Views/SourceDropView.swift")
    assert "LazyVStack" not in sources
    assert "List {" in sources
