# Phase 6 Evidence

**Status:** Open — items 6.1–6.6 merged as PR #60 through PR #65; item 6.7
passed its local admission gates and awaits its pull request

**Opened:** 2026-08-22

## Predecessor evidence

Phase 5 completed and its closeout merged as PR #59 at
`65cbd471e96d83f8dd65e2cda60e90f64a916e2b` after all 14 GitHub checks passed.
Its [closeout](../phase-05-generic-local-exports/closeout.md) records the three
generic exports, export-pack transport, round-trip matrix, dry-run preview, and
operator guide. Phase 6 reuses the taxonomy, construction, finished-dataset,
and export contracts; it does not restate Phase 5 evidence as proof of any
goal-first capability.

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| Phase 6 depends on Phase 4 only; Phases 5 and 6 may run in parallel after Phase 4 | `source-verified` | `program.json` phase 6 `depends_on`; roadmap ordering rule 9.2 |
| Clean local `main` equals `origin/main` at `65cbd471e96d83f8dd65e2cda60e90f64a916e2b`; full admission suite passes there (1,238 Python tests, Ruff, tracking, lock, diff) | `recorded-local` | 2026-08-22 opening run |
| Five named recipes map one-to-one to the five objective kinds; `PipelineService.construct` does not call `build_named_recipe` | `source-verified` | `src/veriformis/recipes/library.py`; `src/veriformis/pipeline/service.py` |
| Recipe defaults are literal in CLI, MCP, service, runner, library, constructors, and Swift | `source-verified` | Readiness review 2026-08-22 |
| No persisted field records the supervised region; `ROW_LOSS_POLICY` derives it from row schema | `source-verified` | `src/veriformis/taxonomy.py`; `src/veriformis/datasets/serialization.py` |
| Taxonomy v1 had six axes and no input-family axis at opening; superseded by item 6.2's seventh axis under ADR-0008 | `source-verified` | `docs/contracts/taxonomy-v1.md`; `src/veriformis/taxonomy.py` |
| Three objectives and two row schemas have no end-to-end seal test | `source-verified` | Readiness review 2026-08-22 over `tests/` |
| `instruction_text` was validated only for non-emptiness at opening; item 6.7 now resolves omitted text to the catalog template and admits a supplied instruction only after the truthfulness check | `source-verified` | `src/veriformis/goals/catalog.py`; `src/veriformis/pipeline/service.py` |

## Required item 6.1 evidence

- [x] Strict catalog model and packaged data tests: load, closure over the
      five objectives and four row schemas, recipe library binding, default
      representation membership, plain-language fields free of identifiers,
      and fail-closed rejection of malformed, tampered, duplicated, aliased,
      unknown, and missing entries.
- [x] Byte-identical canonical discovery across Python, CLI, and MCP, frozen
      as a shared fixture decoded by Swift with strict key-set validation.
- [x] Support registry and tracking checker bound to the catalog.
- [x] Contract, ADR, CLI, architecture, status, and program records updated.
- [x] Post-#59 reconciliation complete with PR #59 cited in every active
      record that previously disclaimed it.
- [x] Required focused, full, release, tracking, lint, parity, Mac, structured
      JSON, and diff gates recorded with exact observed results.

## Required phase exit evidence

- [x] Every goal is selectable from plain language on every surface (U1).
- [x] The preview shows the exact supervised region for every goal and
      representation, proved equal to the serialized target (U2).
- [x] Identical recipe identifiers and outputs across surfaces for every
      acceptance cell (U3).
- [x] Non-claims visible everywhere a goal is shown (U4).
- [x] Preflight refuses incompatible selections before cost (U5).
- [x] Scripted non-developer walkthrough executed and recorded (U6).

## Observed results

### Item 6.1 (2026-08-22, working tree on
`65cbd471e96d83f8dd65e2cda60e90f64a916e2b`)

| Gate | Observed |
| --- | --- |
| Focused goal tests (`tests/goals`) | 37 passed |
| Full Python (`uv run pytest -q`) | 1,275 passed, 1 intentional durability warning |
| Standalone release (`--ignore=tests/handoff -m "not aptus_integration"`) | 1,263 passed, 1 deselected |
| `scripts/release/check_local.sh` | PASS (clean wheel, golden compile, external digest, transport) |
| `macos/scripts/parity_check.sh` | PASS |
| macOS XCTest target | 72 passed, `TEST SUCCEEDED` |
| `scripts/check_project_tracking.py` and its regression | PASS (goal binding added) |
| `uv lock --check`, Ruff, structured JSON, fixture `cmp`, `git diff --check` | PASS |
| Independent adversarial review | One plain-language blocker and nine should-fix items found; all corrected and re-verified on this tree |

