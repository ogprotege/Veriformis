# Phase 10 Progress

Append-only. Corrections add a later entry.

## 2026-08-24 — Phase 10 opened; item 10.1 in progress

**Status:** Packet created from clean `main` at
`abdcce6474aadd33fcf38a5360b63a4f8d293a5c` (PR #96).

Item 10.1 publishes ADR-0014 and keeps `axolotl`, `llama-factory`, and
`unsloth` as candidates. Selecting those consumer identifiers refuses as
Phase 10. Extras are empty lists. Do not emit those profiles. Aptus
remains the sibling handoff until item 10.6. Operator approval is
required after 10.2 before 10.3.

**Next action:** Publish the item 10.1 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 10.2.

## 2026-08-24 — Item 10.1 local gates green

**Status:** Packet, ADR-0014, empty extras, and candidate-refusal tests
are on `phase10/01-profile-expansion-packet`.

Local gates: `uv lock --check`; `ruff check src tests`;
`scripts/check_project_tracking.py` PASS; focused isolation 22 passed;
core pytest 2053 passed, 15 deselected, 1 expected durability warning;
`git diff --check` clean.

**Next action:** Open the item 10.1 pull request. Require every GitHub
check, merge, and synchronize clean main before item 10.2.
