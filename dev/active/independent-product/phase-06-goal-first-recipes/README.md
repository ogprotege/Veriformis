# Phase 6 — Goal-First Recipes and Previews

**Status:** Completed locally; Phase 6.7 pull request pending

**Started:** 2026-08-22

**Completed:** 2026-08-22 (local closeout; publication pending)

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
Items 6.1–6.6 merged sequentially as PR #60
(`7316d94faf2d6c23b7abb6fe200f154da47d398c`), PR #61
(`81becfa676fd9111868b8d4b62549218a644d3e2`), PR #62
(`9cbab117e47cde6bd8850d67f0d363e03f0660ce`), PR #63
(`abdd630e25e83ebf346316319caec892f4d64886`), PR #64
(`b2e28b3dcfe48cd28ec74d8d8eaed12049f72d2d`), and PR #65
(`7b93a32a5a9b18e5bc9c032750f467c4d9c43ea5`), each after green GitHub checks
and clean-main synchronization. The frozen, discovery-closed 74-cell matrix in
6.6 proves every eligible goal, input family, and representation from raw source
through seal and external-digest verify with identical identifiers across every
surface. Item 6.7 implements catalog-default instructions and deterministic
operator truthfulness, makes both non-claim sets visible in the Mac picker and
preview, and adds the predeclared view-model walkthrough. On the current tree
the complete matrix passed 297 cases, the Mac XCTest target passed 102
methods with `TEST SUCCEEDED`, and the standalone Python suite passed 2,006
tests. U1–U6 are judged in `closeout.md`. Publication, GitHub checks, merge,
and clean-main synchronization remain unclaimed.
