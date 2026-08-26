# Veriformis Product Contract

**Status:** Authoritative product contract

**Applies to:** Product scope, implementation plans, user-facing claims, and
optional consumer integrations

**Current baseline:** M1 core plus Groups 1–7 runtime, Group 9 automated
release gates, beta-prep, and private beta Mac workbench Phases 0–2 on `main`,
plus completed independent-product Phases 0–4 and Phase 5.1–5.3's supported
generic `split-jsonl-directory`, canonical `json`, and `constrained-csv` v1
derivatives; Phase 5.4 receipt-anchored export-pack transport merged as PR #56,
Phase 5.5's test-only consolidated semantic round-trip matrix merged as PR #57
at `c72b8e9ec7bc2746d74404226aa086d497e15db1`, Phase 5.6 exact dry-run preview
merged as PR #58 at `cd017941090c7352cb1d10f9a383042b954d4f2e`, and Phase
5.7's operator guidance and closeout merged as PR #59 at
`65cbd471e96d83f8dd65e2cda60e90f64a916e2b`, completing Phases 0–5; Phase 6
goal-first recipes and previews complete, closeout merged as PR #67 at
`6995d17bef0d09f235b1c464e947c38c63dd313d`; Phase 7 existing-dataset import
and mapping complete; Phase 8 consumer profiles complete with implemented
TRL and MLX-LM optional adapters; Phase 9 Parquet, Arrow IPC, and local
Hugging Face DatasetDict v1 implemented as `semantic_content_only`
generics; Phase 10 complete under ADR-0014 with implemented Axolotl,
LLaMA-Factory, and Aptus optional adapters and Unsloth remaining a
non-executable candidate; Phase 11 collection-plan ingest complete;
Phase 12 optional Tesseract 5 OCR complete with `ocr-image` still
explicitly unsupported for default parse; closeout merged as PR #112 at
`892939f527974b69282296ded04eb3b43643554f`; Phase 13 quality intelligence
in progress at item 13.5; version `0.1.0` development alpha

**Implementation review state:** Groups 1–7 complete; Group 9 automated gates
and beta-prep landed; private beta workbench Phases 0–2 and independent-product
Phases 0–12 complete; Phase 13 in progress at item 13.5; maturity alpha;
public Mac claim still owner-gated. `ocr-image` remains explicitly
unsupported for default parse. There is no quality-report command.

**Last reviewed:** 2026-08-25 (independent-product Phase 13.5 leakage)

