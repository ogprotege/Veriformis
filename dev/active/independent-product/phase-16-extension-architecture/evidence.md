# Phase 16 Evidence

**Status:** Open

**Opened:** 2026-08-27

## Predecessor evidence

Phase 15 completed. Closeout merged as PR #139 at
`435bd63c90778674ff4eb68a5d882a168349baca`. At Phase 16 open, clean local
`main`, `origin/main`, and `HEAD` were equal at that commit. Dependencies 3,
4, 11, 13, and 15 were complete in `program.json`.

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| No `veriformis.extensions` module exists | `source-verified` | `src/veriformis/` package layout |
| Python packaging declares only the `veriformis` CLI script and no extension entry points | `source-verified` | `pyproject.toml` |
| CLI, MCP, and `PipelineService` expose no plugin-load or install-extension operation | `source-verified` | `src/veriformis/cli.py`; `src/veriformis/mcp/server.py`; `src/veriformis/pipeline/service.py` |
| Parser dispatch is a suffix chain | `source-verified` | `src/veriformis/parsers/dispatch.py` |
| Constructors use private `_CONSTRUCTORS` exact lookup | `source-verified` | `src/veriformis/construction/constructors.py` |
| Row mapping uses `execute_mapping` on the compiler path | `source-verified` | `src/veriformis/mapping/execute.py` |
| Quality detectors and v1 gates remain preview-only | `source-verified` | `src/veriformis/quality/detectors.py`; `src/veriformis/quality/gates.py` |
| Exporters and consumer profiles share private `_ExportImplementation` catalog entries | `source-verified` | `src/veriformis/exports/service.py` |
| Phase 4.7 hooks are trusted conformance code, not an untrusted plugin boundary | `source-verified` | `docs/product-contract.md` |
| All optional extras are empty | `source-verified` | `pyproject.toml`; `uv.lock` |
| Taxonomy has seven axes and no extension axis | `source-verified` | `src/veriformis/taxonomy.py` |
| Seventeen Finished Dataset v1 gates remain unchanged | `source-verified` | `src/veriformis/contracts.py` |

## Required item 16.1 evidence

- [x] Standard packet opened from the Phase 15 closeout merge.
- [x] Phase 16 moved from `planned` to `in_progress` with this packet path.
- [x] L1 through L15 recorded.
- [x] Active tracking documents reconciled to Phase 16 in progress without
      claiming an implemented extension protocol.
- [x] Baseline isolation tests added.
- [x] Focused tests, tracking, Ruff, lock, core pytest, diff check, and every
      GitHub check pass.
- [x] PR merges and clean local `main` equals `origin/main` before 16.2.

## Item 16.1 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/extensions/test_phase16_extension_isolation.py` | 11 passed |
| `uv run python scripts/check_project_tracking.py` | PASS; 21 roadmap phases and governed packets agree |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,289 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

GitHub checks: all 18 passed on PR #140. Merge SHA
`76c0e2e90d95874b3e117f95554c428c70da1daf`. Clean local `main` equaled
`origin/main` there before 16.2.

## Required item 16.2 evidence

- [x] `docs/contracts/extension-protocol-v1.md` published.
- [x] Strict models for six kinds, origins, lifecycle, extras, deterministic
      requirements, diagnostics, fixtures, and discovery metadata.
- [x] Load/refuse tests for unknown fields, kinds, and contract versions.
- [x] No loader, executable registry, extra, CLI operation, MCP operation, or
      dispatch change.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passes.
- [x] PR merges and clean local `main` equals `origin/main` before 16.3.

GitHub checks: all 18 passed on PR #141. Merge SHA
`4534975fb7d97aef392c6ba0481ea7bd4af1e052`.

## Required item 16.3 evidence

- [x] Built-in-only registry wraps parsers, mapping, constructors, quality
      checks, and the one export catalog.
- [x] Suffix dispatch, constructor lookup, and export selectors unchanged.
- [x] Third-party origin refused. No loader, extra, CLI, or MCP operation.
- [x] Parse reports, constructor selectors, export selectors, and a sealed
      bundle identity remain identical on existing fixtures.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [ ] Every GitHub check passes.
- [ ] PR merges and clean local `main` equals `origin/main` before 16.4.

## Item 16.3 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/extensions/test_internal_registries.py tests/extensions/test_phase16_extension_isolation.py tests/extensions/test_extension_protocol.py` | 45 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS |
| Core pytest excluding optional integration and scale markers | 2,323 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 16.2 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/extensions/test_extension_protocol.py tests/extensions/test_phase16_extension_isolation.py` | 28 passed |
| `uv run python scripts/check_project_tracking.py` | PASS; 21 roadmap phases and governed packets agree |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,306 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |
