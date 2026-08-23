# Phase 6 Closeout

**Status:** Complete locally; item 6.7 pull request pending

**Last reviewed:** 2026-08-22

## Exit-gate judgment

Passed on the current tree. A non-developer can select each supported goal from
plain language and inspect exactly what receives training loss; Python, CLI,
MCP, YAML, and the real Mac CLI bridge resolve to the same recipe identifiers
and outputs. Items 6.1–6.6 are admitted and merged through PR #65 at
`7b93a32a5a9b18e5bc9c032750f467c4d9c43ea5`. Item 6.7's catalog-default
instruction truthfulness, visible non-claims, and scripted walkthrough passed
the required current-tree matrix and Mac runtime suite. U1–U6 are judged
satisfied below. This closeout does not claim GitHub checks, merge, or
clean-main synchronization for the item 6.7 pull request.

## Delivered scope

- Five plain-language goals closed over the existing objectives, row schemas,
  recipes, and loss policies.
- Source-evidence and input-family contracts, bounded goal preview, versioned
  safe presets, compile preflight, and the 74-cell acceptance fixture.
- Item 6.7: catalog-default instructions, deterministic operator truthfulness,
  visible non-claims, typed workbench export delegates, and the scripted
  walkthrough XCTest.
- ADR-0009 and reconciled contracts preserve goal-first default resolution
  while leaving the exact persisted plan literal, serializer, verifier, rows,
  and bundles unchanged.

## Usability judgment

| ID | Result | Evidence |
| --- | --- | --- |
| U1 | Pass | Catalog plain-language fields remain identifier-free and free of summary, answer, and translation claims; `tests/goals/test_goal_catalog.py` enforces it. |
| U2 | Pass | Preview supervised spans equal serialized targets for every goal and compatible representation; retained from item 6.3 and re-checked by the current-tree matrix and preview tests. |
| U3 | Pass | Complete current-tree matrix: 297 Python/CLI/MCP/YAML cases passed in 284.56 seconds. Every frozen cell still pins `recipe_id`, row-set digest, manifest digest, supervision, and exclusions. Instruction overrides remain omitted so catalog defaults execute. |
| U4 | Pass | Discovery, picker, and preview share `not_this` and closed `non_claims`. `testGoalDisclosurePresentationIncludesNotThisAndClosedNonClaims` passed. |
| U5 | Pass | Preflight refuses incompatible selections and untruthful instructions before source capture; retained from item 6.5 and extended by instruction-digest binding. |
| U6 | Pass | `testNonDeveloperGoalWalkthroughPickPreflightCompilePreviewExportWithRealRepoCLI` passed in 4.655 seconds on the current tree. Complete macOS XCTest target: 102 passed, 0 failures, `TEST SUCCEEDED`. |

## Verification summary

- Focused goal tests (`tests/goals`): 481 passed in 14.23 seconds.
- Focused 6.7 instruction/catalog/preflight/preview/surface files: 231 passed
  in 6.77 seconds.
- Complete Python/CLI/MCP/YAML matrix: 297 passed in 284.56 seconds.
- Standalone release (`--ignore=tests/handoff -m "not aptus_integration"`):
  2,006 passed, 1 deselected, 1 intentional durability warning in 340.84
  seconds.
- macOS XCTest target: 102 passed, 0 failures in 272.147 seconds;
  `TEST SUCCEEDED`. All five item 6.7 tests passed.
- `macos/scripts/parity_check.sh`: PASS with identical bundle and file-binding
  identities.
- Project tracking and its regression, lock, Ruff, structured JSON, catalog
  fixture `cmp`, and `git diff --check`: PASS.
- `scripts/release/check_local.sh`: PASS (clean wheel, both golden compiles,
  external digest, transport).

These are local observations on the item 6.7 working tree based on PR #65's
merge commit `7b93a32a5a9b18e5bc9c032750f467c4d9c43ea5`. They do not claim
publication, GitHub checks, merge, or clean-main synchronization.

## Exclusions and remaining constraints

- Do not begin Phase 7 until the item 6.7 pull request is green, merged, and
  clean local `main` equals `origin/main`.
- No objective, row schema, persisted schema, serializer/verifier meaning,
  consumer profile, trainer claim, generated text, or invented target is added.
- Existing-dataset import remains Phase 7. The complete goal-first Mac
  workbench remains Phase 18.
- Generic exports still claim compatibility with no trainer.
