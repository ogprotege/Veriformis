# Veriformis

A local compiler for fine-tuning datasets.

Give it documents or already-shaped training rows. It recovers them
faithfully, records every change, binds every field to evidence, splits
without leakage, and seals a six-file bundle you can verify without
trusting the machine that built it.

The pipeline never calls a model. It never leaves the machine.

**Development alpha `0.1.0`.** Not a public beta. Not production.
Limits: [docs/beta-limitations.md](docs/beta-limitations.md).
Capability claims: [docs/current-status.md](docs/current-status.md).

## Highlights

- Document-source path: `parse → clean → chunk → construct → curate → split → format → validate → seal → verify`
- Existing JSONL, JSON, CSV, Parquet, or Arrow rows: `parse --mode dataset-row` then `map`, then the same tail
- Cleaned text is compiler state until a `full_text` recipe selects it
- Sealed product is a six-file `.vfbundle`; derivatives do not recurate or resplit
- Optional adapters: `trl`, `mlx-lm`, `axolotl`, `llama-factory`, `aptus`. Trainer extras stay empty; among runtime extras, `columnar` installs PyArrow and Datasets. The exporter does not train.

## Install

```bash
git clone https://github.com/ogprotege/Veriformis.git
cd Veriformis
uv sync
uv run veriformis version    # 0.1.0
```

Operator guide: [docs/install.md](docs/install.md).

```bash
export PATH="$PWD/.venv/bin:$PATH"
veriformis --help
```

macOS workbench (unsigned development app, same CLI under the hood):

```bash
./script/build_and_run.sh
```

## Compile

Use at least two independent sources if you need a non-empty evaluation
partition under default split rules. One leakage group: pass
`--allow-empty-evaluation` to `curate` only when that is intentional.

```bash
uv run veriformis parse source-a.txt source-b.txt -o build/workspace
uv run veriformis clean build/workspace
uv run veriformis chunk build/workspace --strategy paragraph
uv run veriformis construct build/workspace --objective full_text
uv run veriformis curate build/workspace
uv run veriformis split build/workspace
uv run veriformis format build/workspace
uv run veriformis validate build/workspace
uv run veriformis seal build/workspace -o build/example.vfbundle
uv run veriformis verify build/example.vfbundle
```

`seal` prints the manifest SHA-256. Keep it outside the bundle. Then:

```bash
uv run veriformis verify build/example.vfbundle \
  --manifest-sha256 EXPECTED_MANIFEST_SHA256
uv run veriformis package build/example.vfbundle \
  -o build/example.vfbundle.zip \
  --manifest-sha256 EXPECTED_MANIFEST_SHA256
uv run veriformis package-verify build/example.vfbundle.zip \
  --manifest-sha256 EXPECTED_MANIFEST_SHA256
```

Without that digest, verification reports `self_consistent`. With a
match, `external_digest`.

Existing JSONL, JSON, compatible CSV, Parquet, or Arrow rows skip
`clean` / `chunk` / `construct`:

```bash
mkdir -p build/import
uv run veriformis mapping-detect rows.jsonl > build/import/detected.json
# For text rows, review the proposal and save it as build/import/plan.json.
# Use the proposal's goal and representation for other schemas.
uv run veriformis parse --mode dataset-row rows.jsonl -o build/import/workspace
uv run veriformis map build/import/workspace \
  --goal learn-the-text --representation whole-text --plan build/import/plan.json
uv run veriformis curate build/import/workspace
uv run veriformis split build/import/workspace
uv run veriformis quality-report build/import/workspace
# then format → validate → seal to a new bundle path → verify
```

`map` takes no defaults: the goal, representation, and a confirmed plan whose
digest binds the captured file are all required. Parquet and Arrow row
sources additionally need `uv sync --extra columnar`. Guide:
[docs/mapping.md](docs/mapping.md). Suffix never switches the
document-source path.

For a supervised document recipe, replace the earlier `construct` command
with this selection, then run the remaining stages into a new bundle path:

```bash
uv run veriformis construct build/workspace \
  --objective continuation \
  --target-row-schema messages
```

Later stages read the bound recipe. For document-source `instruction_output`,
omitting `curate --instruction` uses the goal's truthful catalog template.
Other document row schemas reject an instruction override. Imported rows
preserve their supplied instruction and output fields.

Default `seal` writes this tree and nothing else:

```
example.vfbundle/
  data/train.jsonl
  data/evaluation.jsonl
  metadata/row-provenance.jsonl
  validation.json
  manifest.json
  attestation.json
```

Optional consumer sidecars take an explicit flag. Aptus:
`seal --aptus-handoff`, or `handoff` after sealing. Core install, CLI,
MCP, and required release gates do not need Aptus.

## Inputs

| Kind | Extensions |
| --- | --- |
| Text | `.txt` |
| Markdown | `.md`, `.markdown` |
| Word | `.docx` |
| HTML | `.html`, `.htm` |
| Digitally-born PDF | `.pdf` (default parse refuses image-only pages) |
| Tables and records | `.csv`, `.json`, `.jsonl` |
| Source | `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`, `.rb`, `.sh` |
| Existing rows (`--mode dataset-row` only) | `.jsonl`, `.json`, compatible `.csv`, `.parquet`, `.arrow` (Parquet and Arrow need extra `columnar`) |

Anything else fails as `unsupported-input`. Image-only PDF refuses with
`pdf.ocr-required`; the `ocr-image` input family stays unsupported.

## What it emits

The sealed bundle is the product. Derivatives are later, optional, and
do not recurate or resplit.

| Export | Role |
| --- | --- |
| `split-jsonl-directory` | Canonical train / evaluation JSONL |
| `json` | Canonical JSON tree |
| `constrained-csv` | Flat quoted CSV (`messages` refused) |
| `parquet`, `arrow`, `hugging-face-dataset` | Columnar / DatasetDict; extra `columnar` lists the pins |
| `trl`, `mlx-lm`, `axolotl`, `llama-factory`, `aptus` | Optional adapters over a verified bundle |

Trainer extras stay empty. The exporter does not train. `unsloth` is
named and not executable. Generic containers keep `consumer_id` null.

Deterministic zip: `.vfbundle.zip` around the sealed bundle, and
optional `.vfexport.zip` around one already-published export directory.

## What it will not do

- Invent a summary or any other transformation that did not occur
- Call a network or an LLM
- OCR a scan during default parse; optional local `ocr-preview` is separate
- Upload to a Hub
- Launch training
- Claim public beta or a signed Mac app

Exact capability inventory: [docs/current-status.md](docs/current-status.md).

## Read next

| Page | What it is |
| --- | --- |
| [Install](docs/install.md) | CLI and workbench |
| [Current status](docs/current-status.md) | What `0.1.0` actually does |
| [Product contract](docs/product-contract.md) | Ownership and non-claims |
| [CLI](docs/cli.md) | Commands |
| [Mapping](docs/mapping.md) | Existing-dataset import |
| [Generic exports](docs/generic-exports.md) | JSONL / JSON / CSV choice |
| [Documentation index](docs/README.md) | Contracts, architecture, governance |
| [Contributing](CONTRIBUTING.md) | Checks and house rules |

## Checks

```bash
uv sync --extra test
uv lock --check
uv run ruff check src tests
uv run pytest -q --ignore=tests/handoff \
  -m "not aptus_integration and not profile_integration and not columnar_integration and not scale_benchmark"
git diff --check
```

## License

[MIT](LICENSE).
