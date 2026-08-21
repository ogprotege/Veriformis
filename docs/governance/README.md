# Project Governance and Evidence

**Status:** Active

**Last reviewed:** 2026-08-21 (independent-product Phase 4.7 deterministic evidence)

**Next review:** Independent-product Phase 4.7 merge or Phase 4.8 start, any
later phase closeout, or governance-schema change

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
| [Active Phase 4 packet](../../dev/active/independent-product/phase-04-verified-export-foundation/README.md) | Verified export foundation checklist, decisions, risks, and evidence |

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

At this review, Phase 4 items 4.1–4.6 are merged at
`3da0a7f4f8243a1e3a7390e6969c2ee67d7c65af`. Phase 4.7 private two-render
exact-byte and semantic-content conformance has green focused, full Python,
standalone release, parity, Mac, Ruff, lock, and diff gates; GitHub review
remains pending. Because no renderer/replayer, public surface, supported
container, or consumer profile was added, the support registry and taxonomy do
not change. Phase 4.8 may begin only after the Phase 4.7 PR passes every GitHub
check, merges, and clean local `main` equals `origin/main`.
