# Phase 5 — Lossless Generic Local Exports

**Status:** In progress

**Started:** 2026-08-21

**Roadmap phase:** [Phase 5](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-5--ship-lossless-generic-local-exports)

**Predecessor:** [Phase 4 closeout](../phase-04-verified-export-foundation/closeout.md)

## Purpose

Ship trainer-neutral, lossless local derivatives of a verified canonical
`minimal-v1` bundle through the existing `ExportService`. Generic exports
preserve the exact semantic rows and logical partitions selected by the source
bundle; they do not create a second construction, curation, balancing, or
splitting pipeline.

## Phase boundary

Phase 5 owns generic split JSONL, canonical JSON, structurally lossless CSV,
generic export-pack archiving, semantic round-trip proof, exact dry-run
previews, and operator guidance. Item 5.1 owns only the split JSONL container.
Specific trainer compatibility and consumer profiles remain later work.

Every implementation must enter through the Phase 4 verified export service
and its plan, receipt, publication, and verification boundaries. Packet
opening alone was not support evidence; the separate Phase 5.1 implementation,
contract, tests, and reconciled admission record now support exactly one
generic container.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Seven-item execution sequence and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted and pending scope decisions |
| [risks.md](risks.md) | Active risk register and controls |
| [evidence.md](evidence.md) | Starting facts and required proof |
| [closeout.md](closeout.md) | Pending exit-gate judgment |

## Current state

Phase 5 opened on 2026-08-21 from baseline
`a76e0fe3185b0e317cd453b9c28a1d2054e617dd`. Item 5.1 is locally complete:
`split-jsonl-directory` v1 is implemented, admitted for all four current row
schemas, and reflected in taxonomy/support records without changing the
trainer-neutral boundary. Its pull-request and remote-green merge gate remain
before item 5.2 begins.
