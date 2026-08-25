# Phase 11 Evidence

**Status:** Observed during 11.1–11.8

## Starting facts

- CLI parse required an explicit file list (`PipelineService.parse` →
  `capture_source_batch`).
- Mac `SourceDropView.expand` walked folders in Swift.
- Compile preflight was recipe eligibility over an already-chosen file list.
- `DECLARED_V1_EXTENSIONS` and eight `input_family` values were implemented.
- `ocr-image` was explicitly unsupported.
- Corpus demand matrix ranked new input formats unranked.

## Proof added this packet

- Collection fixtures: mixed directory, hidden, unsupported, symlink,
  duplicate bytes, max_files, package directory, empty directory.
- Parse of a directory equals parse of its explicit files for source count.
- Parser identity unit test.
- Parser hardening matrix for empty/truncated/malformed inputs.
- Image-only PDF still refused via the empty-text fixture.

Local gates on 2026-08-25:

- `uv run ruff check src tests`: passed
- `uv run python scripts/check_project_tracking.py`: PASS
- `uv lock --check`: passed
- `uv run pytest -q --ignore=tests/handoff -m "not aptus_integration and not profile_integration and not columnar_integration"`: 2112 passed, 16 deselected, 1 expected durability warning
- `git diff --check`: passed
