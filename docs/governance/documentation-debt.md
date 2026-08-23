# Documentation Debt Register

**Status:** Active

**Last reviewed:** 2026-08-22 (independent-product Phase 6.7 required-gate completion)

**Next review:** Independent-product Phase 6.7 pull-request merge, Phase 7
opening, or any active-document behavior change

| ID | State | Risk | Debt | Evidence / trigger | Planned resolution |
| --- | --- | --- | --- | --- | --- |
| DOC-001 | Closed 2026-08-11 | High | Current release and beta documents made Aptus verification part of the generic golden/release path. | Phase 1 runtime defaults, standalone scripts/CI, `docs/release.md`, `docs/beta-limitations.md` | Required paths now compile, seal, and externally verify without the adapter; optional self-conformance is separately named and non-blocking |
| DOC-002 | Open | Medium | Historical Group plans remain under `dev/active/`, so location alone does not distinguish completed history from active work. | Existing repository convention | Consider a reviewed archive move after Phase 0; no moves without an explicit plan |
| DOC-003 | Open | Medium | Mermaid diagrams are hand-reviewed and not rendered in CI. | `docs/README.md` debt note | Add a pinned offline renderer only after dependency and CI review |
| DOC-004 | Closed 2026-08-11 | High | Active architecture deep-dives described the retired CLI-owned orchestration model and contained obsolete citations. | Phase 0 semantic documentation audit against current source | Rewritten around `PipelineService`, current adapters, 18 commands, and 10 runtime dependencies; future docs prefer stable symbols over fragile line citations |
| DOC-005 | Closed 2026-08-11 | High | No privacy-preserving corpus/workflow matrix constrained future input, output, and consumer priorities. | `docs/governance/corpus-demand-matrix.json`; scanner regression | Matrix and content-blind scanner added; unsupported priorities remain explicitly unranked until representative owner evidence exists |
| DOC-006 | Open | Medium | Existing status/release documents record the pre-independent program vocabulary and group numbering alongside the new program. | Current historical implementation record | Retain for history; progressively distinguish historical groups from current phases |
| DOC-007 | Open | Medium | The generic v1 row-shape validator persists under the consumer-specific ID `aptus-row-shape`. | `V1_FINISHED_DATASET_GATES` and persisted plan/report identities | Rename only through a versioned contract and report migration; until then document that the ID imports no adapter and proves no live compatibility |

The Phase 5.1–5.3 reviews identified no new documentation debt. Their admitted
split JSONL, canonical JSON, and constrained CSV contracts are reconciled in
the active packet, and item 5.3 merged as PR #55 at `c6d7fc13a09a`. Phase
5.4's receipt-anchored export-pack transport merged as PR #56 at
`499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`; it is not a fourth renderer,
trainer profile, source-bound verification path, or Mac UI action. Phase 5.5's
test-only matrix merged as PR #57 at
`c72b8e9ec7bc2746d74404226aa086d497e15db1` and introduces no new documentation
debt: its
frozen fixture proves all eleven compatible ordinary-file round trips, three
container tamper failures, and the existing constrained-CSV/`messages` refusal
without adding a product importer or support claim. Item 5.6's exact runtime
preview passed all 14 GitHub checks and merged as PR #58 at
`cd017941090c7352cb1d10f9a383042b954d4f2e`. Item 5.7 closes the missing
JSONL/JSON/CSV chooser and axis-separation obligation through the
[generic export operator guide](../generic-exports.md), with no persisted-
schema, runtime, taxonomy, support, consumer, trainer, or new documentation-
debt promotion. Phase 6's goal catalog, goal contracts, input-family taxonomy
axis, preview, presets, compile preflight, acceptance matrix, instruction
truthfulness policy, and usability criteria/implementation reconciliation are
recorded in the Phase 6 packet; U1–U6 and closeout are judged on the current
tree, with publication pending. The Phase 6.7 implementation introduces no new documentation debt and
deliberately leaves
the persisted instruction literal, serializer, verifier, row schemas, consumer
profiles, and trainer claims unchanged. DOC-002, DOC-003, DOC-006, and DOC-007
remain open.

Debt is not silently deleted. Closing an item requires a dated phase progress
entry and evidence or an accepted ADR explaining why the item no longer
applies.
