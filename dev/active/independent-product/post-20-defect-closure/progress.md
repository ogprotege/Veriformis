# Progress

Append-only dated execution log.

## 2026-09-09

- Opened the packet from the full-repository audit of `main` at `5d617f8`.
- Baseline on this host: `uv lock --check`, `ruff`, tracking checker, and
  `git diff --check` pass; core pytest `2701 passed, 5 skipped, 17 deselected`
  in 15m03s (documented figure was ~90s).
- Verified directly before opening: D-01 (wheel omits `scale/support-v1.json`),
  D-02 (`café` → `cafÃ©` with `encoding=None`), D-03 (`splitlines()` in two
  JSONL framers), D-04 (Swift writes the plan into the CLI workspace before
  `parse`), D-05 (descriptor-declared capabilities), D-06 (`_seal_imported`
  has no `try`), D-07 (`canonical_digest` NFC), D-24 (9 goals / 8
  representations / 8 row schemas vs contract 5 / 4 / 4), D-27 (unmarked
  handoff test).

## 2026-09-09 — Phase 1 (ship blockers)

- D-01: `scale/*.json` added to `package-data`; `tests/release/test_package_data_coverage.py`
  compares on-disk data files with the declared globs; `inspect_python_artifacts.sh`
  asserts every data file is a wheel member; `smoke_install.sh` runs every discovery
  command from the clean venv. Verified locally: `veriformis/scale/support-v1.json`
  is now a wheel member.
- D-02: HTML capture decoded by Veriformis before lxml (BOM, strict UTF-8, declared
  charset); refusals `html.charset-unknown` / `html.charset-invalid`; diagnostics
  `html.charset-declared` / `html.bom-removed`. Parser pin `1.0.0 -> 1.1.0`.
  Frozen goal matrix regenerated through `--generate`; diff: exactly the 13
  `html` cells changed, only `manifest_sha256`, `row_set_sha256`, and
  `supervision_sha256`; every other cell byte-identical.
- D-03: `veriformis._jsonl_frames.frame_jsonl_lines` shared by the JSONL parser,
  dataset-row capture, and the handoff loader. Regressions prove U+2028/U+2029/U+0085
  records survive and fail on the unmodified framers.
- D-06: `_publish_or_recover_finished_bundle` and `_seal_messages` shared by both seal
  paths; `_seal_imported` wrapped in `SealPartialPublicationError`; recovery decodes
  `validation.json` with the sealing path's report loader (adopting an exact prior
  imported publication previously crashed on the document report schema).
- D-08: rejection report written before the `map` transaction opens, via temp file,
  fsync, and rename.
- D-09: `_run` returns the outcome; `map`, `seal`, `mapping-rejections` routed through
  it; `csv.Error`, `RecursionError`, oversized-int `ValueError` typed as
  `csv.invalid` / `json.invalid`; per-page pdfium failures typed as
  `pdf.page-unreadable`.
- D-05: `consume_aptus_handoff` recomputes the forbidden schemas from the taxonomy
  pin, flags capability blocks that differ from the pin, recomputes the masking
  expectation, and requires plan/recipe/construction/split/objective identities and
  the source-id set to match sealed provenance. Forged text-bundle descriptor now
  rejected on Python and CLI.
- D-27: `tests/handoff/test_defectclose_handoff.py` moved to `tests/regressions/`
  (collected by the core gate).
- D-04: Swift writes `run.log` and `confirmed-mapping-plan.json` to a sibling
  `<workspace>.workbench/` directory and no longer pre-creates the CLI workspace;
  real-repo-CLI dataset-row compile test added through `WorkbenchViewModel.compile()`.
- D-28: `profile-integration` job syncs `--extra columnar` and sets
  `VERIFORMIS_REQUIRE_PROFILE_LIBRARIES=1`; tests load emitted TRL / MLX-LM /
  Axolotl / LLaMA-Factory partitions through the official `datasets` loader and
  prove no trainer library is imported.
- `AGENTS.md` suite timing corrected from ~90s to the observed ~15 minutes.
