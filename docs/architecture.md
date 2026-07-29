# Architecture

This document describes Veriformis `0.1.0` after the Group 2 dataset-construction
work. Later finished-dataset architecture is labeled separately. See the
[build roadmap](plans/2026-07-29-veriformis-roadmap.md) for the ordered path to
the complete product.

## Current system

Veriformis is a Python 3.11+ package with one installed entry point, the
`veriformis` CLI. The CLI still owns orchestration, error presentation, and
stage ordering. Domain modules own the persisted contracts and transformations.

```text
raw local files
   -> capture raw bytes
   -> parse into canonical IR + diagnostics
   -> clean through a replayable plan
   -> chunk with reconstructible source evidence
   +-> construct evidence-bearing accepted records
   |
   +-> format current M1 chunk projections
       -> validate one immutable revision
       -> seal the current M1 bundle shape
       -> dataset.jsonl + manifest.json
```

Construction and the legacy M1 projection path are separate after chunking.
Group 3 will make serializers consume accepted records. Curation, split,
product-row, exact-validation, and closed-seal contracts remain unimplemented.

There is no shared pipeline service, YAML runner, MCP server, or macOS
application in `0.1.0`.

## Module boundaries

| Module | Current responsibility |
| --- | --- |
| `src/veriformis/contracts.py` | Public product, integrity, construction, canonical-stream, source-kind, objective, row-schema, stage, and error-code constants |
| `src/veriformis/identity.py` | Exact-string durable JSON, NFC-normalized logical paths, digests, and domain-separated deterministic identities |
| `src/veriformis/workspace.py` | Versioned revisions, content-addressed objects, stage dependencies, locking, atomic commits, and corruption checks |
| `src/veriformis/diagnostics.py` | Located, typed parser diagnostics and mandatory parse reports |
| `src/veriformis/evidence.py` | Immutable source ranges and replayable edit, slice, and join derivations |
| `src/veriformis/parsers/` | Plain text, source code, Markdown, and DOCX ingestion |
| `src/veriformis/ir/` | Canonical document model and strict `veriformis.ir/v1` JSON serialization |
| `src/veriformis/rules/` | Deterministic rules, replayable cleaning plans, and transform records |
| `src/veriformis/chunkers/` | Paragraph, fixed, sliding, sentence, and structure chunking with source evidence |
| `src/veriformis/construction/` | Strict objectives and recipes, text and IR field evidence, deterministic constructors, lifecycle models, execution, and replay validation |
| `src/veriformis/serializers/` | Current completion, instruction, and rendered-chat projections |
| `src/veriformis/validate/` | Schema, encoding, and evidence-based provenance gates |
| `src/veriformis/bundle/` | Current bundle manifest, writer, and programmatic verification |
| `src/veriformis/cli.py` | Typer commands and current full-pipeline orchestration |

The domain modules are callable from Python. The package does not yet expose a
stable end-to-end application API. Steps 17 and 18 introduce a typed
`PipelineService` and reduce the CLI to an adapter.

## Canonical recovery

Every supported parser emits a `ParseResult` containing:

- a canonical `Document` IR;
- a hash-pinned `SourceRef`;
- canonical extracted text and its digest;
- the canonical-stream contract version; and
- a mandatory `ParseReport`, which may contain no diagnostics.

The document IR represents headings, paragraphs, lists, tables, code blocks,
blockquotes, images, math, links, citations, notes, and rich inline marks.
Body, footnote, and endnote block spans index one canonical extracted-text
artifact. They do not claim raw-file byte positions.

The canonical visible-text projection retains image alt text, citations, and
footnote and endnote references. Note bodies follow the body in the shared
canonical stream, but `body`, `footnote:<id>`, and `endnote:<id>` remain
distinct logical regions for chunking and source evidence. IR-only metadata,
such as link targets and image sources or titles, remains in the strict IR.
Group 2 `IRFieldEvidence` can bind one strict-IR scalar to its source, immutable
artifact, RFC 6901 pointer, exact value and output digests, encoding, and
construction context.

Parser diagnostics use format-native locations. Text diagnostics can report
lines and raw byte offsets. DOCX diagnostics can report an OOXML part and
XPath. Markdown HTML and Pandoc omissions, unknown Markdown tokens, text
separator normalization, DOCX page provenance limits, and unsupported or
normalized DOCX body and note constructs are explicit. Error diagnostics
refuse the parse before a workspace revision becomes visible.

Raw bytes are captured once before parsing. The parse revision retains the raw
artifact, canonical text, document IR, and diagnostics for each source.
Before `HEAD` changes, the transaction cross-validates the source registry,
canonical artifact, exact IR projection, and parse report. A refused or
inconsistent parse never becomes current.

Persisted IR, parse reports, transform records, chunks, and source evidence use
strict versioned schemas. Their loaders reject unknown or missing fields and
recompute durable identities or digests where applicable.

## Identity model

Durable IDs use a domain-separated `kind-v1-<64 hex>` form.

- A source ID binds the normalized logical path and raw SHA-256.
- An artifact ID binds content, producer, version, configuration, and source scope.
- Cleaning operations, plans, transforms, derivations, evidence, and chunks bind their semantic payloads.
- Objectives, recipes, passes, IR evidence, candidates, reviews, decisions, accepted records, construction diagnostics, and results bind their complete semantic payloads.
- A portable state digest binds current semantic workspace state.
- A revision ID also binds its parent and commit time for audit history.
- Duplicate durable identities or inconsistent persisted identities fail closed.

Two sources with identical bytes but different logical paths remain distinct.
Two inputs with the same basename also remain distinct when their logical paths
differ. Absolute paths and timestamps do not define semantic workspace state.
The CLI derives all logical paths from one explicit `--source-root`, so adding
another source to a parse batch cannot change an existing source identity.

Artifact JSON and durable identity and configuration-digest payloads use
exact-string deterministic serialization, so distinct Unicode normalization
forms remain distinct. Those durable paths apply NFC normalization only to
explicit locator fields, currently logical source paths, before identity
derivation. Exact content digests still bind the persisted bytes.

Roadmap Step 4 applies this model to sources, artifacts, transforms, chunks,
and workspace revisions. Steps 5 and 6 also use domain-separated IDs for
diagnostics, evidence, cleaning operations, and plans. Group 2 extends it to
every construction object. Group 3 must add separate curation and split
identities without mutating accepted record identity.

## Transactional workspace

The workspace physical layout remains schema 1. Newly created and explicitly
migrated workspaces use revision schema 2. Verified unmigrated v1 workspaces
remain on revision schema 1 for legacy-stage commits until migration. The layout
is:

```text
workspace/
├── workspace.json
├── HEAD
├── LOCK
├── objects/
│   └── sha256/<prefix>/<digest>
├── revisions/
│   └── <revision-id>/revision.json
└── .txn/
```

`HEAD` is the only mutable commit pointer. Each successful stage writes
content-addressed objects and an immutable revision manifest before atomically
replacing `HEAD`. An interrupted commit before that replacement leaves the
previous revision current. Commits use an exclusive lock and verify the
expected parent revision. Stale writers fail with
`workspace-revision-conflict`.

Opening a workspace verifies the complete `HEAD`-to-init parent chain and the
content-addressed objects referenced by every revision in that chain. A missing
historical manifest or object fails closed instead of presenting an incomplete
audit history as intact.

The `HEAD` replacement is the commit point. If that replacement succeeds but
the final workspace-directory sync fails, the API returns the visible committed
revision and sets `Workspace.last_commit_durability_warning`. CLI commands emit
the same fact as `warning[commit-durability]`. They do not report a rollback
after readers can already observe the revision.

Each revision contains source descriptors, artifact descriptors, and a state
for every stage. A stage state records its inputs, configuration, logical
outputs, status, and invalidation evidence. `upgrade-workspace` appends the
only supported revision-schema-v1 to revision-schema-v2 migration. It preserves
all v1 source, artifact, and stage facts and adds `construct` as absent.
Pre-revision flat workspaces remain unsupported.

The revision ID is an audit identity. Two otherwise equivalent runs may have
different revision IDs because their parents or commit times differ. The
portable state digest excludes those historical fields. Semantic artifacts
use exact content and configuration identities. Cleaning binds each plan to a
portable per-source parse-input digest, not to a revision ID.

### Logical stage outputs

The revision manifest maps these exact keys to artifact IDs:

| Stage | Logical output keys |
| --- | --- |
| Parse | `registry`; `source/<source-id>/raw`; `source/<source-id>/canonical`; `source/<source-id>/document`; `source/<source-id>/diagnostics` |
| Clean | `transforms`; `source/<source-id>/document`; `source/<source-id>/cleaning-plan`; `source/<source-id>/block-derivations` |
| Chunk | `chunks` |
| Construct | `recipe`; `result` |
| Format | `records`; `records-meta` |
| Validate | `validations` |
| Seal | No workspace output yet. The current command writes an external bundle directory. |

Rerunning a stage invalidates every dependent stage. Parse invalidates all
later stages. Clean invalidates chunk, construct, format, validate, and seal.
Chunk invalidates construct, format, validate, and seal. Construct has no
downstream stage in Group 2, so it does not invalidate the legacy format path.
Format invalidates validation and seal. Validation invalidates seal. Stale
stages retain history in older revisions but expose no active outputs in the
new revision.

Construct commits use a strict stage configuration containing the construction
schema ID, recipe ID, and exact selected source IDs. Before `HEAD` advances,
the transaction reloads the recipe and result, requires canonical JSON and
exact artifact scope, reconstructs the selected source, clean, chunk,
transform, and cleaned-IR inputs, and compares the result with a fresh semantic
replay. A self-consistent result ID is not enough if the result does not replay.

## Replayable cleaning

Cleaning separates planning from replay. A source-scoped `CleaningPlan` binds:

- rule names, parameters, patterns, replacements, and flags;
- ordered operations and allowed document paths;
- source locations and before and after digests;
- character and UTF-8 byte counts;
- warnings, source identity, and a portable per-source parse-input digest; and
- a deterministic plan identity.

The CLI preview and clean commands use the same planner and replay engine.
Preview writes no workspace state. Clean persists each source plan, cleaned
document, block derivations, and the combined transform log in one revision.
Replaying a valid plan over its bound input produces the same output digest.
Tampered paths, identities, operations, or base content fail closed.

A raw-file preview supplied with the same source locator, source bytes, parser,
rules, and cleaning configuration as parse and clean produces the exact same
plan ID. Workspace preview either reuses that persisted plan or computes the
same plan from the parse artifacts. Before clean promotes `HEAD`, the
transaction replays and cross-validates every cleaned IR, cleaning plan, block
derivation set, and transform record.

Text edits preserve rich node wrappers when the edit can be represented safely.
Structural removal is restricted to explicit supported operations. Cleaning
does not silently convert a rich list, table, blockquote, image, or math node
into a plain paragraph.

Inline code, code blocks, math, and other literal payloads are not editable by
the current prose rules. Cleaning treats them as no-op regions unless a future
explicitly typed literal rule is added.

## Source evidence and chunking

A `SourceEvidence` object resolves emitted text through one or more immutable
canonical source ranges. Ordered edit, slice, and join derivations explain each
transformation. Every step binds input and output digests. Evidence resolution
checks the source artifact identity, range bounds, range digest, derivation
identity, and final output digest.

All current chunking strategies emit evidence. Sentence-packed and transformed
chunks no longer rely on a missing span or a Boolean `transformed` bypass. The
provenance gate reconstructs each chunk and compares the result with its text.
Chunking operates within one body or note region at a time and records that
region in both chunk identity context and source ranges.

## Dataset construction

Group 2 adds a pure construction subsystem after verified chunking. A strict
`TrainingObjective` declares one of five semantic field shapes:

- `full_text`: `text`;
- `continuation`: `prompt`, `completion`;
- `section_reconstruction`: `heading`, `section`;
- `before_after_transformation`: `before`, `after`;
- `structured_field`: `input`, `fields`.

A `DatasetRecipe` binds its objective to an exact source set, clean
configuration, segmentation policy, ordered constructor passes and versions,
review policy, required construction gates, and future target row schema.
Recipe curation and split policy values remain explicitly `deferred`. The row
schema is declared but is not emitted in Group 2.

Each constructor returns evidence-bearing drafts and deterministic diagnostics.
Drafts become append-only candidates with recipe, objective, pass, source,
chunk, and transform lineage. Every candidate receives one accepted, rejected,
or pending-review decision. Accepted candidates become immutable dataset
records with unchanged fields and lineage. Review-required recipes cannot
promote a candidate without separate review evidence.

Text fields resolve through Group 1 source evidence. Structured IR fields bind
an immutable document artifact and RFC 6901 scalar pointer. Missing source
chunks, missing section structure, unavailable IR, and other ineligible inputs
produce typed construction diagnostics. `source-chunks-unavailable` records a
selected source omitted by a pass without stopping valid sources. It is not a
substitute for Group 3 coverage accounting.

The cleaned corpus is an intermediate compiler state unless `full_text`
explicitly selects retained source-grounded sequences as targets. There is no
summary objective, remote generation, or LLM call in deterministic v1.

## Legacy M1 formatting

The current format stage still maps chunks directly into records:

- completion: `{"text": "..."}`;
- instruction: `{"instruction": "...", "input": "...", "output": "..."}`;
- chat: a model-template-rendered `{"text": "..."}` row.

Serializers do not preserve chunk identity or field-level evidence. The chat
path attaches `Summarize the following.` and copies the source chunk unchanged
as the assistant response. This is not a truthful summarization operation.
Rendered chat text also removes the prompt and assistant boundary needed for
completion-only masking in downstream trainers.

These serializers do not consume Group 2 `DatasetRecord` values. Group 3 must
separate accepted-record construction from target-schema lowering and add
provenance-bearing product rows.

## Current validation

Validation runs against one immutable workspace revision:

1. `schema` requires the exact key set and string values for the selected current format.
2. `encoding` detects selected mojibake markers and disallowed control characters in `text`, or in `output` for instruction rows.
3. `provenance` reconstructs every chunk from immutable source evidence.

The validation result is committed as `complete` or `failed`. A failed result
cannot satisfy the seal stage dependency. Validation does not yet cover recipe
semantics, record-to-chunk cardinality, duplicates, PII, coverage, balancing,
split leakage, or a complete closed bundle snapshot.

## Current bundle boundary

The current bundle contains:

```text
name.vfbundle/
├── dataset.jsonl
└── manifest.json
```

The seal command reads one immutable revision and refuses a failed or stale
validation stage. The current bundle writer still relies on persisted gate
results. It does not rerun the full gate set against a normalized candidate
file set or commit a workspace seal stage. Programmatic verification checks
declared payload hashes, but it skips the manifest self-hash and accepts
undeclared extra files. Original inputs are not copied into the bundle.

Atomic closed-set sealing, an external digest or attestation, path-safe
verification, and mutation tests belong to roadmap Step 16. Groups 1 and 2 do
not claim those defects are fixed.

## Planned product architecture

The implemented Groups 1 and 2 foundation supports the remaining ordered work:

1. Group 3 adds curation, leakage-safe splitting, construction-aware serialization, product rows, exact validation, atomic sealing, and independent verification.
2. Group 4 adds `PipelineService`, a thin CLI, and dual-objective M1.1 acceptance.
3. Later groups expand ingest and recipes, add MCP and Aptus contracts, and deliver the SwiftUI workbench.

The endpoint remains a finished, constructed, curated, split, validated, and
sealed dataset. Canonical and cleaned text are accountable intermediate states,
not the product boundary.

## Related documentation

- [Product contract](product-contract.md)
- [Integrity Contract v1](contracts/integrity-v1.md)
- [Dataset Construction Contract v1](contracts/dataset-construction-v1.md)
- [Current implementation status](current-status.md)
- [CLI reference](cli.md)
- [Development guide](development.md)
- [Build roadmap](plans/2026-07-29-veriformis-roadmap.md)
