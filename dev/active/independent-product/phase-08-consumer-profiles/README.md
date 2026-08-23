# Phase 8 — First Consumer Profiles

**Status:** Complete

**Started:** 2026-08-23

**Completed:** 2026-08-23

**Roadmap phase:** [Phase 8](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-8--implement-the-first-consumer-profiles)

**Predecessor:** [Phase 7 closeout](../phase-07-existing-dataset-import/closeout.md),
merged as PR #80 at `b7bb7f0c2046fba87fd7c9da12f7d2ccb5c2c88f` after all 14
GitHub checks passed; active-doc continuity merged as PR #81 at
`64a7799c27d1a489f01d77d8ba399910c95c0712`; item 8.1 merged as PR #82 at
`799d56f` after all 14 GitHub checks passed

## Purpose

Prove the consumer-profile architecture against two materially different,
well-documented training systems (TRL and MLX-LM) as optional adapters over
already-verified bundles. Profiles do not curate, resplit, or change
membership or targets.

## Phase boundary

Phase 8 owns admission pins, isolated extras, TRL and MLX-LM emission,
conformance harnesses, config sidecars, and discovery truthfulness. It adds
no fourth generic container, no Parquet/Arrow (Phase 9), no Axolotl /
LLaMA-Factory / Unsloth / Aptus-as-profile (Phase 10), and no training
launcher.

Item 8.1 opened the packet and published ADR-0012. Item 8.2 pins official
TRL and MLX-LM admission records as packaged data with empty extras. Item
8.3 emits the TRL SFT adapter. Item 8.4 emits the MLX-LM LoRA adapter.
Item 8.5 adds official-schema harnesses. Item 8.6 emits launch sidecars.
Item 8.7 promotes taxonomy to implemented.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Seven-item execution sequence, predeclared usability criteria, and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted scope decisions |
| [risks.md](risks.md) | Risk register and controls |
| [evidence.md](evidence.md) | Starting facts and observed proof |
| [closeout.md](closeout.md) | Exit-gate judgment |
| [SESSION.md](SESSION.md) | Crash-recovery pointer for the current item |

## Current state

Item 8.7 promotes `trl` and `mlx-lm` to implemented, names accepted,
transformed, and rejected goals and rows, and closes Phase 8. Generic
export selectors stay `consumer_id` null. Do not start Phase 9, 10, or 13
from this packet.