**Next review:** Phase 13.5 pull-request merge, item 13.6 tokenizer
simulations, or any product-contract change. Do not start Phase 14 from this packet.

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
The seven-axis product vocabulary and compile compatibility are governed by
[Dataset Taxonomy Contract v1](contracts/taxonomy-v1.md).
Consumer-neutral derivative evidence is governed by
[Verified Export Contract v1](contracts/verified-export-v1.md). Its internal
exact-byte publication, deterministic replay, and public surface foundation is
implemented. [Split JSONL Export v1](contracts/split-jsonl-export-v1.md)
governs the first production renderer and supported generic container;
[Canonical JSON Export v1](contracts/canonical-json-export-v1.md) governs the
second fixed-tree generic container;
[Constrained CSV Export v1](contracts/constrained-csv-export-v1.md) governs the
third, flat-schema-only fixed-tree container.
[Deterministic Archive Transport v1](contracts/bundle-transport-v1.md) governs
the manifest-anchored bundle wrapper and the separate receipt-anchored
post-export wrapper; neither is a semantic renderer or trainer profile.

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
persisted meanings. Phase 4 verified export foundation is complete. Its
opening implementation adds a typed internal service boundary and a
descriptor-anchored view of an independently verified finished bundle without
changing existing persisted meanings. Its second increment adds strict
verified-export v1 plan, profile, membership, binding, receipt, and verification
models. The third increment enforces trusted-by-default source admission and an
explicit lower-trust policy without changing ordinary bundle verification.
The fourth adds read-only source-derived plan population and binds the complete
source membership baseline without rendering or publishing destination content.
The fifth fresh-reconstructs normalized candidate semantic rows and provenance
and requires their row-set identity and complete membership projection to match
that baseline. Items 4.1–4.5 are merged at
`1675c1a22830d506bdf27e45150170befc984bdf`. The sixth increment implements
internal exact-byte-only publication: it re-verifies the source and plan,
validates semantic membership and exact planned bytes, writes and independently
reloads a canonical receipt in a closed private staging tree, and atomically
promotes without replacement. It merged as PR #48 at
`3da0a7f4f8243a1e3a7390e6969c2ee67d7c65af`. The seventh increment
renders twice from independent strict inputs. Exact profiles require identical
normalized byte trees; semantic-only profiles require equal versioned canonical
semantic preimages and reconstructed membership from both renders plus
descriptor-reread staged replay. The service computes semantic digests rather
than accepting hook assertions. All required local gates pass, including 14
determinism, 158 export, 163 combined export/contract, 927 full Python, 915
standalone-release with 1 deselected, and 38 Mac tests, and merged as PR #49 at
`6c3f0aff2e35edaa7920a0964270c410bf53f47b`. The eighth increment adds
a private default-empty implementation catalog plus strict discovery, dry run,
self-described inspect, operator-confirmed no-replace execute, and source-bound
verify through `PipelineService`, CLI, MCP, and the CLI-backed Mac bridge. It
merged as PR #50 at `fb0a13d7cab1e456b6ff3b3dc6ebab13b9898edb`, with review
corrections in PR #51 at `d91542fe12c5a492de578ad060836a7d65999e42`. The ninth
increment consolidates adversarial contract, tamper, path, link, source-trust,
membership, race, cancellation, and partial-publication closeout evidence. The
ten persisted v1 schemas and existing `publish` signature are unchanged. No
production renderer or semantic replayer, generic export container, or new
trainer profile shipped. At that Phase 4 closeout, Phase 5 generic exports
remained open.

Those final non-claims are the recorded Phase 4 exit boundary. Phase 5.1 now
ships the exact-byte `split-jsonl-directory` v1 renderer and container with no
consumer profile or trainer-compatibility claim. Historical export request v1
remains exact and selects safe `train` / `evaluation` filename stems with the
complete aligned provenance stream. Additive request v2 requires a complete
canonical `veriformis.split-jsonl-options/v1` object to change those stems or
omit provenance. Both requests preserve exact payload rows, ordering,
objective, curation result, split assignment, and train/evaluation membership.
The ten persisted verified-export v1 schemas, discovery v1, and the existing
`publish` signature remain unchanged. Response v1 remains unchanged for non-
dry-run operations; item 5.6 adds only runtime dry-run response v2.

Phase 5.2 adds canonical `json` v1 under the same boundary. Its fixed tree
contains one membership-bearing dataset object with explicit schema,
objective, loss, row-set, split-result, partition-order, count, and payload-
array fields; one mandatory separate aligned provenance object; a deterministic
README; and the shared receipt. It uses request v1 and refuses configured
request v2. It preserves the same exact rows, order, and partitions and claims
compatibility with no trainer. Item 5.2 merged as PR #54 at
`f6a5d45f01e0b3117c259271bc59f3599a89dbb6`.

Phase 5.3 adds `constrained-csv` v1 under the same boundary for `text`,
`prompt_completion`, and `instruction_output`. Its fixed fully quoted UTF-8/LF
train/evaluation files, dataset card, mandatory aligned provenance, README,
and receipt preserve exact strings, order, and logical partitions. It uses
request v1 and refuses request v2 before source access; after source admission
reveals nested `messages`, it refuses the schema before destination access,
directs nested rows to a JSON container, and claims
compatibility with neither a trainer nor a spreadsheet. All new trainer
profiles remain open later work. Item 5.3 merged as PR #55 at
`c6d7fc13a09a`.

