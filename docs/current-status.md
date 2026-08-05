# Current Implementation Status

**Product version:** `0.1.0`

**Maturity:** Development alpha

**Implementation state:** Groups 1 through 7 complete

**Review date:** 2026-08-05 (docs sync after Group 7 merge to `main`)

**Next review:** The first Group 9 release-gate change, optional Group 8 plan,
or any contract change

This document is the current source of truth for implemented `0.1.0`
capability claims.

## Executive status

Veriformis is a local-first, offline dataset compiler from supported raw
sources to a closed, independently verifiable training-dataset bundle:

```text
parse -> clean -> chunk -> construct -> curate -> split
      -> format -> validate -> seal -> verify
```

**Groups 1–3** deliver integrity, construction, and the finished-dataset
lifecycle (curation, leakage-safe split, product rows, 17-gate validation,
atomic six-file seal, independent verification).

**Group 4** delivers the typed `PipelineService` composition root, thin CLI
adapter, and dual-objective M1.1 API/CLI acceptance.

**Group 5** expands declared ingest (HTML, digitally-born PDF, CSV, JSON,
JSONL), named OCR refusal, the recipe library, statistics, and YAML pipelines.

**Group 6** adds the constrained local MCP adapter and versioned Aptus handoff
v1 with fail-closed consumer verification.

**Group 7** adds the SwiftUI workbench under `macos/`, a thin shell over the
same CLI so digests match terminal runs.

Raw source material remains the product entry. Clean corpus state is an
accountable intermediate, except when a `full_text` recipe explicitly selects
the retained text as its target.

The complete repository check on `main` after Group 7 merge passed with
`655 passed`. This does **not** claim public release readiness (Group 9).

## Implemented interfaces

The installed console entry point is `veriformis`.

| Command | Implemented behavior | Revision outputs or external result |
| --- | --- | --- |
| `parse paths... -o WORKSPACE` | Captures raw bytes and parses supported paths in one transaction | `registry`; per-source `raw`, `canonical`, `document`, and `diagnostics` |
| `clean WORKSPACE` | Plans, replays, and commits deterministic cleaning for every source | `transforms`; per-source `document`, `cleaning-plan`, and `block-derivations` |
| `chunk WORKSPACE` | Runs one of five evidence-bearing chunk strategies | `chunks` |
| `upgrade-workspace WORKSPACE` | Migrates a verified revision-v1 or revision-v2 workspace through every supported migration | One new migration revision per required schema step, or no change when current |
| `construct WORKSPACE --objective OBJECTIVE` | Constructs candidates, decisions, diagnostics, and immutable accepted records for one exact source set | `recipe`, `result` |
| `curate WORKSPACE` | Fixes the complete finished plan and applies ordered deterministic curation | `plan`, `result` |
| `split WORKSPACE` | Assigns complete transitive leakage groups to train and evaluation | `result` |
| `format WORKSPACE` | Lowers included records into the row schema bound by the plan | `row-set`, `train`, `evaluation`, `provenance` |
| `validate WORKSPACE` | Replays all semantics and validates one exact byte snapshot through 17 gates | `snapshot`, `report` |
| `seal WORKSPACE -o BUNDLE` | Revalidates, atomically publishes, independently verifies, and receipts a finished bundle; writes sibling Aptus handoff by default | External six-file bundle; `manifest`, `attestation`; optional `*.aptus-handoff.json` |
| `verify BUNDLE` | Verifies the closed bundle without workspace access | Terminal verification result |
| `preview PATH` | Plans and replays cleaning without writes | Terminal output only |
| `run PIPELINE.yaml` | Executes a versioned YAML pipeline through `PipelineService` | Workspace stages and optional sealed bundle |
| `list-recipes` | Lists named deterministic recipe library identifiers | Terminal output only |
| `mcp` | Runs the constrained local MCP adapter on stdio | MCP tool surface over `PipelineService` |
| `handoff BUNDLE --manifest-sha256 DIGEST` | Builds the versioned Aptus handoff sibling descriptor | `*.aptus-handoff.json` |
| `handoff-verify HANDOFF --bundle BUNDLE` | Fail-closed consumer check of handoff against sealed bundle | Terminal verification result |
| `version` | Prints the package version | Terminal output only |

Surfaces over the same composition root:

| Surface | Location | Role |
| --- | --- | --- |
| Python API | `veriformis.pipeline.PipelineService` | Typed stage orchestration |
| CLI | `veriformis` / `veriformis.cli` | Thin Typer adapter |
| Recipes / YAML | `veriformis.recipes` | Named recipes, statistics, pipeline runner |
| MCP | `veriformis.mcp` / `veriformis mcp` | Constrained local automation |
| Aptus handoff | `veriformis.handoff` | Sibling descriptor + consumer verify |
| macOS workbench | `macos/` | SwiftUI thin CLI adapter |

