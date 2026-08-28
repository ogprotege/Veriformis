# Phase 16: Establish a Safe Extension Architecture

**Status:** In progress

**Started:** 2026-08-27

**Roadmap phase:** [Phase 16](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-16--establish-a-safe-extension-architecture)

**Predecessor:** [Phase 15 closeout](../phase-15-scale/closeout.md), merged as
PR #139 at `435bd63c90778674ff4eb68a5d882a168349baca`.

## Purpose

Let parsers, row mappers, deterministic constructors, quality checks,
container exporters, and consumer profiles grow behind strict internal
contracts without turning dataset projects into executable Python packages.

## Phase boundary

Phase 16 begins with internal typed registries. Built-ins and third-party
extensions remain distinct. Public executable plugins remain prohibited unless
the Phase 16.8 threat model approves a narrow sandbox and the operator accepts
it. The phase adds no new input family, objective, exporter, profile, Mac UI,
or Phase 17 semantic family.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Ten-item sequential execution plan and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted locks and later operator decisions |
| [risks.md](risks.md) | Extension-boundary risk register |
| [evidence.md](evidence.md) | Starting facts and accumulated proof |
| [closeout.md](closeout.md) | Final exit-gate judgment |
| [SESSION.md](SESSION.md) | Crash-recovery pointer for the current item |

## Current state

Item 16.1 merged as PR #140 at `76c0e2e90d95874b3e117f95554c428c70da1daf`.
Item 16.2 pins `veriformis.extension-protocol/v1`. No executable registry,
loader, extra, or public plugin API exists yet.
