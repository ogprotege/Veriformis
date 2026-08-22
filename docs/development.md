# Development Guide

**Last reviewed:** 2026-08-22 (Phase 5.4 export-pack transport local admission)

**Next review:** Any CI gate, packaging, or contributor-tooling change

This guide covers the implemented Veriformis `0.1.0` project. Stage policy
lives in `veriformis.pipeline.PipelineService`. The CLI, MCP adapter, and
SwiftUI workbench are thin adapters over that service (workbench shells the
CLI).

## Requirements

- Python 3.11 or newer
- `uv`
- Git

The package uses a setuptools `src/` layout. Runtime dependencies are declared
in `pyproject.toml` and locked in `uv.lock`, which is checked in.

## Set up the project

```bash
git clone https://github.com/ogprotege/Veriformis.git
cd Veriformis
uv sync --extra test
uv run veriformis --help
```

The `test` extra installs pytest and the repository-pinned Ruff version
(`ruff==0.16.0`, enforced by `required-version` in `pyproject.toml`).

## Daily checks

Run these checks before submitting a change:

```bash
uv lock --check
uv run ruff check src tests
uv run python scripts/check_project_tracking.py
uv run pytest -q --ignore=tests/handoff -m "not aptus_integration"
git diff --check
```

Before a push that touches release gates or packaging, also run:

```bash
bash scripts/release/check_local.sh
```

Rerun the commands for current evidence because totals can grow. Ruff lints
only the `E4`, `E7`, `E9`, and `F` rule families; there is no configured
formatter or type checker in this alpha.

Focused examples:

```bash
uv run pytest tests/construction -q
uv run pytest tests/datasets -q
uv run pytest tests/bundle -q
uv run pytest tests/regressions/test_workspace_v3_migration.py -q
uv run pytest tests/test_cli.py -q
```

## Where things live

The active revision-v3 pipeline is orchestrated by `pipeline/PipelineService`
and adapted by `cli.py`, with state in `workspace.py`. Domain packages:
`parsers/`, `ir/`, `rules/`, `chunkers/`, `construction/`, `datasets/`,
`bundle/`, plus `exports/`, `recipes/`, `handoff/`, and `mcp/`. The SwiftUI
workbench is `macos/`. `serializers/` and `validate/` are legacy M1 only.

| Path | Responsibility |
| --- | --- |
| `src/veriformis/pipeline/` | Typed `PipelineService` composition root |
| `src/veriformis/cli.py` | Thin Typer adapter (stages + run/recipes/mcp/handoff + export operations) |
| `src/veriformis/workspace.py` | Immutable transactional revisions (layout 1, revision 3) |
| `src/veriformis/identity.py` | Deterministic domain-separated identities |
| `src/veriformis/sources.py` | Source registration and hash-pinned identity |
| `src/veriformis/contracts.py` | Public versioned contract constants |
| `src/veriformis/diagnostics.py` | Versioned parser diagnostics |
| `src/veriformis/evidence.py` | Immutable source ranges and `SourceEvidence` |
| `src/veriformis/errors.py` | Typed errors shared by every surface |
| `src/veriformis/parsers/` | Text, Markdown, DOCX, HTML, PDF, CSV, JSON, JSONL, code |
| `src/veriformis/ir/` | Canonical document IR and strict serialization |
| `src/veriformis/rules/` | Cleaning-rule engine, library, and derivations |
| `src/veriformis/chunkers/` | Five evidence-bearing chunk strategies |
| `src/veriformis/construction/` | Objectives, recipes, constructors, lifecycle, replay |
| `src/veriformis/datasets/` | Finished plan, curation, split, rows, 17-gate validation |
| `src/veriformis/bundle/` | Six-file finished bundle + independent verifier |
| `src/veriformis/exports/` | Verified-derivative models, source admission, planning, publication/verification, strict surface protocol, and production exact-byte split JSONL/canonical JSON/constrained CSV implementations |
| `src/veriformis/recipes/` | Named recipes, statistics, YAML pipeline runner |
| `src/veriformis/handoff/` | Aptus handoff v1 build and consumer verification |
| `src/veriformis/mcp/` | Constrained local MCP adapter, including canonical verified-export tools over `PipelineService` |
| `macos/` | SwiftUI workbench and strict verified-export bridge (CLI shell) |
| `src/veriformis/serializers/` | Legacy M1 serializers and chat templates |
| `src/veriformis/validate/` | Legacy and shared gate helpers |

## Test map

