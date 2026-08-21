# ADR-0004 — Canonical Bundle and Derived Exports

**Status:** Accepted

**Date:** 2026-08-11

**Last reviewed:** 2026-08-21 (Phase 4.5 membership enforcement remains faithful)

**Decider:** Repository owner direction

## Context and evidence

Veriformis already seals a strict six-file `minimal-v1` directory whose
manifest binds the exact dataset snapshot, partitions, provenance, validation,
and attestation. Generic external exports and named trainer packs do not yet
have a writer, receipt, or supported product container.

## Decision

The verified Veriformis finished bundle remains the canonical product artifact.
Generic containers and consumer packs are versioned, receipt-bound derivatives
created by one shared export service. Exporters may rename, map, package, or
emit approved sidecars, but they may not construct targets, curate, balance,
resplit, or silently change record membership.

If membership or semantic targets change, the result is a new compiled dataset
plan and bundle, not an export option.

## Consequences and limitations

One canonical lineage prevents each exporter from becoming a second pipeline.
Users receive both a trainer-friendly artifact and a verifiable relationship to
the source bundle. Destination enforcement, receipts, publication, and
deterministic rerendering remain Phase 4 implementation work.

## Alternatives considered

- **Make each trainer artifact canonical:** Rejected because downstream
  contracts differ and change.
- **Put every container inside `minimal-v1`:** Rejected because it expands the
  closed contract, duplicates data, and couples core verification to optional
  dependencies.
- **Unverified post-processing:** Rejected because it loses the integrity chain
  the product already establishes.

## Verification

Phase 4 requires export-plan identity, atomic publication, file bindings,
receipts, tamper checks, parity, and no-membership-change tests.

The Phase 4 opening composes a typed export service beneath `PipelineService`
and captures source semantics in the finished-bundle verifier's existing
descriptor-anchored pass. It does not add an export writer, mutate the bundle,
or establish a second compiler stage. Phase 4.2 adds the exact persisted export
models while retaining that boundary. Phase 4.3 adds trusted-by-default,
read-only source admission with explicit lower trust. Phase 4.4 adds read-only
plan population, deriving all source identities and the complete source
membership baseline from the admitted immutable bundle view. Phase 4.5 fresh-
reconstructs normalized candidate semantic rows and provenance and requires the
exact planned row set and complete membership projection. Destination-byte
verification, writing, and independent derivative verification remain later
increments.

## Review triggers

Any bundle-profile change, export service implementation, resplitting proposal,
or consumer adapter that changes row semantics.
