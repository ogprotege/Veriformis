# Documentation Debt Register

**Status:** Active

**Last reviewed:** 2026-09-09 (post-20 defect closure, Phase 2)

**Next review:** Closeout of the post-20 defect-closure packet, or any
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
| DOC-008 | Open | Medium | Active documents carried "Next review" triggers that fired without a review: the health report and this register stayed at Phase 8 through Phase 20, five documents kept "no semantic replayer ships" after Phase 9, and the goal-catalog contract was re-stamped 2026-09-05 without recording Phase 17. Roughly a third of the `file:line` citations in `docs/architecture*` and `docs/cli.md` no longer land on the named symbol. | 2026-09-09 audit; DOC-004's own remedy ("prefer stable symbols") regressed | The post-20 defect-closure packet re-dated every touched document and corrected the quoted statements; the tracking checker now compares contract row-schema blocks and goal / preset counts with live discovery. Replace remaining line citations with symbol references opportunistically; never add new ones |
| DOC-009 | Open | Medium | `docs/evidence/index.json` holds per-item records for Phases 0–7, partial records for 8 and 9, none for Phases 10–19, and one closeout record for Phase 20, while governance text presents it as the evidence ledger for every phase. | 2026-09-09 audit of the index | Either add one closeout record per phase packet or state in `project-tracking.md` that the index is complete only for Phases 0–7 and 20 |
| DOC-010 | Open | High | Required review could not be resolved on the CLI or MCP: `review-submit` persisted nothing and `construct` accepted no review evidence, while the review contract described packets that "round-trip through Python, CLI, and MCP". | `pipeline/service.py`, `review/exchange.py`, `docs/contracts/review-v1.md` | Post-20 defect D-17 (packet Phase 5) binds a submitted review bundle into a construct re-commit on every surface and documents it in the review contract; close when that lands |
| DOC-011 | Open | Medium | `bundle-transport-v1.md` claimed ZIP64-capable encoding while the canonical verifier rejected the ZIP64 central-directory extra that the stdlib emits past 4 GiB, so the codec refused archives it wrote itself. | `_archive_transport.py` `verify_staged`; 2026-09-09 audit | Post-20 defect D-16 (packet Phase 4) accepts exactly one well-formed ZIP64 extra and records the behavior in the contract; close when that lands |

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
debt promotion. DOC-002, DOC-003, DOC-006, and DOC-007 remain open.

Item 6.7 adds no new documentation debt: instruction templates live in the
existing catalog contract, the walkthrough is recorded in `docs/install.md`,
and DOC-002, DOC-003, DOC-006, and DOC-007 remain open.

Phase 7 closeout adds no new open debt: the operator guide is
[mapping.md](../mapping.md) and the contract is
[row-mapping-v1.md](../contracts/row-mapping-v1.md). A 2026-08-23 continuity
pass aligned active README, status, CLI, architecture, governance, and agent
guidance with Phases 0–7 complete.

Phases 8–20 recorded no debt entries here; the 2026-09-09 audit that opened
the [post-20 defect-closure packet](../../dev/active/independent-product/post-20-defect-closure/README.md)
found that silence to be the drift itself and recorded it as DOC-008 and
DOC-009. DOC-002, DOC-003, DOC-006, DOC-007, DOC-008, and DOC-009 remain
open; DOC-010 and DOC-011 close with defects D-17 and D-16 later in the same packet.

Debt is not silently deleted. Closing an item requires a dated phase progress
entry and evidence or an accepted ADR explaining why the item no longer
applies.
