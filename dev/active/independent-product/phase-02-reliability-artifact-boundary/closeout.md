# Phase 2 Closeout

**Status:** Complete

**Last reviewed:** 2026-08-11

## Exit-gate judgment

Passed. The app remains responsive during the executable long-running fixture;
stdout and stderr drain concurrently; retained memory and UI lines are bounded;
and immediate, every-stage, graceful, forced, and quit-time cancellation paths
produce durable receipts while retaining recoverable workspace state.

The canonical `minimal-v1` directory remains a strict six-file contract.
`.DS_Store` and every undeclared path remain hard failures. ADR 0005 selects a
deterministic `.vfbundle.zip` transport that requires the separately retained
manifest digest, reconstructs the canonical directory, and verifies at
`external_digest`. Mac and Linux tests cover deterministic output and
adversarial members. The workbench exposes the verified archive for Finder use.

## Verification summary

- macOS Python: 675 passed, 1 optional integration deselected.
- Linux/arm64 Python 3.12: 675 passed, 1 optional integration deselected.
- macOS Xcode: complete 28-test suite passed.
- Both golden objectives passed canonical seal, external verify, deterministic
  package, and package verification through source and clean-wheel CLIs.
- Workbench parity, checked-in build/launch, tracking, Ruff, shell syntax, JSON,
  and diff checks passed.

## Limitations carried forward

This phase does not implement generic or trainer-specific exports, new row
schemas/objectives, registered macOS package documents, signing, notarization,
remote publication, or a public-ready product claim. The local Linux result is
recorded-local evidence; required GitHub Linux CI remains the post-push signal.
Phase 3 owns taxonomy contracts and must begin under a new packet.
