# Veriformis: Design Specification

> **Status:** Historical product direction with current implementation-status amendments
>
> **Original date:** 2026-07-28
>
> **Last reviewed:** 2026-08-05 (status header only; body remains historical)
>
> **Repository:** `github.com/ogprotege/Veriformis`

> **Current implementation:** Groups 1 through 7 are implemented on `main` at
> version `0.1.0` (compiler through workbench). See
> [current implementation status](../../current-status.md).
>
> **Planned continuation:** Optional Group 8 and Group 9 public release gates.
> Body text below may still describe earlier surfaces as planned;
> **current-status.md controls present claims.**
>
> See the [product contract](../../product-contract.md),
> [current implementation status](../../current-status.md), and
> [build roadmap](../../plans/2026-07-29-veriformis-roadmap.md).
>

The target **Veriformis** product *(verus + forma, "true-formed")* is a local-first macOS
dataset compiler. It must own the full path from heterogeneous raw sources to finished,
validated, split, provenance-sealed training datasets. Aptus consumes the finished
dataset contract and owns training planning and execution.

---

## 1. Problem

Preparing a corpus for fine-tuning is the most painful, error-prone stage of the workflow:
documents arrive in mixed formats (PDF, DOCX, HTML, MD, TXT, code, CSV/JSON), every
conversion leaks or silently drops content, cleaning rules destroy data without record, and
the final step of shaping text into the exact chat or instruction template a model family
expects is done by hand with no validation. Nothing in the chain talks to anything else
without a translation barrier, and nothing tells you what was lost along the way.

Existing options are libraries (Unstructured, Docling) or cloud services (LlamaParse).
None are a local, private, Mac-native workbench with a complete audit trail and
fine-tuning-native output formats.

## 2. Product doctrine (non-negotiables)

1. **Canonical IR, hub-and-spoke.** Every supported unstructured input parses into one
   document IR. Typed structured inputs enter through declared adapters. Outputs derive
   from accepted dataset records, not separate format-to-format converters.
2. **Nothing silent and no impossible losslessness claim.** Originals remain hash-pinned.
   Parsing loss, unsupported structures, transformations, exclusions, deduplication,
   balancing, and filtering produce explicit evidence. Every accepted record field traces
   to immutable source evidence or a declared deterministic derivation. The enforceable
   contract is source conservation, derivation integrity, and coverage accounting. It does
   not mean that every source byte appears unchanged in every training record.
