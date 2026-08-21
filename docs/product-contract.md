# Veriformis Product Contract

**Status:** Authoritative product contract

**Applies to:** Product scope, implementation plans, user-facing claims, and
optional consumer integrations

**Current baseline:** M1 core plus Groups 1–7 runtime, Group 9 automated
release gates, beta-prep, and private beta Mac workbench Phases 0–2 on `main`,
plus independent-product Phases 0–3 and Phase 4 verified-export foundation in
progress, version `0.1.0` development alpha

**Implementation review state:** Groups 1–7 complete; Group 9 automated gates
and beta-prep landed; private beta workbench Phases 0–2 and independent-product
Phases 0–3 on `main`; Phase 4 in progress; maturity alpha; public Mac claim
still owner-gated

**Last reviewed:** 2026-08-21 (independent-product Phase 4.2 model contract)

**Next review:** Phase 4 source-trust enforcement; beta label cut, public-ready
checklist, or any product-contract change

**Next execution document:** [Independent Product Roadmap](./plans/2026-08-11-veriformis-independent-product-roadmap.md)

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
  -> target-row-schema lowering
  -> exact-snapshot validation
  -> atomic, provenance-sealed training datasets
```

A cleaned corpus is an internal compiler state. When a recipe selects
`full_text`, cleaned text supplies the exact target content for constructed
records. Those records become a finished dataset only after the declared
curation, split, row lowering, validation, and sealing lifecycle. Clean state is
not a handoff for another product because Veriformis owns that downstream work.

This document establishes the product-level scope. Roadmap Step 1 translated it
into [Integrity Contract v1](contracts/integrity-v1.md), public contract
constants, and executable acceptance fixtures. Steps 7 through 10 are governed
by [Dataset Construction Contract v1](contracts/dataset-construction-v1.md).
Steps 11 through 16 are governed by
[Finished Dataset Contract v1](contracts/finished-dataset-v1.md).
The six-axis product vocabulary and compile compatibility are governed by
[Dataset Taxonomy Contract v1](contracts/taxonomy-v1.md).
Consumer-neutral derivative evidence is governed by
[Verified Export Contract v1](contracts/verified-export-v1.md); its execution
service remains under Phase 4 implementation.

## Ownership boundary

Veriformis owns the dataset from raw source capture through final seal. Its responsibility includes ingestion, faithful extraction, normalization, cleaning, source-evidence preservation, training-objective selection, deterministic record construction, curation, quality measurement, balancing, leakage-safe splitting, target-row-schema lowering, validation, and bundle verification.

Downstream training systems begin with a finished Veriformis dataset contract.
They own training planning, runtime selection, artifact compilation, and
training execution. A versioned consumer profile may rename or adapt a verified
dataset under explicit semantics, but it must not silently replace Veriformis's
curation, membership, or split policy. Aptus is one optional consumer
integration and is not required for the Veriformis product.

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

Group 3 implements the finished-dataset runtime. `FinishedDatasetPlan` binds one
exact recipe and construction result to deterministic curation, leakage-safe
split policy, serialization, all 17 validation gates, and the `minimal-v1`
retention profile. Revision schema v3 persists curation, split, product-row,
snapshot, validation, manifest, and attestation artifacts. Seal revalidates the
exact current snapshot, atomically publishes a closed six-file bundle, and
supports independent `self_consistent` or externally anchored
`external_digest` verification.

This remains a working **alpha** until a deliberate maturity cut and, for
public Mac distribution, the full Group 9 public-ready checklist with retained
evidence (see [release guide](release.md) and
[beta limitations](beta-limitations.md)). Group 3 passed its independent
architecture and security closeout. Group 4 delivered `PipelineService`, the
thin CLI adapter, and dual-objective M1.1 acceptance. Group 5 expanded declared
ingest (HTML, digitally-born PDF, CSV, JSON, JSONL), named OCR refusal, the
recipe library, statistics, and YAML pipelines. Group 6 delivered constrained
local MCP and the versioned Aptus handoff. Group 7 delivered the SwiftUI
workbench over the CLI; private beta Phases 0–2 add a KISS compile shell and
debugger tools (sidebar, run sheet, history, settings, failure detail, digests,
and rerun) without changing stage policy. Group 9
automated gates cover supported-platform CI, package-install smoke, golden
corpus compile evidence, and the packaging runbook. Beta-prep and
[install](install.md) documentation record operator setup and non-claims without
rebranding the product as beta. Owner-executed signing, notarization, and
clean-Mac install evidence remain required for a **public Mac app** claim.
Optional Group 8 (model-assisted construction) remains owner-gated.

Independent-product Phases 0–3 add the tracking and claim-control foundation,
standalone defaults, deterministic bundle transport, reliability controls, and
the implemented taxonomy and discovery registry without changing existing v1
persisted meanings. Phase 4 verified export foundation is in progress. Its
opening implementation adds a typed internal service boundary and a
descriptor-anchored view of an independently verified finished bundle without
changing existing persisted meanings. Its second increment adds strict
verified-export v1 plan, profile, membership, binding, receipt, and verification
models. Plan construction, publication, public export commands, generic export
containers, and new trainer profiles remain unimplemented.

## End-to-end compiler contract

| Stage | Veriformis responsibility | Required evidence |
| --- | --- | --- |
| Raw capture | Register every source and preserve its identity before transformation | Source identifier, original path or retained copy, SHA-256, size, parser selection |
| Canonical recovery | Recover text, structure, metadata, and source locations into one canonical IR | Canonical-stream version and digest, source ranges, parser diagnostics, extraction coverage, explicit degradation |
| Cleaning and normalization | Apply declared changes without silently flattening or deleting source meaning | Replayable edit plan, rule identity and parameters, before and after hashes, structure-preservation result, warnings |
| Dataset construction and promotion | Build candidates for a declared `TrainingObjective`, apply construction integrity and any required review, then create immutable records | Versioned `DatasetRecipe`, field-level evidence, constructor identity and version, review evidence, promotion decision, deterministic derivation |
| Dataset curation | Measure, exclude, quarantine, deduplicate, balance, and account for accepted records | `FinishedDatasetPlan`, quality facts, curation reasons and decisions, coverage ledger |
| Balancing and splitting | Produce authoritative train and evaluation partitions without related-record leakage | Leakage groups, balancing decisions, final membership, assignment digest, realized split statistics |
| Row lowering and compatibility | Lower accepted records into the selected training row schema without inventing a task | Row-schema version, masking expectation, preserved metadata, generic row-shape result (currently persisted under the legacy ID `aptus-row-shape`) |
| Validation and seal | Validate the exact snapshot, write a closed file set, and make later mutation detectable | Gate versions and results, input and output digests, bundle manifest, co-located attestation, separately retained manifest digest when external binding is required, independent verification result |

## Training objective, recipe, and record states

A versioned `TrainingObjective` states what the model should learn. A versioned
`DatasetRecipe` binds that objective to source selection, cleaning and
segmentation policy, ordered constructors, target schema, construction gates,
and any human-review requirement. Its Group 2 curation and split fields remain
explicitly deferred. Group 3 `FinishedDatasetPlan` binds one exact recipe and
construction result to executable curation, balancing, split, serialization,
validation-gate, partition, and bundle-retention policy.

A deterministic `ConstructionPass` emits an append-only `CandidateRecord` with its proposed payload and field-level source evidence. Construction-integrity checks and any required review create an explicit `PromotionDecision`. Promotion creates an immutable `DatasetRecord`. Group 3 then applies deterministic curation and authoritative split assignment before lowering to the target row schema. It derives emitted rows and manifest entries from unchanged accepted records. Rejected, pending-review, excluded, and quarantined values remain auditable.

Human review is a recipe or project policy, not a universal prerequisite. A deterministic recipe with no review gate may seal when all declared gates pass. A recipe that requires approval must refuse promotion or seal until approval evidence exists.

## Honest loss accounting

Veriformis does not promise impossible literal losslessness. A training dataset cannot always contain every byte or semantic feature from every source. Parsing may encounter unsupported structures. Cleaning may remove noise. Construction may select, divide, combine, or normalize material. Curation may reject records. Deduplication and balancing may exclude otherwise valid candidates.

The enforceable promise is accountable transformation:

1. **Source conservation.** Originals remain hash-pinned and recoverable according to the selected retention policy.
2. **Nothing silent.** Parsing loss, unsupported structures, cleaning edits, construction omissions, curation exclusions, deduplication, balancing, and filtering produce explicit evidence.
3. **Derivation integrity.** Every accepted field resolves to immutable source evidence or a declared deterministic derivation.
4. **Coverage accounting.** Workspace artifacts state what source material contributed, what did not, and why. The final minimal bundle binds those artifact identities and digests through its validation snapshot.
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

The roadmap's future `GeneratorPass` is optional, post-v1 work. It is not required for the deterministic product release. It requires a separate owner-approved implementation plan. Any future generator must record model identity and immutable revision, prompt and system-prompt digests, parameters, source evidence supplied to the model, candidate output, provider version, reproducibility limits, and review policy. Its candidates must pass through the same construction promotion, curation, split, row-lowering, validation, and sealing contracts. It may not bypass them or weaken deterministic workflows.

## Trainer-facing semantics and optional Aptus integration

Veriformis selects the row schema according to the recipe and preserves the intended loss boundary:

| Row schema | Training semantics |
| --- | --- |
| `text` | The retained sequence receives full supervision |
| Prompt-completion | Prompt tokens are context; completion tokens receive supervision |
| Instruction-output | Instruction and input are context; output receives supervision |
| Structured `messages` | The conversation is rendered by the selected tokenizer contract; only the final assistant suffix receives supervision |

Rendered model-family chat text may be used for preview and conformance checks.
It must not replace structured `messages` when doing so would change the
declared consumer masking behavior.

Group 3 validates the implemented semantic row shapes. Group 6 emits the
optional versioned sibling Aptus
handoff descriptor (`veriformis.aptus-handoff/v1`) and a fail-closed consumer
check that verifies external digest, partition digests, row schema, masking
expectations, and the portable assignment projection. The adapter policy
currently rejects plain `text` rows. Its repository checks prove descriptor
self-conformance, not compatibility with a live named Aptus build. Live
training execution remains outside Veriformis. The independent product roadmap
plans a consumer-neutral export contract and versioned optional trainer
profiles; those capabilities are not implemented by the completed taxonomy
phase.

## Fail-closed seal

A dataset is not finished because a JSONL file exists. Seal must validate the exact recipe, sources, edit plans, candidates, accepted records, split assignment, emitted product rows, and file set that it publishes. Missing evidence, stale validation, empty required output, path escape, unexpected files outside policy, digest mismatch, or post-validation mutation must prevent sealing or make verification fail.

The implemented `minimal-v1` seal contains exactly train and evaluation JSONL,
one aligned provenance stream, the validation report, the manifest, and the
attestation. Its co-located attestation establishes internal consistency. Only
a caller-supplied expected manifest SHA-256 establishes the
`external_digest` verification grade.

The M1.1 acceptance gate requires one raw multi-source corpus to produce two independently verifiable bundles through the same compiler foundation: one full-text objective and one source-derived supervised objective. Repeating the run must reproduce candidate, dataset, split-assignment, and bundle-content digests, except for declared non-semantic fields.

## Non-claims

Veriformis does not train models, prove that a dataset will improve a particular model, infer a training objective from ambiguous source material, guarantee that automated extraction understands every source structure, or claim that mathematical or statistical checks replace human judgment where a recipe requires review.

## Related documentation

- [Independent Product Roadmap](./plans/2026-08-11-veriformis-independent-product-roadmap.md)
- [Independent Product Analysis](./analysis/2026-08-11-independent-product-analysis.md)
- [Project Tracking and Evidence Policy](./governance/project-tracking.md)
- [Machine-readable Support Registry](./governance/support-registry.json)
- [Integrity Contract v1](./contracts/integrity-v1.md)
- [Dataset Construction Contract v1](./contracts/dataset-construction-v1.md)
- [Finished Dataset Contract v1](./contracts/finished-dataset-v1.md)
- [Dataset Taxonomy Contract v1](./contracts/taxonomy-v1.md)
- [Verified Export Contract v1](./contracts/verified-export-v1.md)
- [Current implementation status](./current-status.md)
- [Architecture](./architecture.md)
- [Existing design specification](./superpowers/specs/2026-07-28-veriformis-design.md)
- [Completed M1 implementation record](./superpowers/plans/2026-07-28-veriformis-m1.md)
