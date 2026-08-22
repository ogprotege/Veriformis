# Phase 6 Progress Log

This file is append-only by dated entry. Corrections are recorded in later
entries rather than deleting earlier history.

## 2026-08-22 — Phase 6 started

**Status:** In progress

**Predecessor:** Phase 5 completed and its closeout merged as PR #59 at
`65cbd471e96d83f8dd65e2cda60e90f64a916e2b` after all 14 GitHub checks passed.
The Phase 6.1 branch `phase6/01-goal-catalog` was created from clean local
`main` equal to `origin/main` at that commit.

**Starting facts reviewed:**

- Five named recipes exist in `veriformis.recipes.library`, but
  `PipelineService.construct` does not build recipes through that library, and
  `recipe_id` is derived from `DatasetRecipe` fields rather than a library id.
- Recipe and stage defaults are repeated as literals in the CLI, MCP server,
  pipeline service, YAML runner, recipe library, constructors, and the Swift
  workbench.
- No persisted field records the supervised region; it is derived from the
  row schema through the taxonomy loss policy at export time.
- The taxonomy has six axes and no input-family axis; input support is
  expressed as declared suffixes and parser kinds.
- `section_reconstruction`, `before_after_transformation`, and
  `structured_field` have no end-to-end parse-to-seal test; neither do the
  `instruction_output` and `messages` row schemas.
- `instruction_text` is a caller-supplied literal validated only for
  non-emptiness; no template or truthfulness check exists.
- The Mac workbench exposes only an objective picker, a continuation split
  ratio, and an allow-empty-evaluation toggle; its compile parity evidence is
  argument-shape only.
- Roughly twenty active records still describe the Phase 5.7 pull request as
  unclaimed because they were authored inside that pull request.

**Decisions pinned at opening:** the Mac workbench receives a goal picker,
preflight panel, and preview screen in this phase; `input_family` becomes the
seventh taxonomy axis; the supervised region is derived, not persisted. See
`decisions.md`.

**Next action:** Complete item 6.1 by reconciling the post-#59 records,
freezing the goal catalog as packaged versioned data, exposing read-only
discovery on every surface, binding the support registry and tracking checker,
publishing the contract and ADR, and recording the required local evidence
before publishing the item 6.1 pull request.

## 2026-08-22 — Item 6.1 locally complete

**Status:** Local implementation and admission gates passed; pull-request
merge pending.

The packaged `veriformis.goal-catalog/v1` data
(`src/veriformis/goals/catalog-v1.json`) now binds five plain-language goals
one-to-one to the five persisted objective kinds and their named recipes, and
four representations one-to-one to the four persisted row schemas and their
taxonomy loss policies. Strict models reject non-canonical bytes, duplicate
JSON keys, unknown keys, malformed identifiers, control characters, machine
identifiers or summary/answer/translation claims in plain-language text,
non-integer contract versions, duplicate or missing objectives, and any
default or compatibility set that drifts from the taxonomy matrix.
`PipelineService.discover_goals`, CLI `goals`, and MCP `goals` emit the exact
packaged text; the Swift bridge `discoverGoals` decodes the shared frozen
fixture strictly. The support registry records `training.implemented_goals`
and the tracking checker binds it to the catalog and recipe library.

Post-#59 reconciliation cited PR #59 at
`65cbd471e96d83f8dd65e2cda60e90f64a916e2b` across the program ledger, WIP,
current status, product contract (including the stale single-container
sentence), documentation index, README, CLI and install guides, governance
records, the Phase 5 packet's forward-looking statements, and the evidence
index. The Goal Catalog Contract v1 and ADR-0007 were published, and the
usability criteria U1–U6 were predeclared in `plan.md`.

An independent adversarial review found one blocker: the structural-attribute
goal's plain language had promised record fields and document titles that the
`structured_field` constructor never produces. The copy was rewritten to name
exactly the recovered attributes the constructor selects and to state that
plain text, JSON, and CSV yield nothing for this goal. Nine should-fix items
(strict integer version, identifier grammar, control characters, claim
vocabulary on representations, a test that passed for the wrong reason, a
stale command count, missing module-list entries, MCP trailing-newline parity,
and U1 wording) were corrected and re-verified.

Observed gates on the reconciled working tree:

- 37 focused goal tests passed; 1,275 full Python tests passed with only the
  intentional durability-warning regression warning; 1,263 standalone release
  tests passed with 1 deselected and the same warning.
- Clean-wheel installation and both golden compile/external-digest/transport
  flows passed; standalone CLI/workbench parity passed.
- The complete macOS XCTest target passed 72 tests with `TEST SUCCEEDED`.
- Project tracking (now binding goals), its regression test, lock, Ruff,
  structured JSON, fixture byte equality, and diff checks passed.

**Next action:** Publish the item 6.1 pull request, require every GitHub
check to pass, merge, and synchronize clean local `main` with `origin/main`
before item 6.2 begins.
