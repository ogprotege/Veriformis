# Phase 4 — Verified Export Foundation

**Status:** In progress

**Started:** 2026-08-21

**Roadmap phase:** [Phase 4](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-4--build-the-verified-export-foundation)

**Predecessor:** [Phase 3 closeout](../phase-03-taxonomy/closeout.md)

## Purpose

Build one consumer-neutral, verified-bundle-only export foundation. Export
plans, receipts, publication, and verification remain derivatives of the
canonical `minimal-v1` bundle. They do not become a second construction,
curation, balancing, or splitting pipeline.

CLI, MCP, and the CLI-backed Mac workbench must use the shared Python
composition root. No adapter may copy, rewrite, or reinterpret bundle payloads
on its own.

## Phase boundary

Phase 4 establishes contracts, services, safety, evidence, and surfaces. Its
exit proof uses an injected conformance exporter that is not a supported
product container. Generic JSONL, JSON, and CSV exports remain Phase 5 work;
trainer-specific profiles remain later work.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Nine-PR execution sequence and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted architectural and evidence decisions |
| [risks.md](risks.md) | Active risk register and controls |
| [evidence.md](evidence.md) | Starting facts and observed proof |
| [closeout.md](closeout.md) | Pending exit-gate judgment |

## Current state

The packet is open. The first increment established the typed `ExportService`
beneath `PipelineService` and a descriptor-anchored verified source view. The
second defines the strict verified-export v1 plan, profile, dependency,
membership, binding, receipt, and verification models. The third enforces
trusted-by-default source admission and requires an explicit policy for lower
self-consistent trust. The fourth adds read-only plan population: every source,
objective, split, row, and membership-baseline fact comes from one admitted
bundle view, while callers supply only strict profile, dependency, and file-plan
evidence. The fifth fresh-reconstructs normalized candidate semantic rows,
provenance, row-set identity, and membership, then requires exact equality with
the plan baseline. Destination-byte verification, writing, public export
commands, generic containers, and new consumer profiles remain unimplemented.
