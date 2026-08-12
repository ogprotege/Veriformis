# Phase 2 Evidence

**Evidence status:** Complete

**Predecessor:** [Phase 1 closeout](../phase-01-standalone-independence/closeout.md)

## Source-verified starting facts

| Fact | Evidence | Limitation |
| --- | --- | --- |
| Workbench view model is main-actor isolated | `macos/Sources/ViewModels/WorkbenchViewModel.swift` | Does not alone prove a visible freeze |
| Compile uses an inherited unstructured task and synchronous runner | `WorkbenchViewModel.compile`, `VeriformisCLI.run` | Must be replaced and regression-locked |
| Runner invokes `Process.waitUntilExit()` | `macos/Sources/Services/VeriformisCLI.swift` | Pipe handlers drain concurrently but cancellation is absent |
| UI retains at most 2,000 displayed lines | `WorkbenchViewModel.appendLog` | Combined process output is still unbounded |
| Canonical verifier rejects extra paths | Finished bundle verifier and tamper tests | Correct behavior; distribution boundary remains open |
| Finder mutation was observed locally | Independent-product analysis retained observation | Single-machine evidence; cross-platform/archive tests required |

## Required final evidence

- Responsive async runner and view-model tests.
- High-volume stdout/stderr and invalid UTF-8 tests.
- Cancellation, TERM/KILL escalation, receipt, and workspace recovery tests.
- Artifact-boundary ADR and deterministic/adversarial transport tests.
- Verified non-mutating workbench artifact actions.
- Xcode build/tests/launch plus Python, tracking, documentation, and diff gates.

Exact results are appended only after observation.

## Final observed evidence — 2026-08-11

| Claim | Grade | Observed result / evidence |
| --- | --- | --- |
| Process execution does not block the main actor | Test-verified | `CLIBridgeTests.testProcessRunnerSuspendsWithoutBlockingMainActor` passed |
| Heavy dual-stream output drains and retention is bounded | Test-verified | 5,000 stdout + 5,000 stderr lines; 64 KiB retained ceiling; tail assertions passed |
| Invalid UTF-8 is stable | Test-verified | Invalid byte decoded with U+FFFD; process succeeded |
| Cancellation is accountable and recoverable | Test-verified | Immediate, TERM, KILL escalation, controller reuse, all ten workbench stages, receipt/history, and app-quit tests passed |
| Canonical directory remains closed | Test-verified | `.DS_Store` source mutation and existing undeclared-member tests fail verification |
| Transport bytes are deterministic | Test-verified | Two outputs from one bundle compare byte-for-byte equal; canonical-encoding verifier passes |
| Transport is path/link/tamper safe | Test-verified | Traversal, duplicate, link metadata, extra member, payload mutation, size/digest mismatch, and noncanonical bytes rejected |
| Publication fails cleanly | Test-verified | Existing targets are never overwritten; simulated pre-publication `ENOSPC`/`EACCES` leave no target or staging file; post-publication staging cleanup failure returns a verified receipt with an explicit warning |
| macOS core suite | Recorded-local | 675 passed, 1 optional test deselected |
| Linux core suite | Recorded-local | Python 3.12 Linux/arm64 container: 675 passed, 1 optional test deselected |
| macOS workbench suite | Recorded-local | Complete Xcode suite passed; 28 test methods in the checked-in target |
| Standalone golden transport | Recorded-local | `full_text` and `continuation` seal, external verify, package, and package-verify passed |
| Clean installed wheel | Recorded-local | Wheel origin in isolated site-packages; no Aptus distribution; installed CLI golden/package passed |
| Workbench launch | Recorded-local | `./script/build_and_run.sh --verify` built and confirmed fresh PID 97528 |
| Parity and governance | Recorded-local | CLI/workbench canonical parity, tracking, Ruff, JSON, shell syntax, and diff checks passed |

### Deterministic golden identities

| Objective | Manifest SHA-256 | Transport archive SHA-256 |
| --- | --- | --- |
| `full_text` | `2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733` | `d17217ace8e8929ce4d41f88b3a2bca54b6976ed95b9c7dc42122e97bdfb9980` |
| `continuation` | `58df8db589199821d1d51fefbe7d2a777a0e72ea8bb642dada4dfa350f89ef6b` | `d898ccb3ade4a5fc2c129c4271e191a7e500b190a728fd8ee18095451b13ec3b` |

The Linux container was local, disposable, and used a read-only host mount
copied into its ephemeral filesystem. This is recorded-local evidence, not a
GitHub Actions result. App launch is unsigned Debug operation, not signing or
notarization evidence.

### Rerun commands

```text
uv run pytest -q --ignore=tests/handoff -m "not aptus_integration"
uv run ruff check src tests
xcodebuild -project macos/Veriformis.xcodeproj -scheme Veriformis -configuration Debug -derivedDataPath /tmp/veriformis-phase2-all-dd test
bash scripts/release/golden_compile.sh
bash scripts/release/smoke_install.sh
bash macos/scripts/parity_check.sh
./script/build_and_run.sh --verify
uv run python scripts/check_project_tracking.py
git diff --check
```
