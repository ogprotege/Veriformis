# CLI Reference

This reference describes the implemented Veriformis `0.1.0` CLI after Group
1. Planned commands and dataset-construction surfaces are listed separately.

## Run the CLI

From a development checkout:

```bash
uv sync --extra test
uv run veriformis --help
```

The installed console command is `veriformis`.

## Supported inputs

`parse` accepts explicit files with these extensions:

- documents: `.txt`, `.md`, `.markdown`, `.docx`;
- source code: `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`, `.rb`, `.sh`.

Source code files are ingested as one code block. Directories, PDF, HTML, CSV,
JSON, JSONL, and other extensions are not supported in `0.1.0`. Text inputs
must be UTF-8.

## End-to-end example

```bash
uv run veriformis parse source.md -o build/workspace
uv run veriformis clean build/workspace
uv run veriformis chunk build/workspace --strategy paragraph
uv run veriformis format build/workspace --format completion
uv run veriformis validate build/workspace --format completion
uv run veriformis seal build/workspace -o build/example.vfbundle
```

The seal destination must not already exist.

## Workspace and artifacts

Commands no longer exchange mutable files such as `registry.json` or
`chunks.json` at the workspace root. A workspace contains:

```text
WORKSPACE/
├── workspace.json
├── HEAD
├── LOCK
├── objects/sha256/<prefix>/<digest>
├── revisions/<revision-id>/revision.json
└── .txn/
```

`HEAD` names the current immutable revision. Its manifest maps logical output
keys to content-addressed artifact IDs. The current keys are:

| Stage | Logical output keys |
| --- | --- |
| Parse | `registry`; `source/<source-id>/raw`; `source/<source-id>/canonical`; `source/<source-id>/document`; `source/<source-id>/diagnostics` |
| Clean | `transforms`; `source/<source-id>/document`; `source/<source-id>/cleaning-plan`; `source/<source-id>/block-derivations` |
| Chunk | `chunks` |
| Format | `records`; `records-meta` |
| Validate | `validations` |

Each successful stage commits a new revision atomically. Rerunning an upstream
stage invalidates dependent stage states and removes their active output keys.
Older revisions remain available as immutable history. Workspace open verifies
the complete parent chain and every referenced historical object. A legacy flat
workspace fails with `unsupported-workspace-version` and requires explicit
migration.

If `HEAD` is committed but its final directory sync cannot be confirmed, the
command succeeds with the visible revision and prints
`warning[commit-durability]`. Treat that warning as a request to preserve the
workspace and verify it again after storage is stable.

Revision IDs are audit identities and bind parent history plus commit time.
Equivalent runs can therefore have different revision IDs. Portable state
digests and per-source parse-input digests bind reproducible semantic state and
cleaning plans.

## Commands

### `parse`

```text
veriformis parse PATHS... -o WORKSPACE [--source-root ROOT]
```

The command captures every raw file before parsing and commits all selected
sources together. Each source receives a deterministic ID bound to its logical
path and raw SHA-256. Same-basename inputs remain distinct when their logical
paths differ. Distinct logical source instances with identical bytes also
remain distinct.

`--source-root` defines the stable root used to derive every logical path. It
defaults to the current directory. Every input must resolve beneath that root.
An absolute input outside the default root fails closed and tells the caller to
set `--source-root`. Adding another file to the parse batch never changes an
existing source's logical path or identity.

The parse revision stores:

- `registry` for source descriptors;
- `source/<source-id>/raw` for exact captured bytes;
- `source/<source-id>/canonical` for canonical extracted text;
- `source/<source-id>/document` for canonical IR; and
- `source/<source-id>/diagnostics` for the mandatory parse report.

Document IR and parse reports use strict versioned schemas. The canonical
visible-text projection retains image alt text, citations, and note references.
Footnote and endnote bodies remain distinct logical regions within the shared
canonical stream.

