# Veriformis

Veriformis is being built as a local-first compiler that takes heterogeneous raw source material through faithful recovery, cleaning, dataset construction, curation, splitting, validation, and sealing. Its endpoint is a finished, auditable training dataset, not merely cleaned text.

> **Development alpha:** Version `0.1.0` implements the M1 core and stage-command CLI. It is useful for development and evaluation, but it is not yet a release-ready dataset workbench. Read the [current implementation status](docs/current-status.md) before using its output for training.

## What works today

The implemented workflow is:

```text
parse -> clean -> chunk -> format -> validate -> seal
```

Version `0.1.0` provides:

- local parsing for plain text, Markdown, DOCX, and selected source-code files;
- a canonical document model with source identities and extracted-text spans;
- deterministic cleaning with an explicit transform log and a destructive-change safety limit;
- paragraph, fixed, sliding, sentence, and structure-aware chunking;
- completion, instruction, and rendered-chat record serializers;
- schema, encoding, and chunk-provenance gates; and
- a bundle directory containing `dataset.jsonl` and `manifest.json`.

The current pipeline makes no LLM calls and does not send documents to a network service.

## Supported inputs

| Category | Extensions |
| --- | --- |
| Text | `.txt` |
| Markdown | `.md`, `.markdown` |
| Word | `.docx` |
| Source code | `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`, `.rb`, `.sh` |

Other extensions fail with an `unsupported-input` error.

## Development setup

Veriformis requires Python 3.11 or newer and uses [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ogprotege/Veriformis.git
cd Veriformis
uv sync --extra test
uv run veriformis version
```

The last command should print:

```text
0.1.0
```

## Current completion quickstart

The completion format is the clearest currently exercised path. Start with a text, Markdown, or DOCX file such as `notes.txt`:

```bash
uv run veriformis parse notes.txt -o workspace
uv run veriformis clean workspace
uv run veriformis chunk workspace --strategy paragraph
uv run veriformis format workspace --format completion
uv run veriformis validate workspace --format completion
uv run veriformis seal workspace -o notes.vfbundle
```

The output directory must not already exist. A successful seal currently contains:

```text
notes.vfbundle/
├── dataset.jsonl
└── manifest.json
```

Inspect both files before using the dataset.

## Important limitations

Version `0.1.0` has several high-impact limitations:

- Workspaces are mutable and filename-based. Inputs with the same stem can overwrite one another.
- Chunk and transform identities are not safely source-scoped across a multi-document workspace.
- Rerunning an upstream stage does not invalidate downstream records or validation results.
- `seal` trusts persisted validation flags instead of rerunning gates against the exact candidate bundle.
- Sentence chunks can lack exact spans, and transformed chunks do not receive source-text equality checks.
- Record serializers omit record-level provenance metadata.
- Bundle verification checks declared payload hashes but skips the manifest self-hash and ignores undeclared files.
- Instruction output is a direct projection of chunks, not a complete objective-construction system.
- The chat path currently pairs a generic summary instruction with unchanged source text, then emits rendered `text`. Do not treat it as a truthful supervised-chat builder.

See [Current implementation status](docs/current-status.md) for the complete boundary.

## What comes next

| Phase | Scope |
| --- | --- |
| Implemented M1 | Current deterministic core and stage-command CLI |
| M1.1 | Transactional workspaces, source-scoped identity, construction recipes, curation, splitting, exact validation and sealing, structured training rows, and a shared pipeline service |
| Later milestones | PDF, HTML, structured-data ingest, YAML pipelines, MCP, versioned Aptus integration, and a SwiftUI workbench |
| Future opt-in work | Governed model-assisted construction behind a recorded `GeneratorPass` contract |
| Public release | Supported-platform gates, artifact evidence, packaging, signing, notarization, migration checks, and release verification |

The complete sequence and exit gates are in the [authoritative build roadmap](docs/plans/2026-07-29-veriformis-roadmap.md).

## Documentation

- [Documentation index](docs/README.md)
- [Product contract](docs/product-contract.md)
- [Current implementation status](docs/current-status.md)
- [Architecture](docs/architecture.md)
- [CLI reference](docs/cli.md)
- [Authoritative build roadmap](docs/plans/2026-07-29-veriformis-roadmap.md)

## Development checks

```bash
uv lock --check
uv run ruff check src tests
uv run pytest -q
```

At the documented 0.1.0 baseline, Ruff passes and the suite contains 50 passing tests. CI currently runs Ruff and pytest on Ubuntu with Python 3.12. Broader package, platform, type, coverage, and security gates remain future work.

## License

Veriformis is provided under the [MIT License](LICENSE).