| Area | Tests |
| --- | --- |
| Package and version | `tests/test_scaffold.py` |
| Raw-source and full CLI paths | `tests/test_cli.py`, `tests/known_gaps/` |
| Public contracts | `tests/contracts/` |
| Workspace, migration, staleness, format e2e, tamper | `tests/regressions/` |
| Pipeline service / dual-objective | `tests/pipeline/` |
| Construction | `tests/construction/` |
| Curation, split, serialization, validation | `tests/datasets/` |
| Canonical IR | `tests/ir/` |
| Parsers (including Group 5 formats) | `tests/parsers/` |
| Cleaning rules | `tests/rules/` |
| Chunkers | `tests/chunkers/` |
| Recipes / YAML | `tests/recipes/` |
| MCP parity | `tests/mcp/` |
| Optional Aptus adapter | `tests/handoff/` (`aptus_integration` marker) |
| Finished seal / verifier | `tests/bundle/` |
| Verified export models, membership, publication, API, and adapter parity | `tests/exports/`, `tests/contracts/test_verified_export_contract.py`, `tests/regressions/fixtures/phase4/export-surfaces.json` |
| macOS workbench | `macos/Tests/`, `macos/scripts/parity_check.sh` |
| Group 9 release gates | `tests/regressions/test_group9_release_gates.py`, `scripts/release/` |
| Program tracking and support claims | `tests/regressions/test_project_tracking.py`, `scripts/check_project_tracking.py` |
| Fixtures | `tests/fixtures/` (support) |

Add a regression test before repairing an integrity defect. Keep multi-source
fixtures because source scope, leakage closure, collision resistance, and raw
entry are durable contracts. Group 3 defects must remain ordinary passing
tests, not expected failures.

## Continuous integration

GitHub Actions (`.github/workflows/ci.yml`) runs on pushes and pull requests.

| Job | What it runs |
| --- | --- |
| `test` | Matrix: Python 3.11–3.13 on Ubuntu, plus Python 3.12 on macOS; `uv lock --check`, Ruff, core pytest excluding `aptus_integration` |
| `install-smoke` | `scripts/release/smoke_install.sh` (clean wheel origin + full installed-CLI golden path) |
| `golden-compile` | `scripts/release/golden_compile.sh` (both objectives → canonical seal → `external_digest`; no handoff) |
| `aptus-integration` | Non-blocking optional adapter self-conformance: marked tests + explicit handoff script |

Local-only: `git diff --check`. Not yet hard gates: static type checking,
coverage thresholds, dependency audit, signed/notarized Mac install.

Release procedure and owner Mac signing/notarization checklist:
[docs/release.md](release.md).

## Engineering constraints

### Keep raw sources as the entry boundary

Product acceptance begins with supported raw source material. A test that
starts from cleaned text, a `DatasetRecord`, or prebuilt JSONL can exercise a
domain unit but cannot prove the product path.

Cleaned corpus state remains intermediate unless a `full_text` objective
selects it. Other objectives must derive exact semantic context and targets
before curation.

### Keep current behavior deterministic and local

The implemented pipeline has no LLM or network stage. Do not add either to the
deterministic path. Any future model-assisted `GeneratorPass` requires a
separate approved contract and the same evidence, curation, split, validation,
and seal lifecycle.

### Preserve source evidence

Parser spans refer to the canonical extracted stream. Tests must verify both
text and span contracts. If parsing drops or normalizes content, make the loss
explicit.

Visible image alt text, citations, and note references belong in the canonical
projection. Body, footnote, and endnote blocks share one stream but retain
separate evidence regions. `IRFieldEvidence` binds IR-only scalar metadata to
its exact source, artifact, RFC 6901 pointer, value and output digests,
encoding, and construction context.

Use exact-string serialization for artifacts, identities, and configuration
digests. Normalize only fields whose contracts define NFC equivalence,
currently logical source paths. Do not substitute revision IDs for portable
semantic digests.

### Preserve revision integrity

Use `Workspace` transactions for every persisted stage result. Never write
inter-stage files at the workspace root or mutate content-addressed objects.
Tests must cover expected-revision conflicts, atomic visibility, descendant
invalidation, duplicate identities, and digest verification.

Active workspaces use revision schema 3. Group 3 stage configs and artifacts
must bind one `plan_id`. Curate, split, format, validate, and seal commits must
reload and replay their semantic inputs before promotion.

The v2 to v3 migration must preserve Group 2 facts and retire legacy
downstream state without reinterpreting it.

### Keep construction, curation, and serialization distinct

Construction creates evidence-bearing accepted `DatasetRecord` values.
Curation decides which records remain and why. Splitting assigns complete
leakage groups. Serialization lowers each included record into the schema
fixed by the recipe and plan.

A serializer must not invent an objective, target, instruction, review state,
curation decision, or split assignment. It must not read chunks as substitute
rows.

