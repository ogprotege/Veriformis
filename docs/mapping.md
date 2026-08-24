# Existing-dataset import

This page is the operator guide for dataset-row mapping. It is not a trainer
manual and it does not change `ProductRow` v1.

**Last reviewed:** 2026-08-23 (independent-product Phase 9.7 columnar import)

## When to use which compiler path

| Mode | Use when | Command |
| --- | --- | --- |
| `document-source` (default) | The files are prose, code, HTML, PDF text, or other documents. Construction invents rows from recovered spans. | `veriformis parse …` with no `--mode` |
| `dataset-row` | The files already contain training rows in JSONL, JSON, compatible CSV, Parquet, or Arrow IPC. Mapping fills an existing catalog representation. Constructors do not run. | `veriformis parse … --mode dataset-row` then `veriformis map …` |
| `mixed` | You need both document-constructed rows and imported rows in one product later. Parse each family separately. Do not fuse a `.txt` file and a `.jsonl` or `.parquet` file in one parse. | `--mode mixed` only when every path is already one family |

Suffix `.jsonl`, `.json`, `.csv`, `.parquet`, or `.arrow` does not switch
paths. The same JSON array compiled as document-source becomes IR
paragraphs; compiled as dataset-row it becomes captured objects. Parquet
and Arrow stay unsupported in document-source parse. Extra `columnar`
stays empty; those captures import PyArrow only when the file is read.

## Confirmation

`veriformis mapping-detect FILE` proposes one or more `mapping-plan/v1`
objects. Even a unique proposal requires its confirmation digest before `map`
mutates a workspace. Ambiguous files (for example a row that could be `text`
or `prompt_completion`) do not auto-publish.

Packaged templates from `veriformis mapping-templates` cover the unique
detector shapes (`text`, `prompt_completion`, `instruction_output`,
`messages`). Load a template, bind the confirmation digest for the captured
files, then pass that plan to `map`.

## Partition policy

The mapping plan's `membership_policy` is required:

- `replaced` — ignore imported split labels; the leakage-safe splitter assigns membership.
- `advisory` — labels are diagnostics; the splitter still assigns membership.
- `authoritative` — imported `train` / `evaluation` labels become Finished Dataset partitions. Other names fail closed. Leakage overlap fails closed.

There is no silent default that honors a `split` column.

## JSONL, JSON, CSV, Parquet, and Arrow

- JSONL: one object per nonempty line. Nested `messages` two-turn objects are admitted.
- JSON: a top-level array of objects, or one object with a `records` or `rows` array. Nested paths use JSON pointer.
- CSV: header required, comma, UTF-8, no trim or pad. Jagged or nested cells fail closed. CSV cannot represent `messages`; use `split-jsonl-directory` or `json`.
- Parquet and Arrow IPC: one table of objects. Nested `messages` is admitted. Null product fields fail closed. Capture requires extra `columnar`.

Rejected rows are written to a content-addressed
`veriformis.mapping-rejection-report/v1` beside the workspace. That report is
not a verified export. Accepted rows may still seal.

## What import does not claim

- No trainer, spreadsheet, or Hub compatibility.
- No portable exact bytes for Parquet or Arrow across library versions.
- No preference, tool-call, multimodal, or arbitrary multi-turn chat family.
- No executable mapping functions and no LLM.
- No construction chunks on imported fields. Provenance is `mapped_value`.
- No full Mac mapping spreadsheet (Phase 18). The Mac workbench can show
  CLI-backed detect output.

See [Row Mapping Contract v1](contracts/row-mapping-v1.md).
