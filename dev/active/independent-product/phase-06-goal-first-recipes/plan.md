# Phase 6 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-22

Each numbered roadmap work item is one sequential pull request on branch
`phase6/0N-<slug>` titled `Phase 6.N: <imperative>`. A pull request must pass
its focused and required repository gates, pass every GitHub check, merge, and
leave clean local `main` equal to `origin/main` before the next item begins.

The plan below is the roadmap's seven work items, each widened where the
Phase 6 readiness review (2026-08-22) found the roadmap sentence thinner than
the repository requires. The widening is recorded in `decisions.md`.

## Standing constraints

- Every goal resolves to exactly one of the five persisted objective kinds
  (`full_text`, `continuation`, `section_reconstruction`,
  `before_after_transformation`, `structured_field`) and one of the four
  persisted row schemas. Phase 6 adds, renames, and drops none of them.
- Supervised instruction and conversation representations are admitted only
  where the source supplies both context and target; they are row-schema
  representations over the four supervised objectives, not a sixth objective.
- No invented question, answer, summary, or target. No automatic judgment that
  fine-tuning is the right solution. No trainer or consumer compatibility claim.
- Defaults and catalog text are versioned packaged data, never duplicated CLI,
  MCP, or Swift constants.
- Preview and preflight never mutate a workspace, call a renderer, or write a
  destination. The supervised region is derived from objective field roles and
  the taxonomy loss policy; it is not persisted.
- The seventh taxonomy axis (`input_family`) is additive to taxonomy v1 under
  an ADR; the contract version does not change.

## Checklist

### 6.1 Build the goal catalog

- [x] Create the standard Phase 6 packet, mark the phase `in_progress`, and
      reconcile every active record that still describes the Phase 5.7 pull
      request as unclaimed: `program.json` (Phase 5 `next_gate`), `WIP.md`,
      `docs/current-status.md`, `docs/product-contract.md` (including the
      stale "one split-JSONL container" sentence), `docs/README.md`,
      `README.md`, `docs/cli.md`, `docs/install.md`,
      `docs/governance/README.md`,
      `docs/governance/project-tracking.md`,
      `docs/governance/documentation-debt.md`,
      `docs/governance/health-report.md`, the program `README.md`,
      `CLAUDE.md`, and the Phase 5 packet's "not claimed" statements, citing
      PR #59 at `65cbd471e96d83f8dd65e2cda60e90f64a916e2b`.
- [x] Freeze `veriformis.goal-catalog/v1` as packaged versioned data
      (`src/veriformis/goals/catalog-v1.json`) loaded through strict Pydantic
      models: five goals, each bound to exactly one objective, its training
      family, its named recipe library id, its default representation, and its
      compatible representations; four representations, each bound to exactly
      one row schema and its loss policy; every goal/representation pair
      closed over the taxonomy compatibility matrix.
- [x] Give every goal plain-language fields that contain no machine
      identifier (any objective, row-schema, loss-policy, recipe, or alias
      identifier containing `_`, `-`, or `.`; bare English words such as
      `text` remain ordinary words) and no summary, answer, or translation
      claim: `title`, `plain_language`, `what_the_model_learns`,
      `what_you_provide`, and `not_this`.
- [x] Expose read-only discovery through `PipelineService.discover_goals`,
      CLI `goals`, MCP `goals`, and the Swift bridge `discoverGoals` with strict
      key-set, identifier, and closure validation; prove Python, CLI, and MCP
      emit byte-identical canonical JSON and freeze it as
      `tests/regressions/fixtures/phase6/goal-catalog.json` shared with
      Swift tests.
- [x] Bind the support registry (`training.implemented_goals`) and
      `scripts/check_project_tracking.py` to the catalog so a goal cannot be
      advertised without an implemented objective and recipe.
- [x] Publish `docs/contracts/goal-catalog-v1.md` and ADR-0007 (goal-first
      catalog and presets as versioned data over existing objectives); update
      `docs/cli.md`, `docs/architecture.md`, `docs/current-status.md`,
      `CLAUDE.md`, the support registry, and the evidence index.
