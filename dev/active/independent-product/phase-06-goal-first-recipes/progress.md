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

## 2026-08-22 — Item 6.3 merged; item 6.4 started

**Status:** Item 6.3 merged as PR #62 at
`9cbab117e47cde6bd8850d67f0d363e03f0660ce` after all 14 GitHub checks passed
on the first run; clean local `main` equals `origin/main` at that commit.
Branch `phase6/04-recipe-presets` was created from it.

Item 6.4 scope: `veriformis.recipe-preset/v1` as packaged versioned data
holding the recipe-wide defaults and one safe preset per goal; one resolution
function used by the service, CLI, MCP, YAML runner, and recipe library so
every surface executes the same defaults and every selection path yields one
`recipe_id`; `--goal`, `--preset`, and `--representation` selection on
`chunk`, `construct`, and `curate` with explicit overrides only; the recipe
library on the execution path; `presets` discovery on CLI and MCP; a
catalog-driven workbench goal picker with an Advanced disclosure and no Swift
recipe constants; and a tracking gate that refuses recipe default literals.

**Next action:** Finish the workbench and tests, run the complete admission
gates, record evidence, and publish the item 6.4 pull request.

## 2026-08-22 — Item 6.4 locally complete

**Status:** Local implementation and admission gates passed; pull-request
merge pending.

`presets-v1.json` is the single versioned source of every recipe default and
of one safe preset per goal. `resolve_recipe_settings` is the only resolution
path: the service, CLI, MCP, YAML runner, and recipe library default every
setting parameter to `None` and resolve omitted values through the data, so a
goal, its safe preset, and its objective with equal overrides yield one
settings digest, one `recipe_id`, and one finished plan. `construct` builds
the recipe through the named recipe library; `construct --preset` fails closed
when the workspace chunks were not produced with the preset's segmentation.
The workbench discovers goals and presets at startup, offers a plain-language
goal picker with the goal's safe preset and a recipe-settings disclosure, and
passes only the selection and explicit overrides; it holds no recipe constant.
The tracking checker binds `implemented_presets` to the data and refuses a
recipe default literal in any surface source or the workbench. The workbench
parity script now exercises the goal-first sequence.

A defect-closure regression required that surfaces reject the persisted
`primary_source_cap` spelling; the resolver was narrowed to the documented
hyphenated spelling while the library keeps accepting the persisted value it
receives from resolved settings.

Observed gates on the reconciled working tree:

- 138 focused goal, preset, surface-identity, and defect-closure tests passed;
  1,371 full Python tests passed with only the intentional durability-warning
  regression warning; 1,359 standalone release tests passed with 1 deselected
  and the same warning.
- Clean-wheel installation and both golden compile/external-digest/transport
  flows passed; the goal-first standalone CLI/workbench parity passed.
- The complete macOS XCTest target passed 79 tests with `TEST SUCCEEDED`.
- Project tracking (presets and the literal gate), its regression test, lock,
  Ruff, structured JSON, fixture byte equality, and diff checks passed.
- The independent adversarial review found no blocker and proved recipe
  identity byte-for-byte against the pre-change construction for all five
  objectives; its seven should-fix items (CLI reference tables, YAML
  `recipe_library_id` conflict detection, review-policy consistency, the
  `unknown strategy` message, the workbench label, legacy re-run restore, a
  dead test block) were corrected and re-verified.

**Next action:** Publish the item 6.4 pull request, require every GitHub check
to pass, merge, and synchronize clean
local `main` with `origin/main` before item 6.5 begins.

## 2026-08-22 — Item 6.4 merged; item 6.5 started

**Status:** Item 6.4 merged as PR #63 at
`abdd630e25e83ebf346316319caec892f4d64886` after all 14 GitHub checks
passed; the pull request had no review threads and clean local `main` equaled
`origin/main` at that commit. Branch `phase6/05-compile-preflight` was created
from it.

Item 6.5 scope is the bounded runtime-only
`veriformis.compile-preflight/v1` response over raw source paths and one
goal/preset/representation selection. It must capture each file once, replay
the real parser, selected cleaning, preset segmentation, construction,
curation, and split logic entirely in memory, report per-source parser and
goal eligibility, exact missing-evidence diagnostics, expected exclusions,
coverage and split blockers, and create no workspace, renderer, or
destination. Python, CLI, MCP, and the Mac panel must agree exactly; the Mac
must rerun preflight immediately before creating a workspace.

