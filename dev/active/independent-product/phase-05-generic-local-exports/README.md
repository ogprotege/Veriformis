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
opening alone was not support evidence. The separately admitted Phase 5.1 and
5.2 implementations support split JSONL and canonical JSON respectively. Item
5.3 locally admits constrained CSV for the three flat row schemas; later Phase
5 work remains unimplemented.

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
`a76e0fe3185b0e317cd453b9c28a1d2054e617dd`. Item 5.1 merged as PR #53 at
`4f12a55063c2721993b65cfbe30e68eaad55f87f`. Item 5.2's `json` v1 merged as
PR #54 at `f6a5d45f01e0b3117c259271bc59f3599a89dbb6`. Item 5.3 locally adds
`constrained-csv` v1 with fixed `data/train.csv` and `data/evaluation.csv`, a
dataset card, mandatory aligned provenance, README, and the shared receipt.
Every field is quoted with the frozen UTF-8/LF dialect. It admits `text`,
`prompt_completion`, and `instruction_output`, refuses `messages` with an
actionable JSON alternative, has no options, consumer, or trainer claim, and
changes no source row or logical partition. Its remote-green merge gate remains
before item 5.4 begins. See the
[Constrained CSV Export Contract v1](../../../../docs/contracts/constrained-csv-export-v1.md).