- [x] Predeclare the usability criteria below before any preview or picker
      work begins.
- [x] Record focused, full, release, tracking, Mac, parity, lint, structured
      JSON, and diff evidence before claiming the item.

### 6.2 Define goal contracts and the input-family axis

- [x] Extend each catalog goal with `required_source_evidence`,
      `target_construction`, `supervision_boundary` (per representation, the
      loss policy and its plain-language boundary), `curation_defaults`,
      `review_policy`, `compatible_generic_exports` (derived from the
      production export catalog, so constrained CSV excludes `messages`), and
      `non_claims`.
- [x] Add the seventh taxonomy axis `input_family` under ADR-0008: versioned
      families over the existing parser kinds and declared suffixes
      (`plain-text`, `markdown`, `source-code`, `word-document`, `html`,
      `pdf-text`, `delimited-table`, `json-records`) with
      `ocr-image` recorded `explicitly_unsupported`; extend discovery, the Swift
      decoder, the support registry, and the tracking checker without changing
      the taxonomy contract version.
- [x] Bind each goal to its `eligible_input_families` and prove the binding
      against the existing parser and constructor diagnostics.
- [x] Extend `docs/contracts/goal-catalog-v1.md` and
      `docs/contracts/taxonomy-v1.md`; update the frozen discovery fixtures.

### 6.3 Add goal-specific preview

- [x] Add `PipelineService.preview_goal` over a workspace at or beyond the
      `construct` stage returning runtime-only `veriformis.goal-preview/v1`:
      for each selected record, the exact recovered source span(s) with
      offsets, derivation lineage (source, chunk, pass, constructor), context
      and target fields, the rendered row for the selected representation, the
      exact supervised character span(s) within that row with the loss policy
      and its plain-language boundary, and, when curation exists, every
      excluded record with its stable reason codes.
- [x] Bound the response exactly as the Phase 5.6 preview does (64 KiB per
      payload, 256 KiB response, whole-value omission with an exact reason,
      ASCII-safe transport).
- [x] Expose CLI `goal-preview`, MCP `goal_preview`, the Swift bridge, and a
      Mac preview screen that highlights context, target, and the supervised
      region in plain words.
- [x] Prove, for every objective and compatible representation, that the
      supervised span equals the serialized target exactly, that excluded
      records carry the curation reason codes, that the workspace is unchanged,
      and that Python, CLI, MCP, and the Mac bridge agree.

### 6.4 Add versioned recipe presets and the advanced editor

- [x] Freeze `veriformis.recipe-preset/v1` as packaged versioned data: one
      `safe` preset per goal carrying segmentation, construction parameters,
      representation, curation policy, split policy, and review policy.
- [x] Make the preset data the single source of every default consumed by
      CLI options, MCP tool defaults, `PipelineService`, the YAML runner, the
      recipe library, and the Swift workbench; delete the duplicated literals
      and add a test that fails when any surface reintroduces one.
- [x] Put the named recipe library on the execution path: `construct --goal
      GOAL [--preset PRESET]`, MCP `construct(goal=…)`, YAML
      `goal:`/`preset:`,
      and `PipelineService.construct` build the `DatasetRecipe` through the
      library; retire or wire `build_default_finished_plan`; unify the
      `balance_mode` spelling.
- [x] Add the advanced editor as explicit, schema-validated overrides over a
      preset (CLI flags, MCP fields, YAML keys, and a Mac disclosure group).
- [x] Replace the Mac workbench's hard-coded objective picker and copy with a
      catalog-driven goal picker whose titles, descriptions, presets, and
      defaults come from discovery.
- [x] Prove identical `recipe_id` for every goal/preset across Python, CLI,
      MCP, YAML, and the Mac argv plan; prove preset tampering fails closed.

### 6.5 Add compile preflight

