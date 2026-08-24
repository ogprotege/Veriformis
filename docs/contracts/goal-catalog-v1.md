# Goal Catalog Contract v1

**Contract ID:** `veriformis.goal-catalog`

**Contract version:** `1`

**Schema identifier:** `veriformis.goal-catalog/v1`

**Execution profile:** `offline-deterministic-v1`

**Implementation status:** Implemented in independent-product Phase 6.1
(goal catalog and read-only discovery), extended additively by Phase 6.2
(per-goal contracts and input-family eligibility), Phase 6.3 (the
runtime-only goal preview), Phase 6.4 (goal and preset selection on every
compile surface under the [Recipe Preset Contract v1](recipe-preset-v1.md)),
Phase 6.5 (the runtime-only compile preflight), Phase 6.6 (the
discovery-closed acceptance matrix), and Phase 6.7 (per-goal instruction
templates and deterministic instruction truthfulness).

**Last reviewed:** 2026-08-22 (independent-product Phase 6.7)

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
| `eligible_input_families` | Non-empty, unique implemented input families in taxonomy order whose recovery supplies the goal's evidence |
| `required_source_evidence` | Plain-language statement of the evidence the source must contain |
| `required_evidence_diagnostics` | The construction diagnostic codes that report that evidence missing; a subset of `V1_CONSTRUCTION_DIAGNOSTIC_CODES` |
| `target_construction` | Plain-language statement of exactly how context and target are derived |
| `supervision_boundary` | Plain-language statement of which part is context and which receives loss |
| `curation_defaults` | Object with `minimum_target_characters`, `balance_mode`, `maximum_records_per_primary_source`, `evaluation_ratio_ppm`, `evaluation_required`, `split_seed`; validated as an executable `CurationPolicy`; equal to the recipe-wide defaults in the [Recipe Preset Contract v1](recipe-preset-v1.md), which every surface executes. `balance_mode` uses the persisted `CurationPolicy` spelling (`none`, `primary_source_cap`); surfaces accept only the documented hyphenated `primary-source-cap` |
| `review_policy_default` | `none` or `required` |
| `review_policy_options` | Exactly `["none", "required"]` |
| `non_claims` | Exactly the closed v1 codes `no-trainer-compatibility`, `no-generated-text`, `no-invented-target`, `no-fine-tuning-suitability-judgment` |
| `instruction_template` | The only default instruction literal for this goal; a complete source-derived task statement used when `instruction-and-output` omits an operator instruction |
| `instruction_task` | The unique phrase the template and every admitted operator instruction MUST name |
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
| `compatible_generic_exports` | Non-empty, unique production generic export containers in taxonomy order whose descriptors admit `row_schema` |

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
   `instruction_template`, `instruction_task`, `supervised_region`) MUST NOT
   contain, in any letter case, a machine identifier: an objective,
   row-schema, loss-policy, recipe, or alias identifier that contains `_`,
   `-`, or `.`. Bare English words that are also identifiers (`text`,
   `messages`, `continuation`, `completion`, `instruction`, `chat`) are
   permitted as ordinary words. Fields MUST be non-empty, MUST NOT carry
   surrounding whitespace, MUST NOT contain control characters, and
   `not_this` MUST NOT repeat an entry.
7. `title`, `plain_language`, `what_the_model_learns`, `what_you_provide`,
   `required_source_evidence`, `target_construction`,
   `supervision_boundary`, `instruction_template`, `instruction_task`, and
   every representation's `title`, `plain_language`, and `supervised_region`
   MUST NOT describe a summary, an answer, or a translation. `summary` is
   not a goal, objective, alias, or representation. The same claim
   vocabulary (`summar`, `answer`, `translat`) applies to every operator
   instruction admitted for `instruction-and-output`.
   `instruction_template` MUST contain `instruction_task` as a contiguous
   case-insensitive substring. `instruction_task` MUST be unique per goal.

