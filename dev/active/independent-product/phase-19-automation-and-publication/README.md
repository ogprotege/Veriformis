# Phase 19: Complete Automation and Optional Publication Boundaries

**Status:** In progress

**Started:** 2026-08-31

**Roadmap phase:** [Phase 19](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-19--complete-automation-and-optional-publication-boundaries)

**Predecessor:** [Phase 18 closeout](../phase-18-goal-first-workbench/closeout.md), merged as
PR #169 at `9f384eeedb401441c564c511b642904c403dad38`. Clean `main` at packet
open is PR #170 at `2737476eb2df83d82f575e3735b68487ee7cabc8` (install-smoke
SIGPIPE fix after closeout).

## Purpose

Support reproducible pipelines, CI, and opt-in sharing without turning the
local compiler into a required cloud service. A locked project spec reproduces
the same semantic dataset and verified exports on supported clean hosts.
Network publication stays absent from the default path.

## Phase boundary

Phase 19 begins with honesty records. `veriformis.pipeline/v1` stays executable
and byte-stable. There is no project spec, lockfile, spec dry-run, resume
path, Hub execute, or new MCP tool in item 19.1. PipelineService owns policy.
CLI and MCP are adapters. This packet does not start Phase 20.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Ten-item sequential execution plan and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted locks and later operator decisions |
| [risks.md](risks.md) | Automation and publication risk register |
| [evidence.md](evidence.md) | Starting facts and accumulated proof |
| [closeout.md](closeout.md) | Final exit-gate judgment |
| [SESSION.md](SESSION.md) | Crash-recovery pointer for the current item |

## Current state

Item 19.2 pins additive `veriformis.project-spec/v1`. Loading a spec is not
execute. Pipeline/v1 stays. There is no dry-run, lockfile, resume path, Hub
execute, or new MCP tool. Default `review_policy` stays `none`. Quality gates
remain preview-only.