The opening adversarial audit found a contract blocker in the existing real
construction path: synthetic PDF `Page N` headings could produce section and
structured-field records even though `pdf-text` is excluded for both goals.
Item 6.5 therefore adds one shared goal/input-family gate used by preflight and
real construction. The audit also requires the preflight probe to reach the
pure split calculation, because a one-leakage-group dataset can pass curation
and still fail the preset's required-evaluation policy.

**Next action:** Complete the shared family gate and one-capture in-memory
probe, expose the response through every surface, add the pre-workspace Mac
panel and the goal-by-family/refusal matrix, then run the complete admission
gates before publishing PR 6.5.

## 2026-08-22 — Item 6.5 locally complete

**Status:** Local implementation and admission gates passed; pull-request
merge pending.

`veriformis.compile-preflight/v1` is now the shared runtime-only admission
report over raw sources. One root-pinned capture feeds the production parser,
selected cleaning replay, preset segmentation, named construction, global
curation, and leakage-group split entirely in memory. The service, CLI, MCP,
Swift bridge, and workbench panel share the same closed response. The
workbench invalidates stale reports and reruns preflight immediately before it
may create a workspace, run sheet, or history entry. Real construction and
preflight use the same goal/input-family gate.

Observed gates on the reconciled working tree:

- 245 focused compile-preflight, matrix, pipeline, and recipe-surface tests
  passed; 1,593 full Python tests passed with only the intentional
  durability-warning regression warning.
- The standalone release run passed 1,581 tests with 1 deselected and the
  same warning; clean-wheel installation and both golden
  compile/external-digest/transport flows passed.
- The workbench parity script passed and the complete macOS XCTest target
  passed 93 tests with `TEST SUCCEEDED`.
- Project tracking, lock, Ruff, structured JSON, and diff checks passed.
- Independent consistency review passed after every concrete finding was
  corrected and rechecked, including root retarget refusal, alias-before-read,
  exact source identity/request binding, transport bounds and privacy, Swift
  locator parity, exhaustive refusal codes, and exact catalog non-claims.

**Next action:** Publish the item 6.5 pull request, require every GitHub check
to pass, merge, and synchronize clean local `main` with `origin/main` before
item 6.6 begins.

## 2026-08-22 — Item 6.5 merged; item 6.6 started

**Status:** Item 6.5 merged as PR #64 at
`b2e28b3dcfe48cd28ec74d8d8eaed12049f72d2d` after all 14 GitHub checks
passed; the pull request had no review threads and clean local `main` equaled
`origin/main` at that commit. Branch `phase6/06-goal-acceptance-matrix` was
created from it.

Item 6.6 owns the frozen discovery-closed acceptance fixture. Every catalog
goal must compile every eligible input family and compatible representation
from raw source through seal and external-digest verify, with `recipe_id`,
semantic row-set digest, manifest digest, supervised boundaries, and exclusion
codes pinned. Python, CLI, MCP, YAML, and the real Mac CLI bridge must agree for
every cell. The matrix also closes the explicit sealed-product gaps for
section reconstruction, recorded changes, structured values,
instruction/output, messages, and DOCX.

**Next action:** Build the deterministic raw-source matrix and frozen expected
fixture, add every surface and real-CLI proof, then run the complete admission
gates before publishing PR 6.6.

## 2026-08-22 — Item 6.6 locally complete

**Status:** Local implementation and admission gates passed; pull-request
publication and merge pending.

The canonical `veriformis.goal-acceptance-matrix/v1` fixture closes discovery
to 74 cells over 16 deterministic raw-source descriptors. Each cell uses two
distinct sources in one eligible family, retains the safe preset's required
evaluation policy, produces non-empty train and evaluation partitions, and
pins recipe, semantic row-set, manifest, supervision, and exact ordered
exclusion identities through external-digest verification. Plain-text source
A contains repeated and unique evidence, so seven cells prove real
`exact-duplicate` exclusions without violating finished-dataset source
coverage. NFC non-ASCII evidence exercises scalar handling. Python, CLI, MCP,
YAML, and the real Mac CLI bridge agree for every cell.

