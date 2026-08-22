# Independent Product Program

**Status:** Active program — Phases 0–4 complete; Phase 5 in progress; Phase 6 planned

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
- [Phase 5 — Lossless generic local exports](phase-05-generic-local-exports/README.md) — in progress

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
`4f12a55063c2721993b65cfbe30e68eaad55f87f`. Item 5.2 implements canonical
`json` v1 with explicit split/schema metadata, complete separately aligned
provenance, exact-byte publication, and no trainer profile; independent
security/documentation review and its remote-green merge gate remain before
item 5.3. Phase 6 remains planned and requires its own packet before work
begins.

## State change procedure

1. Confirm predecessor gates and roadmap permission.
2. Create the standard phase packet.
3. Update `program.json` and WIP in the same change.
4. Add the first dated progress entry and risk review.
5. Run `uv run python scripts/check_project_tracking.py`.

No phase status is inferred from branches, file counts, or elapsed time.
