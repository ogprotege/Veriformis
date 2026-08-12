# Independent Product Program

**Status:** Active program — Phase 2 completed; Phase 3 is next

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

Future phase packets are created only when a phase changes from `planned` to
`in_progress`. This prevents empty directories from being mistaken for active
implementation.

## State change procedure

1. Confirm predecessor gates and roadmap permission.
2. Create the standard phase packet.
3. Update `program.json` and WIP in the same change.
4. Add the first dated progress entry and risk review.
5. Run `uv run python scripts/check_project_tracking.py`.

No phase status is inferred from branches, file counts, or elapsed time.
