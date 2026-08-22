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
Items 6.1–6.3 merged as PR #60 (`7316d94faf2d6c23b7abb6fe200f154da47d398c`),
PR #61 (`81becfa676fd9111868b8d4b62549218a644d3e2`), and PR #62
(`9cbab117e47cde6bd8850d67f0d363e03f0660ce`), each after all 14 GitHub
checks passed. Item 6.4 is locally complete on branch
`phase6/04-recipe-presets`: `veriformis.recipe-preset/v1` as the single
versioned source of every recipe default and one safe preset per goal,
`--goal`/`--preset`/`--representation` selection with explicit overrides on
`chunk`, `construct`, and `curate` across Python, CLI, MCP, and YAML, the
recipe library on the execution path, `presets` discovery, a catalog-driven
workbench goal picker with a recipe-settings disclosure and no Swift recipe
constants, and a tracking gate that refuses recipe default literals. Its pull
request, GitHub checks, merge, and clean-main synchronization are not claimed
by this packet.
