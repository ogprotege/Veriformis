# Current Implementation Status

**Product version:** `0.1.0`

**Maturity:** Development alpha

**Implementation state:** M1 core plus Group 1 integrity foundation

**Review date:** 2026-07-29

This document separates implemented behavior from planned behavior. It is the
current source of truth for `0.1.0` capability claims.

## Executive status

Veriformis is a working deterministic compiler core with a stage-command CLI.
It captures raw source bytes, parses supported files into canonical IR, records
known extraction changes, cleans through replayable plans, chunks with source
evidence, emits current M1 row projections, runs three validation gates, and
writes the current hash-bearing bundle shape.

Group 1 is implemented. Workspaces now use immutable revisions and
content-addressed objects. Identities are source-scoped. Parser reports are
mandatory. Chunk provenance resolves through immutable source evidence.
Cleaning preview and application share one planner and replay engine. IR,
parse reports, transforms, chunks, and evidence have strict versioned persisted
schemas.

Veriformis is not yet the complete raw-source-to-finished-dataset product. It
still lacks recipe-driven record construction, candidate lifecycle, curation,
quality policy, authoritative train and evaluation splits, structured training
rows, exact bundle validation, a closed seal boundary, and a stable shared
application API.

The [authoritative roadmap](plans/2026-07-29-veriformis-roadmap.md) assigns that
work to Groups 2 through 4.

## Implemented interfaces

The installed console entry point is `veriformis`.

| Command | Implemented behavior | Revision outputs or external result |
| --- | --- | --- |
| `parse paths... -o WORKSPACE` | Captures and parses explicit supported paths in one transaction | `registry`; per-source `raw`, `canonical`, `document`, and `diagnostics` keys |
| `clean WORKSPACE` | Plans, replays, and commits selected deterministic rules per source | `transforms`; per-source `document`, `cleaning-plan`, and `block-derivations` keys |
| `chunk WORKSPACE` | Runs one of five evidence-bearing chunking strategies | `chunks` |
| `format WORKSPACE --format FORMAT` | Emits completion, instruction, or rendered-chat rows | `records`, `records-meta` |
| `validate WORKSPACE --format FORMAT` | Runs schema, encoding, and evidence-based provenance gates | `validations` |
| `seal WORKSPACE -o BUNDLE` | Reads one validated revision and writes the current bundle shape | External `dataset.jsonl`, `manifest.json` |
| `preview PATH` | Plans and replays cleaning over one file without writes | Terminal output only |
| `version` | Prints the package version | Terminal output only |

There is no `run`, `verify`, MCP, GUI, or YAML-pipeline CLI command in `0.1.0`.

## Workspace and identity status

The workspace contains `workspace.json`, `HEAD`, `LOCK`, immutable revision
manifests, content-addressed objects, and a transaction directory. `HEAD`
selects the current revision. A successful stage becomes visible through one
atomic pointer replacement. Failed or interrupted pre-commit work leaves the
previous revision current.

Parse and clean cross-validate their semantic artifacts before that pointer
replacement. Parse checks the registry, source descriptors, canonical text,
exact IR projection, and reports. Clean checks parsed and cleaned IR, replayed
plans, block derivations, and transform records.

Commits verify an expected parent revision under an exclusive lock. A stale
writer fails with `workspace-revision-conflict`. Opening a workspace verifies
the complete parent chain through the init revision and every historical
revision's referenced object digests. A legacy flat workspace is rejected
pending explicit migration.

If `HEAD` becomes visible but its final directory sync fails, the commit returns
as committed and exposes a crash-durability warning through the workspace API
and CLI. This avoids falsely reporting rollback after the commit point.

Stage dependencies are active. Parse invalidates every later stage. Clean
invalidates chunk through seal. Chunk invalidates format through seal. Format
invalidates validation and seal. Validation invalidates seal. Invalidated
outputs remain available only through older immutable revisions.

Source IDs bind normalized logical paths and raw digests. Artifact IDs also
bind content, producer, configuration, and source scope. Cleaning operations,
plans, derivations, evidence, chunks, and revisions use deterministic,
domain-separated identities. Same-basename sources and distinct logical source
instances with identical bytes remain distinct.

`parse --source-root ROOT` defines the portable locator root and defaults to
the current directory. Inputs outside that root fail closed. Source identity
does not depend on which other files appear in the same parse batch.

