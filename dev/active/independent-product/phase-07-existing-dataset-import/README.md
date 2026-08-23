# Phase 7 — Existing-Dataset Import and Mapping

**Status:** Complete

**Started:** 2026-08-23

**Completed:** 2026-08-23

**Roadmap phase:** [Phase 7](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-7--add-first-class-existing-dataset-import-and-mapping)

**Predecessor:** [Phase 6 closeout](../phase-06-goal-first-recipes/closeout.md),
merged as PR #67 at `6995d17bef0d09f235b1c464e947c38c63dd313d` and stamped
complete as PR #69 at `6c4694c2e1c523156cd7c8f34c12f258a3ce0b01`

## Purpose

Normalize datasets that already contain training rows into the current
semantic row schemas, with explicit confirmed mappings, field-level
provenance, honest partition policy, and the same seal → generic-export path
as constructed datasets.

## Phase boundary

Phase 7 owns input modes, row-source and mapping contracts, mapping execution,
detection/confirmation, provenance replay, full-file preview, partition
policy, JSON/CSV admission, rejection reports, and mapping templates. It adds
no sixth objective, fifth row schema, Parquet/Arrow importer, consumer
profile, or executable mapping code.

Item 7.1 names the three compiler paths and keeps only `document-source`
executable.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Ten-item execution sequence, predeclared usability criteria, and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted scope decisions |
| [risks.md](risks.md) | Risk register and controls |
| [evidence.md](evidence.md) | Starting facts and observed proof |
| [closeout.md](closeout.md) | Exit-gate judgment |

## Current state

Phase 7 completed on 2026-08-23. Items 7.1–7.10 merged as PR #71–#80.
Closeout merged as PR #80 at `b7bb7f0c2046fba87fd7c9da12f7d2ccb5c2c88f`
after all 14 GitHub checks passed.