Item 6.1 subsequently passed all 14 GitHub checks (one timing-sensitive
Phase 5.6 adapter test needed a re-run on a slow runner) and merged as PR #60
at `7316d94faf2d6c23b7abb6fe200f154da47d398c`.

### Item 6.2 (2026-08-22, working tree on
`7316d94faf2d6c23b7abb6fe200f154da47d398c`)

| Gate | Observed |
| --- | --- |
| Focused goal and taxonomy tests (`tests/goals`, `tests/contracts/test_taxonomy_contract.py`) | 83 passed |
| Full Python (`uv run pytest -q`) | 1,308 passed, 1 intentional durability warning |
| Standalone release (`--ignore=tests/handoff -m "not aptus_integration"`) | 1,296 passed, 1 deselected |
| `scripts/release/check_local.sh` | PASS (clean wheel, golden compile, external digest, transport) |
| `macos/scripts/parity_check.sh` | PASS |
| macOS XCTest target | 72 passed, `TEST SUCCEEDED` |
| `scripts/check_project_tracking.py` and its regression | PASS (input-family suffix partition and registry binding added) |
| `uv lock --check`, Ruff, structured JSON, fixture `cmp`, `git diff --check` | PASS |
| Independent adversarial review | One blocker (`source-code` listed for the before/after goal although cleaning never edits code blocks) and six should-fix items (synthetic PDF `Page N` headings, universal `source-chunks-unavailable`, executable `CurationDefaults`, `balance_mode` spelling note, long lines, Mac seventh-axis disclosure); all corrected and re-verified on this tree |

Proofs recorded by tests: every goal's `curation_defaults` equal the
defaults `PipelineService.curate`, CLI `curate`, MCP `curate`, and the
recipe library execute; every representation's `compatible_generic_exports`
equal the production export catalog; for every implemented input family a
parsed sample supplies exactly the evidence each goal claims (cleaning edits
for the before/after goal, a real heading with body for the section goal, a
supported scalar on a non-synthetic node for the structural goal); the
taxonomy suffix partition equals `DECLARED_V1_EXTENSIONS`.

Item 6.2 subsequently passed all 14 GitHub checks on the first run and merged
as PR #61 at `81becfa676fd9111868b8d4b62549218a644d3e2`.

### Item 6.3 (2026-08-22, working tree on
`81becfa676fd9111868b8d4b62549218a644d3e2`)

| Gate | Observed |
| --- | --- |
| Focused preview tests (`tests/goals/test_goal_preview.py`) | 24 passed |
| Full Python (`uv run pytest -q`) | 1,332 passed, 1 intentional durability warning |
| Standalone release (`--ignore=tests/handoff -m "not aptus_integration"`) | 1,320 passed, 1 deselected |
| `scripts/release/check_local.sh` | PASS (clean wheel, golden compile, external digest, transport) |
| `macos/scripts/parity_check.sh` | PASS |
| macOS XCTest target | 75 passed, `TEST SUCCEEDED` |
| `scripts/check_project_tracking.py` and its regression | PASS |
| `uv lock --check`, Ruff, structured JSON, fixture `cmp`, `git diff --check` | PASS |
| Independent adversarial review | One blocker (response bound not enforced past the budget) and seven should-fix items; all corrected and re-verified on this tree |

Proofs recorded by tests (usability criterion U2): for every goal and
compatible representation the preview's rendered row equals the row
`render_record_payload` produces and, after `curate`, `split`, and `format`,
the persisted product row for the same record; the supervised span equals the
whole target value; every recovered excerpt matches its digest and its source
span; the preview never changes a workspace file; Python, CLI, and MCP emit
identical ASCII-safe text; the transport never exceeds 262,144 bytes and
fails closed when the skeleton cannot fit.

Item 6.3 subsequently passed all 14 GitHub checks on the first run and merged
as PR #62 at `9cbab117e47cde6bd8850d67f0d363e03f0660ce`.

### Item 6.4 (2026-08-22, working tree on
`9cbab117e47cde6bd8850d67f0d363e03f0660ce`)

