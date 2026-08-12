# Defect Closure Plan

## Method

Each cluster was developed test-first in an isolated worktree branch: write the
regression, prove it fails on unmodified `main`, apply the minimal fix, prove it
passes, then run the full core suite and Ruff. Branches are integrated into
`agent/defect-closure-pre-phase3` for one reviewable pull request.

## Clusters and gates

| # | Branch | Files (primary) | Pinned regression |
| --- | --- | --- | --- |
| 1 | `defect/workspace` | `workspace.py` | Orphan-artifact re-commit stays a no-op; workspace still opens; complete pipeline not spuriously staled |
| 2 | `defect/parsers` | `parsers/html.py`, `parsers/docx.py`, `parsers/markdown.py` | Div/span/tail text recovered or diagnosed; DOCX sdt-cell and code-run pieces preserved or diagnosed; blockquote footnote refusals fire |
| 3 | `defect/datasets` | `datasets/_json.py`, `datasets/validation.py`, `datasets/splitting.py`, `bundle/verifier.py`, `pipeline/service.py` | Deep JSON → typed error / failed report / `BundleVerificationError`; chained DSU no crash; `primary-source-cap` reachable end-to-end |
| 4 | `defect/transport-handoff` | `bundle/transport.py`, `handoff/aptus_v1.py`, `cli.py`, `mcp/server.py` | Warnings-as-errors publication returns success; U+2028 handoff round-trips; traversal/forged descriptor rejected; partial-publication guidance surfaced in `run` and MCP |
| 5 | `defect/cleaning-yaml` | `rules/library.py`, `chunkers/strategies.py`, `recipes/pipeline_spec.py`, `recipes/runner.py` | Combining marks preserved; sentence-chunk boundary whitespace no longer crashes; unknown/duplicate spec keys and unknown recipe ids rejected |
| 6 | `defect/review-plumbing` | `pipeline/service.py` | Reviewed construction result curates/splits/seals through the service loader |
| 7 | `defect/workbench-defaults` | `macos/Sources/...` | Default compile omits `--allow-empty-evaluation`; split ratio matches CLI |

## Integration order

Merge in cluster-number order into `agent/defect-closure-pre-phase3`. The only
expected file-level overlap is `pipeline/service.py` (cluster 3's balance-mode
mapping and cluster 6's review-input recovery touch different methods); resolve
any conflict by keeping both edits.

## Exit gates

1. Every new regression test passes; each was shown to fail on unmodified `main`.
2. Full core suite green: `uv run pytest -q --ignore=tests/handoff -m "not aptus_integration"`.
3. Handoff suite green: `uv run pytest -q tests/handoff -m "not aptus_integration"`.
4. `uv run ruff check src tests` clean.
5. `uv lock --check` and `uv run python scripts/check_project_tracking.py` pass.
6. `git diff --check` clean.
7. Swift workbench suite green (or a recorded reason it could not run locally).
8. Net test count strictly greater than the 675 baseline.