8. `eligible_input_families` MUST name only families whose recovery supplies
   the goal's `required_source_evidence`; a family that can never supply it
   MUST be absent. Current exclusions: `delimited-table` and `json-records`
   carry no supported scalar; `source-code` is one code block that cleaning
   never edits, so it can supply no before-and-after pair; `pdf-text`
   recovery supplies paragraphs under synthetic per-page labels, not real
   headings, so it can supply neither a section nor a recorded attribute.
   `required_evidence_diagnostics` MUST include `source-chunks-unavailable`
   for every goal because construction reports it for every objective. Item
   6.6 proves every named family end to end.
9. `curation_defaults` MUST equal the recipe-wide defaults of the Recipe
   Preset Contract v1, which `PipelineService`, the CLI, MCP, the YAML runner,
   the recipe library, and the workbench all resolve through one function; a
   test enforces the equality.
10. `compatible_generic_exports` MUST equal the production export catalog's
    admitted containers for the representation's row schema; a test derives
    it from `PipelineService.discover_exports()`.

## Goal bindings (v1)

| Goal | Objective | Eligible input families | Missing-evidence diagnostics |
| --- | --- | --- | --- |
| `learn-the-text` | `full_text` | all eight | `source-chunks-unavailable` |
| `continue-a-passage` | `continuation` | all eight | `source-chunks-unavailable`, `continuation-boundary-unavailable` |
| `recover-a-section-from-its-heading` | `section_reconstruction` | `markdown`, `word-document`, `html` | `source-chunks-unavailable`, `section-structure-unavailable` |
| `reproduce-a-recorded-change` | `before_after_transformation` | all except `source-code` | `source-chunks-unavailable`, `transformation-pair-unavailable`, `transformation-pair-empty-or-unchanged` |
| `extract-a-structured-value` | `structured_field` | `source-code`, `markdown`, `word-document`, `html` | `source-chunks-unavailable`, `structured-ir-artifact-unavailable`, `structured-field-unavailable`, `structured-field-chunk-unavailable`, `structured-field-empty-value` |

Every goal states `curation_defaults` of `minimum_target_characters` 1,
`balance_mode` `none`, no per-source cap, `evaluation_ratio_ppm` 500000,
`evaluation_required` true, and `split_seed` `veriformis-v1`;
`review_policy_default` `none`; and all four non-claim codes. Representations
admit `split-jsonl-directory`, `json`, `parquet`, `arrow`, and
`hugging-face-dataset` for every row schema and `constrained-csv` for
the three flat schemas only.

| Goal | `instruction_task` | `instruction_template` |
| --- | --- | --- |
| `learn-the-text` | exact source passage | Reproduce the exact source passage as written. |
| `continue-a-passage` | exact source remainder | Continue the passage with its exact source remainder. |
| `recover-a-section-from-its-heading` | exact source section body | Produce the exact source section body for this heading. |
| `reproduce-a-recorded-change` | recorded cleaning change | Apply the recorded cleaning change to this exact source text. |
| `extract-a-structured-value` | exact structural attribute | Produce the exact structural attribute recorded by this source. |

Those five templates are the only default instruction literals. They are
byte-identical to the instruction strings pinned by the Phase 6.6
acceptance matrix for every `instruction_output` cell.

## Resolution

`resolve_goal(goal_id, representation_id=None)` returns exactly
`(objective, row_schema, recipe_library_id, loss_policy)`. A missing
representation selects the goal's default. An unknown goal, an unknown
representation, a UI alias, or an incompatible pair fails with
`goal-catalog-invalid` before any workspace is opened. The returned objective
and row schema are the only values that may enter a `DatasetRecipe`; goal and
representation identifiers are never persisted in a recipe, row, or bundle.

`resolve_operator_instruction(...)` is the only default-instruction path.
It returns the catalog template or one admitted operator instruction:

