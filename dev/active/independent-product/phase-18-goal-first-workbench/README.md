# Phase 18: Complete the Goal-First Mac Workbench

**Status:** In progress

**Started:** 2026-08-28

**Roadmap phase:** [Phase 18](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-18--complete-the-goal-first-mac-workbench)

**Predecessor:** [Phase 17 closeout](../phase-17-advanced-dataset-families/closeout.md), merged as
PR #159 at `7d851c8a531eac7217051effe000048403a3b866`.

## Purpose

Make the full independent workflow approachable on Mac without hiding
contracts or rebuilding them in Swift.

## Phase boundary

Phase 18 begins with honesty records. The workbench remains a thin CLI
adapter. Document-source compile, goal picker, preflight, and post-compile
preview already exist. Dataset-row mapping, export screens, and Mac Review
wait for later licensed items. Swift owns no dataset policy. ADR-0017 and
ADR-0018 Decision A stand. This packet does not start Phase 19.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Ten-item sequential execution plan and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted locks and later operator decisions |
| [risks.md](risks.md) | Workbench-adapter risk register |
| [evidence.md](evidence.md) | Starting facts and accumulated proof |
| [closeout.md](closeout.md) | Final exit-gate judgment |
| [SESSION.md](SESSION.md) | Crash-recovery pointer for the current item |

## Current state

Item 18.1 merged as PR #160. Item 18.2 pins ADR-0019 and
`veriformis.workbench-adapter/v1`. Sidebar remains Home / Compile /
History / Settings. Compile remains document-source. Loading a wrap pin
is not a screen.
