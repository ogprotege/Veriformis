# Project Governance and Evidence

**Status:** Active

**Last reviewed:** 2026-08-21 (independent-product Phase 4 closeout)

**Next review:** Independent-product Phase 5 or Phase 6 packet opening, any
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
| [Completed Phase 4 packet](../../dev/active/independent-product/phase-04-verified-export-foundation/README.md) | Verified export foundation checklist, decisions, risks, evidence, and closeout |

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

At this review, Phase 4 is complete. Its surface implementation merged as PR
#50 at `fb0a13d7cab1e456b6ff3b3dc6ebab13b9898edb`, and its review corrections
merged as PR #51 at `d91542fe12c5a492de578ad060836a7d65999e42`. Phase 4.9
consolidates the adversarial harness and reconciles this program. Production
discovery is empty and no renderer, replayer, supported container, or consumer
profile was added. The support registry closes only the resolved generic-export-
service foundation gap; its capability lists and the taxonomy remain unchanged.
Phases 5 and 6 may begin only under their own packets after the closeout pull
request merges and clean local `main` equals `origin/main`.
