# Current Implementation Status

**Product version:** `0.1.0`

**Maturity:** Development alpha

**Implementation state:** M1 core plus Groups 1 and 2

**Review date:** 2026-07-29

This document separates implemented behavior from planned behavior. It is the
current source of truth for `0.1.0` capability claims.

## Executive status

Veriformis is a working deterministic compiler core with a stage-command CLI.
It captures raw source bytes, parses supported files into canonical IR, records
known extraction changes, cleans through replayable plans, chunks with source
evidence, and constructs evidence-bearing candidate and accepted records under
versioned recipes. It also retains the separate M1 path that projects chunks
directly, runs three validation gates, and writes the current hash-bearing
bundle shape.

Groups 1 and 2 are implemented. Workspaces use immutable revisions and
content-addressed objects. Identities are source-scoped. Parser reports are
mandatory. Chunk provenance resolves through immutable source evidence.
Cleaning preview and application share one planner and replay engine. IR,
parse reports, transforms, chunks, and evidence have strict versioned persisted
schemas. Construction adds five deterministic objectives, recipes, ordered
passes, field evidence, candidate decisions, optional review evidence,
immutable accepted records, and pre-commit semantic replay.

Veriformis is not yet the complete raw-source-to-finished-dataset product. It
still lacks curation, quality policy, authoritative train and evaluation
splits, construction-aware serialization, emitted product rows, exact
whole-dataset validation, a closed seal boundary, and a stable shared
application API.

The [authoritative roadmap](plans/2026-07-29-veriformis-roadmap.md) assigns that
work to Groups 3 and 4.

## Implemented interfaces

The installed console entry point is `veriformis`.

| Command | Implemented behavior | Revision outputs or external result |
| --- | --- | --- |
| `parse paths... -o WORKSPACE` | Captures and parses explicit supported paths in one transaction | `registry`; per-source `raw`, `canonical`, `document`, and `diagnostics` keys |
| `clean WORKSPACE` | Plans, replays, and commits selected deterministic rules per source | `transforms`; per-source `document`, `cleaning-plan`, and `block-derivations` keys |
| `chunk WORKSPACE` | Runs one of five evidence-bearing chunking strategies | `chunks` |
| `upgrade-workspace WORKSPACE` | Atomically migrates a verified revision-schema-v1 workspace to revision schema 2 | New migration revision, or no change when already current |
| `construct WORKSPACE --objective OBJECTIVE` | Runs one deterministic objective over an exact source selection and commits its lifecycle result | `recipe`, `result` |
| `format WORKSPACE --format FORMAT` | Emits completion, instruction, or rendered-chat rows | `records`, `records-meta` |
| `validate WORKSPACE --format FORMAT` | Runs schema, encoding, and evidence-based provenance gates | `validations` |
| `seal WORKSPACE -o BUNDLE` | Reads one validated revision and writes the current bundle shape | External `dataset.jsonl`, `manifest.json` |
| `preview PATH` | Plans and replays cleaning over one file without writes | Terminal output only |
| `version` | Prints the package version | Terminal output only |

There is no `run`, `verify`, MCP, GUI, or YAML-pipeline CLI command in `0.1.0`.

## Workspace and identity status

The physical workspace layout remains schema 1. Newly created and explicitly
migrated workspaces use revision schema 2, which adds the `construct` stage.
Verified unmigrated revision-schema-v1 workspaces continue producing v1
legacy-stage revisions until `upgrade-workspace` runs. The workspace contains
`workspace.json`, `HEAD`, `LOCK`, immutable revision
manifests, content-addressed objects, and a transaction directory. `HEAD`
selects the current revision. A successful stage becomes visible through one
atomic pointer replacement. Failed or interrupted pre-commit work leaves the
previous revision current.

Parse, clean, chunk, and construct cross-validate their semantic artifacts
before that pointer replacement. Construct reloads canonical recipe and result
artifacts, reconstructs the selected source, clean, chunk, transform, and IR
inputs, and requires exact deterministic replay before `HEAD` advances.

Commits verify an expected parent revision under an exclusive lock. A stale
writer fails with `workspace-revision-conflict`. Opening a workspace verifies
the complete parent chain through the init revision and every historical
revision's referenced object digests. `upgrade-workspace` appends the only
supported revision-schema-v1 to revision-schema-v2 migration. It preserves
every source, artifact, and legacy stage fact and adds `construct` as absent.
Pre-revision flat workspaces remain unsupported.

If `HEAD` becomes visible but its final directory sync fails, the commit returns
as committed and exposes a crash-durability warning through the workspace API
and CLI. This avoids falsely reporting rollback after the commit point.

Stage dependencies are active. Parse invalidates every later stage. Clean
invalidates chunk, construct, format, validate, and seal. Chunk invalidates
construct, format, validate, and seal. Construct currently has no downstream
stage because Group 3 has not connected it to formatting. Rerunning construct
therefore leaves the legacy format path unchanged. Format invalidates
validation and seal. Validation invalidates seal. Invalidated outputs remain
available only through older immutable revisions.

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