Diagnostics use stable IDs and format-native locations. A report may be empty.
Known Markdown HTML and Pandoc omissions, unknown Markdown tokens, text
separator normalization, DOCX page limits, and unsupported or normalized
DOCX body and note constructs are explicit. A parser refusal does not create
or advance a workspace.

Before `HEAD` advances, parse cross-validates the registry, canonical text,
exact IR projection, source descriptors, and parse reports.

The output directory may be new or an existing revision workspace. It may not
be a non-empty unrelated directory. Replacing parse state invalidates every
later stage.

### `clean`

```text
veriformis clean WORKSPACE [--rules NAME,NAME] [--custom REGEX]
```

Built-in rules:

- `page-numbers`
- `headers-footers`
- `whitespace`
- `urls`
- `emails`
- `special-chars`
- `lowercase`

With no `--rules` or `--custom`, cleaning uses `page-numbers` and
`whitespace`. Supplying either option replaces that default selection.
`--custom` adds one regular-expression removal rule. There is no
replacement-text option in the CLI.

For each source, the command creates and replays one source-scoped cleaning
plan. The plan binds its rule configuration, ordered operations, allowed
document paths, source locations, before and after digests, character counts,
UTF-8 byte counts, warnings, and a portable per-source parse-input digest. The
commit stores:

- `transforms` for the combined compatibility transform log;
- `source/<source-id>/document` for cleaned IR;
- `source/<source-id>/cleaning-plan` for the exact replayable plan; and
- `source/<source-id>/block-derivations` for later evidence reconstruction.

A rule that would remove more than 30 percent of its target is skipped and
reported. Safe text edits preserve rich wrappers. Structural block removal is
limited to supported explicit operations. Invalid or tampered plans fail
closed. Repeating clean with the same current configuration is a no-op and
does not advance `HEAD`.

Current prose rules do not edit inline code, code blocks, math, or other
literal payloads. These are no-op regions until an explicitly typed literal
rule exists. Before promotion, clean cross-validates strict cleaned IR,
replayed plans, block derivations, and transform records.

### `chunk`

```text
veriformis chunk WORKSPACE \
  [--strategy paragraph|fixed|sliding|sentence|structure] \
  [--size 1000] \
  [--overlap 100]
```

`paragraph` is the default. `size` and `overlap` are character counts.
`overlap` affects `fixed` and `sliding`; the other strategies ignore it.

Strategies:

- `paragraph`: groups blocks without exceeding `size` when possible;
- `fixed`: creates fixed character windows with optional overlap;
- `sliding`: uses the current overlapping window engine;
- `sentence`: groups heuristic English sentence splits up to `size`;
- `structure`: starts sections at headings, then applies paragraph grouping.

The command commits `chunks`. Every chunk has a source-scoped identity and
reconstructible `SourceEvidence`. Evidence binds canonical source ranges and
any ordered cleaning, slicing, or joining derivations. The command rejects
duplicate chunk IDs. Estimated tokens use `ceil(characters / 4)`, with a
minimum of one.

Chunks never cross `body`, `footnote:<id>`, or `endnote:<id>` boundaries. The
region is part of both source evidence and chunk identity context. Chunk and
evidence payloads use strict versioned schemas.

### `format`

```text
veriformis format WORKSPACE --format FORMAT \
  [--template llama3] \
  [--instruction TEXT] \
  [--with-heading-path]
```

Formats:

- `completion`: emits `{"text": chunk_text}`. `--with-heading-path` prefixes the heading path.
- `instruction`: emits `instruction`, `input`, and `output`. `--instruction` is required. The heading path becomes `input`, and source chunk text becomes `output`.
- `chat`: renders a generic user and assistant exchange into one `text` field.

Built-in chat templates are `llama3`, `mistral`, `qwen`, `gemma`, and `phi`.
`llama3` is the default. User-provided template files are not supported.

The command commits `records` as JSONL and `records-meta` as JSON. These are
current M1 projections. They are not recipe-driven dataset construction.

