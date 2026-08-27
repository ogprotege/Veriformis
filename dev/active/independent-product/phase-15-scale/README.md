# Phase 15 — Measure and Engineer Scale, Streaming, and Sharding

**Status:** In progress — item 15.3b

**Started:** 2026-08-26

**Completed:**

**Roadmap phase:** [Phase 15](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-15--measure-and-engineer-scale-streaming-and-sharding)

**Predecessor:** [Phase 14 closeout](../phase-14-review-workflows/closeout.md),
merged as PR #131 at `44a1a94150171d9bca4049f5d8069885494e4192`.
Clean local `main` equals `origin/main` there.

## Purpose

Replace unknown scale behavior with named, reproducible support tiers
and bounded-resource execution. There is no retained corpus benchmark
or public scale guarantee today. Exact targets must follow measurement.

## Phase boundary

Phase 15 owns measurement, declared tiers after operator-reviewed
baselines, measured-bottleneck engineering, streaming and sharding only
where the oracle and locks allow, and bounded-resource execution on
`PipelineService` plus CLI/MCP. Item 15.1 opens the packet and proves
current scale facts. It does not add generators, targets, streaming
APIs, shard plans, or Mac progress chrome. Mac scale UX belongs to
Phase 18. Do not start Phase 16 from this packet.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Nine-item execution sequence, usability criteria, and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted scope decisions, including the ten locks |
| [risks.md](risks.md) | Risk register and controls |
| [evidence.md](evidence.md) | Starting facts and observed proof |
| [closeout.md](closeout.md) | Exit-gate judgment |
| [SESSION.md](SESSION.md) | Crash-recovery pointer for the current item |

## Current state

Item 15.3b is open. The measurement ladder is packaged. Reports are
evidence, not SLAs. A modest fig-leaf tier is forbidden. Dataset-row
compile is unmeasured. Do not start 15.4 until the operator reviews
the ladder. Do not start Phase 16 from this packet.
