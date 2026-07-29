# Current Implementation Status

**Product version:** `0.1.0`

**Maturity:** Development alpha

**Audited source baseline:** `58d8f42`

**Audit date:** 2026-07-29

This document separates implemented behavior from planned behavior. It is the current source of truth for 0.1.0 capability claims.

## Executive status

Veriformis M1 is a working deterministic compiler core with a stage-command CLI. It can parse supported files, clean and chunk their canonical representation, serialize records, run three validation gates, and write a hash-bearing bundle.

It is not yet a trustworthy end-to-end constructor for large supervised datasets. It lacks transactional workspace state, complete construction and curation contracts, authoritative train and evaluation splits, exact-snapshot validation, a closed bundle trust boundary, and a stable shared application API.

The [authoritative roadmap](plans/2026-07-29-veriformis-roadmap.md) defines the work needed to close that gap.

## Implemented interfaces

The installed console entry point is `veriformis`. The current CLI exposes:

| Command | Implemented behavior | Primary artifacts |
| --- | --- | --- |
| `parse paths... -o WORKSPACE` | Parses explicit supported paths by extension | `registry.json`, `<stem>.ir.json`, `<stem>.extracted.txt` |
| `clean WORKSPACE` | Applies selected deterministic rules to every loaded document | Updated IR files, `transforms.json` |
| `chunk WORKSPACE` | Runs one of five chunking strategies | `chunks.json` |
| `format WORKSPACE --format FORMAT` | Emits completion, instruction, or rendered-chat rows | `records.jsonl`, `records.meta.json` |
| `validate WORKSPACE --format FORMAT` | Runs schema, encoding, and provenance gates | `validations.json` |
| `seal WORKSPACE -o BUNDLE` | Refuses saved failed gates and writes the current bundle shape | `dataset.jsonl`, `manifest.json` |
| `preview PATH` | Dry-runs cleaning over one file and writes nothing | Terminal output only |
| `version` | Prints the package version | Terminal output only |

There is no `run`, `verify`, MCP, GUI, or YAML-pipeline CLI command in 0.1.0.

## Supported inputs

| Input | Current behavior |
| --- | --- |
| `.txt` | Blank-line paragraph parsing with extracted-stream spans |
| `.md`, `.markdown` | Markdown parsing into the canonical document model |
| `.docx` | Body-order Word parsing into the canonical document model |
| `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`, `.rb`, `.sh` | Parsed as one language-tagged code block |

HTML, PDF, CSV, JSON, and JSONL ingest are not implemented. OCR is not implemented.

## Cleaning and chunking

Available cleaning rules are:

- `page-numbers`
- `headers-footers`
- `whitespace`
- `urls`
- `emails`
- `special-chars`
- `lowercase`
- one custom removal regular expression

When no explicit rule or custom expression is supplied, the CLI applies only `page-numbers` and `whitespace`. A rule that would remove more than 30 percent of the current block is skipped and reported as a warning.

Available chunking strategies are:

- `paragraph`
- `fixed`
- `sliding`
- `sentence`
- `structure`

The default strategy is `paragraph`. Default size is 1,000 characters and default overlap is 100 where those parameters apply.

## Current record modes

| Mode | Current representation | Status |
| --- | --- | --- |
| `completion` | `{"text": chunk_text}` with optional heading prefix | Implemented full-sequence record projection |
| `instruction` | One supplied instruction, heading path as input, and chunk text as output | Experimental projection, not a complete construction system |
| `chat` | Hard-coded generic summary request plus unchanged chunk answer, rendered to `text` | Semantically unsafe for trusted supervised-chat construction |

Current chat templates are `llama3`, `mistral`, `qwen`, `gemma`, and `phi`. User-supplied template files are not implemented.

The chat limitation is material. The current code does not perform summarization, yet it labels unchanged source text as a summary response. It also lowers the exchange to rendered text before any downstream trainer applies its own schema and masking rules.

## Current validation boundary

Validation currently runs three gates:

1. **Schema:** Requires exact keys and string values for the selected record mode.
2. **Encoding:** Reports selected mojibake markers and disallowed control characters in each record's `text`, or its `output` for instruction rows. It does not inspect the current instruction or input fields.
3. **Provenance:** Checks source registration, nonnegative block indexes, span bounds, and source-text equality for untransformed chunks that have spans.

Validation does not currently establish:

