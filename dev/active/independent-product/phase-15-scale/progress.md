# Phase 15 Progress

Append-only. Corrections add a later entry.

## 2026-08-26 — Phase 15 opened; item 15.1 in progress

**Status:** Packet created from clean `main` at
`44a1a94150171d9bca4049f5d8069885494e4192` (PR #131 Phase 14 closeout).

Item 15.1 opens the packet. There is no retained corpus benchmark,
published support tier, or public scale guarantee. Canonical JSON v1
makes no scale, streaming, or memory claim. Hugging Face Dataset export
pins one shard per split. Operator locks of 2026-08-26 are recorded.
Sequential PRs 15.1–15.9. Stop after 15.3 for operator review of
baselines before 15.4. Do not start Phase 16 from this packet.

**Next action:** Publish the item 15.1 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 15.2.

## 2026-08-26 — Item 15.1 local gates green

**Status:** Packet, tracking, and scale-isolation tests are on
`phase15/01-scale-packet`.

Local gates: `uv lock --check`; `ruff check src tests`;
`scripts/check_project_tracking.py` PASS; focused isolation 12 passed;
core pytest 2251 passed, 16 deselected, 1 expected durability warning;
`git diff --check` clean.

**Next action:** Open the item 15.1 pull request. Require every GitHub
check, merge, and synchronize clean main before item 15.2.
