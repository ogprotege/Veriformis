# ADR-0009 — Catalog-Default Instructions and Deterministic Truthfulness

**Status:** Accepted

**Date:** 2026-08-22

**Decider:** Repository owner direction

## Context and evidence

Finished Dataset v1 requires an `instruction_output` serialization plan to
carry one exact, non-empty instruction literal. Before independent-product
Phase 6.7, goal-first compile surfaces treated that plan requirement as a
requirement that the operator always supply `--instruction`, and they checked
only presence. The Phase 6.6 acceptance matrix therefore repeated four
source-grounded instruction literals outside the goal catalog. Nothing proved
that an operator replacement named the selected source-derived task or avoided
claiming a summary, translation, answer, invention, or another transformation
that the recipe does not perform.

Roadmap item 6.7 requires prompt and static-instruction truthfulness without an
LLM or heuristic judgment. The goal catalog is already the versioned authority
for what each goal means, while Finished Dataset v1 is the authority for the
exact literal that serialization persists and emits.

## Decision

1. Each of the four supervised goals carries one `default_instruction` and one
   closed `instruction_task_claim` in `veriformis.goal-catalog/v1`.
   `learn-the-text` carries null for both because `full_text` admits only the
   whole-text representation.
2. Goal-first surfaces resolve instruction text before they create a finished
   plan. Omission for `instruction_output` selects the catalog default. An
   explicit operator value is an override and is admitted only when the shared
   deterministic validator confirms that it affirmatively names the selected
   goal's task and contains no vocabulary for another task or an absent
   transformation. Matching uses a Unicode-casefolded validation view, word
   boundaries, flexible internal phrase whitespace, and the closed task,
   absent-transformation, and immediate-negation vocabularies frozen in the
   [Goal Catalog Contract v1](../contracts/goal-catalog-v1.md#instruction-resolution-and-truthfulness).
   Empty and non-plain values fail first; otherwise missing own-task and
   absent-transformation reasons are emitted in that order. The validator
   preserves an admitted string exactly; no validation view rewrites it.
3. The catalog field `requires_operator_instruction` remains `true` exactly
   for `instruction_output` as compatibility metadata: that representation has
   an operator-visible instruction choice and its resolved serialization plan
   requires an instruction literal. It does **not** mean that every goal-first
   caller must provide an override. Omission is satisfied by the catalog
   default. Non-instruction representations continue to reject an instruction
   override.
4. Finished Dataset v1 is unchanged. A persisted `instruction_output`
   `SerializationPlan` still contains one exact, non-empty, content-addressed
   literal, and rows still emit that literal unchanged. The serializer and
   independent verifier do not consult the goal catalog, infer an instruction,
   or reinterpret an existing bundle. Source-derived context and target text
   are unchanged.
5. Instruction defaults are not recipe-preset defaults. Presets continue to
   own segmentation, construction, curation, split, representation, and review
   settings; the goal catalog alone owns default instruction text.
6. The two goal fields and the runtime truthfulness refusal are additive within
   Goal Catalog v1. The catalog is not persisted in a workspace or bundle, so
   no workspace, bundle, row, receipt, or verifier migration is introduced.

## Consequences and limitations

- CLI, MCP, YAML, preflight, preview, the pipeline service, and the Mac bridge
  resolve omission through the same catalog data and hold no independent
  default instruction literal.
- A valid operator override can be more specific than the catalog default, but
  the check is deliberately lexical and closed. It is not a semantic model,
  writing assistant, or fine-tuning-suitability judgment.
- Compile preflight refuses an untruthful override before source capture. A
  valid override is preserved byte-for-byte into the finished plan. Its request
  identity binds the catalog SHA-256 plus both the supplied and effective
  instruction digests, so changing a catalog default cannot retain the same
  preflight identity.
- `messages` remains an exact two-turn projection of source-derived context and
  target. Phase 6.7 adds no system prompt or prompt template to that schema.
- Existing sealed bundles remain governed by the exact plan literal already
  inside them. Verification proves their existing contract; it does not apply
  a later catalog policy retroactively.

## Alternatives considered

- Continue requiring an operator literal: rejected because it duplicates safe
  task text outside the catalog and leaves omission behavior inconsistent
  across goal-first surfaces.
- Move instruction inference into serialization: rejected because the
  serializer has no goal authority and Finished Dataset v1 forbids inference.
- Use an LLM or broad natural-language classifier: rejected because Phase 6 is
  offline, deterministic, and fail-closed.
- Put instruction defaults in recipe presets: rejected because instruction
  meaning belongs to the selected goal, not segmentation or curation policy.

## Verification and review triggers

Verification covers strict catalog closure, all four omitted defaults, positive
and negative operator vocabulary cases, exact admitted-string preservation,
preflight refusal before source access, preview and persisted-plan behavior,
every compatible representation in the Phase 6 acceptance matrix, and
Python/CLI/MCP/YAML/Mac parity.

Review this decision for any new objective, goal, representation, instruction
policy, prompt template, persisted instruction meaning, semantic validator, or
proposal to make the serializer or verifier consult goal data.