- [ ] Add `PipelineService.preflight` over raw source paths plus a goal,
      representation, and preset, returning runtime-only
      `veriformis.compile-preflight/v1`: per-source input family and parser
      eligibility with the exact refusal reason, goal-by-family eligibility,
      incompatible selections (representation, consumer profile, preset
      override), missing evidence for the goal (boundary, heading structure,
      scalar field), expected exclusions with reason codes, and known
      limitations, without creating or mutating a workspace.
- [ ] Expose CLI `preflight`, MCP `preflight`, the Swift bridge, and a Mac
      preflight panel shown before compile.
- [ ] Prove every goal-by-family cell, every refusal reason, and that a source
      reported eligible compiles and a source reported ineligible is refused by
      the real stages on the same inputs.

### 6.6 Add the goal acceptance matrix

- [ ] Freeze a discovery-closed fixture
      (`tests/regressions/fixtures/phase6/goal-acceptance-matrix.json`) that
      compiles every goal across every eligible input family and every
      compatible representation from raw sources through `seal` and `verify`,
      pinning `recipe_id`, row-set and manifest digests, supervised
      boundaries, and exclusion reason codes.
- [ ] Close the coverage gaps the readiness review found:
      `section_reconstruction`,
      `before_after_transformation`, and `structured_field` sealed end to end;
      `instruction_output` and `messages` sealed end to end; `.docx` compiled;
      MCP parity asserting `recipe_id`; a Swift test that runs the real CLI and
      compares recipe and manifest digests.
- [ ] Prove identical identifiers and outputs across Python, CLI, MCP, YAML,
      and Mac for every matrix cell.

### 6.7 Validate truthfulness and close Phase 6

- [ ] Add per-goal static instruction templates to the catalog as the only
      default instruction literals, each stating exactly the source-derived
      task; admit an operator instruction only when it passes a deterministic,
      documented truthfulness check (names the goal's task; contains no claim
      vocabulary for transformations the goal does not perform).
- [ ] Prove `messages` user turns are exact context and `instruction_output`
      instructions never describe a summary, translation, answer, or other
      absent transformation, for every goal and representation.
- [ ] Judge the predeclared usability criteria with recorded evidence.
- [ ] Reconcile contracts, evidence, status, WIP, support registry, program
      ledger, ADRs, and documentation debt; write the closeout.

## Predeclared usability criteria

These are declared before any picker or preview is built so the exit gate is
judged against criteria fixed in advance, as the roadmap's usability layer
requires.

| ID | Criterion | How it is judged |
| --- | --- | --- |
| U1 | Plain-language selection | Every goal's `title`, `plain_language`, `what_the_model_learns`, `what_you_provide`, and `not_this` contain no machine identifier (any taxonomy or recipe identifier containing `_`, `-`, or `.`; bare English words such as `text` are permitted) and no summary, answer, or translation claim; a test enforces it. |
| U2 | Loss inspection | For every goal and compatible representation, the preview shows the exact supervised span, labeled in plain words, and a test proves the span equals the serialized target. |
| U3 | Surface identity | Every acceptance-matrix cell yields identical `recipe_id`, row-set and manifest digests, supervised boundaries, and exclusion reasons across Python, CLI, MCP, YAML, and the Mac bridge. |
| U4 | Visible non-claims | Every goal surfaces `not_this` and `non_claims` in discovery, the picker, and the preview. |
| U5 | Refusal before cost | Every incompatible selection and ineligible source is refused by preflight with an actionable reason before any workspace is created. |
| U6 | Scripted walkthrough | A documented non-developer walkthrough (pick goal → preflight → compile → preview → export) is executed through the Mac view model under XCTest and recorded as evidence at closeout. |

## Exit gate

A non-developer can select each supported goal from plain language and
inspect exactly what receives training loss; all surfaces resolve to the same
recipe identifiers and outputs.

**Result:** Pending.

## Non-goals

- Automatically deciding whether fine-tuning is the right solution.
- Inventing question/answer pairs, summaries, or any target the source does
  not supply.
- Adding an objective, row schema, training family, construction behavior,
  consumer profile, trainer claim, or generated text.
- Dataset quality intelligence (Phase 13), existing-dataset import (Phase 7),
  or the complete goal-first Mac workbench (Phase 18).