## Workspace and identity status

The physical workspace layout remains schema 1. Active workspaces use revision
schema 3 and contain `workspace.json`, `HEAD`, `LOCK`, immutable revision
manifests, content-addressed objects, and a transaction directory. `HEAD`
selects the current revision. A successful stage becomes visible through one
atomic pointer replacement.

Revision schema 3 uses these stages and direct dependencies:

| Stage | Direct dependencies |
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

Rerunning a stage invalidates every descendant. Older states remain available
only through immutable historical revisions. Group 3 stage configurations and
artifacts bind the same `plan_id`.

Opening a workspace verifies the complete parent chain and every referenced
object digest. Commits check an expected parent revision under an exclusive
lock. A stale writer fails with `workspace-revision-conflict`. If `HEAD`
becomes visible but final directory sync fails, the command reports the visible
commit with `warning[commit-durability]` instead of claiming rollback.

`upgrade-workspace` supports revision v1 to v2 and v2 to v3. The v2 to v3
migration preserves verified parse, clean, chunk, and construct state. It adds
absent curate and split stages and resets legacy format, validate, and seal
state to absent. Historical objects and revisions remain intact. Legacy chunk
rows and saved gate flags never become Group 3 evidence.

Source IDs bind normalized logical paths and raw digests. Artifact IDs also
bind content, producer, configuration, and source scope. Cleaning, evidence,
chunks, construction, curation, splitting, rows, validation, and bundle values
use deterministic domain-separated identities. Same-basename sources and
distinct logical sources with identical bytes remain distinct.

Persisted artifact JSON and durable identity payloads preserve exact Unicode
strings and key sequences. NFC normalization applies only to locator fields
whose contract defines it, currently logical source paths. Revision IDs remain
audit identities that can differ across equivalent histories. Portable state
and artifact identities carry semantic reproducibility.

## Supported inputs and recovery

| Input | Current behavior |
| --- | --- |
| `.txt` | UTF-8 blank-line paragraph parsing with canonical-stream spans and separator-normalization diagnostics |
| `.md`, `.markdown` | Markdown parsing into canonical IR with located diagnostics for HTML, Pandoc metadata, and unsupported tokens |
| `.docx` | Body and note parsing with OOXML-located diagnostics for unsupported constructs, normalization, unresolved notes, and unavailable page provenance |
| `.html`, `.htm` | Deterministic `lxml` body extraction; scripts/styles omitted with diagnostics |
| `.pdf` | Digitally-born PDF text-layer extraction via `pypdfium2`; page headings; empty text layer refuses with named OCR limitation |
| `.csv` | UTF-8 rectangular table recovery with fixed excel dialect and explicit padding diagnostics |
| `.json`, `.jsonl` | UTF-8 structured path projection into evidence-bearing paragraphs |
| `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`, `.rb`, `.sh` | UTF-8 text captured as one language-tagged code block |

Every parser returns a `ParseReport`, which may be empty. Its status,
diagnostics, locations, IDs, and digest are persisted. OCR remains unsupported
and is refused by name on empty-text PDFs.

The canonical visible-text projection preserves image alt text, citations, and
footnote and endnote references. Note bodies share the canonical artifact but
retain distinct `footnote:<id>` and `endnote:<id>` evidence regions. Metadata
that exists only in IR can use strict `IRFieldEvidence`.

## Cleaning and source evidence

Current cleaning rules are `page-numbers`, `headers-footers`, `whitespace`,
`urls`, `emails`, `special-chars`, `lowercase`, and one custom removal regular
expression. With no explicit selection, the CLI applies `page-numbers` and
`whitespace`. A rule that would remove more than 30 percent of its target is
skipped and reported.

Each clean run creates a source-scoped `CleaningPlan` with exact configuration,
operations, allowed paths, source locations, before and after digests,
character and UTF-8 byte counts, warnings, and a portable parse-input digest.
Clean replays the plan before commit. Preview uses the same planner and replay
engine and writes nothing.

Every emitted chunk stores `SourceEvidence`. Evidence binds canonical ranges
and ordered edit, slice, or join derivations. It verifies source and artifact
identity, range bounds, each derivation, and final text. Sentence and
transformed chunks have no provenance bypass.

## Dataset construction

Group 2 implements five exact objective field contracts:

