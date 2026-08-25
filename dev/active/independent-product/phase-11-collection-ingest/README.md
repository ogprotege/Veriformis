# Phase 11 — Harden Collection Ingest and Qualify Additional Input Types

**Status:** Complete

**Started:** 2026-08-25

**Completed:** 2026-08-25

**Roadmap phase:** [Phase 11](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-11--harden-collection-ingest-and-qualify-additional-input-types)

**Predecessor:** [Phase 10 closeout](../phase-10-profile-expansion/closeout.md).
Homepage README rewrite merged as PR #103 at
`0b0e188`. Clean local `main` equals `origin/main` there before this packet.

## Purpose

Make heterogeneous input practical at project scale without claiming
unsupported “any input” behavior. Collection membership becomes a first-class
contract shared by CLI, MCP, and the Mac bridge.

## Phase boundary

Phase 11 owns the collection plan, collection inventory, parser hardening
fixtures, parser identity pins, and honest skip records for archives, process
isolation, and new input families. It does not add OCR, new suffixes, Hub
upload, or quality heuristics.

Items 11.1–11.8 land as one pull request by operator instruction.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Eight-item execution sequence, usability criteria, and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted scope decisions |
| [risks.md](risks.md) | Risk register and controls |
| [evidence.md](evidence.md) | Starting facts and observed proof |
| [closeout.md](closeout.md) | Exit-gate judgment |
| [SESSION.md](SESSION.md) | Crash-recovery pointer |

## Current state

Collection plan v1 is implemented. Archives, parser subprocesses, and new
input families are skipped with records. Do not start Phase 12 or 13 from
this packet.
