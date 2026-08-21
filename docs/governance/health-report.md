# Documentation Health Report

**Status:** Independent-product Phase 4.6 exact-byte publication reconciled;
all local gates passed, with GitHub review pending

**Review date:** 2026-08-21

**Repository baseline:** Working tree based on
`1675c1a22830d506bdf27e45150170befc984bdf`

**Next review:** Independent-product Phase 4.6 merge, Phase 4.7 start, or the
next active-document behavior change

## Scope examined

- Root entry and contributor records: `README.md`, `WIP.md`, `CLAUDE.md`, and
  `CONTRIBUTING.md`.
- Active product documentation under `docs/`.
- Versioned contracts and architecture hubs.
- Historical specifications and roadmaps.
- Existing implementation packets and release evidence under `dev/active/`.
- Current parser, objective, row, bundle, handoff, and workbench source used by
  capability claims.

## Classification

### Active

- Product contract, current status, architecture, CLI, development, install,
  release, and beta-limitations documents.
- Independent product analysis and roadmap.
- Project governance, support registry, evidence index, ADRs, documentation
  debt, WIP, the completed Phase 0–3 packets, and the active Phase 4 packet.
- Versioned integrity, construction, finished-dataset, verified-export, and
  optional Aptus handoff contracts, plus the implemented taxonomy contract.

These documents govern current behavior, future work, or active execution and
must be updated when their scope changes.

### Historical / archived in place

- `docs/plans/2026-07-29-veriformis-roadmap.md`.
- `docs/plans/2026-08-06-private-beta-workbench.md`.
- `docs/superpowers/specs/2026-07-28-veriformis-design.md`.
- `docs/superpowers/plans/2026-07-28-veriformis-m1.md`.
- Completed Group 1–7 plans/reviews and private workbench Phase 0–2 records.

These retain implementation history. Their status text or surrounding index
labels identify them as historical; old implementation-tense statements inside
dated records do not override current status.

### Deprecated

No documentation file is currently classified as deprecated. Runtime legacy
modules may exist, but documentation is either active or historical. A future
deprecated document must link its replacement and removal/review trigger.

## Drift findings and disposition

| Finding | Evidence | Disposition |
| --- | --- | --- |
| Old roadmap was still called authoritative in indexes | Previous docs index, WIP, product contract | Corrected; independent roadmap now controls future work |
| Workbench Phase 2 was implemented but several active docs said Phases 0–1 / Phase 2 next | Phase 2 design and current Swift source | Corrected in active entry, status, WIP, contributor, and Mac docs |
| Root README omitted implemented HTML/PDF/CSV/JSON/JSONL inputs | Parser dispatch | Corrected |
| Contributor guide described implemented Groups 4–9 as planned | Current source/status versus old contributor boundary | Corrected |
| No machine phase state, support claims, or completion check | Repository inventory | Added ledger, support/evidence registries, phase packet, checker, and regression |
| Aptus appeared in current generic release behavior | Historical CLI/MCP/workbench defaults and release scripts | Corrected with off-by-default surfaces, import isolation, canonical-only required gates, and separately named adapter self-conformance |
| Generic validator retains consumer-specific persisted ID | `V1_FINISHED_DATASET_GATES`, saved plan/report identities | Preserved to avoid unversioned compatibility break; documented and recorded as DOC-007 migration debt |
| Historical files live under `dev/active/` | Existing repository layout | Recorded as DOC-002; no unapproved moves made |
| Active architecture described CLI-owned orchestration and obsolete dependency counts | Semantic audit against `PipelineService`, adapters, source tree, and `pyproject.toml` | Reconciled across the architecture tree and versioned contracts; obsolete CLI citations removed |
| Group 2/3 contracts described already implemented work as future deferrals | Current source/status versus contract closeout prose | Historical deferrals labeled as such and linked to current status |
| No privacy-safe demand evidence constrained roadmap ranking | Phase 0 corpus gate | Added a content-blind scanner, schema, matrix, and test-verified fixture aggregate; unavailable owner evidence remains explicit |
| Phase 4 opened while active governance indexes still described it as planned and without a packet | Phase 4 program transition and `phase-04-verified-export-foundation` packet | Reconciled program, WIP, program index, and governance language to Phase 4 in progress; 4.1–4.5 are merged at `1675c1a22830d506bdf27e45150170befc984bdf`, 4.6 implements internal exact-byte publication with green focused and full Python suites, and later/public capabilities remain unclaimed |
| Active docs still said no derivative writer or destination verifier existed after Phase 4.6 landed locally | `ExportService.publish`, private publication helper, verified-export contract, focused Python suite (150 tests), full Python suite (914 tests) | Reconciled the internal exact-byte publisher and independent closed-tree verifier while preserving the no-renderer, no-public-surface, no-supported-container, and Phase 4.7 semantic/rerender boundaries |

## Current health assessment

| Area | Assessment | Basis |
| --- | --- | --- |
| Authority clarity | Good | Explicit hierarchy and historical labels |
| Current capability accuracy | Good within audited active scope | Automated code-bound comparisons plus semantic reconciliation of architecture, contracts, status, WIP, release boundary, and Mac guide |
| Phase visibility | Good | 21-phase ledger, WIP mirror, completed Phase 0–3 packets, and active Phase 4 packet with items 4.1–4.5 merged, 4.6 locally implemented with every local gate green, and GitHub review plus later items open |
| Evidence honesty | Good | Evidence grades distinguish observed summaries from retained artifacts |
| Historical organization | Adequate | Preserved and labeled, but completed work remains in `dev/active/` |
| External-link freshness | Not yet automated | Primary links were reviewed during analysis; no crawler is a current gate |
| Diagram validation | Manual | Mermaid rendering remains documentation debt |
| Demand/corpus evidence | Bounded and honest | Tracked fixture aggregate is reproducible; local retained-output counts are non-portable; owner-corpus, scale, container, and trainer-frequency evidence remains unavailable and unranked |

## Ordered next actions

1. Open the Phase 4.6 pull request, merge only when every GitHub check is green,
   synchronize local `main`, and begin Phase 4.7 only afterward.
2. Preserve the legacy row-shape ID until a versioned report migration is
   authorized; do not treat the name as an adapter dependency.
3. Decide whether completed `dev/active/group-*` packets should move to a
   historical subtree; propose moves before execution.
4. Add pinned offline Mermaid validation only after dependency review.

Phase 4.6 implements only internal exact-byte publication and closed-tree
verification. A shipped renderer, public export commands, semantic-content
replay, deterministic rerender proof, and generic export containers remain
outside the current implemented claim.

The detailed open list is maintained in
[Documentation Debt](documentation-debt.md). This report summarizes health; it
does not replace the debt register or phase packet.