| Objective | Fields |
| --- | --- |
| `full_text` | `text` |
| `continuation` | `prompt`, `completion` |
| `section_reconstruction` | `heading`, `section` |
| `before_after_transformation` | `before`, `after` |
| `structured_field` | `input`, `fields` |

There is no deterministic summary objective and construction makes no LLM
call. Ineligible source units produce typed diagnostics instead of invented
content.

A `DatasetRecipe` binds one objective, an exact source set, cleaning and
segmentation identities, ordered constructor passes, review policy, required
construction gates, and one target row schema. Each candidate retains exact
recipe, pass, source, chunk, transform, and field-evidence lineage. One
`PromotionDecision` covers each candidate. Required-review recipes cannot
promote a candidate without separate `ReviewEvidence`.

Construct commits canonical `recipe` and `result` artifacts. Before `HEAD`
advances, the workspace reconstructs every selected source, clean, chunk,
transform, and IR input and compares the result with a fresh deterministic
replay.

## Curation and coverage

`curate` creates the complete `FinishedDatasetPlan` and applies this fixed
order:

1. minimum target-character filtering;
2. source-scoped conflict quarantine;
3. exact objective-and-field deduplication;
4. optional deterministic primary-source cap; and
5. selected-source coverage closure.

Each Group 2 record receives exactly one included, excluded, or quarantined
decision. Exact duplicates retain the minimum record ID as representative.
Conflict classes quarantine every member when an identical context and exact
source scope has distinct targets. Balance mode is `none` or
`primary-source-cap`.

Coverage accounts for candidates, records, statuses, and contributions for
every selected source, including multi-source records. The blocker codes are
`no-constructed-candidates`, `no-dataset-records`, and
`no-included-contribution`. Blockers remain inspectable but prevent a passing
finished-dataset validation.

## Leakage-safe splitting

`split` admits only curation-included representatives. It connects records
through shared source IDs, equal raw-source digests, multi-source joins, and
inherited exact-dedup-family relations. Complete transitive components become
indivisible leakage groups.

Assignment uses the plan seed and evaluation ratio. It orders groups
deterministically and selects one bounded prefix closest to the requested
evaluation record count. No group crosses a partition. Evaluation is required
by default. Fewer than two leakage groups fails with `split-invalid` unless the
plan explicitly allows an empty evaluation partition.

## Product rows and provenance

Serialization consumes the exact plan, construction result, curation result,
and split result. It lowers one included record into one row. It does not read
chunks as substitute records, reopen curation, resplit, or invent an objective
or target.

| Row schema | Exact payload shape |
| --- | --- |
| `text` | `{"text":"<target>"}` |
| `prompt_completion` | `{"prompt":"<context>","completion":"<target>"}` |
| `instruction_output` | `{"instruction":"<plan literal>","input":"<context>","output":"<target>"}` |
| `messages` | Two turns with exact source context as user and exact target as final assistant |

Only `full_text` may use `text`. Only `instruction_output` uses the non-empty
instruction literal fixed during `curate`. Structured `messages` remain
structured. Rendered model-family chat is not a sealed product row.

Train and evaluation JSONL contain only the chosen schema keys. One combined
provenance stream binds each row to its record, recipe, objective, pass,
sources, chunks, transforms, evidence, curation decision, leakage group,
assignment, partition ordinal, and exact payload digest. Partition rows are
ordered by record ID. Combined row and provenance order is train first, then
evaluation.

## Exact validation

Validation binds exact upstream artifact IDs and digests, source scope, plan,
row set, three emitted JSONL byte streams, canonical bundle paths, and validator
versions into one immutable `DatasetSnapshot`.

All 17 gates report in this exact order:

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

A valid failing report persists with failed stage status and retains all
findings. Unreadable critical input blocks dependent gates rather than
producing false passes. A failed or stale report cannot satisfy seal.

The `aptus-row-shape` validation gate proves product-row shape only. Group 6
adds the sibling Aptus handoff and consumer verification for sealed partitions
and assignment projection. Live training and in-Aptus backend enforcement
remain outside this repository. Current Aptus MLX intake rejects plain `text`
rows.

## Bundle and verification boundary

The `minimal-v1` bundle contains exactly:

```text
name.vfbundle/
├── data/train.jsonl
├── data/evaluation.jsonl
├── metadata/row-provenance.jsonl
├── validation.json
├── manifest.json
└── attestation.json
```

Seal reloads one verified workspace revision, rebuilds and revalidates its
exact snapshot, copies the already validated payload bytes into a private
temporary sibling, writes the deterministic manifest and attestation, syncs
the files and directories, runs the independent verifier, rechecks the
expected workspace revision, and atomically promotes the directory without
overwriting an existing destination. A retry may attach receipts to an exact
prior publication only after external-digest verification, byte comparison,
and revalidation.