| Input | Result |
| --- | --- |
| Representation is not `instruction-and-output`, instruction omitted | `null`; no instruction is stored or rendered |
| Representation is not `instruction-and-output`, instruction supplied | `instruction-not-applicable` |
| `instruction-and-output`, instruction omitted (`null`) | The goal's `instruction_template` after the same truthfulness check |
| `instruction-and-output`, empty or surrounding-whitespace text | `instruction-required` |
| `instruction-and-output`, non-empty text that lacks `instruction_task` or contains `summar`, `answer`, or `translat` | `instruction-untruthful` |
| `instruction-and-output`, non-empty text that names `instruction_task` and contains no forbidden claim fragment | That exact text |

`curate`, compile preflight, goal preview, the CLI, MCP, the YAML runner,
and the Mac bridge all resolve through this function. Catalog templates are
the only default instruction literals; surfaces MUST NOT invent another
prefix, question, summary, or task statement. `messages` user turns remain
the exact context field and NEVER receive an instruction prefix.

## Discovery

| Surface | Operation | Output |
| --- | --- | --- |
| Python | `PipelineService.discover_goals()` | Fresh JSON-ready dict equal to the packaged data |
| CLI | `veriformis goals` | The exact packaged bytes |
| MCP | `goals` | The exact packaged text, including the terminal newline |
| Mac bridge | `VeriformisCLI.discoverGoals` | Strictly decoded `GoalCatalog`; missing or extra keys, empty or control-character text, malformed or duplicate identifiers, an objective outside the five kinds, a row-schema sequence other than taxonomy order, an unclosed default or compatibility set, and `requires_operator_instruction` drift are rejected; per-objective compatibility rows and default row schemas are validated only by Python, which is authoritative |

The frozen fixture `tests/regressions/fixtures/phase6/goal-catalog.json`
MUST equal the packaged bytes and is decoded by the Swift tests.

## Goal preview v1

`veriformis.goal-preview/v1` is a runtime-only, read-only response over a
workspace whose `construct` stage is complete. It is not one of the persisted
schemas and is never written to a workspace, bundle, or export.

| Surface | Operation |
| --- | --- |
| Python | `PipelineService.preview_goal(workspace, representation=None, instruction=None, record_ids=())` |
| CLI | `veriformis goal-preview WORKSPACE [--representation ID] [--instruction TEXT] [--record ID]...` |
| MCP | `goal_preview(workspace, representation, instruction, record_ids)` |
| Mac bridge | `VeriformisCLI.previewGoal`; the workbench shows the preview after a compile |

Semantics:

1. The goal is the catalog goal of the recipe's objective. The representation
   defaults to the recipe's `target_row_schema`; an explicit representation
   MUST be compatible with the goal, otherwise the preview fails closed after
   reading only the persisted recipe and before any record is read. A
   workspace below revision schema 3 fails closed with the upgrade
   instruction.
2. Sample policy `first-accepted-record-per-primary-source` selects the first
   accepted record of each primary source (the first entry of the record's
   sorted `source_ids`) in persisted order; explicit `record_ids` select
   exactly those accepted records in the requested order, and unknown or
   repeated ids fail closed.
3. For each selected record the preview reports its derivation lineage
   (`source_ids`, `logical_paths`, `chunk_ids`, `pass_id`, `constructor_id`,
   `constructor_version`), its `context` fields by objective field role (empty
   for the whole-text representation) and its `target` field, every piece of
   `recovered_source` evidence (an exact span of the recovered source stream
   with its digest and derivation kinds, or one strict-IR scalar by JSON
   pointer whose exact encoded value is the field value; in both cases
   `text_sha256` is the SHA-256 of the exact `excerpt`), the `rendered_row`
   exactly as `format` lowers it through the same function (proved against
   the persisted product rows), the `context_row_keys`, and the `supervised`
   span: the row key and the range, in Unicode code points (not bytes, UTF-16
   units, grapheme clusters, or tokens), that receives loss. The supervised
   span is derived from the objective field roles and the taxonomy loss
   policy; it always equals the whole target value and is never persisted.
   The preview also carries the goal's `not_this` and `non_claims` so every
   surface that shows a goal shows its non-claims (usability criterion U4).
