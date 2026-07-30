# Architecture

**Last reviewed:** 2026-07-29 after Group 3 completion

**Next review:** The first Group 4 service change

This document describes the current Veriformis `0.1.0` architecture. Group 3
is complete. Its independent architecture and security review found no
unresolved Critical, High, or Important defect.

## Current system

Veriformis is a Python 3.11+ modular monolith with one installed entry point,
the `veriformis` CLI. Domain modules own strict persisted contracts and pure
transformations. The CLI remains the composition root until Group 4 adds a
surface-neutral service.

```text
raw local files
  -> capture exact bytes
  -> canonical IR + parser diagnostics
  -> replayable clean plan + cleaned IR
  -> chunks + reconstructible source evidence
  -> recipe-driven candidates + accepted records
  -> deterministic curation + coverage
  -> transitive leakage groups + authoritative partitions
  -> objective-preserving product rows + aligned provenance
  -> exact 17-gate snapshot validation
  -> atomic six-file seal + independent verification
```

Clean corpus state is intermediate unless `full_text` selects it as the exact
training target. Every other objective derives explicit context and target
fields before curation and serialization.

There is no shared `PipelineService`, YAML runner, MCP server, or macOS
application in `0.1.0`.

## Module boundaries

| Module | Current responsibility |
| --- | --- |
| `src/veriformis/contracts.py` | Product, integrity, construction, finished-dataset, stage, gate, schema, reason, and verification registries |
| `src/veriformis/identity.py` | Exact-string durable JSON, locator normalization, digests, and domain-separated deterministic identities |
| `src/veriformis/workspace.py` | Revision schemas, content-addressed objects, stage dependencies, migrations, locking, atomic commits, semantic replay, and corruption checks |
| `src/veriformis/diagnostics.py` | Located typed parser diagnostics and mandatory parse reports |
| `src/veriformis/evidence.py` | Immutable source ranges and replayable edit, slice, and join derivations |
| `src/veriformis/parsers/` | Plain text, source code, Markdown, and DOCX ingestion |
| `src/veriformis/ir/` | Canonical document model and strict `veriformis.ir/v1` serialization |
| `src/veriformis/rules/` | Deterministic rules, replayable cleaning plans, and transform records |
| `src/veriformis/chunkers/` | Five chunk strategies with source evidence |
| `src/veriformis/construction/` | Objectives, recipes, field evidence, constructors, candidate lifecycle, execution, and replay validation |
| `src/veriformis/datasets/` | Finished plan, curation, coverage, splitting, row lowering, provenance, snapshots, and exact validation |
| `src/veriformis/serializers/` | Retained legacy M1 projection and chat-preview helpers, not the active revision-v3 format boundary |
| `src/veriformis/validate/` | Legacy gates plus shared validation helpers; finished-dataset validation lives in `datasets/validation.py` |
| `src/veriformis/bundle/` | Legacy bundle compatibility, finished manifest and attestation models, atomic publisher, and independent verifier |
| `src/veriformis/cli.py` | Typer commands and current stage orchestration |

Domain functions are callable from Python, but there is no stable end-to-end
application API. Group 4 owns `PipelineService` and thin CLI conversion.

## Canonical recovery

Every supported parser emits a canonical `Document`, a hash-pinned source
reference, canonical extracted text, a canonical-stream version, and a
mandatory `ParseReport`. The report may contain no diagnostics.

The IR represents headings, paragraphs, lists, tables, code blocks,
blockquotes, images, math, links, citations, and notes. Body, footnote, and
endnote spans index one canonical extracted-text artifact but retain separate
logical regions. They do not claim raw-file byte positions.

The visible-text projection preserves image alt text, citations, and note
references. IR-only scalar metadata can be bound through `IRFieldEvidence`,
which records its source, immutable IR artifact, RFC 6901 pointer, value digest,
output digest, encoding, and construction context.

Parser diagnostics use format-native locations. Text can report line and raw
byte offsets. DOCX can report OOXML parts and XPath. Unsupported, normalized,
or omitted constructs remain explicit. Error diagnostics refuse promotion
before a revision becomes current.

Raw bytes are captured before parsing. The parse transaction cross-validates
the registry, source descriptors, raw artifact, canonical stream, IR
projection, and diagnostics before changing `HEAD`.

## Identity model

Durable IDs use domain-separated `kind-v1-<64 hex>` forms.

- A source ID binds normalized logical path and raw SHA-256.
- An artifact ID binds content, producer, version, configuration, and source scope.
- Cleaning plans, transforms, evidence, and chunks bind their semantic payloads.
- Objectives, recipes, passes, candidates, decisions, reviews, records,
  diagnostics, and results bind their complete construction semantics.
- Plans, curation results, leakage groups, split assignments, product rows,
  provenance, snapshots, reports, manifests, attestations, and verification
  results bind their complete finished-dataset semantics.
- A portable state digest binds current semantic workspace state.
- A revision ID also binds its parent and commit time for audit history.

