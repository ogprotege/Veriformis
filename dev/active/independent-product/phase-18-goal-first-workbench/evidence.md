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
