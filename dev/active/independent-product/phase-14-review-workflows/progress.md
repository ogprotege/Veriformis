# Phase 14 Progress

Append-only. Corrections add a later entry.

## 2026-08-26 — Phase 14 opened; item 14.1 in progress

**Status:** Packet created from clean `main` at
`4d7b00fca9b685df95aa2a19349604f2b40d2406` (PR #123 stamp of PR #122).

Item 14.1 opens the packet. Construction `review_policy` defaults to
`none`. `ReviewEvidence` is an unsigned local attestation. CLI, MCP, and
`PipelineService` cannot submit completed review evidence. OCR preview
and quality findings are not queues. No Phase 13 heuristic is admitted
to block seal. Operator locks of 2026-08-26 are recorded. Sequential PRs
14.1–14.8. Do not start Phase 15 from this packet.

**Next action:** Publish the item 14.1 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 14.2.

## 2026-08-26 — Item 14.1 local gates green

**Status:** Packet, tracking, and review-isolation tests are on
`phase14/01-review-packet`.

Local gates: `uv lock --check`; `ruff check src tests`;
`scripts/check_project_tracking.py` PASS; focused isolation 9 passed;
core pytest 2205 passed, 16 deselected, 1 expected durability warning;
`git diff --check` clean.

**Next action:** Open the item 14.1 pull request. Require every GitHub
check, merge, and synchronize clean main before item 14.2.

## 2026-08-26 — Item 14.1 merged

**Status:** Phase 14.1 merged as PR #124 at
`2ba797ed093e72bc82a6b58166e0dc2e6c908d18`. Clean local `main` equals
`origin/main` there.

**Next action:** Open the item 14.2 pull request.

## 2026-08-26 — Item 14.2 review contracts

**Status:** `veriformis.review-bundle/v1` binds an empty bundle to a
finished-dataset plan. Waivers cannot change bytes. Corrections are
transforms or mapping revisions. `blocks_seal` is false. There is no
CLI submit command.

Local gates: tracking PASS; ruff pass; focused review 17 passed; core
pytest 2213 passed, 16 deselected, 1 expected durability warning.

**Next action:** Publish the item 14.2 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 14.3.

## 2026-08-26 — Item 14.2 merged

**Status:** Phase 14.2 merged as PR #125 at
`abd8645662722bd8a45b3f2fae070812aa9d980d`. Clean local `main` equals
`origin/main` there.

**Next action:** Open the item 14.3 pull request.

## 2026-08-26 — Item 14.3 first queues

**Status:** `report_core_queues` lists the five core kinds. Required-review
construction fills `construction-pending` items. Opt-in kinds stay off
unless requested. The bundle does not block seal.

Local gates: tracking PASS; ruff pass; focused review 19 passed; core
pytest 2215 passed, 16 deselected, 1 expected durability warning.

**Next action:** Publish the item 14.3 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 14.4.

## 2026-08-26 — Item 14.3 merged

**Status:** Phase 14.3 merged as PR #126 at
`ac708087d850800335c659d734d428fb1ae080c2`. Clean local `main` equals
`origin/main` there.

**Next action:** Open the item 14.4 pull request.

## 2026-08-26 — Item 14.4 corrections

**Status:** A correction binds a new transform (`trn`) or mapping-plan
(`mpl`) identity. Identical-byte transforms and unchanged mappings fail
closed. `overwrite_accepted_record` refuses in-place mutation. Waivers
do not change bytes. The bundle still does not block seal.

Local gates: tracking PASS; ruff pass; focused review 27 passed; core
pytest 2223 passed, 16 deselected, 1 expected durability warning.

**Next action:** Publish the item 14.4 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 14.5.

## 2026-08-26 — Item 14.4 merged

**Status:** Phase 14.4 merged as PR #127 at
`2ba3d763706c4fbed1b4a19aaafd722c38ef0786`. Clean local `main` equals `origin/main` there.

**Next action:** Open the item 14.5 pull request.

## 2026-08-26 — Item 14.5 sampling

**Status:** Algorithm `veriformis.review-sample-hmac-sha256/v1` ranks a
complete recorded population by HMAC-SHA256 of a named seed. The draw
replays. It claims no statistical meaning. Sample-acceptance items are
not required reviews.

Local gates: tracking PASS; ruff pass; focused review 33 passed; core
pytest 2229 passed, 16 deselected, 1 expected durability warning.

**Next action:** Publish the item 14.5 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 14.6.
