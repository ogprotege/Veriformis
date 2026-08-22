# Phase 6 — Goal-First Recipes and Previews

**Status:** In progress

**Started:** 2026-08-22

**Completed:** —

**Roadmap phase:** [Phase 6](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-6--deliver-goal-first-recipes-and-previews)

**Predecessor:** [Phase 5 closeout](../phase-05-generic-local-exports/closeout.md),
merged as PR #59 at `65cbd471e96d83f8dd65e2cda60e90f64a916e2b`

## Purpose

Let a person say what they want the model to learn in plain language and get
the same deterministic recipe, rows, supervised region, exclusions, and sealed
output from every surface, without first learning the objective, row-schema,
supervision, or recipe-setting vocabulary.

## Phase boundary

Phase 6 owns the goal catalog, per-goal contracts, the seventh taxonomy axis
for input families, goal-specific previews, versioned recipe presets and the
advanced editor, compile preflight, the goal acceptance matrix, and
instruction/prompt truthfulness validation. It resolves every goal to one of
the five existing persisted objective kinds and one of the four existing row
schemas. It adds no objective, row schema, construction behavior, trainer
claim, consumer profile, generated text, or invented question, answer,
summary, or target.

The Mac workbench gains a catalog-driven goal picker, preflight panel, and
loss/row preview screen in this phase because Phase 18 depends on them and the
Phase 6 exit gate is phrased for a non-developer. Those screens expose only
capabilities owned by `PipelineService`.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Seven-item execution sequence, predeclared usability criteria, and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted scope decisions |
| [risks.md](risks.md) | Risk register and controls |
| [evidence.md](evidence.md) | Starting facts and observed proof |
| [closeout.md](closeout.md) | Exit-gate judgment |

## Current state

Phase 6 opened on 2026-08-22 from baseline
`65cbd471e96d83f8dd65e2cda60e90f64a916e2b` (PR #59, the Phase 5 closeout).
Item 6.1's plain-language goal catalog merged as PR #60 at
`7316d94faf2d6c23b7abb6fe200f154da47d398c` and item 6.2's goal contracts and
`input_family` axis merged as PR #61 at
`81becfa676fd9111868b8d4b62549218a644d3e2`, each after all 14 GitHub checks
passed. Item 6.3 is locally complete on branch `phase6/03-goal-preview`: the
runtime-only `veriformis.goal-preview/v1` response through
`PipelineService.preview_goal`, CLI `goal-preview`, MCP `goal_preview`, the
strict Swift bridge, and a post-compile workbench preview screen, bounded
exactly on its ASCII transport and proved against the persisted product rows.
Its pull request, GitHub checks, merge, and clean-main synchronization are not
claimed by this packet.
