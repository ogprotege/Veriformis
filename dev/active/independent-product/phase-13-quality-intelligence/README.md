# Phase 13 — Build Dataset Quality Intelligence

**Status:** In progress

**Started:** 2026-08-25

**Completed:**

**Roadmap phase:** [Phase 13](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-13--build-dataset-quality-intelligence)

**Predecessor:** [Phase 12 closeout](../phase-12-optional-ocr/closeout.md),
merged as PR #112 at `892939f527974b69282296ded04eb3b43643554f`, then
stamped as PR #113 at `783a2a1448049a2fbfa384df586e9d1497b36afb`. Clean
local `main` equals `origin/main` there.

## Purpose

Help users decide whether the compiled artifact is also a suitable training
dataset. Compile, seal, and the seventeen finished-dataset validation gates
already exist. Broader decision-support metrics do not.

## Phase boundary

Phase 13 owns a versioned quality report, named heuristics, inspectable
clusters, optional policy findings, previewable gates, and calibrated
fixtures. Item 13.1 opens the packet and proves current quality facts. It
does not add a report schema, CLI command, or blocking heuristic. Do not
start Phase 14 from this packet.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Nine-item execution sequence, usability criteria, and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted scope decisions |
| [risks.md](risks.md) | Risk register and controls |
| [evidence.md](evidence.md) | Starting facts and observed proof |
| [closeout.md](closeout.md) | Exit-gate judgment |
| [SESSION.md](SESSION.md) | Crash-recovery pointer for the current item |

## Current state

Item 13.3 is in progress. `veriformis.quality-report/v1` records facts,
policy, and recommendations as separate layers and fills plan-bound
distribution facts. The report is not enforcing. There is no
quality-report command. Do not start Phase 14 from this packet.