Persisted artifact JSON and durable identity and configuration-digest payloads
preserve exact Unicode string and object-key sequences. Those durable paths
apply NFC normalization only to explicit locator fields, currently logical
source paths, before identity derivation. Exact content hashes still bind
stored bytes. Revision IDs are audit identities that include parent history
and commit time. They can differ across equivalent runs. Portable state digests
and per-source parse-input digests bind reproducible semantic state.

Step 4 identity coverage applies only to current source, artifact, transform,
chunk, and revision primitives. Steps 5 and 6 also identify diagnostics,
evidence, cleaning operations, and plans. Candidate, dataset-record, and split
types are not implemented. Later groups must adopt the same identity substrate.

## Supported inputs and diagnostics

| Input | Current behavior |
| --- | --- |
| `.txt` | UTF-8 blank-line paragraph parsing with canonical-stream spans and separator-normalization diagnostics |
| `.md`, `.markdown` | Markdown parsing into canonical IR with located diagnostics for HTML, Pandoc metadata, and unsupported tokens |
| `.docx` | Body and note parsing with OOXML-located diagnostics for unsupported constructs, normalization, unresolved notes, and unavailable page provenance |
| `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`, `.rb`, `.sh` | UTF-8 text captured as one language-tagged code block |

Every supported parser returns a `ParseReport`. A report can be empty. Its
status, typed diagnostics, locations, diagnostic IDs, and report digest are
persisted with the source. HTML, PDF, CSV, JSON, and JSONL ingest are not
implemented. OCR is not implemented.

The canonical visible-text projection preserves image alt text, citations,
and footnote and endnote references. Note bodies share the canonical artifact
but retain `footnote:<id>` and `endnote:<id>` regions distinct from `body`.
Metadata visible only in IR, such as link targets and image sources or titles,
does not yet have field-level evidence. Group 2 must add that evidence before
implementing `structured_field` construction.

## Cleaning and source evidence

Available cleaning rules are:

- `page-numbers`
- `headers-footers`
- `whitespace`
- `urls`
- `emails`
- `special-chars`
- `lowercase`
- one custom removal regular expression

When no explicit rule or custom expression is supplied, the CLI applies
`page-numbers` and `whitespace`. A rule that would remove more than 30 percent
of its target is skipped and reported.

Each clean run creates a source-scoped `CleaningPlan`. It records rule
configuration, ordered operations, allowed paths, source locations, before and
after digests, character and UTF-8 byte counts, warnings, a per-source
parse-input digest, and identity. Clean replays that plan before committing its
output. Tampered plans fail replay.

Rich wrappers survive supported text edits. Structural removal is restricted
to supported explicit operations.

Inline code, code blocks, math, and other literal payloads are no-op regions
for current prose cleaning rules. No current rule may silently change their
program or mathematical meaning.

The `preview` command accepts both built-in rules and `--custom`. It uses the
same planner and replay engine as `clean`, prints its plan ID, and writes
nothing. Given the same source locator, bytes, parser, rules, and cleaning
configuration, raw-file preview, workspace preview, and clean produce the exact
same plan ID.

Every current chunk stores `SourceEvidence`. Evidence binds canonical source
ranges and ordered edit, slice, or join derivations. It verifies source and
artifact identity, range bounds and digest, each derivation, and the final text
digest. Sentence and transformed chunks have no evidence bypass.

Chunks stay within one body, footnote, or endnote region, and the region is
bound into evidence and chunk identity.

## Current record modes

| Mode | Current representation | Status |
| --- | --- | --- |
| `completion` | `{"text": chunk_text}` with optional heading prefix | Implemented full-sequence projection |
| `instruction` | One supplied instruction, heading path as input, and chunk text as output | Experimental projection, not recipe-driven construction |
| `chat` | Generic summary request plus unchanged chunk answer, rendered to `text` | Semantically unsafe for trusted supervised-chat construction |

Current chat templates are `llama3`, `mistral`, `qwen`, `gemma`, and `phi`.
User-supplied template files are not implemented.

The chat limitation remains material. The code does not summarize, yet it
labels unchanged source text as a summary response. It also lowers the exchange
to rendered text before a trainer can apply structured masking rules.

## Current validation boundary

Validation reads one immutable revision and runs three gates:

1. **Schema:** Requires exact keys and string values for the selected current record mode.
2. **Encoding:** Reports selected mojibake markers and disallowed control characters in `text`, or in `output` for instruction rows.
3. **Provenance:** Reconstructs every chunk from immutable source evidence and requires exact text equality.

The result is committed with a complete or failed stage status. A failed or
stale validation stage cannot satisfy the seal dependency.

Validation does not establish:

- a declared training-objective or recipe relation;
- record-to-chunk cardinality or field-level record evidence;
- duplicate, PII, quality, coverage, curation, or balance policy;
- leakage groups or train and evaluation assignments;
- a non-empty dataset requirement;
- exact candidate-bundle closure; or
- compatibility with a specific Aptus backend.

## Current bundle boundary

`seal` writes:

```text
dataset.vfbundle/
├── dataset.jsonl
└── manifest.json
```

It reads the current immutable revision and refuses missing, failed, or stale
dependency stages. The manifest records current bundle, source, transform,
chunk, dataset, validation, version, and hash metadata.

Original source files, split files, a detached digest, and an Aptus descriptor
are not emitted. The command does not commit a workspace seal-stage artifact.

The Python `verify_bundle` function checks hashes for declared non-manifest
files. It skips the manifest self-hash, accepts undeclared extra files, and has
no signature or external trust anchor. No CLI `verify` command exists.

## High-impact remaining limitations

### Dataset construction is not implemented

The format stage projects chunks directly. It does not execute a versioned
`TrainingObjective`, `DatasetRecipe`, or ordered `ConstructionPass`. There are
no candidate, rejection, review, promotion, or immutable dataset-record states.

### Curation and splitting are not implemented

The current pipeline does not deduplicate, filter, account for coverage,
balance, or create authoritative leakage-safe train and evaluation assignments.

### Record lineage is not emitted

Chunk evidence exists inside the workspace, but current serializers emit only
payload fields. Rows do not retain record, chunk, source, transform, or evidence
identifiers. Exact-key M1 schema checks still reject added metadata.

### Exact seal closure is not implemented

Seal trusts the committed validation report instead of rerunning the full gate
set against a normalized candidate file set. The current verifier accepts
undeclared files and lacks an external digest. Empty output, path closure,
manifest trust, and post-validation mutation cases remain pinned to Step 16.

### Bundle bytes are not reproducible

Semantic workspace artifacts are deterministic for the same inputs and
configuration, even when audit revision IDs differ. Sealed bundles are not
byte-identical because each manifest contains a new random bundle ID and
current timestamp.

## Phase boundary

| Status | Capability |
| --- | --- |
| Implemented M1 | Canonical IR, supported parsers, deterministic rules, five chunkers, three row projections, three gates, stage CLI, and current bundle writer |
| Implemented Group 1 | Versioned transactional workspace, current source/artifact/transform/chunk/revision primitives, mandatory parse diagnostics, immutable source evidence, replayable cleaning plans, acceptance fixtures, and regression coverage |
| Planned Group 2 | Training objectives, recipes, construction passes, candidate lifecycle, and deterministic constructors |
| Planned Group 3 | Curation, leakage-safe splits, construction and serialization separation, Aptus-native rows, exact validation, atomic sealing, and independent verification |
| Planned Group 4 | `PipelineService`, thin CLI, and dual-objective M1.1 acceptance |
| Later | Expanded ingest and recipes, YAML, MCP, versioned Aptus handoff, and SwiftUI workbench |
| Future opt-in | Governed source-grounded model assistance through `GeneratorPass`, under a separate approved plan |
| Public release | Supported-platform gates, artifact evidence, packaging, signing, notarization, migration checks, and release verification |
| Outside current product | OCR, model training, cloud accounts, multi-user service, billing, and telemetry |

The deterministic pipeline remains offline and makes no LLM calls. The
roadmap does not permit model-assisted generation inside Groups 1 through 7.

## Development and release status

The project uses Python 3.11 or newer, a setuptools `src` layout, uv, Ruff,
and pytest. The Group 1 closeout requires:

```text
uv lock --check
uv run ruff check src tests
uv run pytest -q
git diff --check
```

Confirmed later-step defects remain visible as strict expected failures. A
Group 1 defect may not remain expected-failed when Group 1 closes.

Rerun these commands for current Group 1 closeout evidence. Test totals are
intentionally omitted because coverage grows. Strict expected failures remain
assigned to their later roadmap steps.

Repository CI currently runs on Ubuntu with Python 3.12. It does not yet
provide a Python-version matrix, type checking, coverage enforcement,
dependency review, package-install tests, macOS packaging, signing,
notarization, or public release automation.

Version `0.1.0` remains a development alpha, not a release-readiness claim.

## Next authority

Group 2 is next. It must build truthful dataset construction on the Group 1
integrity substrate. Use the [Veriformis Build Roadmap](plans/2026-07-29-veriformis-roadmap.md)
for the exact numbered order and exit gates.