4. When `curate` is complete the preview carries each selected record's
   decision status and reason codes, lists every excluded or quarantined
   record with its reason codes under `exclusions`, counts included, excluded,
   and quarantined records, and reuses the persisted instruction text for the
   instruction-and-output representation unless the caller supplies one.
5. `instruction-and-output` resolves an omitted instruction (no persisted
   text and no caller text) through `resolve_operator_instruction` to the
   goal's catalog template and renders the row. An empty supplied
   instruction fails closed with `instruction-required`. An untruthful
   supplied instruction fails closed with `instruction-untruthful`. The
   closed omission code `operator-instruction-required` remains reserved
   and is no longer the omitted-instruction path.
6. Bounds mirror the Phase 5.6 export preview and are measured on the exact
   ASCII transport text: a record whose entry exceeds 65,536 bytes is omitted
   whole with `exact-record-exceeds-preview-limit`; the response is assembled
   skeleton-first (every record omitted, no exclusions, no diagnostics) and
   fails closed with an exact reason if even that cannot fit 262,144 bytes;
   records are then filled in order while the whole response fits, and the
   rest are omitted whole with `exact-record-exceeds-response-budget`;
   omission removes excerpts, context, target, and the rendered row but keeps
   identities, digests, spans, and `exact_size_bytes`. Exclusions and
   diagnostics that no longer fit are counted in `omitted_exclusion_count` and
   `omitted_diagnostic_count`. The emitted text never exceeds 262,144 bytes
   and values are never truncated or rewritten.
7. Transport is `transport_text()`: ASCII-safe, two-space-indented JSON with
   sorted keys that decodes to the exact Unicode values; the CLI prints it and
   MCP returns it unchanged.
8. The preview never opens a workspace transaction, calls a renderer, or
   accesses a destination, and it changes no persisted model, request,
   discovery, selector, taxonomy, support, consumer, or trainer claim.

## Compile preflight v1

`veriformis.compile-preflight/v1` is a runtime-only, read-only response over
explicit raw source paths plus one goal, preset, and representation selection.
It is never written to a workspace, bundle, or export.

| Surface | Operation |
| --- | --- |
| Python | `PipelineService.preflight(paths, source_root=..., goal=..., preset=..., representation=..., ...)` |
| CLI | `veriformis preflight PATH... [--source-root ROOT] (--goal ID \| --preset ID) [--representation ID] [overrides...]` |
| MCP | `preflight(paths, source_root, goal, preset, representation, ...)` |
| Mac bridge | `VeriformisCLI.preflight`; the workbench presents the verdict before, and reruns it immediately before, creating a compile workspace |

The response has the following closed top-level fields:

| Field | Meaning |
| --- | --- |
| `schema_id` | Exactly `veriformis.compile-preflight/v1` |
| `request_digest` | Digest of the complete selection, overrides, logical source arguments, and instruction digest |
| `captured_source_digest` | Digest binding the sorted logical paths, raw SHA-256 values, and sizes from this one capture; absent before successful capture |
| `evaluated_through` | Deepest completed boundary: `selection`, `capture`, `parse`, `family`, `construct`, `curate`, or `split` |
| `admitted` | `true` only when selection is compatible, every source is admitted, curation has no source-coverage blocker, and required splitting succeeds |
| `selection` | Requested identifiers and instruction-presence bit plus the completely resolved goal, preset, representation, recipe, row schema, settings, cleaning, construction, curation, and review-policy facts |
| `counts` | Exact source, eligibility, candidate, record, decision, and inclusion counts |
| `sources` | One ordered verdict per supplied source |
| `incompatibilities` | Closed selection/override failures with implicated fields and actionable messages |
| `missing_evidence` | The actual construction diagnostics proving goal evidence absent |
| `expected_exclusion_counts`, `expected_exclusions` | Construction and curation decisions with their exact reason codes |
| `coverage_blockers` | Per-source curation coverage failures |
| `known_limitations` | Explicit non-claims and point-in-time limits |
| omission counts | Counts of whole diagnostics or exclusions omitted only to satisfy transport bounds |

