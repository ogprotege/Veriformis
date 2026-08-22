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

## 2026-08-22 — Item 6.1 merged; item 6.2 started

**Status:** Item 6.1 merged as PR #60 at
`7316d94faf2d6c23b7abb6fe200f154da47d398c` after all 14 GitHub checks passed;
clean local `main` equals `origin/main` at that commit. Branch
`phase6/02-goal-contracts` was created from it.

One observation from the item 6.1 checks: the Phase 5.6 adapter test
`test_mcp_cancellation_race_preserves_visible_publication_outcome[False-ok]`
failed once on the `test (py3.12, ubuntu-latest)` push-trigger run and passed
on the identical pull-request-trigger cell and on re-run. That test gave a
worker thread one second to finish a real export execution before the
cancellation race; the failing runner took 185 seconds for the suite versus
about 70 locally. Item 6.1 did not touch that test or the export path. Item
6.2 widens the thread-event budget in that test
(`tests/exports/test_adapters.py`)
to thirty seconds as a declared test-robustness fix; the race remains ordered
by events, not time.

Item 6.2 scope: extend every catalog goal with `eligible_input_families`,
`required_source_evidence`, `required_evidence_diagnostics`,
`target_construction`, `supervision_boundary`, `curation_defaults`,
`review_policy_default`, `review_policy_options`, and closed `non_claims`;
bind each representation to `compatible_generic_exports`; add `input_family`
as the seventh taxonomy axis under ADR-0008 with suffix and parser closure
enforced by the tracking checker; update discovery, the Swift decoders, golden
fixtures, the support registry, and contracts.

**Next action:** Finish the 6.2 proofs (defaults equal every executing
surface, exports equal the production catalog, parsers supply exactly the
evidence each goal claims), run the complete admission gates, record
evidence, and publish the item 6.2 pull request.

## 2026-08-22 — Item 6.2 locally complete

**Status:** Local implementation and admission gates passed; pull-request
merge pending.

Every catalog goal now states its eligible input families, required source
evidence with the construction diagnostics that report it missing, target
construction, supervision boundary, curation defaults, review policy, and the
closed non-claim codes; every representation states its compatible generic
exports. `input_family` is the seventh taxonomy axis: eight implemented
recovery families partition the declared v1 suffixes and name their parser
kinds, `ocr-image` is explicitly unsupported, and discovery, the Swift
decoder and compile-view disclosure, the golden fixture, the support
registry, and the tracking checker changed in the same tree.

An independent adversarial review found one blocker: `source-code` had been
listed as eligible for the before/after goal, but cleaning never edits a code
block, so that family can never supply a recorded change; the proof test had
only checked that any block existed. The binding was corrected and the test
now runs cleaning and requires real edits. The review also showed that PDF
recovery emits synthetic `Page N` headings rather than document structure, so
`pdf-text` was removed from the section and structural-attribute goals under
the no-invented-target doctrine, with a test binding that exclusion to the
parser's labels. Five further should-fix items (universal
`source-chunks-unavailable`, `CurationDefaults` validated as an executable
`CurationPolicy`, the `balance_mode` spelling note, long lines, and the Mac
seventh-axis disclosure) were corrected and re-verified.

Observed gates on the reconciled working tree:

- 83 focused goal and taxonomy tests passed; 1,308 full Python tests passed
  with only the intentional durability-warning regression warning; 1,296
  standalone release tests passed with 1 deselected and the same warning.
- Clean-wheel installation and both golden compile/external-digest/transport
  flows passed; standalone CLI/workbench parity passed.
- The complete macOS XCTest target passed 72 tests with `TEST SUCCEEDED`.
- Project tracking (now binding input families and the suffix partition), its
  regression test, lock, Ruff, structured JSON, fixture byte equality, and
  diff checks passed.

**Next action:** Publish the item 6.2 pull request, require every GitHub
check to pass, merge, and synchronize clean local `main` with `origin/main`
before item 6.3 begins.

## 2026-08-22 — Item 6.2 merged; item 6.3 started

**Status:** Item 6.2 merged as PR #61 at
`81becfa676fd9111868b8d4b62549218a644d3e2` after all 14 GitHub checks passed
on the first run; clean local `main` equals `origin/main` at that commit.
Branch `phase6/03-goal-preview` was created from it.

Item 6.3 scope: `veriformis.goal-preview/v1`, a runtime-only read-only
response over a workspace at or beyond `construct`, through
`PipelineService.preview_goal`, CLI `goal-preview`, MCP `goal_preview`, the
Swift bridge, and a post-compile workbench preview screen. Per selected
record it carries derivation lineage, exact recovered evidence (source spans
or strict-IR scalars), context and target, the row rendered through the same
function `format` uses, the exact supervised span and loss policy, and the
curation decision; excluded records carry their reason codes. Bounds mirror
the Phase 5.6 export preview.

**Next action:** Finish the Swift bridge, decoder, and preview screen; run the
complete admission gates; record evidence; publish the item 6.3 pull request.

## 2026-08-22 — Item 6.3 locally complete

**Status:** Local implementation and admission gates passed; pull-request
merge pending.

`veriformis.goal-preview/v1` is implemented as a runtime-only, read-only
response over a workspace at or beyond `construct`, through
`PipelineService.preview_goal`, CLI `goal-preview`, MCP `goal_preview`, the
strict Swift bridge `previewGoal`, and a post-compile workbench preview
screen. Per selected record it carries derivation lineage, exact recovered
evidence (source spans or strict-IR scalars, each digest-bound to its
excerpt), context and target fields, the row rendered through the same
function `format` uses, the exact supervised span in Unicode code points with
its loss policy, the curation decision, and the goal's non-claims; excluded
records carry their reason codes. The response is assembled skeleton-first
and bounded on its exact ASCII transport at 64 KiB per record and 256 KiB per
response, failing closed with an exact reason when even the skeleton cannot
fit.

An independent adversarial review found one blocker: past the response
budget the first implementation kept appending redacted record skeletons and
never budgeted diagnostics, so a 320-source corpus produced a 350 KB response
under a 256 KiB claim. The assembly was rewritten skeleton-first with the
bound measured on the transport text and proved by a test over forty sources
under a reduced budget, including the fail-closed path. Seven should-fix
items were also corrected: a legacy revision-v1 workspace now fails closed
with the upgrade instruction instead of a `KeyError`; the representation is
resolved from the persisted recipe before any record is read; strict-IR
evidence digests are the SHA-256 of the exact excerpt; span units are stated
as Unicode code points on every surface; the preview carries `not_this` and
`non_claims` (U4); a stale workbench preview can no longer land after a new
run starts; and the rendered row is proved equal to the persisted product row
for the same record after `curate`, `split`, and `format`.

Observed gates on the reconciled working tree:

- 24 focused preview tests passed (13 goal-by-representation cells plus
  curation, instruction, omission, bound, duplicate-id, legacy-workspace,
  product-row equality, parity, and frozen-fixture proofs); 1,332 full Python
  tests passed with only the intentional durability-warning regression
  warning; 1,320 standalone release tests passed with 1 deselected and the
  same warning.
- Clean-wheel installation and both golden compile/external-digest/transport
  flows passed; standalone CLI/workbench parity passed.
- The complete macOS XCTest target passed 75 tests with `TEST SUCCEEDED`.
- Project tracking, its regression test, lock, Ruff, structured JSON, fixture
  byte equality, and diff checks passed.

**Next action:** Publish the item 6.3 pull request, require every GitHub
check to pass, merge, and synchronize clean local `main` with `origin/main`
before item 6.4 begins.