Phase 5.4's `deterministic-export-pack-zip-v1` merged as PR #56 at
`499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`. The optional post-export
transport uses the existing `package` / `package-verify` command family to wrap
canonical `export-receipt.json` plus its exact bound file set as `.vfexport.zip`
under a separately retained receipt digest. It consumes the existing embedded
plan and receipt without changing the ten persisted verified-export v1 models
or the three production selectors. Receipt-anchored archive verification
preserves the embedded source trust grade and is not source-bound export
verification. It adds no consumer/trainer profile, request version, MCP
operation, or Mac UI action.

Phase 5.5 merged as PR #57 at
`c72b8e9ec7bc2746d74404226aa086d497e15db1` as test-only consolidated evidence
over the unchanged three production selectors. A frozen ordinary-file fixture reloads
all eleven compatible container/schema pairs to the identical ordered train and
evaluation payloads, complete provenance, and source `RowSet`. It also proves a
canonical semantic tamper fails for each container and preserves constrained
CSV's actionable pre-publication refusal for nested `messages`. The fixture is
not a product importer or public semantic replayer and changes no API, persisted
schema, taxonomy, support state, consumer profile, or trainer claim.

Phase 5.6 exposes exact bounded runtime information through the existing
dry-run operation. Response v2 contains exactly the unchanged plan summary and
one `veriformis.export-dry-run-preview/v1`: ordinal zero from each non-empty
train/evaluation partition, complete exact payloads only at or below 65,536
canonical UTF-8 JSON bytes and within the response budget, and the sorted
plan-derived relative destination tree plus `export-receipt.json`. Omission is
whole-row with an exact reason, never truncation or paraphrase. ASCII-safe
transport decodes to the exact original values. Preview derivation calls no
renderer and accesses no destination. The ten persisted verified-export v1
models, request v1/v2, discovery v1, production selectors, taxonomy, support
state, and trainer-neutral boundary remain unchanged. Item 5.6 passed all 14
GitHub checks and merged as PR #58 at
`cd017941090c7352cb1d10f9a383042b954d4f2e`.

Phase 5.7 publishes the [generic export operator guide](generic-exports.md) and
closes Phase 5. The guide separates objective, semantic row schema, physical
container, and consumer profile; it records the exact compatibility matrix and
does not create a trainer, spreadsheet, importer, renderer, or support claim.

The private Phase 4.7 hooks are trusted conformance code rather than an
untrusted plugin boundary. Semantic replay currently retains each complete
produced file in memory; its fixture is statically bounded. Before any semantic
profile is shipped, that profile must define and enforce explicit byte, record,
nesting, and other applicable resource limits.

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
training execution remains outside Veriformis. The independent product ships
three `portable_exact_bytes` generic containers, `split-jsonl-directory`,
canonical `json`, and `constrained-csv` v1, plus three
`semantic_content_only` generics, `parquet`, `arrow`, and
`hugging-face-dataset` v1. None selects a trainer or claims trainer
compatibility. Taxonomy lists the three columnar containers as
implemented. TRL, MLX-LM, Axolotl, LLaMA-Factory, and Aptus are
implemented optional adapters. Extra `columnar` and the trainer extras
stay empty. There is no Hub upload. Unsloth remains a non-executable
candidate. The exporter does not train.

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
- [Deterministic Archive Transport v1](./contracts/bundle-transport-v1.md)
- [Verified Export Contract v1](./contracts/verified-export-v1.md)
- [Split JSONL Export Contract v1](./contracts/split-jsonl-export-v1.md)
- [Canonical JSON Export Contract v1](./contracts/canonical-json-export-v1.md)
- [Constrained CSV Export Contract v1](./contracts/constrained-csv-export-v1.md)
- [ADR-0006: Receipt-Anchored Export-Pack Transport](./adr/0006-receipt-anchored-export-pack-transport.md)
- [Current implementation status](./current-status.md)
- [Architecture](./architecture.md)
- [Existing design specification](./superpowers/specs/2026-07-28-veriformis-design.md)
- [Completed M1 implementation record](./superpowers/plans/2026-07-28-veriformis-m1.md)