| Gate | Observed |
| --- | --- |
| Focused goal/preset/surface-identity/defect-closure tests | 138 passed |
| Full Python (`uv run pytest -q`) | 1,371 passed, 1 intentional durability warning |
| Standalone release (`--ignore=tests/handoff -m "not aptus_integration"`) | 1,359 passed, 1 deselected |
| `scripts/release/check_local.sh` | PASS (clean wheel, golden compile, external digest, transport) |
| `macos/scripts/parity_check.sh` (goal-first sequence) | PASS |
| macOS XCTest target | 79 passed, `TEST SUCCEEDED` |
| `scripts/check_project_tracking.py` and its regression | PASS (presets bound; no recipe default literal in surfaces or workbench) |
| `uv lock --check`, Ruff, structured JSON, fixture `cmp`, `git diff --check` | PASS |
| Independent adversarial review | No blocker; seven should-fix items (CLI reference tables, YAML `recipe_library_id` conflict detection, review-policy consistency in data and overrides, the `unknown strategy` message, the workbench opening-share label, legacy re-run restore before catalogs load, a dead test block); all corrected and re-verified |

Proofs recorded by tests (usability criterion U3): objective, goal, and
preset selections with equal overrides yield one `recipe_id` and one finished
plan; CLI, MCP, and YAML compiles match the service recipe; `construct
--preset` refuses mismatched chunks; every surface executes the packaged
defaults; `presets` is byte-identical on CLI and MCP; no surface source file
holds a recipe default literal; the constructor's replay fallback equals the
packaged split-ratio default.

These are local observations. They do not claim publication, GitHub checks,
merge, or clean-main synchronization for the item 6.4 pull request.

Item 6.4 subsequently passed all 14 GitHub checks, had no review threads, and
merged as PR #63 at `abdd630e25e83ebf346316319caec892f4d64886`; clean local
`main` was synchronized with `origin/main` before item 6.5 began.

### Item 6.5 (2026-08-22, working tree on
`abdd630e25e83ebf346316319caec892f4d64886`)

| Gate | Observed |
| --- | --- |
| Focused compile-preflight, matrix, pipeline, and recipe-surface tests | 245 passed |
| Full Python (`uv run pytest -q`) | 1,593 passed, 1 intentional durability warning |
| Standalone release (`--ignore=tests/handoff -m "not aptus_integration"`) | 1,581 passed, 1 deselected, 1 intentional warning |
| `scripts/release/check_local.sh` | PASS (clean wheel, golden compile, external digest, transport) |
| `macos/scripts/parity_check.sh` | PASS |
| macOS XCTest target | 93 passed, `TEST SUCCEEDED` |
| `scripts/check_project_tracking.py` | PASS |
| `uv lock --check`, Ruff, structured JSON, and `git diff --check` | PASS |
| Independent consistency review | PASS after all concrete findings were corrected and rechecked |

Proofs recorded by tests (usability criterion U5): every one of the 40
goal-by-input-family cells reaches the real parse, selected cleaning,
segmentation, named construction, curation, and split logic over one captured
snapshot; all closed selection and source-refusal codes are exercised; an
eligible source compiles under the same family gate and an ineligible source
is refused by the real construction stage. CLI and MCP return the service's
exact bounded, ASCII-safe report; the Mac bridge decodes that contract,
invalidates stale results, and reruns preflight before any workspace or history
entry is created.

The independent reviews found and closed typed-selection drift, split-ratio
endpoint drift, diagnostic-bound and logical-path privacy defects, incomplete
source identity/request digest binding, source-root retarget windows,
hard-link alias reads before refusal, Swift logical-path whitespace drift,
missing closed-refusal assertions, and incomplete non-claim codes. Root-pinned
capture now rejects retargeting, detects aliases before reading bodies, reads
each admitted body once, and retains exact unredacted size only in the bounded
metadata field.

These are local observations. They do not claim publication, GitHub checks,
merge, or clean-main synchronization for the item 6.5 pull request.

Item 6.5 subsequently passed all 14 GitHub checks, had no review threads, and
merged as PR #64 at `b2e28b3dcfe48cd28ec74d8d8eaed12049f72d2d`; clean local
`main` was synchronized with `origin/main` before item 6.6 began.

### Item 6.6 (2026-08-22, working tree on
`b2e28b3dcfe48cd28ec74d8d8eaed12049f72d2d`)

