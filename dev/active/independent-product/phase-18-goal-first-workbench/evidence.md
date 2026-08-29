# Phase 18 Evidence

**Status:** Open

**Opened:** 2026-08-28

## Predecessor evidence

Phase 17 completed. Closeout merged as PR #159 at
`7d851c8a531eac7217051effe000048403a3b866`. At Phase 18 open, clean local
`main`, `origin/main`, and `HEAD` were equal at that commit. Dependencies 6,
7, 8, 9, 10, 13, 14, and 15 were complete in `program.json`. Phases 16 and 17
were also complete.

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| Sidebar destinations remain home, compile, history, settings | `source-verified` | `macos/Sources/Models/WorkbenchModels.swift` |
| Compile plan is parse → clean → chunk → construct → curate → split → format → validate → seal | `source-verified` | `macos/Sources/Services/VeriformisCLI.swift` |
| Compile plan has no `--mode` and no `dataset-row` | `source-verified` | `macos/Sources/Services/VeriformisCLI.swift` |
| `mapping-detect` and export discover/dry-run/execute exist on the CLI bridge | `source-verified` | `macos/Sources/Services/VeriformisCLI.swift` |
| Views and the view model do not call mapping-detect, export, or review packets | `source-verified` | `macos/Sources/Views`; `WorkbenchViewModel.swift` |
| Default workbench Aptus handoff is false | `source-verified` | `macos/Sources/ViewModels/WorkbenchViewModel.swift` |
| No `GeneratorPass` under `src/veriformis` or `macos/Sources` | `source-verified` | package and workbench sources |
| ADR-0017 Decision A and ADR-0018 Decision A still hold | `source-verified` | `docs/adr/0017-no-untrusted-extension-loader.md`; `docs/adr/0018-no-compile-path-generator.md` |
| Quality gates remain preview-only | `source-verified` | `src/veriformis/quality/gates.py` |

## Required item 18.1 evidence

- [x] Standard packet opened from the Phase 17 closeout merge.
- [x] Phase 18 moved from `planned` to `in_progress` with this packet path.
- [x] L1 through L15 recorded.
- [x] Active tracking documents reconciled to Phase 18 in progress without
      claiming Review, Exports, or dataset-row execute.
- [x] Baseline isolation tests added.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 18.2.

## Item 18.2 source-verified facts

| Fact | Grade | Source |
| --- | --- | --- |
| ADR-0019 Decision A: Swift is a process adapter | `source-verified` | `docs/adr/0019-thin-workbench-adapter.md` |
| `veriformis.workbench-adapter/v1` is a schema pin | `source-verified` | `docs/contracts/workbench-adapter-v1.md`; `src/veriformis/workbench/adapter.py` |
| Loading a pin is not a screen execute | `source-verified` | `tests/workbench/test_workbench_adapter.py` |
| Review, Exports, and mapping screens still absent | `source-verified` | `macos/Sources/Views` |

## Required item 18.2 evidence

- [x] ADR-0019 accepted with Decision A and the required threat rows.
- [x] Strict `veriformis.workbench-adapter/v1` pin models.
- [x] Unknown commands, fields, and versions fail closed.
- [x] No Review, Exports, or dataset-row UI.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.

## Required item 18.3 evidence

- [x] Home and Compile copy is goal-first. Aptus is optional, not required.
- [x] Copyable CLI equivalent of the current document-source compile plan.
- [x] Sidebar remains Home / Compile / History / Settings.
- [x] No dataset-row, export execute, or review submit.
- [x] Focused tests, xcodebuild, parity, tracking, Ruff, lock, core pytest,
      and diff check pass.

## Required item 18.4 evidence

- [x] Mode picker uses ADR-0010 identifiers `document-source`,
      `dataset-row`, and `mixed`.
- [x] Dataset-row wraps mapping-detect, operator confirm, mapping-preview,
      then parse and map. Unconfirmed plans cannot compile.
- [x] Mixed refuses fused document and row members with the CLI reason.
- [x] Family goals wait for a confirmed mapping plan that binds their
      schema.
- [x] Mapping lives on Compile. MappingView, Review, and Exports screens
      remain absent.
- [x] Focused tests, xcodebuild, parity, tracking, Ruff, lock, core pytest,
      and diff check pass.

## Required item 18.5 evidence

- [x] Progressive disclosure of chunk, construct, curate, split,
      review_policy, representation, compatible generic exports, and
      non-claims from the selected preset and goal.
- [x] Overrides remain explicit. No Swift-side default `review_policy`
      other than the catalog value.
- [x] Validation and profile selectors are inspect-only.
- [x] Focused tests, xcodebuild, parity, tracking, Ruff, lock, core pytest,
      and diff check pass.

