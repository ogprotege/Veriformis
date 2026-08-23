# ADR-0013 — Columnar Containers as Optional Generic Exports

**Status:** Accepted

**Date:** 2026-08-23

**Decider:** Phase 9.1 opening; independent-product roadmap Phase 9

## Context and evidence

[ADR-0002](0002-standalone-product-boundary.md) requires Veriformis to install,
compile, seal, verify, and export without a trainer or a heavy optional
library. [ADR-0003](0003-four-axis-dataset-model.md) already names physical
container as a distinct axis. [ADR-0004](0004-canonical-bundle-derived-exports.md)
makes the verified six-file bundle the canonical product and generic
containers receipt-bound derivatives. Taxonomy v1 lists `parquet`, `arrow`,
and `hugging-face-dataset` as planned. Production export discovery currently
exposes three generic containers plus TRL and MLX-LM split-JSONL adapters.

Phase 5 JSONL, JSON, and constrained CSV claim `portable_exact_bytes`. Official
PyArrow and Hugging Face Datasets documentation describe Parquet and Arrow as
columnar, compressed, split-file formats whose on-disk bytes can change
across library versions even when the table is semantically the same.

Phase 9 must add those containers without making PyArrow a core dependency
and without pretending Parquet is JSONL.

## Decision

1. `parquet`, `arrow`, and `hugging-face-dataset` are generic physical
   containers. Their export selectors MUST keep `consumer_id` null. They
   MUST NOT be trainer profiles. Selecting those identifiers before the
   matching Phase 9 item is executable MUST fail closed with an actionable
   reason that names that later item (`parquet` names 9.4, `arrow` names
   9.5, `hugging-face-dataset` names 9.6).
2. Core install, compile, seal, JSONL/JSON/CSV export, TRL/MLX-LM adapters,
   and core pytest MUST NOT import PyArrow, Hugging Face Datasets, pandas,
   or another columnar library. Those packages belong in optional extra
   `columnar` and optional CI jobs, the same isolation as Aptus and the
   empty `trl` / `mlx-lm` extras.
3. A columnar export MAY rename files, shard, compress, and emit approved
   sidecars. It MUST NOT construct targets, curate, resplit, or change
   record membership or loss-policy IDs.
4. Semantic identity MUST be a versioned fingerprint independent of
   library-specific metadata that can drift. The export receipt MUST still
   bind the exact emitted bytes of this pinned extra. Columnar v1 MUST NOT
   claim `portable_exact_bytes` across arbitrary third-party library
   versions.
5. Hub upload, remote dataset fetch, and training launch are out of scope.
6. Nested `messages` is in scope. Null product fields remain unrepresentable
   and MUST fail in Veriformis before a library sees them.

## Consequences

- Existing generic and profile exports stay byte-compatible.
- Later Parquet, Arrow, and Hugging Face Dataset work have a named gate to
  open without advertising support.
- A columnar extra cannot become a core release dependency without a new ADR.
- Performance or storage claims require measured 9.8 evidence.

## Alternatives considered

- Shipping Parquet files in 9.1: rejected; the packet and isolation policy
  must land first.
- Treating Hugging Face Dataset as a consumer profile: rejected; container
  and profile are different axes. Local Dataset/DatasetDict is a physical
  container.
- Importing PyArrow into the core extra: rejected; that would violate
  standalone release gates.
- Claiming portable exact bytes for Parquet: rejected; library metadata
  and encodings drift.

## Verification

Item 9.1 requires ADR publication, packet opening, planned-container
refusal, empty extra `columnar`, and proof that existing executable
selectors remain discoverable. Items 9.2–9.8 add pins, fingerprints,
renderers, import, harnesses, benchmarks, and closeout.

## Review triggers

Item 9.4 Parquet execution; item 9.5 Arrow execution; item 9.6 Hugging Face
Dataset execution; any proposal to require PyArrow for core install,
compile, generic JSONL/JSON/CSV export, or release.