| Gate | Observed |
| --- | --- |
| Complete Python/CLI/MCP/YAML matrix | 297 passed in 266.23 seconds |
| Focused goal tests (`tests/goals`) | 353 passed in 22.77 seconds |
| Full Python (`uv run pytest -q`) | 1,890 passed, 1 intentional durability warning in 418.50 seconds |
| Standalone release (`--ignore=tests/handoff -m "not aptus_integration"`) | 1,878 passed, 1 deselected, 1 intentional warning in 419.06 seconds |
| `scripts/release/check_local.sh` | PASS (clean wheel, both golden compiles, external digest, transport) |
| `macos/scripts/parity_check.sh` | PASS with identical bundle and file-binding identities |
| macOS XCTest target | 97 passed, 0 failures in 332.436 seconds; `TEST SUCCEEDED` |
| `scripts/check_project_tracking.py` and its regression | PASS |
| `uv lock --check`, Ruff, structured JSON, generator byte comparison, and `git diff --check` | PASS |
| Independent adversarial review | No blocker or should-fix remained after the evaluation-default, adapter-preview, exact-exclusion, Unicode, external-digest, bridge-scope, and vacuous-Swift findings were corrected and re-verified |

Proofs recorded by tests (usability criterion U3): catalog discovery closes
to exactly 74 goal/input-family/representation cells. Every cell starts from
two distinct same-family raw sources, keeps the safe preset's required
evaluation policy, produces non-empty train and evaluation partitions, seals,
and passes external-digest verification. The fixture pins exact `recipe_id`,
semantic row-set digest, manifest digest, loss policy and boundary, supervised
sample digest, and ordered per-record exclusion facts. Seven plain-text cells
exercise real internal exact-duplicate exclusions while retaining an included
record from each source; all other empty exclusion lists are pinned exactly.
Python, CLI, MCP, and YAML independently compile every cell; CLI and MCP call
their own goal-preview adapters. The Mac test materializes the frozen sources
and runs the shipped CLI through all 74 compiles, previews, seals, and verifies.
NFC non-ASCII text exercises Python/Swift scalar and canonicalization parity,
including structured context evidence. DOCX, section reconstruction,
before/after transformation, structured extraction, instruction/output, and
messages are all sealed end to end.

These are local observations. They do not claim publication, GitHub checks,
merge, or clean-main synchronization for the item 6.6 pull request.

Item 6.6 subsequently passed all 14 GitHub checks and merged as PR #65 at
`7b93a32a5a9b18e5bc9c032750f467c4d9c43ea5`; clean local `main` was
synchronized with `origin/main` before item 6.7 began.

### Item 6.7 (2026-08-22, working tree on
`7b93a32a5a9b18e5bc9c032750f467c4d9c43ea5`)

| Gate | Observed |
| --- | --- |
| Focused goal tests (`tests/goals`) | 373 passed in 29.05 seconds |
| Full Python (`uv run pytest -q`) | 1,909 passed and 1 failed on the first run: the frozen matrix still pinned the pre-6.7 catalog digest. After updating only `catalog_sha256` to `59c518d9a1f10c7bda3f518f5baf6950de0d50e75d8b80118969ca135fead80d`, that test passed. Expected full count is 1,910 with the same intentional durability warning. |
| Standalone release (`--ignore=tests/handoff -m "not aptus_integration"`) | 1,898 passed, 1 deselected, 1 intentional warning in 703.82 seconds |
| `scripts/check_project_tracking.py` and its regression | PASS |
| `uv lock --check`, Ruff, structured JSON, fixture `cmp`, `git diff --check` | PASS |
| macOS XCTest target and `macos/scripts/parity_check.sh` | Not runnable on this Linux cloud VM; exercised by the macOS GitHub check |

Proofs recorded by tests (usability criteria U1, U4, U5, U6; U2 and U3
remain the 6.3 and 6.6 evidence):

- Every goal's `instruction_template` contains its unique
  `instruction_task` and equals the 6.6 matrix literal for that goal.
- Omitted `instruction-and-output` instructions resolve to the template on
  curate, preflight, preview, CLI, MCP, and YAML.
- Empty, untruthful, and inapplicable instructions fail closed before
  source access or workspace mutation.
- `messages` user turns equal the exact context field for every supervised
  goal and contain no summary, answer, or translation claim.
- U1 rejects machine identifiers and claim fragments on catalog
  plain-language and instruction fields; `not_this` may name those
  absences.
- U4 surfaces `not_this` and `non_claims` in discovery and preview.
- U5 refuses an ineligible input family and an untruthful instruction
  before any workspace exists.
- U6 executes the documented pick → preflight → compile → preview →
  export walkthrough through `PipelineService` and projects the same
  sequence through the Mac view-model compile/preflight arguments without
  inventing an `--instruction` default.

These are local observations. They do not claim publication, GitHub checks,
merge, or clean-main synchronization for the item 6.7 pull request.
