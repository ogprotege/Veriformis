# Phase 17: Add Governed Advanced Dataset Families

**Status:** In progress

**Started:** 2026-08-28

**Roadmap phase:** [Phase 17](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-17--add-governed-advanced-dataset-families)

**Predecessor:** [Phase 16 closeout](../phase-16-extension-architecture/closeout.md), merged as
PR #149 at `a1fbf04d58d73692cc4237b7d741c5da27022581`.

## Purpose

Admit advanced semantic families one at a time from user-provided evidence
while remaining fail-closed, deterministic, and offline by default.

## Phase boundary

Phase 17 begins with honesty records. Classification and preference pairs are
the required executable families. Tool-call, stepwise, unpaired preference,
trainer-profile mappings, and generation wait for later licensed items.
Multimodal stays `explicitly_unsupported`. Pre-tokenized training stays
planned. Family admission is not an extension-protocol event. ADR-0017
Decision A stands. This packet does not start Phase 18.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Ten-item sequential execution plan and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted locks and later operator decisions |
| [risks.md](risks.md) | Advanced-family risk register |
| [evidence.md](evidence.md) | Starting facts and accumulated proof |
| [closeout.md](closeout.md) | Final exit-gate judgment |
| [SESSION.md](SESSION.md) | Crash-recovery pointer for the current item |

## Current state

Item 17.1 opens the packet and records the SFT-only baseline. No advanced
family contract, row schema, objective, loss policy, constructor, mapping
template, goal, or profile mapping is added yet.