3. **Fail-closed.** A bundle that fails validation does not seal. An unsupported input
   (e.g., a scanned PDF with no text layer) is refused with a clear reason, never
   processed into garbage. (Aptus's evidence-ladder ethos, applied one stage earlier.)
4. **Deterministic v1.** The v1 dataset pipeline makes no LLM calls and performs no remote
   model generation. Cleaning, construction, curation, splitting, formatting, validation,
   and sealing are deterministic and testable. A future opt-in `GeneratorPass` requires a
   separate owner-approved plan and the same evidence, curation, review, split, validation,
   and sealing lifecycle. It is not a v1 release prerequisite.
5. **Local and private.** No cloud, no accounts, no telemetry. Documents never leave the
   machine. The corpus may contain sensitive unpublished scholarly material.

## 3. Scope

This section describes the intended product. Version `0.1.0` currently implements
Markdown, DOCX, plain text, source-code ingestion, canonical IR, replayable cleaning,
evidence-bearing chunks, five deterministic objectives, curation, authoritative splitting,
four product row schemas, exact validation, the `minimal-v1` finished bundle, independent
verification, and the stage-command CLI. PDF, HTML, structured input adapters,
`PipelineService`, MCP, and the macOS application remain planned.

### v1 in scope
- **Inputs:** Markdown, DOCX, plain text, HTML, digitally-born PDF (text layer present),
  source code files, JSON/CSV/JSONL (already-structured, validated passthrough).
- **Language:** English.
- **Objectives:** full-sequence text and truthful source-derived supervised objectives
  declared by a versioned `DatasetRecipe`.
- **Outputs:** validated JSONL training bundles using `text`,
  prompt-completion, instruction-output, or structured `messages` rows, with record-level
  evidence metadata and authoritative split assignments.
- **Surfaces:** Python library and CLI first, followed by the local MCP adapter and macOS
  SwiftUI workbench after their roadmap gates pass.
- **Integration target:** Aptus consumes the sealed dataset and split contract. Group 3
  validates row shape only. Training execution remains outside Veriformis.

### Explicitly out of scope (v1)
- OCR / scanned documents (refused cleanly; the future IR and provenance model
  are designed so page-image lineage and script metadata can be added without rework).
- Non-English language handling (same future-horizon design accommodation).
- LLM-based QA-pair / synthetic-data generation.
- Cloud sync, multi-user, auth, billing.
- Actual training (that is Aptus's job).

## 4. Architecture

Veriformis remains a layered modular monolith with one Python core. The current CLI is the
composition root. Groups 1 through 3 implement parsing through exact bundle verification.
The planned `PipelineService` will provide the stable surface-neutral boundary without
changing that deployment shape.

The subsections below preserve the original target design where a component remains
planned. [Current implementation status](../../current-status.md) controls present-tense
availability claims.

```text
CLI                 local MCP                 SwiftUI workbench
 |                      |                            |
 +----------------------+----------------------------+
                        |
                 typed PipelineService
                        |
raw sources -> parsers -> canonical IR -> replayable cleaning -> source evidence
                        |
                 versioned DatasetRecipe
                        |
                 ConstructionPass sequence
                        |
                  CandidateRecord set
                        |
          construction decision and optional review
                        |
              immutable DatasetRecord set
                        |
                curation and coverage
                        |
          balancing and leakage-safe split assignment
                        |
          Aptus row-shape formatting -> exact validation
                        |
             atomic bundle seal and verification
```

The current stage-command runtime reaches from supported raw sources through the Group 3
finished bundle. The diagram shows the target shared service and later adapters. Those
surface layers remain planned.

### 4.1 Document IR (`ir/`)
The spine: a canonical document model with first-class provenance, designed for
roundtrip fidelity.

- **Block nodes:** heading(level), paragraph, list(ordered?, depth), list_item, blockquote,
  code_block(language), table, image(ref, alt), math, footnote/endnote, thematic_break.
- **Inline:** text spans with marks such as bold, italic, code, link, superscript, subscript,
  citation marker.
- **Provenance:** every block carries `source_id`, optional `page`, and char offsets
  into the source's extracted text stream.
- Serializable to/from JSON (roundtrip-testable: parse → IR → serialize → parse ≡ identity).

### 4.2 Parsers (`parsers/`)
One module per format, each emitting IR + registering the source (path, sha256, size).
The md/docx pair is vendor-and-extend work (decision D1, §12). Proven canonical-IR
parsing code taken in-house and extended to attach provenance, no runtime dependency.
- `md`: canonical-IR markdown parser with provenance attachment.
- `docx`: OOXML (unzipped-XML) parser on the same IR, with provenance.
- `txt` / `code`: trivial; code keeps language tag from extension.
- `html`: readability-style main-content extraction → IR (see D4, §12).
- `pdf`: **pypdfium2** (Apache-2.0/BSD; *not* PyMuPDF, which is AGPL and would poison
  distribution). Page-level extraction preserves page provenance. Scanned/no-text-layer
  PDFs → fail-closed refusal naming OCR as the missing capability.
- `json`/`csv`/`jsonl`: structured passthrough with schema validation (feeds the
  serializer stage directly).

### 4.3 Cleaning rules (`rules/`)
Deterministic, ordered, composable rules; every firing logged as a transform record
(rule id, params, affected spans, bytes removed). Dry-run/preview is a first-class API
(the GUI's before/after view depends on it).

Rule library (from the salvaged UDP taxonomy, with its two known bugs fixed):
- `remove_headers_footers`: repeated line detection across pages (not naive ALL-CAPS).
- `remove_page_numbers`: **line-anchored** patterns only (`^\s*\d+\s*$`,
  `^Page \d+( of \d+)?$`). The tunerepo regex that deleted every standalone number is the
  canonical regression test.
- `normalize_whitespace`, `remove_urls`, `remove_emails`, `remove_special_chars`
  (whitelist-based, conservative), `to_lowercase`, `custom_regex` (user-supplied, logged
  verbatim).
- Safety valve: any rule that would remove more than a configurable fraction
  (default 30%) of a document warns instead of silently applying.

### 4.4 Chunkers (`chunkers/`)
- `fixed` (size + overlap), `sentence` (rule-based English splitter with abbreviation
  guard), `paragraph`, `sliding` (window + overlap; **short-document edge case fixed**:
  a doc smaller than the window yields one chunk, never zero), `structure` (heading-path
  aware: chunks never cross section boundaries; heading path stored as context).
- Every chunk carries: `chunk_id`, `source_id`, IR block path, char start/end,
  `heading_path`, token estimate.

### 4.5 Dataset recipes and construction (`construction/`)

A versioned `TrainingObjective` states what the model should learn. A versioned
`DatasetRecipe` binds that objective to source selection, cleaning and segmentation,
ordered `ConstructionPass` operations, target schema, construction gates, and optional
review policy. Group 3 `FinishedDatasetPlan` composes that immutable recipe and result with
executable curation, split, serialization, validation, and retention policy.

Each deterministic `ConstructionPass` emits append-only `CandidateRecord` objects with
field-level `SourceEvidence`. Built-in deterministic constructors cover full-text,
continuation, section reconstruction, logged transformation, and structured-field tasks.
Serializers do not invent an objective.

### 4.6 Curation, record promotion, and splitting (`datasets/`)

Curation records target-length findings, source-scoped conflicts, exact deduplication,
exclusions, quarantine, optional primary-source caps, and selected-source coverage.
Group 2 promotion creates immutable `DatasetRecord` values before Group 3 curation.
Rejected, pending-review, excluded, and quarantined values remain auditable.

Veriformis assigns authoritative train and evaluation partitions before formatting.
Related records share a leakage group, and the sealed bundle binds final membership and an
assignment digest. Under the future shared versioned contract, Aptus must consume those
partitions or exactly reproduce and verify them.

### 4.7 Serializers (`serializers/`)

Serializers lower accepted `DatasetRecord` objects into the recipe's declared row schema.
They do not create prompts, targets, review state, or split policy.

- `text`: retained sequence receives full supervision.
- `prompt` + `completion`: prompt is context; completion receives supervision.
- `instruction` + `input` + `output`: instruction and input are context; output receives
  supervision.
- structured `messages`: the future Aptus handoff renders the selected tokenizer contract
  and supervises only the final assistant suffix.

Payload JSONL contains only the selected training schema keys. Record identity, recipe
identity, construction-pass identity, source evidence, quality facts, leakage group,
assignment, partition, ordinal, and payload digest survive in one aligned provenance
stream. Rendered model-family chat text remains an unsealed preview or conformance
artifact.

### 4.8 Validation gates (`validate/`)

All gates report. The bundle seals only if every required gate passes against the exact
snapshot being published. Version `0.1.0` runs these 17 gates in order:

1. `construction-replay`
2. `record-lifecycle`
3. `curation`
4. `deduplication`
5. `quality`
6. `balance`
7. `coverage`
8. `split`
9. `leakage`
10. `row-binding`
11. `objective`
12. `schema`
13. `encoding`
14. `masking`
15. `partition-nonempty`
16. `aptus-row-shape`
17. `snapshot`

The Aptus gate proves row shape only. It does not prove a shared bundle handoff or backend
enforcement of Veriformis partitions.

### 4.9 Bundle and seal (`bundle/`)

The current `minimal-v1` bundle contains exactly:

```text
my-dataset.vfbundle/
├── data/train.jsonl
├── data/evaluation.jsonl
├── metadata/row-provenance.jsonl
├── validation.json
├── manifest.json
└── attestation.json
```

The validation snapshot transitively binds the plan, recipe, construction, curation,
split, and row set. The manifest binds the snapshot, validation report, content root, and
every permitted payload path, role, media type, size, digest, and record count.

Seal revalidates the exact saved passing report, writes validated bytes into a private
temporary sibling, creates a deterministic manifest and co-located attestation, syncs and
independently verifies the closed tree, rechecks the workspace revision, and promotes the
directory atomically without overwrite.

Verification rejects missing or extra paths, unsafe path forms, symlinks, hard-link policy
violations, special files, digest or count mismatches, row and provenance misalignment,
and validation or attestation mismatch. It reports `self_consistent` without an external
anchor and `external_digest` only when a caller supplies the matching manifest SHA-256.

### 4.10 Surfaces

- **CLI (`veriformis`):** Typer stage commands implement the current full runtime. Group 4
  will make this surface a thin adapter over `PipelineService`.
- **MCP server (`mcp/`):** Planned constrained local automation over the same service.
- **macOS GUI (`desktop/macos/`):** Planned SwiftUI workbench over authenticated local IPC
  and the same service.

Only the stage-command CLI exists in version `0.1.0`.

## 5. Data flow

```text
raw heterogeneous sources
  -> source registration and faithful parsing
  -> canonical IR plus explicit extraction diagnostics
  -> replayable cleaning and normalized corpus state
  -> source evidence units
  -> versioned recipe and deterministic construction passes
  -> candidate records
  -> construction decisions and optional review
  -> immutable dataset records
  -> deterministic curation and coverage
  -> balancing and leakage-safe split assignment
  -> Aptus row-shape formatting
  -> exact-snapshot validation
  -> atomic provenance-sealed bundle plus independent verification
```

A full-sequence text recipe may select the clean corpus state as its final training
objective. Supervised recipes continue through source-grounded record construction. Both
paths use the same curation, evidence, split, validation, and sealing contracts.

## 6. Error handling

The target application contract uses typed failures with human-readable reasons and stable
machine codes. Unsupported input is refused with the missing capability named. Failed or
stale required gates prevent sealing. CLI, MCP, and SwiftUI adapters must translate the
same service results without changing policy.

Version `0.1.0` uses stable typed domain errors across the integrity,
construction, finished-dataset, seal, and verifier boundaries. Group 4 must centralize
surface-neutral results so the CLI no longer owns orchestration or fallback presentation.

## 7. Testing strategy

Source fidelity, explicit loss accounting, and derivation integrity are testable claims:
- **Roundtrip fidelity:** IR → serialize → parse ≡ identity, per format.
- **Provenance integrity:** reconstruct accepted fields from the versioned canonical stream
  or their declared deterministic derivations and verify the original source hash.
- **Golden files:** fixture corpus per parser (including nasty cases: multi-column PDF,
  nested DOCX lists, malformed HTML, mixed encodings).
- **Rule-safety regressions:** the tunerepo number-deleting regex is enshrined as a test;
  every rule has must-keep/must-remove fixture pairs.
- **Property tests:** chunk coverage (no source text silently orphaned), size bounds,
  overlap correctness, sliding-window short-doc edge case.
- **Gate tests:** fail-closed behavior (bad bundle never seals; scanned PDF refused).
- **Template conformance:** rendered chat output diffed against reference tokenizer
  templates per model family.
- pytest; fixtures live in `tests/fixtures/`.

## 8. Stack & conventions

- The current core uses Python 3.11+, `uv`, `pyproject.toml`, Ruff, pytest, Pydantic v2,
  Typer, Jinja2, markdown-it-py, python-docx, and lxml.
- Later milestones may add pypdfium2, trafilatura, and fastmcp only when their roadmap
  steps begin.
- MIT license. Conventional commits. Current CI runs Ruff and pytest on Ubuntu with Python
  3.12. Broader build, platform, type, coverage, security, and release gates remain planned.
- Code conventions follow Aptus: contract-first modules, typed boundaries,
  no silent mutation, docs that state scope limits up front.

## 9. Repo layout

Current directories are unmarked. Planned directories are labeled.

```
Veriformis/
├── pyproject.toml / uv.lock
├── src/veriformis/
│   ├── ir/  parsers/  rules/  chunkers/  construction/  datasets/
│   ├── serializers/  validate/  bundle/
│   ├── cli.py
│   ├── pipeline/             # planned PipelineService
│   └── mcp/                  # planned local adapter
├── desktop/macos/            # planned SwiftUI workbench
├── tests/  fixtures/
├── docs/   (incl. this spec)
└── reference/tunerepo-salvage/   # lineage material (already imported)
```

## 10. Milestones and current state

- **M1, completed:** canonical IR, Markdown, DOCX, text and code parsers, deterministic
  cleaning, chunkers, initial serializers, schema, encoding and provenance gates, bundle
  writer, and stage-command CLI. See the completed M1 plan.
- **Groups 1 through 3 runtime, implemented:** transactional workspace, source-scoped
  identity, explicit loss diagnostics, recipe-driven construction, candidate promotion,
  deterministic curation, authoritative leakage-safe splits, contract product rows,
  exact validation, atomic seal, and independent bundle verification. Group 3 passed its
  independent architecture and security closeout.
- **M1.1 Group 4, planned:** shared `PipelineService`, thin CLI, and dual-objective
  raw-to-sealed acceptance through both direct API and CLI.
- **M2, planned:** remaining declared inputs, expanded deterministic builders, quality
  reporting, balancing controls, and repeatable YAML pipelines.
- **M3, planned:** constrained local MCP automation and the versioned Aptus handoff.
- **M4, planned:** macOS SwiftUI dataset workbench over the same service.
- **Future, optional:** separately approved `GeneratorPass` construction. This is not part
  of deterministic v1 and is not a prerequisite for public release.
- **Release:** documented, packaged, signed, notarized, installed, independently verified,
  and tested against a compatible Aptus release.

## 11. Lineage & salvage

- **tunerepo-salvage** (`reference/tunerepo-salvage/`): UDP cleaning/chunking taxonomy as
  reference spec (two known bugs documented in `SALVAGE-MANIFEST.md` and covered by
  regression tests), UDP playground as UX reference. Everything else from tunerepo was
  deliberately destroyed; the old repo and staging folder are deletable once this file
  is committed.
- **Aptus:** desktop packaging pattern and future dataset-contract integration target. The
  exact shared contract must be versioned and verified when its roadmap step begins.
- Certain md/docx parsing internals are vendored from the owner's prior private work
  (decision D1). That source is not named or referenced anywhere in this repository
  by request; it remains untouched.

## 12. Decisions

Resolved with the owner, 2026-07-28:

- **D1, md/docx parsing:** vendor-and-extend prior internal code (no runtime
  dependency on the private source; provenance fields added in-house).
- **D2, near-dup detection:** in v1, behind a flag (exact-hash always on).
- **D3, token statistics:** estimates in core; exact tokenizer counts via optional
  extra (`veriformis[tokens]`).
- **D4, HTML extraction:** trafilatura (MIT) primary; reassess at M2 if extraction
  quality disappoints on the golden-file corpus.
