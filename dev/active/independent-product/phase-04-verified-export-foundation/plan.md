# Phase 4 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-21

Each numbered roadmap work item is one sequential pull request. A PR must pass
its focused and full required local gates, pass every required GitHub check,
merge, and leave clean local `main` equal to `origin/main` before the next PR
branch is created.

## Checklist

### 4.1 Add the typed export service

- [x] Create the standard Phase 4 packet and mark the phase `in_progress`.
- [x] Add one `ExportService` beneath the Python composition root.
- [x] Capture manifest, validation, row, partition, and provenance semantics in
      the same descriptor-anchored pass that verifies the source bundle.
- [x] Preserve the existing `verify_finished_bundle()` return contract and
      error envelope.
- [x] Pin service injection, external-digest, lower-trust, tamper, subclass,
      falsey-injection, and runtime-type-introspection tests.

### 4.2 Define versioned export models

- [x] Publish the verified export v1 contract.
- [x] Define strict export plan, container profile, consumer profile,
      destination-file binding, receipt, and verification models.
- [x] Recompute every durable identity from canonical exact fields.
- [x] Add malformed, unsupported-version, duplicate-key, float, Unicode, and
      round-trip contract tests.

### 4.3 Enforce source trust

- [x] Require a retained expected manifest digest for a trusted export.
- [x] Permit self-consistent input only through an explicit lower-trust policy.
- [x] Record the exact source trust grade; never silently upgrade it.
- [x] Refuse absent or mismatched trust evidence before any destination write.

### 4.4 Bind complete source and output evidence

- [x] Bind bundle, manifest, snapshot, validation, split, row-set, and row-schema
      identities.
- [x] Bind container/profile versions, dependencies, normalized output paths,
      media types, row counts, and the profile's exact-byte or semantic digest
      evidence.
- [x] Keep absolute destination roots, clocks, temporary names, and warnings out
      of portable identities.

### 4.5 Enforce the derivative-only boundary

- [ ] Bind complete record, assignment, leakage-group, partition, and ordinal
      membership projections.
- [ ] Reject omission, addition, duplication, filtering, target mutation,
      balancing, repartitioning, and resplitting.
- [ ] Expose no public plan flag capable of changing dataset membership.

### 4.6 Publish atomically and safely

- [ ] Use private sibling staging and one no-replace atomic promotion.
- [ ] Enforce portable path safety and closed file/directory sets.
- [ ] Add explicit cancellation checkpoints and cleanup.
- [ ] Verify staged output independently before publication.
- [ ] Report visibility honestly if publication succeeds but a later receipt
      step fails.

### 4.7 Define deterministic evidence limits

- [ ] Distinguish portable exact-byte claims from semantic-content-only claims.
- [ ] Re-render and compare exact-byte profiles.
- [ ] Reconstruct and verify semantic content for semantic-only profiles.
- [ ] Freeze deterministic plan, receipt, and conformance-tree fixtures without
      advertising the injected test exporter as a supported container.

### 4.8 Expose export APIs on every surface

- [ ] Add discovery, dry run, overwrite-policy, inspect, execute, and verify
      methods through `PipelineService`.
- [ ] Add `veriformis export` and `veriformis export-verify` as thin adapters.
- [ ] Add MCP tools over the same service.
- [ ] Add strict CLI-backed Mac bridge support without a second registry or
      filesystem implementation.
- [ ] Prove identical plans and digests across all surfaces.

### 4.9 Complete the adversarial harness and closeout

- [ ] Cover contract properties, tampering, unexpected files, traversal,
      Unicode/case aliases, links, races, cancellation, and partial publication.
- [ ] Prove source-digest mismatch and every membership mutation fail closed.
- [ ] Run the complete Python, release, Mac, parity, tracking, structure, link,
      and diff gates.
- [ ] Reconcile current status, architecture, support, evidence, WIP, program
      ledger, and this packet.
- [ ] Mark Phase 4 complete only after its roadmap exit evidence passes.

## Exit gate

An injected generic conformance exporter creates an atomic, receipt-bound
derivative. Tampering, unexpected files, source-digest mismatch, membership
change, and partial publication fail verification. Python, CLI, MCP, and the
CLI-backed Mac bridge produce identical plans and digests.

## Non-goals

- Shipping Phase 5 JSONL, JSON, or CSV containers.
- Claiming compatibility with Aptus, MLX-LM, TRL, or another trainer.
- Adding an export workspace stage or changing `minimal-v1`.
- Public plugin APIs, network publication, replacement-by-force, signing,
  notarization, or a maturity promotion.
