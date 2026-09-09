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
