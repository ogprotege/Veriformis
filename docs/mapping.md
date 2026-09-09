# Existing-dataset import

This page is the operator guide for dataset-row mapping. It is not a trainer
manual and it does not change `ProductRow` v1.

**Last reviewed:** 2026-09-09 (operator examples and quality preview)

## When to use which compiler path

| Mode | Use when | Command |
| --- | --- | --- |
| `document-source` (default) | The files are prose, code, HTML, PDF text, or other documents. Construction builds evidence-bound rows from recovered spans. | `veriformis parse …` with no `--mode` |
| `dataset-row` | The files already contain training rows in JSONL, JSON, compatible CSV, Parquet, or Arrow IPC. Mapping fills an existing catalog representation. Constructors do not run. | `veriformis parse … --mode dataset-row` then `veriformis map …` |
| `mixed` | You need both document-constructed rows and imported rows in one product later. Parse each family separately. Do not fuse a `.txt` file and a `.jsonl` or `.parquet` file in one parse. | `--mode mixed` only when every path is already one family |

Suffix `.jsonl`, `.json`, `.csv`, `.parquet`, or `.arrow` does not switch
paths. The same JSON array compiled as document-source becomes IR
paragraphs; compiled as dataset-row it becomes captured objects. Parquet
and Arrow stay unsupported in document-source parse. Extra `columnar`
lists the pins; those captures import PyArrow only when the file is read.

## Confirmation

`veriformis mapping-detect FILE` proposes one or more `mapping-plan/v1`
objects. Even a unique proposal requires its confirmation digest before `map`
mutates a workspace. Ambiguous files (for example a row that could be `text`
or `prompt_completion`) do not auto-publish. Detect uses the same field
normalizers as `map`: two-turn `messages`, list-valued `turns` with a tool
trace, and list-valued `steps` of at least two nonempty strings. A string in
`turns` or `steps` is a named miss (`no mapping detector matched this file`),
not a coerced list.

Packaged templates from `veriformis mapping-templates` cover the unique
detector shapes (`text`, `prompt_completion`, `instruction_output`,
`messages`, `label-classification`, `preference-pair`, `tool-call-conversation`, `stepwise-trace`). Load a template, bind the confirmation digest for the captured
files, then pass that plan to `map`.

## Small text-row walkthrough

Run from a checkout after `uv sync`. This fixture has two distinct text rows
in one source file. Ordinary imported SFT rows form record-level leakage
groups, so this fixture produces non-empty train and evaluation partitions.
Advanced families apply their own leakage-group rules. If fewer than two
groups survive, splitting refuses required evaluation; opt into
`--allow-empty-evaluation` at `curate` only when that is intentional.
The Mac mapping flow also selects one source file.

Use a new directory for each run:

```bash
VF_IMPORT_DEMO="$(mktemp -d /tmp/veriformis-import-demo.XXXXXX)"
export VF_IMPORT_DEMO
printf '%s\n' '{"text":"Alpha supplied training text."}' '{"text":"Beta supplied training text."}' > "$VF_IMPORT_DEMO/rows.jsonl"
uv run veriformis mapping-detect "$VF_IMPORT_DEMO/rows.jsonl" --source-root "$VF_IMPORT_DEMO" > "$VF_IMPORT_DEMO/detected.json"
cat "$VF_IMPORT_DEMO/detected.json"
```

After reviewing the unique `learn-the-text` / `whole-text` proposal, save that
exact object and preview it. For another input, select the intended proposal
and use its goal and representation; do not assume the first match is correct.