Important: the current chat path says `Summarize the following.` but uses the
unchanged chunk as the answer. It also pre-renders the exchange into `text`.
Do not treat it as a truthful summary dataset or structured assistant-only
supervision.

### `validate`

```text
veriformis validate WORKSPACE --format completion|instruction|chat
```

The command reads one immutable revision and runs:

- `schema`: exact keys and string values for the selected current format;
- `encoding`: selected mojibake markers and disallowed control characters in `text`, or in `output` for instruction rows; and
- `provenance`: exact reconstruction of every chunk from immutable source evidence.

It commits `validations` with stage status `complete` when all gates pass and
`failed` otherwise. A failed gate exits with status 1 and cannot satisfy the
seal dependency.

Validation does not yet check dataset-recipe semantics, record-to-chunk
cardinality, duplicates, PII, coverage, quality, balancing, split leakage,
non-empty output, or compatibility with a specific Aptus backend.

### `seal`

```text
veriformis seal WORKSPACE -o OUTPUT.vfbundle
```

The command requires complete parse, clean, chunk, format, and validation
states in the current immutable revision. It reads the logical outputs
`registry`, `transforms`, `chunks`, `records`, `records-meta`, and
`validations`, plus the source descriptors and canonical artifacts referenced
by that revision.

It writes:

```text
OUTPUT.vfbundle/
├── dataset.jsonl
└── manifest.json
```

The manifest includes current source, transform, chunk, dataset, validation,
version, and hash metadata.

Current integrity boundary:

- seal trusts the committed validation report instead of rerunning every gate against a normalized candidate file set;
- seal writes no committed workspace seal-stage output;
- the CLI does not expose or automatically call `verify_bundle`;
- programmatic verification skips the manifest self-hash and accepts undeclared extra files; and
- no detached digest or attestation closes the trust boundary.

These limits belong to roadmap Step 16. Group 1 does not claim atomic sealing
or closed-set verification.

### `preview`

```text
veriformis preview PATH [--rules NAME,NAME] [--custom REGEX]
```

Preview parses one source, creates a source-scoped cleaning plan, replays that
plan through the same engine used by `clean`, and prints:

- transform counts and removed UTF-8 bytes;
- warnings;
- the deterministic plan ID; and
- the first 400 characters before and after cleaning.

It writes no workspace state. With the same source and rule selection, preview
and clean produce the same cleaned document content. With the same locator,
bytes, parser, rules, and cleaning configuration, raw-file preview, workspace
preview, and clean produce the exact same plan ID. Use `preview --source-root`
to match the locator chosen by `parse --source-root`.

### `version`

```text
veriformis version
```

Prints `0.1.0`.

## Exit status

| Status | Meaning |
| --- | --- |
| `0` | Command completed |
| `1` | Validation failed, seal failed, or either command could not read valid required state |
| `2` | Unsupported input, invalid option, or another typed error from parse, clean, chunk, format, or preview |

Some serializer-template and bundle-writer failures still sit outside a fully
typed application-service result. Steps 17 and 18 close that surface boundary.

## Planned CLI behavior

Group 2 adds truthful objective and recipe-driven construction behind the
existing pipeline foundation. Group 3 adds curation, split, exact validation,
atomic seal, and independent verification operations. Group 4 introduces a
typed pipeline service and makes the CLI a thin adapter. Later work adds YAML
automation. Planned commands must not appear in current examples before their
exit gates pass.

See the [build roadmap](plans/2026-07-29-veriformis-roadmap.md), especially
Steps 7 through 19.

## Related documentation

- [Product contract](product-contract.md)
- [Integrity Contract v1](contracts/integrity-v1.md)
- [Current implementation status](current-status.md)
- [Architecture](architecture.md)
- [Development guide](development.md)
- [Build roadmap](plans/2026-07-29-veriformis-roadmap.md)
