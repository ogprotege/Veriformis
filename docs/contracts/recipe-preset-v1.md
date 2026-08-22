# Recipe Preset Contract v1

**Contract ID:** `veriformis.recipe-preset`

**Contract version:** `1`

**Schema identifier:** `veriformis.recipe-preset/v1`

**Execution profile:** `offline-deterministic-v1`

**Implementation status:** Implemented in independent-product Phase 6.4.

**Last reviewed:** 2026-08-22 (independent-product Phase 6.4)

**Next review:** Any default, preset, goal, representation, chunk-strategy,
curation-policy, or consumer-profile change

## Purpose

Recipe settings were once literals repeated in the CLI, the MCP server, the
pipeline service, the YAML runner, the recipe library, and the Swift
workbench. This contract makes one packaged, versioned data file the single
source of every recipe default and of each goal's safe named preset. Every
surface resolves its effective settings through the same function, so the
same selection yields the same `recipe_id` and finished plan everywhere.

## Normative language

`MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, and `MAY` are normative terms.

## Authority

| Concept | Authority reused here |
| --- | --- |
| Goals and representations | [Goal Catalog Contract v1](goal-catalog-v1.md) |
| Segmentation policy | [Dataset Construction Contract v1](dataset-construction-v1.md) `SegmentationPolicy` |
| Curation and split policy | [Finished Dataset Contract v1](finished-dataset-v1.md) `CurationPolicy`, `SplitPolicy` |
| Consumer profiles and compile compatibility | [Taxonomy Contract v1](taxonomy-v1.md) |
| Architecture decision | [ADR-0007](../adr/0007-goal-first-catalog-as-versioned-data.md) |

## Versioned data

The presets are packaged versioned data at
`src/veriformis/goals/presets-v1.json`: canonical UTF-8 JSON with two-space
indentation, sorted keys, and one trailing newline. The loader rejects
non-canonical bytes, duplicate or unknown keys, and any closure violation.

Top-level object:

| Key | Value |
| --- | --- |
| `schema_id` | exactly `veriformis.recipe-preset/v1` |
| `contract_id` | exactly `veriformis.recipe-preset` |
| `contract_version` | exactly the JSON integer `1` |
| `defaults` | the recipe-wide defaults object |
| `presets` | ordered array of preset objects, exactly one `safe` preset per goal in catalog order |

### Defaults and preset objects

Both carry `segmentation` (`strategy`, `size`, `overlap`, validated as an
executable `SegmentationPolicy`), `construction` (`split_ratio_ppm` in
1..999999, `require_review`, an implemented `consumer_profile`), `curation`
(the Goal Catalog `curation_defaults` shape, validated as an executable
`CurationPolicy`), and `review_policy` (`none` or `required`). A preset adds
`preset_id` (exactly `<goal_id>.<name>`), `goal_id`, a `representation_id`
the goal allows, `title`, and `plain_language`. Every preset MUST be
compilable under the taxonomy for its objective, row schema, and profile.

## Resolution

`resolve_recipe_settings(...)` is the only resolution path. It accepts a
selection (`goal`, `preset`, or the persisted `objective`; optional
`representation` or legacy `target_row_schema`) plus explicit overrides for
every segmentation, construction, curation, and review field, and returns
`ResolvedRecipeSettings` with a `settings_digest` over the effective settings.

1. A preset implies its goal and representation; a conflicting `goal` or
   `objective` fails closed.
2. A goal or objective without a preset resolves through that goal's `safe`
   preset. The digest covers only effective settings, so
   `goal`, `preset=<goal>.safe`, and `objective` selections with the same
   overrides produce the same digest.
3. Overrides apply on top of the preset and are validated as executable
   policies; a `balance_mode` override accepts only the documented surface
   spelling `primary-source-cap` (the persisted `primary_source_cap` is data,
   not an operator value).
4. Unknown goals, presets, representations, or incompatible combinations fail
   closed before any workspace is opened.

## Surfaces

| Surface | Behavior |
| --- | --- |
| `PipelineService.chunk` / `construct` / `curate` | Every setting parameter defaults to `None`; omitted settings resolve from the selected preset or the goal's safe preset. `construct` builds the recipe through the named recipe library. `construct --preset` fails closed when the workspace chunks were not produced with the preset's segmentation. |
| CLI `chunk`, `construct`, `curate` | `--goal`, `--preset`, `--representation` select; every other option is an explicit override with no literal default. `--objective` remains as the persisted-kind selection. |
| MCP `chunk`, `construct`, `curate` | The same parameters, appended after the existing ones. |
| YAML `veriformis.pipeline/v1` | Stage keys `goal`, `preset`, and (construct) `representation`; omitted values resolve from the data. `recipe_library_id` remains supported. |
| CLI `presets` / MCP `presets` / `PipelineService.discover_presets` | Emit the exact packaged text. |
| Mac workbench | Discovers `goals` and `presets` at startup, offers a plain-language goal picker with the goal's safe preset, and an Advanced disclosure for explicit overrides; it holds no recipe default constant and passes only the selection and explicit overrides (`chunk --preset`, `construct --goal --preset`, `curate --preset`). |

The tracking checker binds `training.implemented_presets` to the packaged
presets and fails when any surface source file or the workbench holds a
recipe default literal.

## Version and migration

The contract version changes only when a preset's meaning changes. Adding a
preset, a default field with an additive meaning, or a representation binding
that preserves closure is additive within v1. Presets are never persisted in a
workspace or bundle; only the resolved recipe and finished plan are.

## Non-goals

- Deciding whether fine-tuning is appropriate.
- Adding an objective, row schema, construction behavior, or trainer claim.
- Preflight (Phase 6.5) and the acceptance matrix (Phase 6.6).
