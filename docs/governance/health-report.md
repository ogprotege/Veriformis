# Documentation Health Report

**Status:** Independent-product Phase 5.5 locally admitted; publication pending

**Review date:** 2026-08-22

**Repository baseline:** Working tree based on Phase 5.4 merge
`499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`

**Next review:** Independent-product Phase 5.5 merge or Phase 5.6, Phase 6
start, or the next active-document behavior change

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
  debt, WIP, the completed Phase 0–4 packets, and the active Phase 5 packet.
- Versioned integrity, construction, finished-dataset, verified-export, split-
  JSONL, canonical-JSON, constrained-CSV, and optional Aptus handoff contracts, plus the
  implemented taxonomy contract.

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
| Active docs still described Phase 4.6 as pending and Phase 4.7 rerender/semantic replay as absent | PR #48 merge at `3da0a7f4f8243a1e3a7390e6969c2ee67d7c65af`; private two-render service path; 14 determinism, 158 export, 163 combined export/contract, and 927 full Python tests | Reconciled current status, product, architecture, development, governance, program, WIP, and evidence records to Phase 4.7 locally green/PR pending while retaining the trusted-private-hook, whole-file-memory, no-public-surface, no-supported-container, and unchanged-schema limits |
| Active docs still described Phase 4.7 as local and export surfaces as absent after its merge | PR #49 merge at `6c3f0aff2e35edaa7920a0964270c410bf53f47b`; strict production-empty discovery and Python/CLI/MCP/Mac adapters | Reconciled the merged Phase 4.7 baseline and locally implemented Phase 4.8 surfaces while preserving the no-shipped-implementation, no-supported-container/profile, unchanged-taxonomy, and unchanged-persisted-schema limits |
| Active docs still described Phase 4.8 as pending after both its feature and review-correction merges | PR #50 at `fb0a13d7cab1e456b6ff3b3dc6ebab13b9898edb`; PR #51 at `d91542fe12c5a492de578ad060836a7d65999e42`; Phase 4.9 adversarial harness | Reconciled the packet, product/status, architecture, governance, program, WIP, and evidence records to completed Phase 4 while preserving the empty production catalog and no-container/profile limits |
| The support registry and drift checker still required `gap-generic-export-service` to remain open “before Phase 4” after the foundation landed | Completed typed service, strict public operations, production-empty discovery, and Phase 4 exit harness | Close the resolved service-foundation gap and its stale checker assertion without promoting a generic container or consumer profile; Phase 5 retains implementation support |
| Phase 4 closeout merged while active tracking still showed Phase 5 as planned and had no packet | PR #52 at `a76e0fe3185b0e317cd453b9c28a1d2054e617dd`; Phase 5 roadmap dependency and opening decision | Created the standard Phase 5 packet and reconciled program, WIP, and governance indexes to `in_progress`; item 5.1 is active, while packet creation alone makes no support claim |
| Phase 5.1 changed production discovery and physical-container support from the Phase 4 empty baseline | Split JSONL implementation, request-v2 configuration, four-schema round trips, tamper evidence, and current contracts | Promoted exactly `split-jsonl-directory` v1, retained historical request/discovery/response and persisted export v1 contracts, and reconciled current architecture, operator, support, evidence, and packet records without adding a trainer profile |
| Phase 5.2 added a second exact-byte generic container while active docs still described JSON as planned | Canonical JSON implementation, strict dataset/provenance models, four-schema admission suite, source-row-set closure regression, and container contract | Promoted exactly canonical `json` v1 alongside split JSONL; retained request/discovery/response and persisted export v1 contracts, fixed the tree, refused request v2, and reconciled active product, architecture, operator, support, and packet records without claiming CSV, previews, archives, or trainer compatibility |
| Phase 5.3 added a third exact-byte generic container while active docs still described CSV as planned | Constrained CSV implementation, frozen flat-schema dialect/tree, strict reload and tamper checks, nested-`messages` refusal, support admission, and container contract | Promoted exactly `constrained-csv` v1 for `text`, `prompt_completion`, and `instruction_output`; retained request/discovery/response and persisted export v1 contracts, refused request v2 before source or destination access, refused `messages` after source admission but before destination access or publication, and reconciled active product, architecture, operator, support, and packet records without claiming previews, archives, trainer, or spreadsheet compatibility |
| PR #55 merged while active records still described Phase 5.3 as local and Phase 5.4 as blocked or unimplemented | PR #55 at `c6d7fc13a09a`; ADR-0006; receipt-anchored export-pack implementation and transport contract | Recorded the Phase 5.3 merge and Phase 5.4 active local boundary across root, packet, product, architecture, development, and governance narratives; described `.vfexport.zip` as post-export receipt-anchored transport while withholding test counts, completion, source-bound, fourth-renderer, trainer, MCP, and Mac UI claims |
| Phase 5.4 local implementation initially lacked complete promotion proof and path-stable verification | Independent contract and code reviews; all-three-container matrix; archive-path replacement and legacy bundle-compatibility regressions | Added the missing matrix and exact-only governance requirement, corrected trust output and stale authority text, restored shipped bundle behavior, held one no-follow archive descriptor through verification, and recorded the green local admission without claiming GitHub or phase completion |
| PR #56 merged while active records still described Phase 5.4 publication as pending, and item 5.5 lacked one closed shared semantic matrix | PR #56 at `499d61fa2e7d`; discovery-derived fixture and strict ordinary-file reload suite | Recorded the Phase 5.4 merge and locally admitted Phase 5.5 as exactly eleven compatible container/schema round trips, one canonical semantic tamper per container, and actionable constrained-CSV/`messages` refusal; retained the existing three selectors and added no importer, replayer, API, taxonomy, support, or trainer promotion |

