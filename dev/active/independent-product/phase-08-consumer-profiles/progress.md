# Phase 8 Progress

Append-only. Corrections add a later entry.

## 2026-08-23 — Phase 8 opened; item 8.1 in progress

**Status:** Packet created from clean `main` at
`64a7799c27d1a489f01d77d8ba399910c95c0712` (PR #81 after PR #80).

Item 8.1 publishes ADR-0012 and keeps `trl` / `mlx-lm` planned. Generic
exports stay `consumer_id` null. Selecting those identifiers refuses with the
later item. Do not emit trainer files.

Focused isolation tests passed (8). Tracking, Ruff, structured JSON, and
diff check passed. Core pytest passed 1964 with 1 deselected and the
intentional transport durability warning.

**Next action:** Publish the item 8.1 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 8.2.
