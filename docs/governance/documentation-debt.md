# Documentation Debt Register

**Status:** Active

**Last reviewed:** 2026-08-21 (independent-product Phase 4.2 model contract)

**Next review:** Independent-product Phase 4.2 state transition or any
active-document behavior change

| ID | State | Risk | Debt | Evidence / trigger | Planned resolution |
| --- | --- | --- | --- | --- | --- |
| DOC-001 | Closed 2026-08-11 | High | Current release and beta documents made Aptus verification part of the generic golden/release path. | Phase 1 runtime defaults, standalone scripts/CI, `docs/release.md`, `docs/beta-limitations.md` | Required paths now compile, seal, and externally verify without the adapter; optional self-conformance is separately named and non-blocking |
| DOC-002 | Open | Medium | Historical Group plans remain under `dev/active/`, so location alone does not distinguish completed history from active work. | Existing repository convention | Consider a reviewed archive move after Phase 0; no moves without an explicit plan |
| DOC-003 | Open | Medium | Mermaid diagrams are hand-reviewed and not rendered in CI. | `docs/README.md` debt note | Add a pinned offline renderer only after dependency and CI review |
| DOC-004 | Closed 2026-08-11 | High | Active architecture deep-dives described the retired CLI-owned orchestration model and contained obsolete citations. | Phase 0 semantic documentation audit against current source | Rewritten around `PipelineService`, current adapters, 18 commands, and 10 runtime dependencies; future docs prefer stable symbols over fragile line citations |
| DOC-005 | Closed 2026-08-11 | High | No privacy-preserving corpus/workflow matrix constrained future input, output, and consumer priorities. | `docs/governance/corpus-demand-matrix.json`; scanner regression | Matrix and content-blind scanner added; unsupported priorities remain explicitly unranked until representative owner evidence exists |
| DOC-006 | Open | Medium | Existing status/release documents record the pre-independent program vocabulary and group numbering alongside the new program. | Current historical implementation record | Retain for history; progressively distinguish historical groups from current phases |
| DOC-007 | Open | Medium | The generic v1 row-shape validator persists under the consumer-specific ID `aptus-row-shape`. | `V1_FINISHED_DATASET_GATES` and persisted plan/report identities | Rename only through a versioned contract and report migration; until then document that the ID imports no adapter and proves no live compatibility |

Debt is not silently deleted. Closing an item requires a dated phase progress
entry and evidence or an accepted ADR explaining why the item no longer
applies.