Observed gates on the reconciled working tree:

- The complete Python/CLI/MCP/YAML matrix passed 297 tests in 266.23 seconds;
  `tests/goals` passed 353 tests in 22.77 seconds.
- Full Python passed 1,890 tests in 418.50 seconds with only the intentional
  durability-warning regression warning.
- The standalone release selection passed 1,878 tests with 1 deselected and
  the same warning in 419.06 seconds; `check_local.sh` then passed its clean
  wheel, both golden compiles, external-digest, and transport gates.
- The parity script passed with identical bundle/file identities. The complete
  macOS XCTest target passed 97 tests with no failures in 332.436 seconds.
- Project tracking and its regression, lock, Ruff, all structured JSON,
  byte-identical fixture regeneration, fixture SHA-256
  `60be61c2c4bf67313f68eb527e5ba5ca1d0cb138f9beb8637a47219596cc2a86`,
  and diff checks passed.
- The final independent adversarial audit found no remaining implementation,
  U3, code, fixture, Swift, or contract blocker or should-fix.

**Next action:** Publish the item 6.6 pull request, require every GitHub check
to pass, merge, and synchronize clean local `main` with `origin/main` before
item 6.7 begins.

## 2026-08-22 — Item 6.6 merged; item 6.7 started

**Status:** Item 6.6 merged as PR #65 at
`7b93a32a5a9b18e5bc9c032750f467c4d9c43ea5` after all 14 GitHub checks
passed; clean local `main` equals `origin/main` at that commit. Branch
`cursor/phase6-07-truthfulness-closeout-38f4` was created from it.

Item 6.7 scope: per-goal static instruction templates as the only default
instruction literals; a deterministic truthfulness check that admits an
operator instruction only when it names the goal's task and contains no
claim vocabulary for a transformation the goal does not perform; proofs that
`messages` user turns are exact context and `instruction_output` instructions
never claim summary, translation, answer, or another absent transformation;
judgment of predeclared usability criteria U1–U6; and the Phase 6 closeout
reconciliation.

**Next action:** Finish the resolver, surface wiring, and U1–U6 proofs; run
the complete admission gates; write the closeout; publish the item 6.7 pull
request.

## 2026-08-22 — Item 6.7 locally complete

**Status:** Local implementation and admission gates passed; pull-request
publication and merge pending.

Every catalog goal now carries `instruction_template` and a unique
`instruction_task`. The four supervised templates are byte-identical to the
instruction literals already pinned by the 6.6 acceptance matrix. Omitted
instructions on `instruction-and-output` resolve to the template through
`resolve_operator_instruction`; empty or surrounding-whitespace text fails
as `instruction-required`; a supplied instruction that lacks the task phrase
or contains `summar`, `answer`, or `translat` fails as
`instruction-untruthful`; an instruction on any other representation fails
as `instruction-not-applicable`. `curate`, preflight, preview, CLI, MCP, the
YAML runner, and the Mac bridge share that function. `messages` user turns
remain the exact context field. Preflight no longer reports that
truthfulness is pending.

Usability criteria: U1 is enforced on catalog plain language and the new
instruction fields; U2 remains the 6.3 preview span proofs; U3 remains the
6.6 matrix; U4 is discovery `not_this` / `non_claims` plus preview carriage;
U5 refuses ineligible families and untruthful instructions before a
workspace exists; U6 is the documented pick → preflight → compile → preview
→ export walkthrough, executed through `PipelineService` and through the Mac
view-model compile/preflight argument projection.

This Linux cloud VM cannot run XCTest or the Mac parity script; those gates
are recorded as exercised by the macOS GitHub check. Observed Python gates:
373 focused goal tests passed; standalone release passed 1,898 with 1
deselected; the only full-suite first-run failure was the matrix catalog
digest, corrected by pinning `catalog_sha256` to the new catalog bytes.

**Next action:** Publish the item 6.7 pull request, require every GitHub
check to pass, merge, and synchronize clean local `main` with `origin/main`.
Phase 6 then ends; Phase 7 may begin under its own packet.
