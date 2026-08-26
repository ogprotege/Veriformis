# Phase 13 Progress

Append-only. Corrections add a later entry.

## 2026-08-25 — Phase 13 opened; item 13.1 in progress

**Status:** Packet created from clean `main` at
`783a2a1448049a2fbfa384df586e9d1497b36afb` (PR #113 stamp of PR #112).

Item 13.1 opens the packet. The seventeen finished-dataset gates and four
quality-finding codes remain the implemented quality surface.
`near_duplicate_policy` stays `disabled`. Preflight still names
`no-quality-intelligence`. There is no quality-report command. Operator
instruction 2026-08-25: sequential PRs now that the repository is public.

**Next action:** Publish the item 13.1 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 13.2.

## 2026-08-25 — Item 13.1 local gates green

**Status:** Packet, tracking, and quality-isolation tests are on
`phase13/01-quality-packet`.

Local gates: `uv lock --check`; `ruff check src tests`;
`scripts/check_project_tracking.py` PASS; focused isolation 8 passed;
core pytest 2164 passed, 16 deselected, 1 expected durability warning;
`git diff --check` clean.

**Next action:** Open the item 13.1 pull request. Require every GitHub
check, merge, and synchronize clean main before item 13.2.

## 2026-08-25 — Item 13.1 merged

**Status:** Phase 13.1 merged as PR #114 at
`cdbab4e6eadb74a8f0710b4b1fd6ecc46c0fe0f5`. Clean local `main` equals
`origin/main` there.

**Next action:** Open the item 13.2 pull request.

## 2026-08-25 — Item 13.2 quality report schema

**Status:** `veriformis.quality-report/v1` binds an empty report to a
finished-dataset plan. Facts, policy, and recommendations are separate
types. `enforcing` is false. There is no CLI command.

Local gates: tracking PASS; ruff pass; focused quality/isolation 14
passed; core pytest 2170 passed, 16 deselected, 1 expected durability
warning.

**Next action:** Publish the item 13.2 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 13.3.

## 2026-08-25 — Item 13.2 merged

**Status:** Phase 13.2 merged as PR #115 at
`89d579629eba3d2cb36444f40f5fe38d3a08ddcc`. Clean local `main` equals
`origin/main` there.

**Next action:** Open the item 13.3 pull request.

## 2026-08-25 — Item 13.3 dataset distributions

**Status:** `report_dataset_distributions` fills the closed v1 fact set
from a bound recipe, construction, curation, and split. Language without
constructed evidence is `evidence-unqualified`. The report is not
enforcing. There is no CLI command.

Local gates: tracking PASS; ruff pass; focused quality/isolation 20
passed; core pytest 2176 passed, 16 deselected, 1 expected durability
warning.

**Next action:** Publish the item 13.3 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 13.4.

## 2026-08-25 — Item 13.3 merged

**Status:** Phase 13.3 merged as PR #116 at
`b2acf7cbd4fa497fb8b7adf5dda5f32b991aa25a`. Clean local `main` equals
`origin/main` there.

**Next action:** Open the item 13.4 pull request.

## 2026-08-25 — Item 13.4 near-duplicate clusters

**Status:** Algorithm `veriformis.near-duplicate-ws-shingle-jaccard/v1`
records inspectable clusters and ppm threshold previews. It is not
semantic identity and does not delete rows. Curation
`near_duplicate_policy` stays `disabled`. The report is not enforcing.

Local gates: tracking PASS; ruff pass; focused quality/isolation 23
passed; core pytest 2178 passed, 16 deselected, 1 expected durability
warning. Follow-up pins Unicode casefold/whitespace clustering.

**Next action:** Publish the item 13.4 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 13.5.

## 2026-08-25 — Item 13.4 merged

**Status:** Phase 13.4 merged as PR #117 at
`8b011502cc6848adc0bbf13b64592f60a94e384c`. Clean local `main` equals
`origin/main` there.

**Next action:** Open the item 13.5 pull request.

## 2026-08-25 — Item 13.5 leakage checks

**Status:** `report_leakage_checks` records imported partition-hint
mismatches and digest-bound reference corpus hits. Unbound corpora are
`unbound`. The report is not enforcing and does not certify
contamination absence.

Local gates: tracking PASS; ruff pass; focused quality/isolation 25
passed; core pytest 2181 passed, 16 deselected, 1 expected durability
warning.

**Next action:** Publish the item 13.5 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 13.6.
