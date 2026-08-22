# Project Governance and Evidence

**Status:** Active

**Last reviewed:** 2026-08-22 (independent-product Phase 6.7 locally complete)

**Next review:** Independent-product Phase 6.7 pull-request merge, any Phase 6
item closeout, any later phase closeout, or governance-schema change

This directory defines how Veriformis records work and prevents capability
claims from drifting away from code and evidence.

## Active records

| Record | Purpose |
| --- | --- |
| [Project tracking policy](project-tracking.md) | Authority, status transitions, update protocol, and evidence rules |
| [Support registry](support-registry.json) | Machine-readable current, planned, candidate, and unsupported capabilities |
| [Documentation debt](documentation-debt.md) | Known documentation gaps and review triggers |
| [Documentation health report](health-report.md) | Freshness, classification, drift findings, and ordered next actions |
| [ADR index](../adr/README.md) | Durable architectural and product decisions |
| [Evidence index](../evidence/index.json) | Machine-readable evidence records and evidence grades |
| [Program ledger](../../dev/active/independent-product/program.json) | Machine-readable phase status and dependencies |
| [Completed Phase 4 packet](../../dev/active/independent-product/phase-04-verified-export-foundation/README.md) | Verified export foundation checklist, decisions, risks, evidence, and closeout |
| [Completed Phase 5 packet](../../dev/active/independent-product/phase-05-generic-local-exports/README.md) | Generic local export checklist, decisions, risks, evidence, operator guidance, and closeout |

Run the governance drift check with:

```bash
uv run python scripts/check_project_tracking.py
```

The ordinary pytest suite invokes the same check. A mismatch between the
roadmap, program ledger, WIP phase table, support registry, or implemented code
constants therefore fails normal repository verification.

## Authority boundary

These governance records do not turn plans into implementation. Current
capability claims still require code and test evidence, and
`docs/current-status.md` remains the human-readable source of truth. The
support registry makes those claims checkable; it does not weaken their burden
of proof.

At this review, Phase 4 is complete and its closeout merged as PR #52 at
`a76e0fe3185b0e317cd453b9c28a1d2054e617dd`. Phase 5 opened from that clean
baseline under its own standard packet. Item 5.1 merged as PR #53 at
`4f12a55063c2721993b65cfbe30e68eaad55f87f`. Item 5.2 merged as PR #54 at
`f6a5d45f01e0b3117c259271bc59f3599a89dbb6`. Item 5.3's
`constrained-csv` v1 merged as PR #55 at `c6d7fc13a09a` for the three flat row
schemas with fixed exact bytes, mandatory provenance, nested-`messages`
refusal, and no consumer or trainer claim.

Item 5.4's `deterministic-export-pack-zip-v1` merged as PR #56 at
`499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`. The optional `.vfexport.zip`
transport wraps one unchanged, already-published export directory under a
separately retained canonical receipt digest. It is not a fourth renderer,
source-bound export verification, consumer/trainer profile, MCP operation, or
Mac UI action.
Item 5.5 merged as PR #57 at
`c72b8e9ec7bc2746d74404226aa086d497e15db1`. Its test-only frozen ordinary-file
fixture closes all eleven compatible current container/schema pairs, proves one
canonical semantic tamper fails per container, and retains constrained CSV's
actionable pre-publication `messages` refusal. It adds no importer, replayer,
API, taxonomy, support state, or trainer claim. Item 5.6's runtime preview
returns the unchanged plan and exact bounded ordinal-zero samples/tree in
response v2 without renderer or destination access. It passed all 14 GitHub
checks and merged as PR #58 at
`cd017941090c7352cb1d10f9a383042b954d4f2e`. Item 5.7 publishes the
[generic export operator guide](../generic-exports.md) and reconciles Phase 5
closeout without a taxonomy or support promotion. It passed all 14 GitHub
checks and merged as PR #59 at
`65cbd471e96d83f8dd65e2cda60e90f64a916e2b`.
Consumer compatibility still requires a separately admitted named profile.
Phase 6 (goal-first recipes and previews) is locally complete under its
[packet](../../dev/active/independent-product/phase-06-goal-first-recipes/README.md);
items 6.1–6.6 are on `main` and item 6.7 closeout awaits its merge.
