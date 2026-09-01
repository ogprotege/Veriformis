# Phase 20: Cut the Stable Independent 1.0 Product

**Status:** In progress

**Started:** 2026-08-31

**Roadmap phase:** [Phase 20](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-20--cut-the-stable-independent-1.0-product)

**Predecessor:** [Phase 19 closeout](../phase-19-automation-and-publication/closeout.md), merged as
PR #180 at `084e504a799b6c1c1cc130c8ee819b13de5d6bbe`. Clean `main` equals
`origin/main` there.

## Purpose

Release a supportable product whose claims are bounded by retained evidence.
Every 1.0 claim must link to a passing clean-machine, contract/conformance,
performance, security, or migration result. Unsupported candidates are
excluded rather than weakly claimed.

## Phase boundary

Phase 20 begins with honesty records. Version stays `0.1.0` development alpha
until item 20.10 after the evidence index is complete. There is no support
matrix freeze, version bump, signed Mac, Hub execute, or support-lifecycle
document in item 20.1. PipelineService owns policy. CLI and MCP are adapters.
This packet does not invent a Phase 21.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Ten-item sequential execution plan and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted locks and later operator decisions |
| [risks.md](risks.md) | Release-cut risk register |
| [evidence.md](evidence.md) | Starting facts and accumulated proof |
| [closeout.md](closeout.md) | Final exit-gate judgment |
| [SESSION.md](SESSION.md) | Crash-recovery pointer for the current item |

## Current state

Phase 20 is in progress. Item 20.2 freezes the CLI-first 1.0 support matrix.
Version remains `0.1.0` development alpha. ADR-0020 Decision A stands. Hub
execute is skipped. Public signed/notarized Mac is not in the 1.0 matrix
unless 20.6 produces owner-signed evidence (default: skip with a record).
