# Veriformis Product Contract

**Status:** Authoritative product contract

**Applies to:** Product scope, implementation plans, user-facing claims, and Aptus handoff

**Current baseline:** M1 core plus Groups 1 and 2, version `0.1.0`

**Next execution document:** [Veriformis Build Roadmap](./plans/2026-07-29-veriformis-roadmap.md)

## Product promise

The completed Veriformis product must be a local-first compiler for fine-tuning datasets. It must accept heterogeneous raw source material and produce finished, training-ready datasets whose source use, transformations, construction decisions, curation decisions, split assignments, validation results, and emitted files can be inspected and verified.

The full product path is:

```text
heterogeneous raw sources
  -> faithful canonical recovery
  -> normalized IR and clean corpus state
  -> objective-driven record construction
  -> curation and quality control
  -> leakage-safe balancing and splitting
  -> target-schema formatting
  -> exact-snapshot validation
  -> atomic, provenance-sealed training datasets
```

A cleaned corpus is an internal compiler state. When a recipe selects
`full_text`, cleaned text supplies the exact target content for constructed
records. Those records become a finished dataset only after the declared
curation, split, formatting, validation, and sealing lifecycle. Clean state is
not a handoff for another product because Veriformis owns that downstream work.

This document establishes the product-level scope. Roadmap Step 1 translated it
into [Integrity Contract v1](contracts/integrity-v1.md), public contract
constants, and executable acceptance fixtures. Steps 7 through 10 are governed
by [Dataset Construction Contract v1](contracts/dataset-construction-v1.md).

## Ownership boundary

Veriformis owns the dataset from raw source capture through final seal. Its responsibility includes ingestion, faithful extraction, normalization, cleaning, source-evidence preservation, training-objective selection, deterministic record construction, curation, quality measurement, balancing, leakage-safe splitting, target formatting, validation, and bundle verification.

Aptus begins with a finished Veriformis dataset contract. Aptus owns training planning, runtime selection, artifact compilation, and training execution. Aptus may verify or exactly reproduce a sealed split assignment under a shared versioned contract, but it must not silently replace Veriformis's curation or split policy.

## Current and planned capability

The implemented M1 core supports a deterministic stage pipeline for Markdown,
DOCX, plain text, and code. Group 1 adds transactional workspace revisions,
source-scoped identity, explicit parser-loss diagnostics, strict versioned
intermediate schemas, immutable chunk evidence, and replayable cleaning plans.

Group 2 adds versioned training objectives and recipes, ordered deterministic
construction passes, source-text and strict-IR field evidence, append-only
candidates, explicit decisions, optional review evidence, immutable accepted
records, and deterministic construction diagnostics. It implements five
objectives: full text, continuation, section reconstruction, before-and-after
transformation, and structured fields. A construct commit stores canonical
recipe and result artifacts and replays their meaning against the declared
source, clean, chunk, transform, and IR inputs before `HEAD` advances.

This remains a working alpha, not the complete product contract. Group 3 must
add curation, authoritative splitting, construction-aware serialization,
product rows, exact-snapshot validation, atomic sealing, and independent
verification. Later groups add the stable service surface, broader inputs,
integrations, the Mac workbench, and release controls. Documentation must label
each later capability as planned until its exit gate passes.

## End-to-end compiler contract

| Stage | Veriformis responsibility | Required evidence |
| --- | --- | --- |
| Raw capture | Register every source and preserve its identity before transformation | Source identifier, original path or retained copy, SHA-256, size, parser selection |
| Canonical recovery | Recover text, structure, metadata, and source locations into one canonical IR | Canonical-stream version and digest, source ranges, parser diagnostics, extraction coverage, explicit degradation |
| Cleaning and normalization | Apply declared changes without silently flattening or deleting source meaning | Replayable edit plan, rule identity and parameters, before and after hashes, structure-preservation result, warnings |
| Dataset construction | Build records for a declared `TrainingObjective` through ordered `ConstructionPass` operations | Versioned `DatasetRecipe`, field-level `SourceEvidence`, constructor identity and version, deterministic derivation |
| Curation and promotion | Measure, reject, quarantine, deduplicate, and optionally review candidate records | Quality facts, rejection reasons, review policy and state, coverage accounting, promotion decision |
| Balancing and splitting | Produce authoritative train and evaluation partitions without related-record leakage | Leakage groups, balancing decisions, final membership, assignment digest, realized split statistics |
| Formatting and compatibility | Lower accepted records into the selected training schema without inventing a task | Row-schema version, masking expectation, preserved metadata, Aptus compatibility result |
| Validation and seal | Validate the exact snapshot, write a closed file set, and make later mutation detectable | Gate versions and results, input and output digests, bundle manifest, detached digest or attestation, independent verification result |

## Training objective, recipe, and record states

A versioned `TrainingObjective` states what the model should learn. A versioned `DatasetRecipe` binds that objective to source selection, cleaning and segmentation policy, ordered constructors, curation rules, balancing and split policy, target schema, required gates, and any human-review requirement.

