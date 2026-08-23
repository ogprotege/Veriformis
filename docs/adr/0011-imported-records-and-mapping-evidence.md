# ADR-0011 — Imported Records and Mapping Evidence

**Status:** Accepted

**Date:** 2026-08-23

**Decider:** Phase 7.2 mapping contracts

## Context and evidence

`DatasetRecord` v1 requires `chunk_ids` and construction field evidence.
Imported rows are not constructed from document chunks. Fabricating chunks
would lie about provenance. Phase 5.3 already refused document CSV recovery as
round-trip evidence.

## Decision

1. Imported rows are `veriformis.imported-record/v1`. They do not widen
   `veriformis.dataset-record/v1`.
2. Every imported field carries `mapped_value` evidence: source id, 1-based
   row index, field path, original-value digest, mapping-rule id, and output
   SHA-256. The field value must match that output digest.
3. A mapping plan names an existing catalog goal and compatible
   representation. Constructors do not run. Membership policy is
   `authoritative`, `advisory`, or `replaced`. JSONL, JSON, and compatible CSV
   are admitted containers. CSV cannot represent nested `messages`.
4. Coercion, missing-value, and invalid-row rules are closed vocabularies.
   v1 admits only `refuse`.
5. Identities are recomputed on load. Extra or missing fields fail closed.

## Consequences

- Format can later lower imported records to unchanged `ProductRow` v1.
- Item 7.3 can execute JSONL mapping against these models without inventing
  chunks.

## Alternatives considered

- Widening DatasetRecord: rejected; exact field set and chunk requirement.
- Synthetic chunks: rejected; construction evidence would be false.

## Review triggers

Item 7.9 rejection export; item 7.10 templates; any new field-evidence kind.