Identical bytes at different logical paths remain separate sources. Absolute
host paths and timestamps do not define semantic dataset state.

Artifact JSON and durable identity payloads use exact-string deterministic
serialization. Distinct Unicode normalization forms remain distinct except in
fields whose contract defines equivalence, currently logical source paths.

## Transactional workspace

The physical layout remains schema 1:

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

Active workspaces use revision schema 3. `HEAD` is the only mutable commit
pointer. A stage writes content-addressed objects and an immutable revision
before atomically replacing `HEAD`. Commits hold an exclusive lock and require
the expected parent. Interrupted pre-commit work leaves the prior revision
current.

Opening a workspace verifies every revision in the active parent chain and
every object that those revisions reference. Missing history or altered bytes
fail closed.

If `HEAD` changes but final directory sync fails, the API returns the visible
revision with a durability warning. It does not report rollback after readers
can observe the commit.

`upgrade-workspace` migrates verified revision v1 through v2 to v3 as needed.
The v2 to v3 migration preserves parse, clean, chunk, and construct facts. It
adds curate and split as absent and retires legacy format, validate, and seal
state in the new revision. Historical revisions and objects remain unchanged.

### Stage graph

```text
parse -> clean -> chunk -> construct -> curate -> split -> format -> validate -> seal
```

The direct dependencies are:

| Stage | Dependencies |
| --- | --- |
| `parse` | none |
| `clean` | `parse` |
| `chunk` | `clean` |
| `construct` | `parse`, `clean`, `chunk` |
| `curate` | `construct` |
| `split` | `construct`, `curate` |
| `format` | `construct`, `curate`, `split` |
| `validate` | `parse`, `clean`, `chunk`, `construct`, `curate`, `split`, `format` |
| `seal` | `parse`, `clean`, `chunk`, `construct`, `curate`, `split`, `format`, `validate` |

Rerunning any stage invalidates all descendants. Old outputs remain only in
historical revisions.

### Logical stage outputs

| Stage | Logical output keys |
| --- | --- |
| Parse | `registry`; per-source `raw`, `canonical`, `document`, `diagnostics` |
| Clean | `transforms`; per-source `document`, `cleaning-plan`, `block-derivations` |
| Chunk | `chunks` |
| Construct | `recipe`, `result` |
| Curate | `plan`, `result` |
| Split | `result` |
| Format | `row-set`, `train`, `evaluation`, `provenance` |
| Validate | `snapshot`, `report` |
| Seal | `manifest`, `attestation` |

Each Group 3 stage configuration and semantic artifact binds the same
`plan_id`. Workspace commit validation reloads and replays curate, split,
format, validate, and seal semantics before promoting the revision.

## Replayable cleaning and chunks

Cleaning separates planning from replay. A source-scoped plan binds rules,
parameters, ordered operations, allowed document paths, source locations,
before and after digests, character and byte counts, warnings, source identity,
and a portable parse-input digest.

Preview and clean share the same planner and replay engine. Clean persists its
plans, cleaned documents, block derivations, and transform log in one revision.
Tampered input, paths, operations, or identities fail replay.

Rich wrappers survive supported text edits. Current prose rules do not edit
inline code, code blocks, math, or other literal payloads.

Every chunk has `SourceEvidence` that resolves its text through immutable
canonical ranges and ordered derivations. Evidence checks the source artifact,
range bounds, range digest, derivation identities, and final output digest.
Chunking never crosses body, footnote, or endnote regions.

## Dataset construction

One strict `TrainingObjective` declares one of five field shapes:

- `full_text`: `text`;
- `continuation`: `prompt`, `completion`;
- `section_reconstruction`: `heading`, `section`;
- `before_after_transformation`: `before`, `after`;
- `structured_field`: `input`, `fields`.

A `DatasetRecipe` binds the objective to exact sources, cleaning,
segmentation, ordered constructors, review policy, construction gates, and the
product row schema. Constructors emit evidence-bearing candidates and
typed diagnostics. Decisions accept, reject, or hold each candidate for
review. Accepted candidates become immutable records without changed fields or
lineage.

Construction is pure, local, and deterministic. The workspace reloads the
canonical recipe and result, reconstructs source, clean, chunk, transform, and
IR inputs, and compares them with fresh replay before commit.

## Finished plan and curation

`FinishedDatasetPlan` composes one exact recipe and construction result with:

- a curation policy;
- a split policy;
- a serialization plan;
- all 17 required validation gates; and
- the `minimal-v1` retention profile.

Curation revalidates Group 2 construction and executes minimum target length,
source-scoped conflict quarantine, exact deduplication, optional
primary-source cap, and coverage closure in that order. Every construction
record receives one decision. Nothing disappears without a reason.

Exact duplicate families keep the lexicographically smallest record ID.
Conflicts quarantine every record in the conflicting class. Coverage records
candidate, record, status, and contribution counts for every selected source,
plus any blocker code that prevents a valid finished dataset.