```bash
python3 - <<'PYPLAN'
import json, os
from pathlib import Path
base = Path(os.environ["VF_IMPORT_DEMO"])
proposals = json.loads((base / "detected.json").read_text())["proposals"]
assert len(proposals) == 1
plan = proposals[0]
assert plan["goal_id"] == "learn-the-text" and plan["representation_id"] == "whole-text"
(base / "plan.json").write_text(json.dumps(plan))
PYPLAN
uv run veriformis mapping-preview "$VF_IMPORT_DEMO/rows.jsonl" --source-root "$VF_IMPORT_DEMO" --plan "$VF_IMPORT_DEMO/plan.json"
uv run veriformis parse "$VF_IMPORT_DEMO/rows.jsonl" --mode dataset-row -o "$VF_IMPORT_DEMO/workspace" --source-root "$VF_IMPORT_DEMO"
uv run veriformis map "$VF_IMPORT_DEMO/workspace" --goal learn-the-text --representation whole-text --plan "$VF_IMPORT_DEMO/plan.json"
uv run veriformis curate "$VF_IMPORT_DEMO/workspace"
uv run veriformis split "$VF_IMPORT_DEMO/workspace"
uv run veriformis quality-report "$VF_IMPORT_DEMO/workspace"
uv run veriformis format "$VF_IMPORT_DEMO/workspace"
uv run veriformis validate "$VF_IMPORT_DEMO/workspace"
uv run veriformis seal "$VF_IMPORT_DEMO/workspace" -o "$VF_IMPORT_DEMO/dataset.vfbundle"
VF_IMPORT_SHA="$(shasum -a 256 "$VF_IMPORT_DEMO/dataset.vfbundle/manifest.json" | awk '{print $1}')"
printf '%s\n' "$VF_IMPORT_SHA" > "$VF_IMPORT_DEMO/MANIFEST.sha256"
uv run veriformis verify "$VF_IMPORT_DEMO/dataset.vfbundle" --manifest-sha256 "$VF_IMPORT_SHA"
```

`quality-report` reads map, curate, and split state for all eight imported
schemas. It writes nothing and does not block seal. A bundle alone lacks the
workspace artifacts needed for this preview. See the
[generic export guide](generic-exports.md) for derivatives of this bundle.

## Partition policy

The mapping plan's `membership_policy` is required:

- `replaced` — ignore imported split labels; the leakage-safe splitter assigns membership.
- `advisory` — labels are diagnostics; the splitter still assigns membership.
- `authoritative` — imported `train` / `evaluation` labels become Finished Dataset partitions. Other names fail closed. Leakage overlap fails closed.

There is no silent default that honors a `split` column.

## JSONL, JSON, CSV, Parquet, and Arrow

- JSONL: one object per nonempty line. Nested two-turn `messages`, list-valued
  `turns` for tool-call traces, and list-valued `steps` are admitted when they
  match the same shapes `map` binds.
- JSON: a top-level array of objects, or one object with a `records` or `rows` array. Nested paths use JSON pointer.
- CSV: header required, comma, UTF-8, no trim or pad. Jagged or nested cells fail closed. CSV cannot represent nested `messages`, `turns`, or `steps`; use `split-jsonl-directory` or `json`.
- Parquet and Arrow IPC: one table of objects. Nested `messages`, list-valued
  `turns`, and list-valued `steps` are admitted when they match `map`. Null
  product fields fail closed. Capture requires extra `columnar`.

Rejected rows are written to a content-addressed
`veriformis.mapping-rejection-report/v1` beside the workspace. That report is
not a verified export. Accepted rows may still seal.

## What import does not claim

- No trainer, spreadsheet, or Hub compatibility.
- No portable exact bytes for Parquet or Arrow across library versions.
- Document-source construction still refuses to invent preference pairs,
  labels, tool traces, or steps. Dataset-row mapping admits operator-supplied
  `preference-pair`, `label-classification`, `tool-call-conversation`, and
  `stepwise-trace` rows. Detect matches those shapes, including list-valued
  `turns` and `steps`. Multimodal rows remain refused.
- No executable mapping functions and no LLM.
- No construction chunks on imported fields. Provenance is `mapped_value`.
- No full Mac mapping spreadsheet. Compile wraps mapping-detect, operator
  confirm, and mapping-preview on one row-source file. Unconfirmed plans
  cannot compile.

See [Row Mapping Contract v1](contracts/row-mapping-v1.md),
[Support Matrix v1](contracts/support-matrix-v1.md), and
[support-lifecycle.md](support-lifecycle.md).
