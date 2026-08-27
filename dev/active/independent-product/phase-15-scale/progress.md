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

## 2026-08-26 — Item 15.1 merged

**Status:** Phase 15.1 merged as PR #132 at
`569ff506a46e6e8ff928167a4320d0a7a5a373f1`. Clean local `main` equals
`origin/main` there.

**Next action:** Open the item 15.2 pull request.

## 2026-08-26 — Item 15.2 deterministic corpora

**Status:** `veriformis.scale-corpus-spec/v1` generates synthetic
markdown, JSONL, nested JSONL, PDF, and duplicate fixtures from a named
seed. Tiny CI specs cover the roadmap dimensions. Destination must be
empty. Owner library bytes are not used.

**Next action:** Record local gates, then publish the item 15.2 pull
request. Require green GitHub checks, merge, and synchronize clean main
before item 15.3.

## 2026-08-26 — Item 15.2 local gates green

**Status:** Generators and scale tests are on
`phase15/02-benchmark-corpora`.

Local gates: `uv lock --check`; `ruff check src tests`;
`scripts/check_project_tracking.py` PASS; focused scale 23 passed;
core pytest 2262 passed, 16 deselected, 1 expected durability warning;
`git diff --check` clean.

**Next action:** Open the item 15.2 pull request. Require every GitHub
check, merge, and synchronize clean main before item 15.3.

## 2026-08-26 — Item 15.2 merged

**Status:** Phase 15.2 merged as PR #133 at
`481fb32ee68ab546ad151e4c520b5761bf6135a4`. Clean local `main` equals
`origin/main` there.

**Next action:** Open the item 15.3 pull request.

## 2026-08-26 — Item 15.3 named-hardware baselines

**Status:** `veriformis.scale-baseline-report/v1` records wall, CPU,
peak RSS, disk amplification, object count, startup, between-stage
cancel, and resume. `sla_claim` is false. Tiny markdown CI smoke is
unmarked. `scale_benchmark` is excluded from core pytest. No published
tier.

**Next action:** Record local gates, then publish the item 15.3 pull
request. Stop after merge for operator review of baselines before 15.4.

## 2026-08-26 — Item 15.3 local gates green

**Status:** Baseline harness and scale tests are on
`phase15/03-baseline-harness`. Recorded-local tiny-markdown report is
in the packet; `sla_claim` is false.

Local gates: `uv lock --check`; `ruff check src tests`;
`scripts/check_project_tracking.py` PASS; focused scale 30 passed;
core pytest 2268 passed, 17 deselected, 1 expected durability warning;
`git diff --check` clean.

**Next action:** Open the item 15.3 pull request. Require every GitHub
check, merge, and synchronize clean main. Stop for operator review of
baselines before 15.4.

## 2026-08-26 — Item 15.3 merged

**Status:** Phase 15.3 merged as PR #134 at
`367cf4e4a484983f9b858ba527e1f054402ae1c5`. Clean local `main` equals
`origin/main` there.

**Next action:** Operator said measure more first; never a modest
fig-leaf tier.

## 2026-08-26 — Item 15.3b measurement ladder

**Status:** Packaged measurement-point specs and named-hardware reports
for markdown 10×40 through 100×1000, PDF, and tiny duplicates. Duplicate
ladder 10×40 refused coverage. Dataset-row compile unmeasured.
`sla_claim` stays false. No published tier.

**Next action:** Record local gates, then publish the item 15.3b pull
request. Do not start 15.4 until the operator reviews the ladder.

## 2026-08-26 — Item 15.3b local gates green

**Status:** Measurement ladder and named-hardware reports are on
`phase15/03b-measurement-ladder`. Duplicate 10×40 compile refused
coverage. Dataset-row compile unmeasured.

Local gates: `uv lock --check`; `ruff check src tests`;
`scripts/check_project_tracking.py` PASS; focused scale 31 passed;
core pytest 2269 passed, 17 deselected, 1 expected durability warning;
`git diff --check` clean.

**Next action:** Open the item 15.3b pull request. Require every GitHub
check, merge, and synchronize clean main. Do not start 15.4 until the
operator reviews the ladder.
