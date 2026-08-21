# ADR-0003 — Four-Axis Dataset Model

**Status:** Accepted

**Date:** 2026-08-11

**Decider:** Repository owner direction, supported by repository and official
trainer-contract analysis

## Context and evidence

The existing construction contract already states that a training objective is
not a row shape or serializer. Official trainer documentation uses the same
physical container for materially different training semantics and adds
consumer-specific filenames, mappings, templates, and masking.

## Decision

Model these axes independently:

1. Training family and objective: what is learned and which fields are targets.
2. Semantic row schema: the meaning of each field.
3. Physical container: how rows, splits, metadata, and sidecars are stored.
4. Consumer profile: destination-specific names, mappings, templates, masking,
   constraints, and conformance versions.

UI, APIs, registries, and validation must not use one ambiguous “format” value
for multiple axes.

## Consequences and limitations

Compatibility becomes explicit and testable, but users may need to answer more
than one question. Goal-first UX must explain the model progressively. Existing
v1 objectives and rows remain implemented; broader training families remain
planned until versioned contracts and tests exist.

## Alternatives considered

- **One format dropdown:** Rejected because JSONL, messages, Parquet, and a
  trainer profile answer different questions.
- **One schema per trainer:** Rejected because it couples semantic records to
  volatile downstream systems and duplicates equivalent meaning.

## Verification

Phase 3 defines persisted contracts, compatibility matrices, migrations,
discovery APIs, and invalid-combination tests. The Phase 3 packet opened
2026-08-20; `veriformis.taxonomy/v1` is the catalog schema and does not
change existing construction or row identities.

## Review triggers

Training-family, loss-policy, semantic-row, container, or consumer-profile
schema design.
