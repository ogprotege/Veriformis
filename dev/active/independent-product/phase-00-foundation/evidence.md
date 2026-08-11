# Phase 0 Evidence

**Evidence status:** Phase 0 completed

**Baseline commit:** `7d116e9c09fb4c64f38b2db2572f820a83c53dba`

## Baseline observed on 2026-08-11

| Check | Result | Grade | Limitation |
| --- | --- | --- | --- |
| `uv lock --check` | Pass | recorded-local | Raw console log not retained |
| `uv run ruff check src tests` | Pass | recorded-local | Raw console log not retained |
| `uv run pytest -q` | 658 passed | recorded-local | Before Phase 0.1 regression test was added |
| `bash macos/scripts/parity_check.sh` | Pass | recorded-local | Temporary artifacts were not retained |
| Xcode `Veriformis` scheme tests | 12 passed | recorded-local | Result bundle was under `/tmp` |
| Local Markdown link check | Pass for new/changed docs | recorded-local | Custom local-path check, not a general web link validator |
| `git diff --check` | Pass | recorded-local | Proves whitespace integrity only |

## Source-verified baseline facts

| Fact | Evidence |
| --- | --- |
| Product version `0.1.0` | `src/veriformis/__init__.py` |
| Declared input suffixes | `src/veriformis/parsers/dispatch.py` |
| Five implemented named objectives | `src/veriformis/recipes/library.py` |
| Four implemented row schemas | `src/veriformis/datasets/serialization.py` |
| Closed six-file `minimal-v1` bundle | `src/veriformis/bundle/finished.py` |
| Aptus adapter is a sibling over verified bundles | `src/veriformis/handoff/aptus_v1.py` |
| CLI and MCP handoff defaults are currently true | `src/veriformis/cli.py`, `src/veriformis/mcp/server.py` |
| Workbench process wait is synchronous | `macos/Sources/Services/VeriformisCLI.swift` |
| Finder added `.DS_Store` to a retained test bundle | `W-Tests-GUI/Test2/dataset-2026-08-06T12-52-39Z.vfbundle/.DS_Store` |

## Phase 0.1 final evidence

Observed locally on 2026-08-11 after the Phase 0.1 implementation:

| Check | Result | Grade | Limitation |
| --- | --- | --- | --- |
| `uv lock --check` | Pass; 50 packages resolved | recorded-local | Raw console log not retained |
| `uv run ruff check src tests` | Pass | recorded-local | Configured Ruff rules only |
| `uv run python scripts/check_project_tracking.py` | Pass | test-verified | Literal/structural claims only; semantic review remains required |
| `uv run pytest -q` | 659 passed in 35.82s | recorded-local | Duration is host-specific; raw console log not retained |
| `bash macos/scripts/parity_check.sh` | Pass; all five compared digests matched | recorded-local | Temporary bundles not retained |
| Xcode `Veriformis` scheme tests | 12 passed, 0 failures | recorded-local | Result bundle retained only temporarily under `/tmp/veriformis-phase0-dd` |
| Changed/new local Markdown links | Pass | recorded-local | Local filesystem targets only; external URLs not crawled |
| `git diff --check` | Pass | recorded-local | Whitespace integrity only |

The regression `tests/regressions/test_project_tracking.py` permanently runs
the tracking checker in the ordinary Python suite. It checks the roadmap,
program ledger, WIP phase table, support registry, evidence paths, active phase
packet, and selected live code constants.

## Phase 0.4 corpus and demand evidence

Observed locally on 2026-08-11 after adding the privacy-preserving matrix:

| Check | Result | Grade | Limitation |
| --- | --- | --- | --- |
| Repository fixture metadata scan | 16 files, 14 directories, 13,812 bytes; committed aggregate reproduced exactly | test-verified | Fixtures establish regression coverage, not owner-corpus prevalence |
| Retained GUI metadata scan | 89 files, 78 directories, 2 bundle directories, 2,995,574 bytes | recorded-local | `W-Tests-GUI` is untracked, output-focused, and unavailable to clean CI |
| `pytest -q tests/regressions/test_corpus_demand_matrix.py` | 3 passed in 0.86s | test-verified | Focused scanner/matrix contract only |
| Ruff on scanner and focused regression | Pass | recorded-local | Configured Ruff rules only |
| Draft 2020-12 schema validation | Pass with local `jsonschema` 4.26.0 | recorded-local | `jsonschema` is not a declared project test dependency |

The durable artifacts are
`docs/governance/corpus-demand-matrix.schema.json`,
`docs/governance/corpus-demand-matrix.json`,
`scripts/scan_corpus_metadata.py`, and
`tests/regressions/test_corpus_demand_matrix.py`. The focused regression
recreates only the tracked fixture observation; it deliberately has no
dependency on the untracked GUI test root.

## Phase 0 final closeout evidence

Observed locally on 2026-08-11 after the corpus and active-document
reconciliation:

| Check | Result | Grade | Limitation |
| --- | --- | --- | --- |
| `UV_CACHE_DIR=/tmp/veriformis-phase0-uv-cache uv lock --check` | Pass; 50 packages resolved | recorded-local | Alternate cache path was required by the execution sandbox |
| `.venv/bin/ruff check src tests scripts` | Pass | recorded-local | Configured Ruff rules only |
| `.venv/bin/python scripts/check_project_tracking.py` | Pass | test-verified | Structural/literal claims; semantic review remains mandatory |
| `.venv/bin/python -m pytest -q` | 662 passed in 34.56s | recorded-local | Host-specific duration; raw log not retained |
| `UV_CACHE_DIR=... bash macos/scripts/parity_check.sh` | Pass; five compared values matched | recorded-local | Current Phase 0 parity still used the pre-Phase-1 optional-adapter-coupled implementation |
| Xcode `Veriformis` scheme tests | 12 passed, 0 failures | recorded-local | Result bundle is temporary under `/tmp/veriformis-phase0-closeout-dd-escalated` |
| Active/local Markdown target check | Pass | recorded-local | Local filesystem targets only; external URLs and heading anchors not crawled |
| Stale architecture phrase scan | Pass | recorded-local | Targeted semantic phrases/citations, not a general natural-language proof |
| `git diff --check` | Pass | recorded-local | Whitespace integrity only |

The initial sandboxed Xcode attempt failed because the sandbox denied
communication with `testmanagerd`; the same required command was rerun with
the necessary authorization and passed. This is recorded as an environment
limitation, not omitted or represented as a product failure.

No representative private owner corpus was read. The scanner never opens file
content, and the committed matrix does not claim customer prevalence, trainer
compatibility, or scale readiness from repository fixtures.