## Required item 18.9 evidence

- [x] Accessibility labels on compile, sources, mapping, export, review,
      and error recovery.
- [x] Keyboard: ⌘1–⌘6 destinations, ⌘Return compile, ⌘. cancel, ⇧⌘C copy
      compile CLI.
- [x] Copyable CLI for mapping, compile, export, and review.
- [x] Virtualization skipped: no measured source-list bottleneck.
- [x] Full localization skipped: English v1 (`developmentRegion = en`).
- [x] GitHub xcodebuild job not licensed.
- [x] Focused tests, xcodebuild, parity, tracking, Ruff, lock, core pytest,
      and diff check pass.

## Item 18.9 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/workbench/` | 97 passed |
| `xcodebuild … test` (Veriformis scheme) | 112 passed |
| `macos/scripts/parity_check.sh` | PASS; manifest `1e5a842a56c5acdbc04e931a5e7a88229535a301fd579863508bb439d8fdd2eb` |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS |
| Core pytest excluding optional integration and scale markers | 2,560 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Required item 18.8 evidence

- [x] Review sidebar wraps review-export, review-import, and
      operator-confirmed review-submit.
- [x] Default `review_policy` stays `none`.
- [x] Corrections display as new identities.
- [x] Required unresolved reviews still block seal (CLI).
- [x] Focused tests, xcodebuild, parity, tracking, Ruff, lock, core pytest,
      and diff check pass.

## Item 18.8 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/workbench/` | 93 passed |
| `xcodebuild … test` (Veriformis scheme) | 112 passed |
| `macos/scripts/parity_check.sh` | PASS; manifest `1e5a842a56c5acdbc04e931a5e7a88229535a301fd579863508bb439d8fdd2eb` |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS |
| Core pytest excluding optional integration and scale markers | 2,556 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Required item 18.7 evidence

- [x] Exports sidebar destination wraps discover, dry-run, inspect,
      operator-confirmed execute, and verify.
- [x] Source bundle identity, manifest digest, and receipt stay visible.
- [x] Generic containers first. Named profiles only for admitted schemas.
- [x] No membership mutation, Hub upload, or training launch.
- [x] Review stays out of the sidebar.
- [x] Focused tests, xcodebuild, parity, tracking, Ruff, lock, core pytest,
      and diff check pass.

## Item 18.7 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/workbench/` | 88 passed |
| `xcodebuild … test` (Veriformis scheme) | 112 passed |
| `macos/scripts/parity_check.sh` | PASS; manifest `1e5a842a56c5acdbc04e931a5e7a88229535a301fd579863508bb439d8fdd2eb` |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS |
| Core pytest excluding optional integration and scale markers | 2,551 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Required item 18.6 evidence

- [x] ResultView shows recovery, mapping, supervised region, preview-only
      quality, exclusions, and split facts.
- [x] Oversized payloads omit whole with an exact reason. Quality does not
      block seal. No renderer. No destination write.
- [x] Focused tests, xcodebuild, parity, tracking, Ruff, lock, core pytest,
      and diff check pass.

## Item 18.6 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/workbench/` | 82 passed |
| `xcodebuild … test` (Veriformis scheme) | 111 passed |
| `macos/scripts/parity_check.sh` | PASS; manifest `1e5a842a56c5acdbc04e931a5e7a88229535a301fd579863508bb439d8fdd2eb` |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS |
| Core pytest excluding optional integration and scale markers | 2,545 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 18.5 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/workbench/` | 79 passed |
| `xcodebuild … test` (Veriformis scheme) | 110 passed |
| `macos/scripts/parity_check.sh` | PASS; manifest `1e5a842a56c5acdbc04e931a5e7a88229535a301fd579863508bb439d8fdd2eb` |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS |
| Core pytest excluding optional integration and scale markers | 2,542 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 18.4 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/workbench/` | 75 passed |
| `xcodebuild … test` (Veriformis scheme) | 109 passed |
| `macos/scripts/parity_check.sh` | PASS; manifest `1e5a842a56c5acdbc04e931a5e7a88229535a301fd579863508bb439d8fdd2eb` |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS |
| Core pytest excluding optional integration and scale markers | 2,538 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 18.3 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/workbench/` | 67 passed |
| `xcodebuild … test` (Veriformis scheme) | 100 passed |
| `macos/scripts/parity_check.sh` | PASS |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS |
| Core pytest excluding optional integration and scale markers | 2,530 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 18.2 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/workbench/test_workbench_adapter.py tests/workbench/test_phase18_workbench_isolation.py` | 62 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,525 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 18.1 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/workbench/test_phase18_workbench_isolation.py` | 8 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,471 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |
