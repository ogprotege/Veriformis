# Closeout

**Status:** Complete. All eight local exit gates passed on 2026-09-09.

**Publication:** [PR #204](https://github.com/ogprotege/Veriformis/pull/204).
Merge requires passing checks on the final pushed HEAD and resolved review
findings. GitHub retains the check runs, final review state, and merge record.
This document does not substitute a local pass for that remote gate.

## Defect judgment

The [evidence table](evidence.md) covers D-01 through D-35. Thirty-four confirmed
defects are closed. D-07 is withdrawn because fresh source inspection and
regressions prove the existing fingerprint preserves NFC and NFD distinctions.
No fingerprint replacement or persisted-stage schema migration was made.

Cursor's saved `3e529f4498312b64e3092cd977a8238bdc84586b` was verified before
continuation. Its claimed stages 1 through 3 were rechecked and corrected
before later work. The complete progression is recorded in [progress.md](progress.md).

| Exit | Required core evidence |
| --- | --- |
| Takeover verification of stages 1 through 3 | 2816 passed, 4 skipped, 32 deselected |
| Stage 4 | 2829 passed, 4 skipped, 32 deselected |
| Stage 5 | 2869 passed, 4 skipped, 32 deselected |
| Stage 6 | 2873 passed, 4 skipped, 32 deselected |
| Stage 7 | 2890 passed, 4 skipped, 32 deselected |
| Stage 8 and required local release script | 2897 passed, no skips, 32 deselected |

Every core gate retains the documented optional integration exclusions. The
stage 8 test-only environment also executes four missing-extra refusal tests
that the existing environment skips when optional columnar libraries are
installed. Each gate reports the expected transport durability warning.

## Final validation

- `scripts/release/check_local.sh`: passed, including lock, Ruff, full core,
  clean-wheel install, packaged discovery, committed golden manifests,
  independent verification, and deterministic transport.
- Unsigned Debug `xcodebuild test`: 122 tests, zero failures, including all
  74 real CLI acceptance cells and ten new Mac hardening regressions.
- `macos/scripts/parity_check.sh`: passed.
- `scripts/release/project_spec_example.sh`: passed with the retained manifest
  `e1146ecae6f714fd5a189d313211bfb37f98907047e6930554b2bb4936e1db3b`.
- Project tracking and `git diff --check`: passed after reconciliation.

## Preserved work and claim

PR #203 was inspected as a divergent branch from the shared base
`5d617f88c1b22513c5f52ac5682a6a5088570d96`. It was not integrated. Its local
and remote branch refs remain at `ae5e13cb0f064a811f10320826f049b9ee5d9c3e`.
The six local-only files remain untracked and match the takeover SHA-256
receipts and saved copies. Original failure evidence remains outside the
repository with those receipts.

Version remains `0.1.0`, development alpha, with claim
`cli-first-independent-core`. No Phase 21, measured scale tier, trainer
execution, generator, Hub execution, plugin loader, or public signed Mac
claim is added. C7 is unchanged. Required imported-row review still refuses
because its v1 format lacks a durable receipt. Dense near-duplicate clusters
can still require quadratic report output. Process cleanup covers descendants
that stay in the owned process group. These limits remain explicit.
