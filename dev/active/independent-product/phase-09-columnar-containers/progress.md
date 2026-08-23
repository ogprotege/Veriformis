# Phase 9 Progress

Append-only. Corrections add a later entry.

## 2026-08-23 — Phase 9 opened; item 9.1 in progress

**Status:** Packet created from clean `main` at
`199e16eeabd8c624b571add9d28034830b3b92da` (PR #88).

Item 9.1 publishes ADR-0013 and keeps `parquet`, `arrow`, and
`hugging-face-dataset` planned. Selecting those container identifiers
refuses with the later item. Extra `columnar` is an empty list. Do not
emit Parquet, Arrow, or Hugging Face Dataset files.

Focused isolation tests passed (15 including Phase 8 isolation). Tracking,
Ruff, lock, and diff check passed. Core pytest passed 2009 with 3
deselected and the intentional transport durability warning.

**Next action:** Publish the item 9.1 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 9.2.