Each source verdict carries its logical path, source identity and raw digest
when captured, size, derived `input_family`, observed parser, parser status,
parser eligibility, goal-family eligibility, evidence status, final admission,
refusal reasons, diagnostic counts and bounded diagnostics, omission reason,
and exact unredacted entry size. Refusal codes are
`source-read-failed`, `unsupported-input`, `parser-refused`,
`goal-input-family-ineligible`, `goal-evidence-unavailable`,
`curation-coverage-blocked`, and
`evaluation-partition-unavailable`. Incompatibility codes are
`selection-required`, `goal-invalid`, `preset-incompatible`,
`representation-incompatible`, `consumer-profile-incompatible`,
`override-invalid`, `instruction-required`, `instruction-not-applicable`,
`instruction-untruthful`, and
`review-evidence-unavailable`.

Semantics:

1. Selection and every explicit cleaning, segmentation, construction,
   curation, and review override resolve through the same versioned recipe
   settings as compile. An invalid selection is reported before source access.
2. Logical paths are derived by the same source-root boundary as `parse`.
   Repeated paths, duplicate logical locators, hard-link or case aliases with
   the same filesystem identity, any symlink component beneath the chosen
   root, paths outside the root, missing paths, directories, FIFOs, sockets,
   and other non-regular inputs fail closed without a blocking read.
   Capture walks from one pinned root directory descriptor with no-follow
   opens, so a component retargeted after locator derivation cannot escape the
   root.
3. Every admitted raw source is captured exactly once. The captured bytes are
   passed unchanged to the production parser and then through the same pure
   cleaning-plan replay, chunking, named construction recipe, global curation,
   and leakage-group split functions used by compile. No stage rereads a path.
4. The logical suffix is the input-family authority and the observed parser
   MUST be declared for that family. The same `require_goal_input_family`
   gate runs in preflight and real construction. In particular, synthetic PDF
   page labels cannot satisfy source-supplied section or structured-field
   evidence.
5. Parser refusal, missing source evidence, review-required recipes without
   review evidence, curation coverage loss, and required-evaluation split
   failure are negative verdicts with exact stable reason or diagnostic codes.
   Expected exclusions remain reported even when compile can otherwise
   proceed; preflight never silently turns an exclusion into admission.
6. The instruction-and-output representation requires an instruction
   value. An omitted instruction resolves to the goal's catalog template
   after the truthfulness check. A supplied instruction is admitted only
   when it names that goal's `instruction_task` and contains no claim
   vocabulary for a transformation the goal does not perform; otherwise
   preflight reports `instruction-required` or `instruction-untruthful`
   before source access. An instruction on any other representation is
   `instruction-not-applicable`.
7. Bounds are measured on exact ASCII transport text. A source entry above
   65,536 bytes drops only its diagnostic detail while preserving the complete
   verdict and omission count. A response above 262,144 bytes drops source
   diagnostic detail, missing-evidence detail, and individual exclusions while
   retaining their counts and every mandatory verdict; if even that skeleton
   cannot fit, preflight fails closed and instructs the caller to select fewer
   sources. Values are never truncated or rewritten.
8. `transport_text()` is ASCII-safe, two-space-indented JSON with sorted keys.
   CLI prints it before exiting `0` for admission or `2` for a negative
   verdict; MCP returns it unchanged.
9. Preflight creates no workspace, opens no workspace transaction, calls no
   renderer, accesses no destination, and changes no persisted contract,
   support claim, consumer profile, or trainer claim. Its point-in-time
   capture is not a publication guarantee: compile recaptures raw sources and
   MUST rerun its own validation, sealing, and independent verification.

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
