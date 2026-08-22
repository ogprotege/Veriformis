# Goal Catalog Contract v1

**Contract ID:** `veriformis.goal-catalog`

**Contract version:** `1`

**Schema identifier:** `veriformis.goal-catalog/v1`

**Execution profile:** `offline-deterministic-v1`

**Implementation status:** Implemented in independent-product Phase 6.1
(goal catalog and read-only discovery). Items 6.2–6.7 extend this contract
additively with per-goal contracts, the input-family axis, previews, presets,
preflight, the acceptance matrix, and instruction truthfulness.

**Last reviewed:** 2026-08-22 (independent-product Phase 6.1)

**Next review:** Any goal, representation, objective, row-schema, loss-policy,
or recipe-library change

## Purpose

A goal is what a person wants the model to learn, stated in plain language.
This contract binds every goal to exactly one existing persisted training
objective and one named recipe, and every representation to exactly one
existing persisted row schema and its taxonomy loss policy. The catalog is a
naming and discovery layer. It MUST NOT add, rename, or drop an objective, a
row schema, a training family, or a loss policy, and it MUST NOT invent a
question, answer, summary, or target.

## Normative language

`MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, and `MAY` are normative terms.
Plain-language text is human guidance, not a persisted identifier.

## Authority

| Concept | Authority reused here |
| --- | --- |
| Objective kinds | [Dataset Construction Contract v1](dataset-construction-v1.md) `TrainingObjective`; [Taxonomy Contract v1](taxonomy-v1.md) |
| Row schemas and loss policies | [Finished Dataset Contract v1](finished-dataset-v1.md); [Taxonomy Contract v1](taxonomy-v1.md) |
| Objective/row compatibility and defaults | [Taxonomy Contract v1](taxonomy-v1.md) compatibility matrix |
| Named recipes | `veriformis.recipes.library` `RECIPE_LIBRARY_IDS` |
| Architecture decision | [ADR-0007](../adr/0007-goal-first-catalog-as-versioned-data.md) |

## Versioned data

The catalog is packaged versioned data at
`src/veriformis/goals/catalog-v1.json`. The file MUST be canonical: UTF-8,
two-space indentation, sorted object keys, exact Unicode, and one trailing
newline. The loader rejects non-canonical bytes, duplicate JSON keys, unknown
keys, and any closure violation below. Every surface emits these exact bytes.

Top-level object:

| Key | Value |
| --- | --- |
| `schema_id` | exactly `veriformis.goal-catalog/v1` |
| `contract_id` | exactly `veriformis.goal-catalog` |
| `contract_version` | exactly the JSON integer `1` (not `1.0`, `true`, or `"1"`) |
| `goals` | ordered array of goal objects, one per objective kind in taxonomy order |
| `representations` | ordered array of representation objects, one per row schema in taxonomy order |

### Goal object

| Field | Meaning |
| --- | --- |
| `goal_id` | Stable identifier matching `^[a-z0-9]+(-[a-z0-9]+)*$`, used on every surface |
| `title` | Plain-language name |
| `plain_language` | One sentence a person would say to select the goal |
| `what_the_model_learns` | The learned behavior in plain words |
| `what_you_provide` | The input a person must supply |
| `not_this` | Non-empty list of explicit non-claims |
| `objective` | Exactly one persisted objective kind |
| `training_family` | The taxonomy family of that objective |
| `recipe_library_id` | The named recipe whose objective equals `objective` |
| `default_representation` | A compatible `representation_id` resolving to the taxonomy default row schema |
| `compatible_representations` | Unique, ordered `representation_id` values resolving exactly to the taxonomy compatibility row for `objective` |
| `state` | Exactly `implemented` in v1 |

### Representation object

| Field | Meaning |
| --- | --- |
| `representation_id` | Stable identifier matching `^[a-z0-9]+(-[a-z0-9]+)*$` |
| `title` | Plain-language name |
| `plain_language` | What the training example looks like |
| `supervised_region` | Which part receives training loss, in plain words |
| `row_schema` | Exactly one persisted row schema |
| `loss_policy` | The taxonomy loss policy of that row schema |
| `requires_operator_instruction` | `true` exactly for `instruction_output` |

## Closure rules

1. `goals` MUST contain exactly one goal per objective kind, in the taxonomy
   order `full_text`, `continuation`, `section_reconstruction`,
   `before_after_transformation`, `structured_field`.
2. `representations` MUST contain exactly one representation per row schema,
   in the order `text`, `prompt_completion`, `instruction_output`, `messages`.
3. A goal's `compatible_representations` MUST resolve to exactly the
   taxonomy compatibility row for its objective, in order; its
   `default_representation` MUST resolve to the taxonomy default row schema.
4. `training_family`, `loss_policy`, and `recipe_library_id` MUST equal the
   taxonomy and recipe-library bindings for their objective or row schema.
5. Supervised instruction and conversation representations are admitted only
   for the four supervised objectives, where the source supplies both the
   context and the target. `full_text` admits only `whole-text`.
6. Plain-language fields (`title`, `plain_language`,
   `what_the_model_learns`, `what_you_provide`, `not_this`,
   `supervised_region`) MUST NOT contain, in any letter case, a machine
   identifier: an objective, row-schema, loss-policy, recipe, or alias
   identifier that contains `_`, `-`, or `.`. Bare English words that are also
   identifiers (`text`, `messages`, `continuation`, `completion`,
   `instruction`, `chat`) are permitted as ordinary words. Fields MUST be
   non-empty, MUST NOT carry surrounding whitespace, MUST NOT contain control
   characters, and `not_this` MUST NOT repeat an entry.
7. `title`, `plain_language`, `what_the_model_learns`, `what_you_provide`,
   and every representation's `title`, `plain_language`, and
   `supervised_region` MUST NOT describe a summary, an answer, or a
   translation. `summary` is not a goal, objective, alias, or representation.
   Item 6.7 extends this claim vocabulary to operator instructions.

## Resolution

`resolve_goal(goal_id, representation_id=None)` returns exactly
`(objective, row_schema, recipe_library_id, loss_policy)`. A missing
representation selects the goal's default. An unknown goal, an unknown
representation, a UI alias, or an incompatible pair fails with
`goal-catalog-invalid` before any workspace is opened. The returned objective
and row schema are the only values that may enter a `DatasetRecipe`; goal and
representation identifiers are never persisted in a recipe, row, or bundle.

## Discovery

| Surface | Operation | Output |
| --- | --- | --- |
| Python | `PipelineService.discover_goals()` | Fresh JSON-ready dict equal to the packaged data |
| CLI | `veriformis goals` | The exact packaged bytes |
| MCP | `goals` | The exact packaged text, including the terminal newline |
| Mac bridge | `VeriformisCLI.discoverGoals` | Strictly decoded `GoalCatalog`; missing or extra keys, empty or control-character text, malformed or duplicate identifiers, an objective outside the five kinds, a row-schema sequence other than taxonomy order, an unclosed default or compatibility set, and `requires_operator_instruction` drift are rejected; per-objective compatibility rows and default row schemas are validated only by Python, which is authoritative |

The frozen fixture `tests/regressions/fixtures/phase6/goal-catalog.json`
MUST equal the packaged bytes and is decoded by the Swift tests.

## Version and migration

The contract version changes only on an incompatible meaning change. Adding a
field, a non-claim, or a representation binding that preserves closure is
additive within v1. Changing a goal's objective, default, or compatibility set
is incompatible and requires a new version with a migration note. The catalog
is never persisted in a workspace or bundle, so no persisted migration exists.

## Non-goals

- Deciding whether fine-tuning is appropriate.
- Inventing question/answer pairs, summaries, or targets.
- Trainer or consumer compatibility claims.
- Any learning behavior not already defined by the construction and
  finished-dataset contracts.