### Preserve exact validation closure

Validation binds one exact set of upstream artifacts and emitted bytes. Every
required gate reports. A failed or blocked gate cannot become a passing seal
dependency.

Adding or changing a finished-dataset artifact, emitted path, schema, or
validator version requires updating the snapshot binding and replay tests. A
saved Boolean is never sufficient.

### Preserve seal and trust boundaries

The `minimal-v1` bundle has exactly six files. The publisher must build in a
private sibling, avoid overwrite, verify before promotion, recheck the
workspace revision, and persist exact receipt bytes.

The verifier must remain independent of workspace state. `self_consistent`
means internal closure only. `external_digest` requires a caller-supplied
expected manifest SHA-256. Never infer external trust from the co-located
attestation.

Directory publication and workspace receipt commit are separate atomic
operations. Tests and errors must report a visible publication honestly if a
later receipt commit fails.

### Preserve the verified-derivative boundary

`ExportService` derives from an already verified finished bundle; it must not
construct targets, curate, balance, resplit, or accept caller-selected
membership. Its private publication boundary re-verifies source and plan and
renders twice from independently strict-reloaded inputs. Every result must pass
the complete membership comparison. Exact profiles require identical normalized
path-to-bytes trees. Semantic-only profiles may produce different physical
bytes, but their private replayer must return equal versioned canonical semantic
preimages and plan-equal normalized membership; the service computes each
digest and replays descriptor-reread staged bytes before promotion.

Phase 4 intentionally closed with no production renderer or semantic replayer.
Phase 5.1–5.3 add reviewed production exact-byte renderers for
`split-jsonl-directory`, canonical `json`, and `constrained-csv` v1; they do
not make the private implementation hook an
untrusted plugin boundary. Tests may still inject the bounded trusted
conformance implementation. Semantic replay currently retains each complete
produced file in memory; the Phase 4.7 fixture is statically bounded, and no
production semantic replayer ships. Any future shipped semantic profile must
define and enforce explicit byte, record, nesting, and other applicable
resource limits.

Locally admitted Phase 5.4 work is transport after publication, not another renderer.
`exports/archive.py` must validate the separately retained canonical receipt
digest, preserve the exact inner plan/receipt/file set and source trust grade,
and call the deterministic codec shared with bundle transport. Archive digest,
size, member count, and durability warning stay runtime facts. Do not add them
to the ten persisted export v1 models or describe receipt-anchored archive
verification as source-bound.

Verified-export surfaces must call the typed `PipelineService` operations. Keep
the production catalog private and descriptor-driven; its current entries are
`split-jsonl-directory`, canonical `json`, and `constrained-csv` v1 with no
consumer profiles.
CLI and MCP must share the canonical export request/response serializer; the
Mac bridge shells those CLI commands and must decode stdout separately from
stderr. Preserve request v1 exactly: for split JSONL it chooses the safe
`train` / `evaluation` names and includes aligned provenance. Configured dry
run, execute, and source-bound verify use request v2 and require the complete
canonical `veriformis.split-jsonl-options/v1` object; it may change only the two
safe stems or omit provenance. Canonical JSON and constrained CSV use request
v1 fixed trees and refuse request v2. Constrained CSV must quote every header
and field under its frozen UTF-8/LF dialect, preserve exact strings, support
only `text`, `prompt_completion`, and `instruction_output`, and refuse nested
`messages` with a JSON alternative. Do not add caller-supplied profiles,
dependencies, file plans, membership, renderers, replayers, replacement, or
force controls. Filename and provenance options must never mutate rows,
ordering, curation, split policy, or partition membership. The Phase 4.9
adversarial closeout harness remains test-only. The Phase 5.4
`.vfexport.zip` path remains outside the export request/discovery protocol:
`package` / `package-verify` require exactly one manifest or receipt anchor,
legacy bundle behavior must remain byte-compatible, and no MCP or Mac UI
operation is added. Item 5.4's local gates passed; pull-request publication,
GitHub evidence, and merge remain pending. Items 5.5–5.7 remain later work.

### Keep optional-integration claims accurate

The legacy-named `aptus-row-shape` gate proves only generic product-row shape;
it imports no Aptus code. Group 6 adds an explicitly invoked sibling descriptor
and fail-closed adapter check (external digest, partition digests, row schema,
masking expectations, assignment projection). Repository tests prove adapter
self-conformance, not compatibility with a live named Aptus release. Live
training and backend enforcement remain outside this repository.

## Adding a parser

A parser should:

