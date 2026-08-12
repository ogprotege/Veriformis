# ADR-0001 — Tracking Authority and Evidence Grades

**Status:** Accepted

**Date:** 2026-08-11

**Decider:** Repository owner direction, implemented through Phase 0

## Context and evidence

The repository already had a roadmap, current status, WIP, contracts, group
plans, and release evidence. Their roles were described in prose, but phase
state and current capability lists were not machine-checked. The old WIP also
contained both current and stale phase statements. A green test run could be
recorded without distinguishing a retained raw artifact from an observed local
summary.

## Decision

Use the authority order and completion rules in
`docs/governance/project-tracking.md`. Maintain:

- a machine program ledger;
- a machine support registry checked against live code constants;
- a machine evidence index with explicit grades;
- a human WIP mirror;
- one standard packet for every active/completed phase; and
- an automated drift check invoked by pytest.

Plans never prove implementation. Phase completion requires exit evidence and
agreement across the program ledger, WIP, current status, support registry,
evidence, and closeout.

## Consequences and limitations

Literal drift becomes a test failure. Semantic truth still requires review;
automation cannot determine whether a product description is misleading.
Maintainers must update several small records when actual state changes.

## Alternatives considered

- **WIP only:** Rejected because free-form prose cannot reliably detect drift.
- **Issue tracker only:** Rejected as the repository must remain intelligible
  offline and across hosting changes.
- **Generate all docs from JSON:** Deferred because narrative contracts and
  evidence limits require reviewed prose.

## Verification

`scripts/check_project_tracking.py` and
`tests/regressions/test_project_tracking.py` enforce the machine-checkable
portion.

## Review triggers

Any new status value, evidence grade, authority order, completion rule, or
program-ledger schema.
