# Phase 1 Execution Plan

**Status:** Completed

**Last updated:** 2026-08-11

## Checklist

### 1.1 Pin standalone acceptance

- [x] Prove CLI `seal` defaults to no sibling handoff and explicit opt-in still works.
- [x] Prove MCP `seal` defaults to no handoff keys/file and explicit tools still work.
- [x] Prove CLI and MCP startup/default seal do not import `veriformis.handoff`.
- [x] Prove the workbench default and legacy-history fallback are false.
- [x] Keep the persisted legacy `aptus-row-shape` gate ID unchanged.

### 1.2 Change runtime defaults

- [x] Disable CLI automatic handoff and lazy-load its adapter only on opt-in.
- [x] Disable MCP automatic handoff and lazy-load optional handoff tools.
- [x] Disable workbench automatic handoff, including old history without the field.
- [x] Emit `--aptus-handoff` only when a workbench operator explicitly opts in.
- [x] Move Aptus copy/control under an optional Integrations area.

### 1.3 Separate core and optional integration evidence

- [x] Mark Aptus-specific tests with an explicit optional-integration marker.
- [x] Make required Python/release jobs run the core selection without Aptus tests.
- [x] Make golden compile prove seal, no automatic sibling, and external-digest verify.
- [x] Make parity derive only canonical bundle facts and assert no sibling handoff.
- [x] Add a separately named optional Aptus integration script/job.

### 1.4 Prove installed standalone operation

- [x] Build a wheel and install it into a clean temporary virtual environment.
- [x] Record the installed module path and dependency list; prove no external Aptus package.
- [x] Run both golden objectives through compile, seal, and external-digest verify using that installed CLI.
- [x] Assert the default installed path creates only canonical bundle artifacts.

### 1.5 Prove workbench operation

- [x] Run Swift tests with the standalone workbench defaults.
- [x] Build the macOS app with the installed Veriformis CLI available.
- [x] Run trainer-neutral CLI/workbench parity.
- [x] Retain an executable launch/bootstrap proof without claiming signing/notarization.

### 1.6 Reconcile authority and close

- [x] Update current status, CLI/install/development/release/beta/Mac docs and migration note.
- [x] Record CLI, MCP, and workbench defaults independently in the support registry and tracker.
- [x] Update WIP, evidence index, documentation debt/health, and program ledger.
- [x] Run full core, optional integration, lint, tracking, parity, install, golden, Swift, link, and diff gates.
- [x] Complete `closeout.md` and mark Phase 1 completed only if every required gate passes.

## Exit gate

A clean environment containing the installed Veriformis package, but no Aptus
package or repository, can compile both golden objectives, seal canonical
bundles, verify them with externally retained manifest digests, build and
exercise the workbench, and pass every required core release gate. No default
artifact or required release criterion depends on Aptus. Explicit Aptus
integration creation and self-conformance verification still pass separately.

## Non-goals

- Deleting the Aptus adapter or its explicit commands.
- Renaming the persisted `aptus-row-shape` gate without a versioned migration.
- Claiming compatibility with a named live Aptus binary without external evidence.
- Embedding Python in the macOS app or completing signed/notarized distribution.