## Leakage-safe splitting

Only included representative records enter splitting. The splitter connects
records through shared source IDs, equal raw digests, multi-source joins, and
the full inherited source relation from excluded exact duplicates. Transitive
components form indivisible leakage groups.

The policy hashes each group with its seed, orders the groups, and chooses a
non-empty proper prefix closest to the requested evaluation record count. A
tie chooses the shorter prefix. Evaluation is required by default. A plan can
explicitly permit an empty evaluation partition when fewer than two groups
exist.

The result binds groups, one assignment per included record, requested and
realized counts, and one assignment digest.

## Construction-aware serialization

The revision-v3 format stage consumes accepted records through the finished
plan, curation result, and split result. It never projects chunks as rows.

The objective provides exact context and target fields. The recipe and
serialization plan select one allowed row schema:

- `text` for `full_text` only;
- `prompt_completion` for source-derived supervised objectives;
- `instruction_output` with one exact plan-bound instruction literal; or
- structured two-turn `messages` with source context as user and target as the
  final assistant turn.

Each included record produces exactly one payload row and one provenance row.
Payload JSONL contains only the selected Aptus schema keys. The separate
provenance stream binds row and payload digests to all record, evidence,
curation, leakage, assignment, partition, and ordinal identities.

Rows are ordered by record ID inside each partition. The combined row set and
provenance order is train first, then evaluation.

## Exact validation

Validation constructs one immutable snapshot from exact active artifacts and
the three planned JSONL byte streams. It runs all required gates in order:

```text
construction-replay, record-lifecycle, curation, deduplication,
quality, balance, coverage, split, leakage, row-binding, objective,
schema, encoding, masking, partition-nonempty, aptus-row-shape, snapshot
```

All gates report. A valid failing report persists with failed stage status.
Dependent gates become blocked when a critical input cannot be read. A passing
Boolean detached from the snapshot has no authority.

The `aptus-row-shape` gate proves only the current row shape. It does not prove
shared bundle intake or backend split enforcement.

## Finished bundle and seal

The exact `minimal-v1` file set is:

```text
name.vfbundle/
├── data/train.jsonl
├── data/evaluation.jsonl
├── metadata/row-provenance.jsonl
├── validation.json
├── manifest.json
└── attestation.json
```

Seal rebuilds the current report and requires byte-semantic equality with the
saved passing report. It writes the four validated payloads to a private
temporary sibling without reserialization, creates a deterministic manifest
and attestation, syncs the tree, runs the independent verifier, rechecks the
expected workspace revision, and atomically promotes the directory without
overwrite.

The manifest binds exact paths, roles, media types, sizes, digests, record
counts, snapshot, validation report, and content root. It does not hash itself.
The co-located attestation binds the exact manifest digest, content root,
bundle, snapshot, and report.

The verifier walks the actual tree without following links and requires the
exact file and directory set. It checks canonical safe paths, regular-file and
hard-link policy, digests, counts, payload and provenance alignment, included
curation decisions, source coverage, conflict and dedup closure, leakage group
consistency, reconstructed row-set identity and bytes, validation binding, and
attestation binding.

Two grades keep the trust claim precise:

- `self_consistent` means all internal structure and bindings agree.
- `external_digest` adds a matching expected manifest SHA-256 supplied through
  a separate trusted channel.

Source replay remains a validation responsibility. It is not a verifier grade.

Directory publication and workspace receipt commit are separate atomic
operations. If the bundle becomes visible before receipt commit fails, the CLI
reports the published path and digest and does not claim rollback.

Publication assumes an integrity-controlled destination parent. Veriformis
anchors staging operations to open directory descriptors and never recursively
cleans a path whose identity changed. The no-replace rename protects cooperating
writers and ordinary failures. It does not claim isolation from a hostile
same-owner process that can rename entries in the parent during the system call.
That threat requires OS permission isolation. A separately retained manifest
digest detects later substitution.

## Application surface boundary

The current CLI calls domain functions directly and owns stage ordering, state
loading, and user-facing errors. This is valid Group 3 behavior, but it is not
the final application boundary.

Group 4 must add:

1. a typed surface-neutral `PipelineService`;
2. a thin CLI adapter over that service; and
3. the dual-objective M1.1 acceptance gate through both API and CLI.

Later groups add remaining input adapters, broader policies, MCP, the shared
Aptus handoff, and the SwiftUI workbench.

## Related documentation

- [Product contract](product-contract.md)
- [Integrity Contract v1](contracts/integrity-v1.md)
- [Dataset Construction Contract v1](contracts/dataset-construction-v1.md)
- [Finished Dataset Contract v1](contracts/finished-dataset-v1.md)
- [Current implementation status](current-status.md)
- [CLI reference](cli.md)
- [Development guide](development.md)
- [Build roadmap](plans/2026-07-29-veriformis-roadmap.md)
