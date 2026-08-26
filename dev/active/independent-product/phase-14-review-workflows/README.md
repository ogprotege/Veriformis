# Phase 14 — Deliver Human Review and Correction Workflows

**Status:** In progress

**Started:** 2026-08-26

**Completed:**

**Roadmap phase:** [Phase 14](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-14--deliver-human-review-and-correction-workflows)

**Predecessor:** [Phase 13 closeout](../phase-13-quality-intelligence/closeout.md),
merged as PR #122 at `ef31559c9184b553209a3c45eca5d943fbb9a680`, then
stamped as PR #123 at `4d7b00fca9b685df95aa2a19349604f2b40d2406`. Clean
local `main` equals `origin/main` there.

## Purpose

Make ambiguous recovery, mapping, curation, and quality decisions resolvable
without editing content-addressed files by hand. Construction already has
optional `ReviewEvidence`. There is no review queue, no CLI submit path, and
no seal block from unresolved required reviews outside construction
promotion.

## Phase boundary

Phase 14 owns review contracts, queues over existing facts, corrections as
transforms or mapping revisions, waivers that do not change bytes,
deterministic sampling, CLI/MCP/Python review exchange, required-review
seal blocking, and supersession. Item 14.1 opens the packet and proves
current review facts. It does not add a queue schema, submit command, or
Mac Review screens. Mac Review belongs to Phase 18. Do not start Phase 15
from this packet.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Eight-item execution sequence, usability criteria, and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted scope decisions, including the six locks |
| [risks.md](risks.md) | Risk register and controls |
| [evidence.md](evidence.md) | Starting facts and observed proof |
| [closeout.md](closeout.md) | Exit-gate judgment |
| [SESSION.md](SESSION.md) | Crash-recovery pointer for the current item |

## Current state

Item 14.4 is in progress. Corrections bind a new transform or mapping
revision. Waivers do not change bytes. In-place mutation of accepted
records fails closed. The bundle does not block seal. Do not start
Phase 15 from this packet.
