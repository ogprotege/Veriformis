# Independent Product Program

**Status:** Active program — Phases 0–11 complete; Phase 12 in progress

**Roadmap:** [Independent Product Roadmap](../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md)

**Machine ledger:** [program.json](program.json)

**Tracking policy:** [Project Tracking and Evidence Policy](../../../docs/governance/project-tracking.md)

This directory is the execution record for the trainer-neutral Veriformis
product program. `program.json` is the machine-readable phase state. Root
`WIP.md` mirrors it for humans, and the regression suite checks that both agree
with roadmap headings.

## Phase packets

- [Phase 0 — Authority and evidence foundation](phase-00-foundation/README.md) — completed
- [Phase 1 — Standalone independence](phase-01-standalone-independence/README.md) — completed
- [Phase 2 — Reliability and artifact boundary](phase-02-reliability-artifact-boundary/README.md) — completed
- [Phase 3 — Goal, schema, container, and profile taxonomy](phase-03-taxonomy/README.md) — completed
- [Phase 4 — Verified export foundation](phase-04-verified-export-foundation/README.md) — completed
- [Phase 5 — Lossless generic local exports](phase-05-generic-local-exports/README.md) — completed
- [Phase 6 — Goal-first recipes and previews](phase-06-goal-first-recipes/README.md) — completed
- [Phase 7 — Existing-dataset import and mapping](phase-07-existing-dataset-import/README.md) — completed
- [Phase 8 — First consumer profiles](phase-08-consumer-profiles/README.md) — completed
- [Phase 9 — Columnar and Hugging Face dataset containers](phase-09-columnar-containers/README.md) — completed
- [Phase 10 — Expand consumer profiles under evidence gates](phase-10-profile-expansion/README.md) — complete
- [Phase 11 — Harden collection ingest and qualify additional input types](phase-11-collection-ingest/README.md) — complete
- [Phase 12 — Add optional local OCR with accountable recovery](phase-12-optional-ocr/README.md) — in progress

Future phase packets are created only when a phase changes from `planned` to
`in_progress`. This prevents empty directories from being mistaken for active
implementation. Phase 4 opened on 2026-08-21 from baseline `db9d93ef`; item
4.1 implemented the typed `ExportService` boundary and descriptor-anchored
verified source inspection and merged as PR #43. Item 4.2 defines strict
verified-export v1 models and merged as PR #44. Item 4.3 enforces
trusted-by-default source admission with an explicit lower-trust policy and
merged as PR #45. Item 4.4 adds read-only plan population from one immutable
verified source view and merged as PR #46. Item 4.5 fresh-reconstructs
normalized candidate semantic rows and provenance, requires their row-set and
complete membership projection to equal the plan baseline, and merged as PR
#47 at `1675c1a22830d506bdf27e45150170befc984bdf`. Item 4.6 implements internal
`portable_exact_bytes` publication: source and plan re-verification, private
descriptor-anchored staging, canonical receipt replay, independent closed-tree
verification, cancellation, and one atomic no-replace promotion, and merged as
PR #48 at `3da0a7f4f8243a1e3a7390e6969c2ee67d7c65af`. Item 4.7 implements
private two-render exact-byte and semantic-content evidence plus descriptor-
reread staged semantic replay and merged as PR #49 at
`6c3f0aff2e35edaa7920a0964270c410bf53f47b`. Item 4.8 implements a production-
empty private catalog and strict discovery, dry run, inspect, execute, and
verify operations through `PipelineService`, CLI, MCP, and the CLI-backed Mac
bridge. It merged as PR #50 at
`fb0a13d7cab1e456b6ff3b3dc6ebab13b9898edb`; its review corrections merged as
PR #51 at `d91542fe12c5a492de578ad060836a7d65999e42`. Item 4.9 completes the
adversarial harness and reconciles the program under the completed
[Phase 4 packet](phase-04-verified-export-foundation/README.md).

Phase 4 shipped no production renderer or semantic replayer, generic export
container, or trainer-specific profile. Its closeout merged as PR #52 at
`a76e0fe3185b0e317cd453b9c28a1d2054e617dd`. Phase 5 then opened under its own
standard packet from that clean baseline. Item 5.1 merged as PR #53 at
`4f12a55063c2721993b65cfbe30e68eaad55f87f`. Item 5.2's canonical `json` v1
merged as PR #54 at `f6a5d45f01e0b3117c259271bc59f3599a89dbb6`. Item 5.3's
consumer-neutral `constrained-csv` v1 merged as PR #55 at
`c6d7fc13a09a` for the three flat row schemas; it refuses nested `messages`
before publication. Item 5.4's optional
`deterministic-export-pack-zip-v1` transport merged as PR #56 at
`499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`. It wraps one unchanged export
directory as receipt-anchored `.vfexport.zip` without adding a fourth renderer,
trainer claim, source-bound archive verification, or Mac UI. Item 5.5's
test-only consolidated eleven-pair ordinary-file semantic round-trip matrix
merged as PR #57 at `c72b8e9ec7bc2746d74404226aa086d497e15db1` with one tamper
case per container and the actionable constrained-CSV/`messages` refusal. It
adds no product importer, replayer, API, taxonomy, support, or trainer
promotion. Item 5.6's exact bounded runtime preview passed all 14 GitHub checks
and merged as PR #58 at
`cd017941090c7352cb1d10f9a383042b954d4f2e`; clean local `main` was
synchronized before item 5.7. The final item publishes the generic-export
operator guide, keeps container choice separate from objective, schema, and
consumer compatibility, and reconciles the completed Phase 5 packet without
changing runtime or support state. It passed all 14 GitHub checks and merged
as PR #59 at `65cbd471e96d83f8dd65e2cda60e90f64a916e2b`; clean local `main`
was synchronized before Phase 6 opened. Phase 6 completed under its
[packet](phase-06-goal-first-recipes/README.md); closeout merged as PR #67 at
`6995d17bef0d09f235b1c464e947c38c63dd313d`. Phase 7 completed under its
[packet](phase-07-existing-dataset-import/README.md); closeout merged as
PR #80 at `b7bb7f0c2046fba87fd7c9da12f7d2ccb5c2c88f` after all 14 GitHub
checks passed. Phase 8 opened on 2026-08-23 under its
[packet](phase-08-consumer-profiles/README.md); items 8.1–8.6 merged as
PR #82–#87; item 8.7 closes the phase with implemented TRL and MLX-LM.
Phase 9 completed under its
[packet](phase-09-columnar-containers/README.md). Phase 10 completed under
its [packet](phase-10-profile-expansion/README.md) with implemented
Axolotl, LLaMA-Factory, and Aptus adapters; Unsloth remains experimental.
Phase 11 completed under its
[packet](phase-11-collection-ingest/README.md). Phase 12 opened under its
[packet](phase-12-optional-ocr/README.md) on 2026-08-25; the operator
accepted Tesseract 5; item 12.3 pins identities; recovery is not
executable; `ocr-image` stays explicitly unsupported.

## State change procedure

1. Confirm predecessor gates and roadmap permission.
2. Create the standard phase packet.
3. Update `program.json` and WIP in the same change.
4. Add the first dated progress entry and risk review.
5. Run `uv run python scripts/check_project_tracking.py`.

No phase status is inferred from branches, file counts, or elapsed time.