A deterministic `ConstructionPass` emits an append-only `CandidateRecord` with its proposed payload and field-level source evidence. In Group 2, construction-integrity checks and any required review create an explicit `PromotionDecision`. Promotion creates an immutable `DatasetRecord`. Group 3 adds curation and authoritative split assignment before formatting and derives emitted rows and manifest entries from accepted records. Rejected and pending-review candidates remain auditable.

Human review is a recipe or project policy, not a universal prerequisite. A deterministic recipe with no review gate may seal when all declared gates pass. A recipe that requires approval must refuse promotion or seal until approval evidence exists.

## Honest loss accounting

Veriformis does not promise impossible literal losslessness. A training dataset cannot always contain every byte or semantic feature from every source. Parsing may encounter unsupported structures. Cleaning may remove noise. Construction may select, divide, combine, or normalize material. Curation may reject records. Deduplication and balancing may exclude otherwise valid candidates.

The enforceable promise is accountable transformation:

1. **Source conservation.** Originals remain hash-pinned and recoverable according to the selected retention policy.
2. **Nothing silent.** Parsing loss, unsupported structures, cleaning edits, construction omissions, curation exclusions, deduplication, balancing, and filtering produce explicit evidence.
3. **Derivation integrity.** Every accepted field resolves to immutable source evidence or a declared deterministic derivation.
4. **Coverage accounting.** The final bundle states what source material contributed, what did not, and why.
5. **Reproducibility.** The same sources, recipe, configuration, and tool versions reproduce the same semantic artifacts, except for declared non-semantic metadata such as timestamps.

Exact persisted artifact JSON and durable identity and configuration-digest
payloads preserve Unicode string and object-key sequences. Those durable paths
apply NFC normalization only to explicit locator fields, such as logical source
paths, before those fields enter an identity payload. Audit revision IDs may
differ because they also bind parent history and commit time. Portable state
and per-source parse-input digests govern semantic reproducibility.

The product may describe this as faithful, source-grounded, loss-accounted, or provenance-sealed. It must not claim byte-for-byte preservation across every stage or claim that every source token appears in training output.

## Deterministic v1 boundary

The v1 dataset pipeline makes no LLM calls and performs no remote model generation. The implemented deterministic builders create full-text, continuation, section-reconstruction, before-and-after transformation, and structured-field candidates when the recipe states a truthful task and every constructed field has evidence. Structured-field construction binds each selected strict-IR scalar to its immutable artifact, RFC 6901 pointer, exact value digest, encoding, output digest, and construction context.

The roadmap's future `GeneratorPass` is optional, post-v1 work. It is not required for the deterministic product release. It requires a separate owner-approved implementation plan. Any future generator must record model identity and immutable revision, prompt and system-prompt digests, parameters, source evidence supplied to the model, candidate output, provider version, reproducibility limits, and review policy. Its candidates must pass through the same curation, promotion, split, formatting, validation, and sealing contracts. It may not bypass them or weaken deterministic workflows.

## Aptus-facing semantics

Veriformis selects the row schema according to the recipe and preserves the intended loss boundary:

| Row schema | Training semantics |
| --- | --- |
| `text` | The retained sequence receives full supervision |
| Prompt-completion | Prompt tokens are context; completion tokens receive supervision |
| Instruction-output | Instruction and input are context; output receives supervision |
| Structured `messages` | The conversation is rendered by the selected tokenizer contract; only the final assistant suffix receives supervision |

Rendered model-family chat text may be used for preview and conformance checks. It must not replace structured `messages` when doing so would change Aptus masking behavior.

## Fail-closed seal

A dataset is not finished because a JSONL file exists. Seal must validate the exact recipe, sources, edit plans, candidates, accepted records, split assignment, formatted rows, and file set that it publishes. Missing evidence, stale validation, empty required output, path escape, unexpected files outside policy, digest mismatch, or post-validation mutation must prevent sealing or make verification fail.

The M1.1 acceptance gate requires one raw multi-source corpus to produce two independently verifiable bundles through the same compiler foundation: one full-text objective and one source-derived supervised objective. Repeating the run must reproduce candidate, dataset, split-assignment, and bundle-content digests, except for declared non-semantic fields.

## Non-claims

Veriformis does not train models, prove that a dataset will improve a particular model, infer a training objective from ambiguous source material, guarantee that automated extraction understands every source structure, or claim that mathematical or statistical checks replace human judgment where a recipe requires review.

## Related documentation

- [Veriformis Build Roadmap](./plans/2026-07-29-veriformis-roadmap.md)
- [Integrity Contract v1](./contracts/integrity-v1.md)
- [Dataset Construction Contract v1](./contracts/dataset-construction-v1.md)
- [Current implementation status](./current-status.md)
- [Architecture](./architecture.md)
- [Existing design specification](./superpowers/specs/2026-07-28-veriformis-design.md)
- [Completed M1 implementation record](./superpowers/plans/2026-07-28-veriformis-m1.md)
