# Phase 19 Evidence

**Status:** Open

**Opened:** 2026-08-31

## Predecessor evidence

Phase 18 completed. Closeout merged as PR #169 at
`9f384eeedb401441c564c511b642904c403dad38`. Clean local `main` at packet open
is PR #170 at `2737476eb2df83d82f575e3735b68487ee7cabc8` (install-smoke
SIGPIPE fix). Dependencies 4, 7, 8, 9, 10, 15, and 18 were complete in
`program.json`. Phases 5, 6, 11–14, 16, and 17 were also complete.

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| `PIPELINE_SCHEMA_VERSION` is `veriformis.pipeline/v1` | `source-verified` | `src/veriformis/recipes/pipeline_spec.py` |
| Stage order omits `map` and `export` | `source-verified` | `_STAGE_ORDER` in `pipeline_spec.py` |
| Pipeline documents have no mode, map, or export keys | `source-verified` | `_TOP_LEVEL_KEYS`; unknown keys fail closed |
| Parse in `run_pipeline_spec` does not pass `mode` | `source-verified` | `src/veriformis/recipes/runner.py` |
| `veriformis run` exists | `source-verified` | `src/veriformis/cli.py` |
| CLI and MCP names are disjoint from generator, install-extension, hub-upload, and quality-report | `source-verified` | CLI app; MCP tool manager |
| Package metadata has no `HF_TOKEN` | `source-verified` | `pyproject.toml` |
| Default `review_policy` is `none` | `source-verified` | `recipe_defaults()` |
| Quality gates remain `admitted_to_block is False` | `source-verified` | `src/veriformis/quality/gates.py` |
| Core compile names no network client | `source-verified` | runner, pipeline spec, PipelineService AST |
| Project spec, lock, resume, and ADR-0020 are absent | `source-verified` | contracts, CLI, MCP, `src/veriformis` |

## Required item 19.1 evidence

- [x] Standard packet opened from clean `main` after Phase 18 closeout.
- [x] Phase 19 moved from `planned` to `in_progress` with this packet path.
- [x] L1 through L15 recorded.
- [x] Active tracking documents reconciled to Phase 19 in progress without
      claiming a project spec, lockfile, dry-run, MCP tool, CI example, or Hub.
- [x] Baseline isolation tests added.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 19.2.

## Required item 19.2 evidence

- [x] Additive `veriformis.project-spec/v1` pin and contract document.
- [x] Loading is not execute. `pipeline/v1` still loads and refuses mode/map.
- [x] Unknown fields, unknown versions, unconfirmed mapping, mixed fused
      members, and family-on-refusing profiles fail closed.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 19.3.

## Required item 19.3 evidence

- [x] JSON Schema generated from the project-spec model.
- [x] Dry-run reconstructs stages, mode, mapping, export, and environment and
      writes no workspace, bundle, or destination.
- [x] `veriformis.project-lock/v1` pins spec digest, versions, and extras.
- [x] Environment inspection names no secrets.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 19.4.

## Required item 19.4 evidence

- [x] JSON diagnostics `{schema_id, code, message, spec_id, stage}`. Truncated
      JSON fails closed. Human CLI text stays.
- [x] Confirmed spec execute through PipelineService. Document-source parse
      omits `--mode`. Dataset-row is parse `--mode dataset-row` then `map`
      then the finished-dataset tail. Export is not auto-run.
- [x] Resume only when lock, workspace HEAD, and source identities match.
      Drift names the mismatched identity.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 19.5.

## Required item 19.5 evidence

- [x] MCP wraps spec-schema, spec-dry-run, spec-lock, env-inspect, spec-run,
      and spec-resume over PipelineService.
- [x] `run_pipeline` still executes `veriformis.pipeline/v1` only.
- [x] `package` / `package-verify` skipped with a record. No Hub. No
      quality-report.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 19.6.

## Required item 19.6 evidence

- [x] Retained public fixtures, example spec, lock, and committed
      `manifest.json` SHA-256 fingerprint.
- [x] CI example job compiles from those fixtures. Golden-compile remains.
- [x] No Hub upload, GitHub secrets, or xcodebuild.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [ ] Every GitHub check passes.
- [ ] PR merges and clean local `main` equals `origin/main` before 19.7.

## Item 19.6 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/automation/` | 56 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,627 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 19.5 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/automation/` | 54 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,625 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 19.4 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/automation/` | 50 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,621 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 19.3 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/automation/` | 40 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,611 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 19.2 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/automation/test_phase19_project_spec.py tests/automation/test_phase19_automation_isolation.py` | 27 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,598 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 19.1 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/automation/test_phase19_automation_isolation.py` | 9 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,580 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |
