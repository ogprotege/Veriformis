# Project Governance and Evidence

**Status:** Active

**Last reviewed:** 2026-08-23 (independent-product Phase 9.3 fingerprints)

**Next review:** Independent-product Phase 9.3 pull-request merge, item 9.4,
any later phase closeout, or governance-schema change

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
| [Completed Phase 6 packet](../../dev/active/independent-product/phase-06-goal-first-recipes/README.md) | Goal-first checklist, decisions, risks, usability evidence, and closeout |
| [Completed Phase 7 packet](../../dev/active/independent-product/phase-07-existing-dataset-import/README.md) | Existing-dataset import modes, mapping, templates, and closeout |
| [Completed Phase 8 packet](../../dev/active/independent-product/phase-08-consumer-profiles/README.md) | First consumer profiles as optional adapters |
| [Active Phase 9 packet](../../dev/active/independent-product/phase-09-columnar-containers/README.md) | Columnar and Hugging Face dataset containers |

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

At this review, independent-product Phases 0–8 are complete on `main` and
Phase 9 is in progress under item 9.3. Arrow and Hugging Face feature
schemas and semantic fingerprints are pinned. `parquet`, `arrow`, and
`hugging-face-dataset` remain planned. Historical Phase 4–8 merge SHAs
remain in those packets and in `docs/current-status.md`.
