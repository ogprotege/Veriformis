# CLI Reference

This reference describes the implemented Veriformis `0.1.0` CLI. Planned commands and surfaces are listed separately and are not available today.

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

Source code files are ingested as one code block. Directories, PDF, HTML, CSV, JSON, JSONL, and other extensions are not supported in `0.1.0`.

All text inputs must be UTF-8.

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

## Commands

### `parse`

```text
veriformis parse PATHS... -o WORKSPACE
```

Writes:

- `registry.json` with source identity and original-file metadata;
- `<stem>.ir.json` with the canonical document IR;
- `<stem>.extracted.txt` with the canonical extracted-text stream.

The workspace is created if needed. Existing same-named artifacts can be overwritten. Two inputs with the same filename stem are unsafe in one workspace.

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

With no `--rules` or `--custom`, cleaning uses `page-numbers` and `whitespace`. Supplying either option replaces that default selection.

`--custom` adds one regular-expression removal rule. There is no replacement-text option in the CLI.

Each selected rule runs on each top-level document block. A rule is skipped when it would remove more than 30 percent of that block. Cleaning mutates the workspace IR and writes `transforms.json`.

### `chunk`

```text
veriformis chunk WORKSPACE \
  [--strategy paragraph|fixed|sliding|sentence|structure] \
  [--size 1000] \
  [--overlap 100]
```

`paragraph` is the default. `size` and `overlap` are character counts. `overlap` affects `fixed` and `sliding`; it is ignored by the other strategies.

Strategies:

- `paragraph`: groups blocks without exceeding `size` when possible;
- `fixed`: fixed character windows with optional overlap;
- `sliding`: the same current window engine with overlap emphasized as a parameter;
- `sentence`: groups heuristic English sentence splits up to `size`;
- `structure`: starts sections at headings, then applies paragraph grouping.

The command writes `chunks.json`. Estimated tokens use `ceil(characters / 4)`, with a minimum of one.

### `format`

```text
veriformis format WORKSPACE --format FORMAT \
  [--template llama3] \
  [--instruction TEXT] \
  [--with-heading-path]
```

Formats:

- `completion`: writes `{"text": chunk_text}`. `--with-heading-path` prefixes the heading path.
- `instruction`: writes `instruction`, `input`, and `output`. `--instruction` is required. `input` is the joined heading path and `output` is the source chunk.
- `chat`: renders a generic user and assistant exchange into one `text` field.

Built-in chat templates are `llama3`, `mistral`, `qwen`, `gemma`, and `phi`. `llama3` is the default. User-provided template files are not supported.

The command writes `records.jsonl` and `records.meta.json`.

Important: the `0.1.0` chat path says `Summarize the following.` but uses the unchanged chunk as the answer. It also pre-renders the whole exchange into `text`. Do not treat that output as a truthful summary dataset or as structured assistant-only supervision.

### `validate`

```text
veriformis validate WORKSPACE --format completion|instruction|chat
```

Runs every current gate and writes `validations.json`:

- `schema`: exact keys and string values for the selected format;
- `encoding`: selected mojibake markers and disallowed control characters in `text`, or in `output` for instruction rows. It does not inspect instruction or input fields;
- `provenance`: registered source, valid block index, span bounds, and unchanged span content where available.

A gate failure exits with status 1. An unknown format exits with status 2.

Validation does not yet check duplicates, PII, dataset coverage, semantic correctness, split leakage, record-to-chunk cardinality, or stale workspace state.

### `seal`

```text
veriformis seal WORKSPACE -o OUTPUT.vfbundle
```

Requires `registry.json`, each registered extracted-text file, `chunks.json`, `records.jsonl`, and `validations.json`. It reads `transforms.json` and `records.meta.json` when present. Persisted failed gates prevent sealing. Missing or malformed workspace artifacts can still cause an uncaught error in `0.1.0`.

Writes:

```text
OUTPUT.vfbundle/
├── dataset.jsonl
└── manifest.json
```

The manifest includes source, transform, chunk, dataset, validation, version, and hash metadata.

Current integrity boundary:

- seal trusts persisted validation results instead of rerunning them;
- seal does not bind validation to an immutable workspace snapshot;
- the CLI does not expose or automatically call `verify_bundle`;
- programmatic verification skips the manifest self-hash and undeclared extra files.

### `preview`

```text
veriformis preview PATH [--rules NAME,NAME]
```

Applies selected rules to the whole canonical extracted stream, prints transform records and warnings, then shows the first 400 characters before and after. It writes nothing.

Preview does not accept `--custom`. Its whole-stream execution can differ from `clean`, which applies rules per top-level block.

### `version`

```text
veriformis version
```

Prints `0.1.0`.

## Exit status

| Status | Meaning |
|---|---|
| `0` | Command completed |
| `1` | Validation failed or sealing failed |
| `2` | Unsupported input or invalid command option handled by the CLI |

Some malformed files, missing workspace artifacts, invalid regular expressions, and unknown chat templates can still escape the typed-error path in `0.1.0`.

## Planned CLI behavior

The roadmap plans a typed pipeline service, transactional workspaces, truthful dataset recipes, construction previews, status and verification operations, structured downstream records, and later YAML automation. None of those commands should appear in current examples until implemented and tested.

See the [build roadmap](plans/2026-07-29-veriformis-roadmap.md), especially steps 1 through 19.

## Related documentation

- [Product contract](product-contract.md)
- [Current implementation status](current-status.md)
- [Architecture](architecture.md)
- [Development guide](development.md)
- [Build roadmap](plans/2026-07-29-veriformis-roadmap.md)