The manifest has no self-hash. `attestation.json` binds the exact manifest
SHA-256 and content root. Because both files are co-located, an unanchored
bundle receives only `self_consistent`. Supplying the expected manifest digest
from a separate trusted channel permits `external_digest`.

The verifier needs no workspace. It rejects missing or extra files and
directories, unsafe or noncanonical paths, case or Unicode collisions,
symlinks, hard links, special files, digest mismatches, count mismatches, row
and provenance misalignment, invalid included decisions, conflict or duplicate
rows, source or group leakage inconsistency, incomplete source coverage,
row-set reconstruction mismatch, validation mismatch, and attestation mismatch.

Bundle publication and workspace receipt commit are separate atomic actions. A
rare failure after publication can leave the bundle visible while the receipt
does not commit. The CLI reports the visible path and manifest digest and does
not claim rollback.

## Remaining limitations

### Aptus handoff is versioned; live Aptus training remains outside this repo

Group 6 emits sibling `*.aptus-handoff.json` descriptors and a fail-closed
consumer check (`handoff-verify`) that proves external-digest verification,
partition digests, row schema, masking expectations, and assignment
projection digests. Live training execution remains Aptus's responsibility.

### Input and policy breadth remains limited

OCR remains unsupported. Curation supports deterministic minimum target
filtering, conflict quarantine, exact deduplication, coverage, and an optional
primary-source cap. Group 5 adds a named recipe library, deterministic
statistics, and versioned YAML pipelines executed only through
`PipelineService`.

### Public release gates remain incomplete

CI does not yet provide a Python-version matrix, type checking, coverage
enforcement, dependency review, package-install testing, macOS packaging,
signing, notarization, or release verification.

## Phase boundary

| Status | Capability |
| --- | --- |
| Implemented M1 | Canonical IR, supported parsers, deterministic rules, five chunkers, initial projections, validation, bundle code, and stage CLI |
| Implemented Group 1 | Transactional workspace, source-scoped identities, diagnostics, immutable evidence, replayable cleaning plans, and regression coverage |
| Implemented Group 2 | Five objectives, strict recipes and passes, field evidence, candidate lifecycle, exact source selection, and construction replay |
| Implemented Group 3 | Curation, leakage-safe split, construction-aware rows, exact 17-gate validation, atomic six-file seal, and independent verification |
| Implemented Group 4 | `PipelineService`, thin CLI adapter, and dual-objective M1.1 API and CLI acceptance |
| Implemented Group 5 | HTML/PDF/CSV/JSON/JSONL ingest, OCR refusal, recipe library, statistics, YAML pipelines |
| Implemented Group 6 | Local MCP adapter, versioned Aptus handoff, consumer verification |
| Implemented Group 7 | SwiftUI workbench (CLI adapter) with digest parity |
| Later | Public release gates; optional model-assisted construction |
| Future opt-in | Governed source-grounded model assistance through a separately approved `GeneratorPass` |
| Public release | Supported-platform gates, artifact evidence, packaging, signing, notarization, migration checks, and release verification |
| Outside current product | OCR, model training, cloud accounts, multi-user service, billing, and telemetry |

The implemented path remains offline and makes no LLM calls.

## Development and release evidence

Post–Group 7 merge on `main` (2026-08-05):

```text
uv lock --check
uv run ruff check src tests
uv run pytest -q            # 655 passed
git diff --check
```

Selected permanent locks:

| Area | Evidence |
| --- | --- |
| Dual-objective M1.1 | `tests/pipeline/test_pipeline_service.py` |
| Declared-format e2e | `tests/regressions/test_group5_declared_format_pipeline.py` |
| MCP / service parity | `tests/mcp/test_mcp_pipeline_parity.py` |
| Aptus handoff | `tests/handoff/test_aptus_handoff_v1.py`, [Aptus Handoff v1](contracts/aptus-handoff-v1.md) |
| Workbench CLI sequence | `macos/scripts/parity_check.sh`, `macos/Tests/` |

Group 3 independent architecture and security review:
[Group 3 code review](../dev/active/group-3-finished-dataset/group-3-finished-dataset-code-review.md).

Version `0.1.0` remains a development alpha until Group 9 release gates pass.

## Next authority

Group 9 public release gates are next for a shippable product. Group 8 remains
optional owner-approved work. See the
[Veriformis Build Roadmap](plans/2026-07-29-veriformis-roadmap.md).