1. capture exact raw bytes before parsing;
2. produce canonical IR and one canonical extracted-text stream;
3. assign valid body and note regions and spans;
4. register source and parser identities;
5. report unsupported, normalized, or lost structures explicitly;
6. serialize through strict versioned schemas; and
7. include adversarial fixtures and a raw-source finished-pipeline test where
   appropriate.

Declared Group 5 formats (HTML, digitally-born PDF, CSV, JSON, JSONL) are
implemented. OCR and non-declared formats remain unsupported.

## Adding a cleaning rule

A rule must be deterministic, preserve document meaning, and return exact edit
ranges. Add tests for normal input, false-positive resistance, the 30 percent
safety threshold, rich-node preservation, plan serialization, replay, and
tamper rejection. Current prose rules must leave code, math, and literal
payloads unchanged.

Preview and clean must share the planner and replay engine. Identical locator,
bytes, parser, rules, and configuration must produce the same plan ID.

## Adding a constructor

A constructor must:

1. implement one declared objective and exact field shape;
2. dispatch through a versioned constructor ID;
3. bind every field to source-text or strict-IR evidence;
4. retain source, chunk, transform, recipe, objective, and pass lineage;
5. emit typed deterministic diagnostics for omissions;
6. remain pure, local, order-independent, and replayable; and
7. include positive, negative, multi-source, Unicode, malformed, and tamper
   tests.

`source-chunks-unavailable` is construction omission evidence. It does not
replace Group 3 coverage accounting.

## Changing curation or splitting

Curation order is contractual: target length, conflict quarantine, exact
deduplication, balance, then coverage. Preserve one explicit decision per
record and the closed reason registries.

Splitting must operate on whole transitive leakage groups. New relations must
not weaken existing source ID, raw digest, multi-source join, or inherited
dedup-family closure. Input reordering must reproduce groups, assignments, and
digests.

Policy expansion belongs to a new version or later approved roadmap work. Do
not add a CLI switch that contradicts the bound plan.

## Changing product rows or bundles

Row tests must cover all allowed objective-to-schema combinations, exact keys,
target preservation, instruction constraints, messages ordering, provenance
alignment, and generic row-shape limits. Preserve the legacy gate ID until a
versioned report migration is designed.

Bundle changes require closed-set path tests, canonical bytes, exact record
counts, tamper cases, independent verification, and explicit trust-grade
behavior. Adding a file to `minimal-v1` is a contract change.

## Contribution flow

1. Read the contract documents, governance policy, active program ledger, and current status listed under
   [Related documentation](#related-documentation) before changing governed
   behavior. The roadmap is ordered; do not implement a later phase while an
   earlier required exit gate is open.
2. Keep each change focused on one behavior or one coherent roadmap step.
3. For integrity or provenance repairs, write the failing regression test
   first, then implement the smallest complete repair.
4. Run the focused tests, then the full [daily checks](#daily-checks).
5. Update the CLI reference, architecture, status, product boundary, and
   tests in the same change when behavior moves.
6. Follow the pull-request checklist in [Contributing](../CONTRIBUTING.md),
   which also lists the minimum test evidence expected per change type.

## Documentation discipline

Use present tense only for tested behavior. Use the exact phase states from the
[tracking policy](governance/project-tracking.md). Update the active phase
packet, program ledger, support registry, WIP, current status, evidence, and
affected product documentation in the same change when truth moves. Preserve
dated historical records and amend only their status notes when later
implementation changes.

Never describe a green build as release readiness. Optional handoffs are
versioned; live training remains outside Veriformis. Do not claim live trainer
compatibility from adapter-only tests, or external bundle trust without a
retained manifest digest.

## Related documentation

- [Product contract](product-contract.md)
- [Integrity Contract v1](contracts/integrity-v1.md)
- [Dataset Construction Contract v1](contracts/dataset-construction-v1.md)
- [Finished Dataset Contract v1](contracts/finished-dataset-v1.md)
- [Deterministic Archive Transport v1](contracts/bundle-transport-v1.md)
- [Split JSONL Export Contract v1](contracts/split-jsonl-export-v1.md)
- [Canonical JSON Export Contract v1](contracts/canonical-json-export-v1.md)
- [Constrained CSV Export Contract v1](contracts/constrained-csv-export-v1.md)
- [Current implementation status](current-status.md)
- [Project tracking and evidence policy](governance/project-tracking.md)
- [Support registry](governance/support-registry.json)
- [Evidence index](evidence/index.json)
- [Architecture](architecture.md) and the [architecture tree](architecture/README.md)
- [CLI reference](cli.md)
- [Independent product roadmap](plans/2026-08-11-veriformis-independent-product-roadmap.md)
- [Contributing](../CONTRIBUTING.md)
