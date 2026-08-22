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

- [x] Bind complete record, assignment, leakage-group, partition, and ordinal
      membership projections.
- [x] Reject omission, addition, duplication, filtering, target mutation,
      balancing, repartitioning, and resplitting.
- [x] Expose no public plan flag capable of changing dataset membership.

### 4.6 Publish atomically and safely

- **Implementation state:** Complete; PR #48 passed every required check and
  merged at `3da0a7f4f8243a1e3a7390e6969c2ee67d7c65af`.
- [x] Use private sibling staging and one no-replace atomic promotion.
- [x] Enforce portable path safety and closed file/directory sets.
- [x] Add explicit cancellation checkpoints and cleanup.
- [x] Verify exact planned bytes and the canonical in-tree receipt independently
      before publication.
- [x] Report visibility honestly if publication succeeds but later bookkeeping
      fails; no normal receipt write occurs after promotion.

The Phase 4.6 merge publishes only `portable_exact_bytes` conformance output;
successful `semantic_content_only` publication, exact-byte rerender proof, and
semantic reconstruction of produced bytes enter only through the private Phase
4.7 conformance boundary below.

### 4.7 Define deterministic evidence limits

- **Implementation state:** Complete; PR #49 passed every required check and
  merged at `6c3f0aff2e35edaa7920a0964270c410bf53f47b`.
- [x] Distinguish portable exact-byte claims from semantic-content-only claims.
- [x] Render twice from independent strict inputs and compare normalized exact-
      byte trees for exact profiles before destination access.
- [x] Render twice, reconstruct versioned canonical semantic preimages and
      complete membership from both outputs, and replay descriptor-reread
      staged bytes for semantic-only profiles.
- [x] Require the service to hash semantic preimages; private hooks cannot
      supply digests or bypass complete membership validation.
- [x] Freeze deterministic plan, receipt, verification, and conformance-tree
      fixtures without changing the ten persisted v1 schemas or
      advertising the injected test exporter as a supported container.

Phase 4.7 changes no public `ExportService.publish` arguments and adds no
renderer/replayer registry. Its rerender evidence is a runtime admission
procedure, not a persisted v1 attestation. Phase 4.8 owns public surfaces and
Phase 4.9 owns the complete adversarial closeout harness.

### 4.8 Expose export APIs on every surface

- **Implementation state:** Complete; every required local gate passes; pull-
  request review pending.
- [x] Add discovery, dry run, overwrite-policy, inspect, execute, and verify
      methods through `PipelineService`.
- [x] Add `veriformis export` and `veriformis export-verify` as thin adapters.
- [x] Add MCP tools over the same service.
- [x] Add strict CLI-backed Mac bridge support without a second registry or
      filesystem implementation.
- [x] Prove identical plans and digests across all surfaces.

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
