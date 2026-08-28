# Project Governance and Evidence

**Status:** Active

**Last reviewed:** 2026-08-28 (independent-product Phase 17.7 tool-call)

**Next review:** Phase 17.7 merge, or governance-schema change.

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
| [Completed Phase 9 packet](../../dev/active/independent-product/phase-09-columnar-containers/README.md) | Columnar and Hugging Face dataset containers |
| [Completed Phase 10 packet](../../dev/active/independent-product/phase-10-profile-expansion/README.md) | Independently admitted consumer profiles |
| [Completed Phase 11 packet](../../dev/active/independent-product/phase-11-collection-ingest/README.md) | Collection-plan ingest and parser hardening |
| [Completed Phase 12 packet](../../dev/active/independent-product/phase-12-optional-ocr/README.md) | Optional local Tesseract 5 OCR |
| [Completed Phase 13 packet](../../dev/active/independent-product/phase-13-quality-intelligence/README.md) | Dataset quality intelligence |
| [Completed Phase 14 packet](../../dev/active/independent-product/phase-14-review-workflows/README.md) | Human review and correction workflows |
| [Completed Phase 15 packet](../../dev/active/independent-product/phase-15-scale/README.md) | Scale, streaming, and sharding |
| [Completed Phase 16 packet](../../dev/active/independent-product/phase-16-extension-architecture/README.md) | Safe extension architecture |
| [Active Phase 17 packet](../../dev/active/independent-product/phase-17-advanced-dataset-families/README.md) | Governed advanced dataset families |

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

At this review, independent-product Phases 0–16 are complete on `main`
and Phase 17 is in progress. Phase 16 closeout merged as PR #149 at
`a1fbf04d58d73692cc4237b7d741c5da27022581`. Item 17.1 is honesty only:
no family contract, row schema, objective, constructor, mapping
template, or generator. The quality report is preview-only.
Construction `review_policy` defaults to `none`. Mac Review belongs to
Phase 18. Optional Tesseract 5 recovery is isolated under empty extra
`ocr`. Default parse still refuses image-only PDF. `ocr-image` stays
explicitly unsupported. Axolotl, LLaMA-Factory, and Aptus are
implemented optional adapters. Unsloth remains a non-executable
candidate. Extra lists for those names stay empty. ADR-0017 Decision A
stands. Do not start Phase 18 from this packet.
