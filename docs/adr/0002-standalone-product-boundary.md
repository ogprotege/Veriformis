# ADR-0002 — Standalone Veriformis Product Boundary

**Status:** Accepted

**Date:** 2026-08-11

**Decider:** Repository owner direction

## Context and evidence

`PipelineService`, workspace, construction, curation, split, serialization,
validation, sealing, and verification are implemented without Aptus. Aptus is
a sibling handoff adapter over a verified finished bundle. However, CLI, MCP,
workbench, release, and roadmap defaults made Aptus appear to be the required
destination.

## Decision

Veriformis must install, compile, validate, seal, verify, export, operate in the
Mac workbench, and pass its core release gates without Aptus or another trainer.
Aptus remains a supported optional integration under the same profile lifecycle
as other consumers.

Phase 1 implements this boundary: CLI, MCP, and workbench seal defaults do not
write an Aptus sibling; the core release path does not invoke the adapter; and
optional adapter evidence runs separately.

## Consequences and limitations

The existing Aptus adapter and tests remain valuable and explicitly invocable.
Compatibility failures in an optional profile do not redefine the correctness
of a verified generic Veriformis dataset. The persisted generic validation ID
`aptus-row-shape` remains temporarily for report compatibility; it imports no
Aptus code and is tracked as versioned migration debt.

## Alternatives considered

- **Make Aptus the canonical downstream:** Rejected because it contradicts the
  independent product goal and the neutral compiler architecture.
- **Delete Aptus support:** Rejected because optional verified integrations are
  useful and the existing adapter contains real integrity checks.

## Verification

The Phase 1 gates require a clean standalone install, golden compile,
external-digest verify, workbench launch, and core test run without Aptus
availability. Optional adapter self-conformance is recorded separately and
does not claim compatibility with a live named Aptus build.

## Review triggers

Any proposal to make a trainer, cloud service, or integration required for core
installation, compile, verification, or release.
