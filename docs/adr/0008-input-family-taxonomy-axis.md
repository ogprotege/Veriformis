# ADR-0008 — Input Family as the Seventh Taxonomy Axis

**Status:** Accepted

**Date:** 2026-08-22

**Decider:** Repository owner direction

## Context and evidence

Taxonomy v1 defined six axes for what is learned and how rows, containers,
profiles, and loss are expressed. Input support was expressed only as a set of
declared suffixes in the parser dispatcher and the support registry. Phase 6
needs a per-source eligibility vocabulary: goal contracts (6.2) bind each goal
to the recovery families that can supply its evidence, compile preflight (6.5)
reports per-source eligibility before any workspace is created, and the
acceptance matrix (6.6) enumerates every goal across every eligible family.
Phase 11 qualifies additional input types and Phase 12 adds optional OCR; each
needs a discoverable, support-registered family to promote.

## Decision

1. `input_family` is the seventh taxonomy axis. Its implemented identifiers
   are `plain-text`, `source-code`, `markdown`, `word-document`, `html`,
   `pdf-text`, `delimited-table`, and `json-records`; `ocr-image` is named
   `explicitly_unsupported`.
2. Each declared v1 suffix belongs to exactly one family, and each family names
   the parser kinds that produce its sources. The tracking checker proves the
   suffix partition equals `DECLARED_V1_EXTENSIONS` and the support registry
   lists the same families.
3. The axis is additive within taxonomy v1: its identifiers classify recovery
   only and are never persisted in a recipe, row, seal, or export, so no
   durable identity or schema version changes. Discovery, the Swift decoder,
   the golden fixture, and the support registry change in the same pull
   request.
4. A family states what recovery supplies, not what is learned. Goal
   eligibility per family lives in the goal catalog and is proved end to end by
   the Phase 6.6 matrix.

## Consequences

- Preflight can name a source's family and refusal reason without parsing the
  whole batch.
- Adding a family, moving a suffix, or promoting `ocr-image` is a roadmap
  step with a support-registry change, not a silent parser edit.
- The Swift workbench treats a discovery payload without `input_family` as
  unavailable; no family is filled from Swift constants.

## Alternatives considered

- Catalog-level grouping without a taxonomy axis: rejected because Phases 11
  and 12 would need the axis anyway and preflight needs one registry.
- A taxonomy v2: rejected because nothing persisted changes meaning.

## Review triggers

Any new parser kind or suffix; Phase 11 input qualification; Phase 12 OCR;
any change to what a family's recovery supplies.
