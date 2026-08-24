# ADR-0014 — Independently Admitted Consumer Profiles

**Status:** Accepted

**Date:** 2026-08-24

**Decider:** Phase 10.1 opening; independent-product roadmap Phase 10

## Context and evidence

[ADR-0012](0012-consumer-profile-as-optional-adapter.md) already makes a
consumer profile an optional adapter over a verified bundle. Phase 8
implemented `trl` and `mlx-lm`. Taxonomy lists `axolotl`,
`llama-factory`, and `unsloth` as candidates. Aptus remains a sibling
handoff descriptor, not an `ExportService` consumer_id. Phase 9 shipped
Parquet, Arrow, and local Hugging Face DatasetDict as generic containers
with `consumer_id` null.

Phase 10 must expand named trainers without coupling the compiler to any
one ecosystem and without advertising a profile that has not passed the
roadmap section-5 admission gate.

## Decision

1. Each Phase 10 profile is admitted independently. A candidate does not
   become executable by being named in the roadmap. Item 10.2 records
   section-5 pins. Later items emit only profiles whose pins pass.
2. Selecting `axolotl`, `llama-factory`, or `unsloth` MUST fail closed as
   a Phase 10 candidate until that profile is promoted. Generic export
   selectors remain `consumer_id` null. TRL and MLX-LM remain implemented
   optional adapters.
3. Optional extras `axolotl`, `llama-factory`, and `unsloth` exist as
   empty lists. Version ranges live in later admission pins. Core install,
   compile, seal, generic export, TRL/MLX-LM adapters, and core pytest
   MUST NOT import those trainers.
4. Moving Aptus onto the common profile lifecycle is item 10.6. Item 10.1
   does not change Aptus defaults, CLI, or MCP.
5. A hosted OpenAI profile is out of this packet. It would require a
   later research note that keeps the offline default and opt-in network
   boundary.
6. The exporter MUST NOT launch training. Closeout is item 10.8.

## Consequences

- Existing TRL, MLX-LM, and generic containers stay executable.
- A failed admission record is honest non-support, not a deferred fake
  adapter.
- A trainer extra cannot become a core release dependency without a new
  ADR.

## Alternatives considered

- Emitting Axolotl files in 10.1: rejected; packet and isolation must
  land first.
- Treating all four candidates as a single coupled release: rejected;
  roadmap requires independent admission.
- Importing trainer SDKs into the core extra: rejected; standalone
  release gates (ADR-0002).

## Verification

Item 10.1 requires ADR publication, packet opening, candidate refusal,
empty extras, and proof that implemented generic and Phase 8 profile
selectors remain executable. Items 10.2–10.8 add pins, renderers,
Aptus migration, harnesses, deprecation policy, and closeout.
