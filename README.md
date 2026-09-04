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
- Optional adapters: `trl`, `mlx-lm`, `axolotl`, `llama-factory`, `aptus`. Extras stay empty. The exporter does not train.

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

macOS workbench (private beta, same CLI under the hood):

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
uv run veriformis parse --mode dataset-row rows.jsonl -o build/workspace
uv run veriformis map build/workspace
# then curate → split → format → validate → seal → verify
```

Guide: [docs/mapping.md](docs/mapping.md). Suffix never switches the
document-source path.

For a supervised recipe, bind objective and row schema at construct:

```bash
uv run veriformis construct build/workspace \
  --objective continuation \
  --target-row-schema messages
```

Later stages read the bound recipe. Only `instruction_output` needs
`curate --instruction TEXT`.

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
| Digitally-born PDF | `.pdf` (image-only / OCR fails closed) |
| Tables and records | `.csv`, `.json`, `.jsonl` |
| Source | `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`, `.rb`, `.sh` |

Anything else fails as `unsupported-input`.

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
- OCR a scan
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
