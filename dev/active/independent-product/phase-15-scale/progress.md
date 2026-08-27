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

## 2026-08-26 — Item 15.3b merged

**Status:** Phase 15.3b merged as PR #135 at
`f4527a378c0b10141f34a710481aced12594a396`. Clean local `main` equals
`origin/main` there.

**Next action:** Operator compiles dataset-row through the existing CLI.
`scale-baseline` still refuses dataset-row. Item 15.4 stays closed.

## 2026-08-27 — Item 15.3c dataset-row CLI compile

**Status:** Operator dataset-row compile of the two-row `text.jsonl`
fixture sealed and verified. `scale-baseline --corpus-id ci-tiny-jsonl`
refused. Peak RSS is the max of separate CLI processes. Amplification
is overhead. `sla_claim` stays false. No published tier. Item 15.4
stays closed.

**Next action:** Record local gates, then publish the item 15.3c pull
request. Do not start 15.4. Do not start Phase 16.

## 2026-08-27 — Item 15.3c local gates green

**Status:** Dataset-row CLI compile evidence and the `scale-baseline`
refusal are on `phase15/03c-dataset-row-cli-compile`. Two-row fixture
sealed. Amplification is overhead. `sla_claim` stays false. Item 15.4
stays closed.

Local gates: `uv lock --check`; `ruff check src tests`;
`scripts/check_project_tracking.py` PASS; focused scale isolation and
baseline 20 passed; `git diff --check` clean.

**Next action:** Open the item 15.3c pull request. Require every GitHub
check, merge, and synchronize clean main. Do not start 15.4. Do not
start Phase 16.

## 2026-08-27 — Item 15.3c merged

**Status:** Phase 15.3c merged as PR #136 at
`56e54dccf7a40ab6fd8c72fe6d1fdcfa8171a978`. Clean local `main` equals
`origin/main` there.

**Next action:** Operator instructed to finish Phase 15. Item 15.4
records the review: no published corpus support tier.

## 2026-08-27 — Item 15.4 operator-reviewed support declaration

**Status:** `veriformis.scale-support-discovery/v1` publishes an empty
tier list. Observed reports and refusals are discovery. `sla_claim`
is false. Unmet sizes stay unmeasured. No rewrite.

**Next action:** Record local gates, then publish the item 15.4 pull
request. Do not start Phase 16.

## 2026-08-27 — Item 15.4 local gates green

**Status:** Scale support discovery is on `phase15/04-support-tiers`.
`published_tiers` is empty. `sla_claim` is false.

Local gates: `uv lock --check`; `ruff check src tests`;
`scripts/check_project_tracking.py` PASS; focused scale 35 passed;
`git diff --check` clean.

**Next action:** Open the item 15.4 pull request. Require every GitHub
check, merge, and synchronize clean main. Do not start Phase 16.

## 2026-08-27 — Item 15.4 merged

**Status:** Phase 15.4 merged as PR #137 at
`1c5c5a9fd296d66778881dd38964729026ec5e44`. Clean local `main` equals
`origin/main` there.

**Next action:** Item 15.5 skips with a record; 15.4 named no bottleneck.

## 2026-08-27 — Item 15.5 skipped: no named bottleneck

**Status:** 15.5 is skipped. 15.4 published no tier and named no
hot path to rewrite. No profiler. No stage rewrite.

**Next action:** Record local gates, then publish the item 15.5 pull
request. Do not start Phase 16.

## 2026-08-27 — Item 15.5 local gates green

**Status:** 15.5 skip record is on `phase15/05-measured-optimize`.

Local gates: `uv lock --check`; `ruff check src tests`;
`scripts/check_project_tracking.py` PASS; focused scale 35 passed;
`git diff --check` clean.

**Next action:** Open the item 15.5 pull request. Require every GitHub
check, merge, and synchronize clean main. Do not start Phase 16.

## 2026-08-27 — Item 15.5 merged

**Status:** Phase 15.5 merged as PR #138 at
`f3c6bd4a300048358a9453b168ee4e8270e47b4e`. Clean local `main` equals
`origin/main` there.

**Next action:** Skip 15.6–15.8 with a record. Close Phase 15 at 15.9.

## 2026-08-27 — Items 15.6–15.9 skip unmeasured work and closeout

**Status:** 15.6 streaming, 15.7 bounded execution, and 15.8 sharding
are skipped with a record. 15.9 adds cancel, long-row, file-count, and
no-preflight checks and closes the packet. `published_tiers` stays
empty. Do not start Phase 16.

**Next action:** Record local gates, then publish the closeout pull
request.

## 2026-08-27 — Items 15.6–15.9 local gates green

**Status:** Skip records, adversarial checks, and closeout are on
`phase15/06-09-close-scale`.

Local gates: `uv lock --check`; `ruff check src tests`;
`scripts/check_project_tracking.py` PASS; focused scale 40 passed;
`git diff --check` clean.

**Next action:** Open the closeout pull request. Require every GitHub
check, merge, and synchronize clean main. Do not start Phase 16.
