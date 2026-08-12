# Evidence

## Review provenance

The closed defects were found by a 2026-08-12 full-repository review over
`main` at `bf45974`: an eight-dimension plan-and-alignment audit and a
seven-cluster bug hunt, each finding adversarially verified and every code
defect reproduced by execution before a fix was written. The green 675-test
baseline did not exercise any of the reproduced paths.

## Starting facts (unmodified `main`)

- Full core suite: 675 passed, 1 optional integration deselected.
- Ruff, lockfile, project tracking, and diff checks: clean.
- Every fix's regression test was shown to FAIL on unmodified `main` before the
  fix (verified per cluster by stashing the source change in its worktree).

## Per-cluster proof

| Cluster | Branch | Fix commit | New tests | Isolated result |
| --- | --- | --- | --- | --- |
| Workspace | `defect/workspace` | `840ae7c` | 4 | 679 core passed |
| Parsers | `defect/parsers` | `b138266` | 15 | 690 core passed |
| Datasets | `defect/datasets` | `daa41e2` | 7 | 682 core passed |
| Transport / handoff | `defect/transport-handoff` | `c20c9fe` | 12 (5 core + 7 handoff) | 680 core; handoff green |
| Cleaning / YAML | `defect/cleaning-yaml` | `808526a` | 20 | 695 core passed |
| Review lifecycle | `defect/review-plumbing` | `22df3de` | 2 | 677 core passed |
| Workbench | `defect/workbench-defaults` | `6ae5192` | 1 | 29 Swift tests |

## Integrated result (all seven merged)

- Full core suite: **728 passed**, 1 optional integration deselected
  (`uv run pytest -q --ignore=tests/handoff -m "not aptus_integration"`).
  Net +53 core regression tests over the 675 baseline.
- Handoff suite: **10 passed** (`uv run pytest -q tests/handoff`).
- Swift workbench suite: **TEST SUCCEEDED**, 29 tests, 0 failures (Phase 2
  baseline was 28; +1 fail-closed-default pinning test).
- Ruff: clean. `uv lock --check`: clean. Project tracking: PASS (21 phases,
  handoff defaults, and bundle/input/objective/row constants unchanged).
  `git diff --check`: clean.
- Only file-level overlap during integration (`pipeline/service.py`, touched by
  the datasets and review-lifecycle clusters) auto-merged cleanly; zero merge
  conflicts across all seven branches.

## Carried-forward compatibility facts

- The `special-chars` cleaning rule is bumped to `version = 2`. Because workspace
  semantic replay re-derives rules by name, an existing workspace that used the
  opt-in `special-chars` rule now **fails closed** at replay
  (`EvidenceError` / `WorkspaceCorruptError`) rather than silently diverging.
  `special-chars` is not a default rule, so the baseline and golden corpora are
  unaffected. The same fail-closed behavior applies to any persisted sentence
  chunk that carried edge whitespace.
- No persisted schema, durable identity, or revision digest changed. Existing
  default-rule workspaces and all sealed bundles continue to load and verify.