Step 4 established identities for source, artifact, transform, chunk, and
revision primitives. Steps 5 and 6 add diagnostics, evidence, cleaning
operations, and plans. Group 2 now applies the same substrate to objectives,
recipes, construction passes, IR evidence, candidates, reviews, decisions,
accepted records, construction diagnostics, and complete construction results.
Split assignments remain a Group 3 type.

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
can now use `IRFieldEvidence`. It binds the exact IR artifact, source, RFC 6901
pointer, scalar digest and encoding, output digest, and construction context.

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

## Dataset construction

Group 2 implements these exact objective field contracts:

| Objective | Constructed fields |
| --- | --- |
| `full_text` | `text` |
| `continuation` | `prompt`, `completion` |
| `section_reconstruction` | `heading`, `section` |
| `before_after_transformation` | `before`, `after` |
| `structured_field` | `input`, `fields` |

There is no deterministic `summary` objective and construction makes no LLM
calls. Full text retains complete source-grounded chunk text. Continuation uses
ordered, non-overlapping source slices. Section reconstruction requires
`structure` segmentation and groups all chunks for the exact cleaned-IR
heading and section body. Before-and-after construction requires a replayable
cleaning transform. Structured-field construction copies a verified scalar
leaf from strict cleaned IR. An ineligible source unit produces a typed
construction diagnostic instead of invented content.

A `DatasetRecipe` binds one objective, an exact sorted non-empty source set, the
active clean configuration digest, the active segmentation policy, ordered
constructor passes and versions, review policy, required construction gates,
and a declared product row schema. Its `curation_policy` and `split_policy` are
literally `deferred`. The row-schema declaration is one of `text`,
`prompt_completion`, `instruction_output`, or `messages`; Group 2 does not
serialize any of those rows.

`construct` selects every current source by default. Repeatable `--source`
options select an exact subset by source ID or logical path. Unknown selectors
and duplicates fail closed. The selected source IDs are bound into stage
configuration, recipe identity, input digest, and both output artifact scopes.
If a selected source has no constructible chunk, each pass emits the
deterministic `source-chunks-unavailable` diagnostic for that source while
other selected sources continue. This is explicit construction-omission
evidence, not Group 3 corpus-wide coverage accounting.

Each pass emits append-only `CandidateRecord` values with exact source, chunk,
transform, objective, recipe, pass, and field-evidence lineage. Every candidate
receives one `PromotionDecision`. A no-review recipe accepts candidates that
pass construction integrity. A required-review recipe leaves candidates
`pending_review` until separate `ReviewEvidence` accepts or rejects them. Only
accepted candidates become immutable `DatasetRecord` values, and promotion
copies their fields and lineage unchanged. The current CLI can request review
but does not yet ingest completed review evidence.

The construct revision contains exactly `recipe` and `result` outputs of kinds
`dataset-recipe` and `construction-result`. Before `HEAD` advances, the
workspace requires canonical JSON, exact source scope, active cleaning and
segmentation bindings, complete artifact lineage, field resolution, identity
checks, and semantic equality with a fresh deterministic replay. A repeat with
the same current inputs and options is a no-op revision.

The cleaned corpus remains an intermediate compiler state unless a `full_text`
recipe explicitly selects its retained sequences as the training target. For
the other four objectives, construction derives truthful context and target
fields from that state. Group 2 records those accepted fields, but Group 3 must
still curate, split, serialize, validate, and seal them as one dataset.

## Legacy M1 record modes

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

These modes are independent of `construct`. The current `format` command reads
chunks, not accepted `DatasetRecord` values.

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

### Construction is not connected to the finished-dataset path

The construct stage produces evidence-bearing accepted records. The format
stage still projects chunks directly and does not consume them. The current
validation and seal stages therefore do not establish or publish the declared
construction objective. A construction result is not yet a finished dataset.

### Curation and splitting are not implemented

The current pipeline does not deduplicate, filter, account for coverage,
balance, or create authoritative leakage-safe train and evaluation assignments.

### Record lineage is not emitted

Accepted construction records retain record, candidate, decision, recipe,
objective, pass, source, chunk, transform, and field-evidence lineage inside
the workspace. Current serializers emit only legacy payload fields. Emitted
rows do not retain that construction lineage, and exact-key M1 schema checks
still reject added metadata.

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
| Implemented Group 2 | Five training objectives, strict recipes and ordered passes, text and IR field evidence, candidate/review/decision/record lifecycle, exact source selection, deterministic diagnostics, semantic replay, and transactional construction artifacts |
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
and pytest. The current closeout requires:

```text
uv lock --check
uv run ruff check src tests
uv run pytest -q
git diff --check
```

Confirmed later-step defects remain visible as strict expected failures. A
Steps 1 through 10 defect may not remain expected-failed after Group 2 closes.

Rerun these commands for current Group 2 closeout evidence. Test totals are
intentionally omitted because coverage grows. Strict expected failures remain
assigned to their later roadmap steps.

Repository CI currently runs on Ubuntu with Python 3.12. It does not yet
provide a Python-version matrix, type checking, coverage enforcement,
dependency review, package-install tests, macOS packaging, signing,
notarization, or public release automation.

Version `0.1.0` remains a development alpha, not a release-readiness claim.

## Next authority

Group 3 is next. It must turn accepted construction records into a curated,
leakage-safe, serialized, exactly validated, atomically sealed dataset without
weakening Groups 1 or 2. Use the [Veriformis Build Roadmap](plans/2026-07-29-veriformis-roadmap.md)
for the exact numbered order and exit gates.
