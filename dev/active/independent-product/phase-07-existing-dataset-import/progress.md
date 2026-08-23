# Phase 7 Progress

Append-only. Corrections add a later entry.

## 2026-08-23 — Phase 7 opened; item 7.1 in progress

**Status:** Packet created from clean `main` at
`6c4694c2e1c523156cd7c8f34c12f258a3ce0b01` (PR #69 stamp after PR #67).

Item 7.1 names `document-source`, `dataset-row`, and `mixed` under ADR-0010.
Only `document-source` executes. Dataset-row and mixed refuse with the later
item in the reason.

**Next action:** Finish 7.1 focused gates, then publish, require green GitHub
checks, merge, and synchronize clean main before item 7.2.

## 2026-08-23 — Item 7.1 implementation present locally

Focused mapping-mode tests passed (9). Tracking, Ruff, structured JSON, and
diff check passed. CLI and compile-preflight regressions passed (65).
Publication remains pending.

**Next action:** Publish the item 7.1 pull request. GitHub Actions may refuse
jobs while the spending budget is exhausted; do not treat that as a product
failure.

## 2026-08-23 — Item 7.1 merged; item 7.2 in progress

Item 7.1 merged as PR #71 at `caf4b1551d099d3b0d5d4de048ba057ea87050a4`.
GitHub Actions remained budget-blocked; merge followed local admission
evidence. Item 7.2 freezes mapping contracts without capture or execution.

## 2026-08-23 — Item 7.2 merged; item 7.3 in progress

Item 7.2 merged as PR #72 at `c71fbb3e33e5d65e4a9d349f9bcbd724c28336c1`.
Item 7.3 captures UTF-8 JSONL, executes confirmed mapping plans into the
four semantic rows with `mapped_value` evidence, opens workspace revision
v4 with stage `map`, and seals imported records as ordinary `ProductRow`
v1. Partition policy remains `replaced`. JSON and CSV remain reserved.

## 2026-08-23 — Item 7.3 merged; item 7.4 in progress

Item 7.3 merged as PR #73. Item 7.4 packages mapping detectors and requires
the confirmation digest of a chosen proposal before `map` mutates a workspace.

## 2026-08-23 — Items 7.4–7.7 merged; item 7.8 in progress

Items 7.4–7.7 merged as PR #74 through PR #77. JSON and CSV remain the item
7.8 admission. Mapping-grade JSON arrays, `{records}`/`{rows}` objects, and
comma CSV with a required header are captured without document recovery.

**Next action:** Finish 7.8 focused gates, then publish, merge on local
admission evidence if GitHub Actions remains budget-blocked, and synchronize
clean main before item 7.9.

## 2026-08-23 — Item 7.8 merged; item 7.9 in progress

Item 7.8 merged as PR #78 at `5a34626d850751811c50d1ad26d13f3297bf98c0`.
Row-level mapping rejections are a content-addressed project artifact, not a
verified export. Accepted rows still seal; rejected rows stay out of the row
set.

**Next action:** Finish 7.9 focused gates, publish, merge on local admission
evidence if GitHub Actions remains budget-blocked, and synchronize clean main
before item 7.10.

## 2026-08-23 — Item 7.9 merged; item 7.10 closeout in progress

Item 7.9 merged as PR #79 at `ef9fded646e55bd8eafabe327ca5cc767fae7d4a`.
Mapping templates, operator guide, U1–U7 judgment, support-registry gap close,
and packet closeout are this item. Do not start Phase 8, 9, or 13.
