# ADR-0012 — Consumer Profile as Optional Adapter

**Status:** Accepted

**Date:** 2026-08-23

**Decider:** Phase 8.1 opening; independent-product roadmap Phase 8

## Context and evidence

[ADR-0002](0002-standalone-product-boundary.md) requires Veriformis to install,
compile, seal, verify, and export without a trainer. [ADR-0003](0003-four-axis-dataset-model.md)
already names consumer profile as a distinct axis. [ADR-0004](0004-canonical-bundle-derived-exports.md)
makes the verified six-file bundle the canonical product and generic containers
receipt-bound derivatives. Taxonomy v1 lists `trl` and `mlx-lm` as planned and
Axolotl, LLaMA-Factory, and Unsloth as candidates. Production export discovery
currently exposes only three generic containers with `consumer_profile` null.

Phase 8 must prove two trainer profiles without turning them into the product
or into a second compiler.

## Decision

1. A consumer profile is an optional, versioned adapter over an already
   verified finished bundle. It may rename files, map columns or roles, emit
   approved sidecars, and add stricter refusals. It MUST NOT construct targets,
   curate, resplit, or change record membership or loss-policy IDs.
2. Generic export selectors remain `consumer_id` null. Selecting `trl` or
   `mlx-lm` before the matching Phase 8 item is executable MUST fail closed
   with an actionable reason that names that later item. Candidate profiles
   remain Phase 10 and MUST refuse as candidates.
3. Core install, compile, seal, generic export, and core pytest MUST NOT
   import TRL, MLX-LM, or another trainer library. Trainer packages belong in
   optional extras and optional CI jobs, the same isolation as Aptus.
4. Aptus remains the existing optional sibling handoff. Moving it onto the
   common profile lifecycle is Phase 10, not Phase 8.
5. The exporter MUST NOT launch training. Sidecars are config or launch
   instructions only (item 8.6).

## Consequences

- Existing generic exports stay byte-compatible.
- Later TRL and MLX-LM work have a named gate to open without advertising
  support.
- A trainer extra cannot become a core release dependency without a new ADR.

## Alternatives considered

- Shipping TRL files in 8.1: rejected; the packet and isolation policy must
  land first.
- Treating a profile as a fourth generic container: rejected; container and
  profile are different axes.
- Importing trainer SDKs into the core extra: rejected; that would violate
  standalone release gates.

## Verification

Item 8.1 requires ADR publication, packet opening, planned-profile refusal,
null consumer discovery, and proof that `pyproject.toml` optional extras remain
only `test`. Items 8.2–8.7 add pins, renderers, harnesses, sidecars, and
closeout.

## Review triggers

Item 8.3 TRL execution; item 8.4 MLX-LM execution; any proposal to require a
trainer library for core install, compile, generic export, or release.
