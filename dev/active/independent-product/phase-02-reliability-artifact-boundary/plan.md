# Phase 2 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-11

## Checklist

### 2.1 Pin current defects

- [x] Prove the current workbench process call can synchronously wait on the main actor.
- [x] Add an executable high-volume stdout/stderr fixture that cannot deadlock.
- [x] Pin deterministic invalid-UTF-8 replacement behavior.
- [x] Pin cancellation before launch, during execution, graceful termination, and forced escalation.
- [x] Preserve a strict failure when an unexpected Finder file appears in a canonical bundle.

### 2.2 Build the reliable process boundary

- [x] Move launch, pipe draining, and termination completion off the main actor.
- [x] Bound retained in-memory output without blocking live line delivery.
- [x] Add compile cancellation and termination escalation.
- [x] Persist a cancellation receipt and a backward-compatible cancelled history state.
- [x] Keep all published view-model mutations on the main actor.
- [x] Cancel an active compile when the application terminates.

### 2.3 Decide and implement the artifact boundary

- [x] Compare a registered package directory and deterministic immutable archive with tests.
- [x] Record the decision and non-goals in an ADR.
- [x] Preserve the strict internal `minimal-v1` directory contract.
- [x] Add a deterministic Finder-safe transport artifact and independent verification path if selected.
- [x] Reject traversal, links, duplicates, unexpected members, mutation, and digest mismatch.

### 2.4 Add safe operator actions

- [x] Reveal the containing directory without opening the canonical bundle for browsing.
- [x] Export/copy only after external-digest verification.
- [x] Never modify or silently clean the canonical bundle.
- [x] Surface cancellation and transport-package evidence in result/history UI.

### 2.5 Operational and closeout proof

- [x] Add the project-local build/run entrypoint and Codex Run action.
- [x] Test missing CLI, high-volume output, invalid UTF-8, cancellation, and recovery.
- [x] Run Python, Swift, parity, package, launch, tracking, and diff gates.
- [x] Reconcile status, contracts, release/install/Mac docs, support registry, and evidence index.
- [x] Complete `closeout.md` and mark Phase 2 completed only after every exit gate passes.

## Exit gate

UI state remains responsive during a long-running child fixture; stdout and
stderr are drained without deadlock; cancellation and interruption produce
bounded logs, a receipt, and a recoverable workspace; and a canonical bundle
transported through the selected Finder-safe form verifies with its externally
retained manifest digest. Unexpected files inside the canonical directory
remain a hard failure.

## Non-goals

- New training objectives, row schemas, trainer profiles, or export containers.
- Ignoring `.DS_Store` or any other undeclared bundle member.
- Changing `minimal-v1` without a versioned migration.
- Claiming public signing, notarization, or clean-Mac distribution.
