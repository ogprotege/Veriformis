# Veriformis

Veriformis is being built as a local-first compiler that takes heterogeneous raw source material through faithful recovery, cleaning, dataset construction, curation, splitting, validation, and sealing. Its endpoint is a finished, auditable training dataset, not merely cleaned text.

> **Development alpha:** Version `0.1.0` implements the M1 core and roadmap Groups 1 and 2. It now constructs evidence-bearing dataset records, but it does not yet curate, split, serialize, validate, or seal those records as one finished dataset. Read the [current implementation status](docs/current-status.md) before using any output for training.

## What works today

The implemented paths are:

```text
raw files -> parse -> clean -> chunk -> construct
                                  \
                                   -> format -> validate -> seal
                                      (legacy M1 projection path)
```

`construct` is the Group 2 dataset-construction stage. The older `format`,
`validate`, and `seal` path still projects chunks directly. Group 3 will make
those serializers consume accepted construction records.

Version `0.1.0` provides:

- local parsing for plain text, Markdown, DOCX, and selected source-code files;
- immutable workspace revisions with atomic commits and stale-stage invalidation;
- source-scoped identities for current sources, artifacts, transforms, chunks, and revisions;
- strict, versioned IR, parse-report, transform, chunk, and source-evidence payloads;
- a canonical document model with mandatory parser reports and hash-pinned raw and canonical source artifacts, including body and note regions;
- deterministic cleaning through replayable, source-scoped plans shared by preview and application;
- paragraph, fixed, sliding, sentence, and structure-aware chunking;
- reconstructible source evidence for every emitted chunk;
- five versioned deterministic training objectives: `full_text`, `continuation`, `section_reconstruction`, `before_after_transformation`, and `structured_field`;
- strict dataset recipes, ordered construction passes, field-level text or IR evidence, candidate decisions, optional review evidence, and immutable accepted records;
- exact source selection by source ID or logical path;
- canonical `dataset-recipe` and `construction-result` artifacts whose semantics are replayed before `HEAD` advances;
- workspace layout schema 1 with revision schema 2 and an explicit revision-v1 upgrade command;
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

## Dataset-construction quickstart

Start with a text, Markdown, or DOCX file such as `notes.txt`:

```bash
uv run veriformis parse notes.txt -o workspace
uv run veriformis clean workspace
uv run veriformis chunk workspace --strategy paragraph
uv run veriformis construct workspace --objective full_text
```

This commits a versioned recipe and construction result. `full_text` explicitly
selects cleaned text as the target. For every other objective, the cleaned
corpus remains an intermediate state from which Veriformis constructs semantic
context and target fields.

Use repeatable `--source SOURCE_ID_OR_LOGICAL_PATH` options to construct from an
exact subset. Omit them to select every current source. See the [CLI
reference](docs/cli.md) for all objective and review options.

## Legacy M1 bundle quickstart

The current bundle path remains separate from Group 2 construction:

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

Inspect both files before using the dataset. They contain the legacy M1 chunk
projection, not the accepted records from `construct`.

The workspace itself is revisioned and content-addressed. `HEAD` selects one
immutable revision, and that revision maps logical stage-output keys to objects
under `objects/sha256/`. See the [CLI reference](docs/cli.md) for the exact
layout and output keys.

Persisted artifact JSON and durable identity and configuration-digest payloads
preserve exact Unicode string and object-key sequences. Those durable paths
apply NFC normalization only to explicit locator fields, such as logical source
paths, before those fields enter an identity payload. Audit revision IDs also
bind history and commit time, while portable state and per-source parse-input
digests drive reproducible semantic output.

## Important limitations

Version `0.1.0` has several high-impact limitations:

- The `construct` stage produces accepted `DatasetRecord` values, but `format` still projects chunks directly and does not consume them.
- Curation, quality policy, authoritative train and evaluation splits, and coverage accounting remain planned.
- A recipe declares a target row schema, but Group 2 does not emit those product rows or any train and evaluation files.
- `seal` trusts persisted validation flags instead of rerunning gates against the exact candidate bundle.
- Record serializers omit record-level provenance metadata.
- Bundle verification checks declared payload hashes but skips the manifest self-hash and ignores undeclared files.
- Atomic closed-set sealing, detached attestation, and a public `verify` command remain planned.
- Instruction output is a direct projection of chunks, not a complete objective-construction system.
- The chat path currently pairs a generic summary instruction with unchanged source text, then emits rendered `text`. Do not treat it as a truthful supervised-chat builder.

See [Current implementation status](docs/current-status.md) for the complete boundary.

## What comes next

| Phase | Scope |
| --- | --- |
| Implemented M1 and Groups 1–2 | Deterministic core, integrity foundation, versioned recipes, evidence-bearing lifecycle, and five truthful constructors |
| Group 3 | Curation, splitting, construction-aware serialization, product rows, exact validation, atomic sealing, and verification |
| Group 4 | Shared pipeline service, thin CLI, and M1.1 acceptance |
| Later milestones | PDF, HTML, structured-data ingest, YAML pipelines, MCP, versioned Aptus integration, and a SwiftUI workbench |
| Future opt-in work | Governed model-assisted construction behind a recorded `GeneratorPass` contract |
| Public release | Supported-platform gates, artifact evidence, packaging, signing, notarization, migration checks, and release verification |

The complete sequence and exit gates are in the [authoritative build roadmap](docs/plans/2026-07-29-veriformis-roadmap.md).

## Documentation

- [Documentation index](docs/README.md)
- [Product contract](docs/product-contract.md)
- [Integrity Contract v1](docs/contracts/integrity-v1.md)
- [Dataset Construction Contract v1](docs/contracts/dataset-construction-v1.md)
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

The current implementation is required to pass these checks. CI currently runs Ruff and pytest on Ubuntu with Python 3.12. Broader package, platform, type, coverage, and security gates remain future work.

## License

Veriformis is provided under the [MIT License](LICENSE).
