# Phase 2 Progress Log

This file is append-only by dated entry. Corrections are recorded in later
entries rather than deleting earlier evidence.

## 2026-08-11 — Phase 2 started

**Status:** In progress

**Predecessor:** Phase 1 completed with standalone CLI, MCP, workbench, install,
and required release gates.

**Verified starting defects:** `WorkbenchViewModel` is `@MainActor`; its
unstructured `Task` inherits that actor and calls synchronous
`VeriformisCLI.run`, which invokes `Process.waitUntilExit()`. The canonical
bundle verifier correctly rejects unexpected members, while retained local
evidence records Finder inserting `.DS_Store` into a `.vfbundle` directory.

**Next action:** Add process-runner and strict unexpected-member regressions,
then implement the asynchronous cancellation boundary without weakening bundle
verification.

## 2026-08-11 — Process and cancellation boundary completed

**Observed RED:** the focused Xcode build failed because
`CLIProcessController` and the asynchronous `run(arguments:controller:)` API did
not exist. This pinned the replacement boundary before implementation.

**Implemented:** child launch and completion execute off the main actor; stdout
and stderr drain concurrently; retained bytes and visible lines are bounded;
invalid UTF-8 uses stable replacement decoding; cancellation records PID,
termination status, and TERM-to-KILL escalation. The workbench persists a
backward-compatible `cancelled` history state and receipt, retains the
workspace, exposes Cancel, and delays app termination until recovery finishes.

**Observed proof:** the complete 28-test Xcode suite passed. It includes
10,000 dual-stream lines, immediate and in-flight cancellation, graceful and
forced termination, runner reuse after cancellation, app-quit coordination,
and cancellation at every parse-through-package workbench stage.

## 2026-08-11 — Artifact boundary accepted and implemented

ADR 0005 selected deterministic stored `.vfbundle.zip` transport. The current
app registers no package UTI, and package presentation would remain an
ordinary mutable directory outside Finder and on Linux. The selected archive
wraps the exact six canonical paths only after `external_digest` verification;
the strict directory verifier still rejects `.DS_Store`.

`package` and `package-verify` were added through `PipelineService` and the CLI.
Verification writes only six fixed destinations in private temporary storage,
reuses canonical bundle verification, and requires byte-for-byte canonical ZIP
encoding. Workbench success now includes the transport archive and its digest;
Finder actions reveal that archive rather than the canonical directory.

**Observed proof:** 11 focused transport test functions passed on macOS and as part of
the complete Linux suite. They cover deterministic bytes, standard extraction,
wrong external digest, `.DS_Store`, unexpected/duplicate/traversal/link
members, payload mutation, no-replace publication, and simulated
`ENOSPC`/`EACCES` plus post-publication cleanup handling.

## 2026-08-11 — Operational closeout

Added `script/build_and_run.sh` as the single checked-in Xcode build/run path,
with run, debug, logs, telemetry, and verify modes. The legacy Mac launcher now
delegates to it, and `.codex/environments/environment.toml` exposes the Run
action. The new script built the checked-in project, launched a fresh app, and
confirmed PID 97528; the temporary app process was then stopped.

Final observed gates: 675 core Python tests passed on macOS and 675 passed in a
local Linux/arm64 Python 3.12 container (one optional integration test
deselected in each); all 28 Xcode tests passed; Ruff, project tracking, parity,
golden compile/package for both objectives, clean-wheel installed-CLI smoke,
shell syntax, JSON parsing, and `git diff --check` passed. No signing,
notarization, public-beta, trainer-export, or live Aptus claim follows.