## Current health assessment

| Area | Assessment | Basis |
| --- | --- | --- |
| Authority clarity | Good | Explicit hierarchy and historical labels |
| Current capability accuracy | Good within audited active scope; Phase 5.4 merged and Phase 5.5 locally admitted | Automated code-bound comparisons plus semantic reconciliation of architecture, contracts, status, WIP, the no-importer boundary, and unchanged production discovery |
| Phase visibility | Good | 21-phase ledger, WIP mirror, completed Phase 0–4 packets, and one active Phase 5 packet |
| Evidence honesty | Good | Evidence grades distinguish observed summaries from retained artifacts |
| Historical organization | Adequate | Preserved and labeled, but completed work remains in `dev/active/` |
| External-link freshness | Not yet automated | Primary links were reviewed during analysis; no crawler is a current gate |
| Diagram validation | Manual | Mermaid rendering remains documentation debt |
| Demand/corpus evidence | Bounded and honest | Tracked fixture aggregate is reproducible; local retained-output counts are non-portable; owner-corpus, scale, container, and trainer-frequency evidence remains unavailable and unranked |

## Ordered next actions

1. Publish Phase 5.5, require every GitHub check to pass, merge, and synchronize
   clean local `main` before beginning item 5.6.
2. Preserve the legacy row-shape ID until a versioned report migration is
   authorized; do not treat the name as an adapter dependency.
3. Decide whether completed `dev/active/group-*` packets should move to a
   historical subtree; propose moves before execution.
4. Add pinned offline Mermaid validation only after dependency review.

The Phase 4 closeout baseline exposed strict export operations across Python,
CLI, MCP, and the CLI-backed Mac bridge while production discovery remained
empty and conformance code remained test-injected. Phase 5.1–5.3 now admit the
first three production entries, `split-jsonl-directory`, canonical `json`, and
`constrained-csv` v1, after container-specific semantic/tamper evidence and
current support records agree. Canonical JSON validation reconstructs the
source row set so top-level identity, split metadata, payload arrays, and
provenance must close together. Constrained CSV admits only the three flat
schemas and refuses nested `messages` with an exact JSON alternative.
Phase 5.3 merged as PR #55 at `c6d7fc13a09a`. Phase 5.4's receipt-anchored
`deterministic-export-pack-zip-v1` transport merged as PR #56 at
`499d61fa2e7d`. It wraps
an unchanged published directory rather than adding a renderer, preserves the
embedded source trust grade, and adds no MCP or Mac UI operation. Phase 5.5's
test-only consolidated fixture is locally admitted after 16 focused, 453
integrated, 1,211 full Python, 1,199 standalone release with one deselection,
58 Mac, parity, Ruff, lock, and structured-JSON checks passed. It covers all
eleven compatible ordinary-file pairs, per-container tamper, and the sole
current incompatible CSV/messages pair without adding an importer or changing
runtime support.
Generic output does not establish trainer compatibility, and any future
shipped semantic profile must enforce explicit resource limits.

The detailed open list is maintained in
[Documentation Debt](documentation-debt.md). This report summarizes health; it
does not replace the debt register or phase packet.
