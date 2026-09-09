# Dataset-row quality-report closeout

Date: 2026-09-09. PR: #203. Reviewed original head:
`ae5e13cb0f064a811f10320826f049b9ee5d9c3e`.
Integration baseline: main `23bdc20b4667a1bd8381debd233d4d12a3bdd87a`
(PR #204, the completed eight-stage post-20 defect closure).

## Behavior and corrections

`quality-report` now previews a dataset-row workspace after map, curate, and
split. The private immutable preview binds the actual imported plan and rows.
It does not create construction records, write workspace files, seal a bundle,
admit a blocking quality gate, or add an MCP tool. Document-source reporting
keeps its existing contract. The version remains `0.1.0` development alpha,
with claim `cli-first-independent-core`.

The original PR failed on mapped instruction/output and messages fixtures
because it looked for a construction field named `completion`. Both failures
were reproduced against the saved original source. The corrected projection
uses the imported curation context and target rules for all eight row schemas.
Tool-call and stepwise target lengths now describe the final supplied answer
or step instead of the serialized trace. Original field names and values remain
available to detectors and field distributions.

The merge retains PR #204's exact near-duplicate prefix index, length filtering,
and transitive-cluster pair scoring. It also retains its current contract text.

## Independent document-source baseline

The same two-source document fixture was run independently against both saved
source trees before accepting a changed golden. Report transport SHA-256:

| Source | SHA-256 |
| --- | --- |
| Old PR base `5d617f88` | `54e4616afe9bd8151aef9336831b1d094fbcfbba2fd96dca3c6216665cc15c53` |
| Current main `23bdc20b` | `0bcf32cb96010a1d93d0e41c92cbcb9630d16718ef84a749e5a327fa77d0462d` |

The integrated preview matches current main byte for byte. The old expected
value remains in git history and retained local evidence. Identity and split
facts changed between those baselines; this PR does not overwrite that history.

## Observed local gates

- `uv run pytest -q tests/quality`: 59 passed. Regression fixtures cover all
  eight imported schemas, exact context/target lengths, original field names,
  repeatability, unchanged workspace file hashes, and non-enforcing reports.
- `bash scripts/release/check_local.sh`: passed with Python 3.12; 2913 core
  tests passed, 32 deselected, and the expected staging-link RuntimeWarning.
  Lock, Ruff, clean-wheel installed CLI, both golden compiles, retained manifest
  digests, and archive verification passed.
- Optional Aptus/profile/columnar integration selection: 35 passed, 2914
  deselected, no skips. Columnar libraries were installed in an isolated
  environment; offline flags and required-library enforcement were enabled.
- `scripts/release/aptus_integration.sh`: passed adapter self-conformance.
- Project tracking, CLI/workbench parity, and the project-spec example passed.
- `scripts/release/xcodebuild_debug.sh`: unsigned Debug build and 122 XCTest
  cases passed on the owner Mac, including the 74-cell real-CLI acceptance test.
- `git diff --check`: passed.

These are local observations. GitHub checks and merge state are recorded by
PR #203. No public signed Mac release, trainer execution, owner-scale imported
corpus measurement, or quality judgment is claimed.

## Retention

Raw logs, the original failure reproduction, and both independent baseline
reports are retained with the product-polish closeout archive outside the
repository. The operator's six local-only files and the complete takeover
backup were copied and hash-verified before any archival disposition. They
are not part of this commit. The original takeover and local files remain
unchanged. C7 was not opened or rebuilt.
