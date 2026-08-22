# ADR-0004 — Canonical Bundle and Derived Exports

**Status:** Accepted

**Date:** 2026-08-11

**Last reviewed:** 2026-08-21 (Phase 5.1 first derivative implementation)

**Decider:** Repository owner direction

## Context and evidence

Veriformis already seals a strict six-file `minimal-v1` directory whose
manifest binds the exact dataset snapshot, partitions, provenance, validation,
and attestation. At Phase 4 closeout, generic external exports and named trainer
packs had no shipped renderer or supported product container. Phase 4.6
supplies an internal atomic publisher and receipt verifier; Phase 4.7 adds only
private two-render exact-byte and semantic-content conformance evidence. Phase
4.8 exposes the shared service through strict Python, CLI, MCP, and CLI-backed
Mac operations, while its private production catalog closes empty. Phase 5.1
now supplies the first production exact-byte implementation,
`split-jsonl-directory` v1, without adding a trainer pack.

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
Users eventually receive both a trainer-friendly artifact and a verifiable
relationship to the source bundle. Exact-byte destination enforcement, receipt
replay, and atomic publication are implemented internally in Phase 4.6. Phase
4.7 privately compares two exact byte trees or two reconstructed canonical
semantic-preimage trees and replays staged semantic bytes. Phase 4.8 fulfills
the surface decision with strict discovery, dry run, self-described inspect,
operator-confirmed no-replace execute, and source-bound verify operations. That
phase intentionally has no discoverable production implementation. Phase 5.1
uses the same boundary to admit one exact-byte generic container. Its request-v1
defaults use `train` / `evaluation` filenames and include aligned provenance;
configured request v2 requires the complete
`veriformis.split-jsonl-options/v1` object to change those safe stems or omit
provenance. The derivative changes neither semantic rows nor membership and
claims compatibility with no trainer.

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
verification and writing arrive in Phase 4.6 for exact-byte plans only. The
service re-verifies source and plan, checks semantic membership and planned
bytes separately, writes and independently reloads a canonical receipt inside
a closed private staging tree, and performs one atomic no-replace promotion.
Phase 4.7 invokes the private renderer twice from independent strict inputs.
Exact profiles require identical normalized byte trees; semantic-only profiles
require equal versioned canonical semantic preimages and complete reconstructed
membership, with service-computed digests and descriptor-reread staged replay.
This adds no persisted rerender transcript or new schema. The private hooks are
trusted conformance code, semantic replay currently retains complete files in
memory, and the fixture is statically bounded. The Phase 4 default service had
no renderer or semantic replayer. Phase 4.8 adds a private exact-selector catalog
and shared strict surface protocol, but production discovery remained empty and
adapters accept no caller-supplied plan, implementation, membership, or
replacement authority. Phase 4.9 consolidates adversarial contract, tamper,
path, link, source-trust, membership, race, cancellation, and partial-
publication proof. The roadmap exit gate passes without a shipped
implementation; generic containers remain Phase 5.

Phase 5.1 verifies `split-jsonl-directory` v1 through that unchanged publisher
and receipt boundary. Its renderer copies the authoritative train and
evaluation payloads into canonical JSONL, emits deterministic README and data-
card evidence, optionally emits the complete aligned provenance stream, and
renders twice to the same exact byte tree. Request v1, the ten persisted
verified-export v1 models, discovery v1, and response v1 remain unchanged;
configured dry run, execute, and source-bound verification use additive request
v2. Tests prove all four current row schemas round-trip with identical order and
partition membership and exercise option, path, tamper, and closed-tree
refusals. Other generic containers and trainer profiles remain later work.

## Review triggers

Any bundle-profile change, export service implementation, resplitting proposal,
or consumer adapter that changes row semantics.