- a truthful training-objective relation;
- record-to-chunk cardinality or field-level evidence;
- duplicate, PII, quality, coverage, or balance policy;
- leakage groups or train and evaluation assignments;
- complete provenance for sentence-packed or transformed chunks;
- a non-empty dataset requirement; or
- compatibility with a specific Aptus backend.

## Current bundle boundary

`seal` writes a directory containing:

```text
dataset.vfbundle/
├── dataset.jsonl
└── manifest.json
```

The manifest records:

- bundle identity and creation time;
- Veriformis version;
- source path, hash, size, and parser;
- transform records;
- chunk metadata;
- dataset counts and estimates;
- saved validation results; and
- declared file hashes.

Original source files, split files, a detached digest, and an Aptus descriptor are not emitted.

The Python `verify_bundle` function checks hashes for declared non-manifest files. It skips the manifest self-hash, accepts undeclared extra files, and does not establish a signature or external trust anchor. No CLI `verify` command exists.

## High-impact limitations

### Mutable workspace state

Workspace artifacts are addressed by filename stem. Two inputs with the same stem can overwrite one another. Rerunning parse, clean, or chunk does not invalidate later records, validations, or bundle inputs.

### Identity collisions

Chunk numbering restarts for each document. Transform records contain a block index but no source identity. In a multi-source workspace, chunk IDs and transformed-block attribution can therefore collide.

### Cleaning fidelity

Cleaning edits top-level block text. When a rich block changes, current rewriting can flatten lists, tables, blockquotes, images, or math into a plain paragraph. Preview and applied cleaning also use different internal paths.

### Provenance gaps

Spans refer to the canonical extracted-text stream, not raw-file byte positions. Sentence chunks can have no span. Transformed chunks retain linkage but skip source-content equality. Unsupported Markdown tokens can be dropped without a typed diagnostic, and DOCX page provenance is not populated.

### Record lineage loss

Serializers emit payload fields without record, chunk, source, transform, or evidence identifiers. Exact-key schema validation rejects extra metadata instead of preserving it.

### Stale validation at seal time

`seal` loads saved validation booleans and does not rerun gates against the exact records it writes. A changed upstream artifact can therefore be sealed under stale passing results. The CLI does not invoke bundle verification after writing.

### Partial bundle verification

The current verifier trusts the manifest's declared file list. It does not reject undeclared files, verify the manifest against an external digest, or enforce a closed path-safe bundle contract.

### Reproducibility limit

Transformations are deterministic for the same inputs and options, but sealed bundles are not byte-identical. Each manifest contains a new random bundle ID and current timestamp.

## Phase boundary

| Status | Capability |
| --- | --- |
| Implemented M1 | Canonical IR, current parsers, deterministic rules, five chunkers, three record projections, three gates, stage CLI, current bundle writer |
| M1.1 | Versioned transactional workspace, source-scoped identities, parse diagnostics, replayable cleaning plans, `DatasetRecipe`, deterministic `ConstructionPass`, candidate and record lifecycle, curation, leakage-safe split assignments, structured training rows, exact validation, atomic sealing, independent verification, `PipelineService`, thin CLI |
| Later | Digital PDF, HTML, CSV, JSON, JSONL, YAML pipelines, expanded deterministic recipes, MCP, versioned Aptus handoff, SwiftUI workbench |
| Future opt-in | Governed source-grounded model assistance through `GeneratorPass`, with complete generation lineage and policy gates |
| Public release | Supported-platform gates, artifact evidence, packaging, signing, notarization, migration checks, and release verification |
| Outside current product | OCR, model training, cloud accounts, multi-user service, billing, and telemetry |

M1.1 must remain deterministic and offline. The roadmap does not permit model-assisted generation inside the v1 implementation groups.

## Development and release status

The project uses Python 3.11 or newer, a setuptools `src` layout, uv, Ruff, and pytest.

Verified at the audited baseline:

```text
uv lock --check             passed
uv run ruff check src tests passed
uv run pytest -q            50 passed
```

Repository CI currently runs on Ubuntu with Python 3.12. It does not yet provide:

- a Python-version matrix;
- type checking;
- coverage enforcement;
- dependency or security review;
- source-distribution and wheel installation tests;
- macOS packaging, signing, or notarization; or
- public release automation.

There is no repository release tag at the audited baseline. Version `0.1.0` should be treated as a development alpha, not a published release claim.

## Next authority

Do not infer future task order from the initial design or completed M1 implementation plan. Use the [Veriformis Build Roadmap](plans/2026-07-29-veriformis-roadmap.md), which defines all numbered work, grouped execution order, and exit gates after the documentation baseline is merged.
