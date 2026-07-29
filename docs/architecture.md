# Architecture

This document describes Veriformis `0.1.0` as implemented. The planned product architecture is labeled separately. See the [build roadmap](plans/2026-07-29-veriformis-roadmap.md) for the ordered path from the current M1 core to the complete product.

## Current system

Veriformis is a Python 3.11+ package with one installed entry point, the `veriformis` CLI. The CLI currently owns orchestration, workspace persistence, error presentation, and stage ordering.

```text
local files
   -> parse
   -> clean
   -> chunk
   -> format
   -> validate
   -> seal
   -> dataset.jsonl + manifest.json
```

There is no shared pipeline service, YAML runner, MCP server, or macOS application in `0.1.0`.

## Module boundaries

| Module | Current responsibility |
|---|---|
| `src/veriformis/cli.py` | Typer commands and full pipeline orchestration |
| `src/veriformis/parsers/` | Plain text, source code, Markdown, and DOCX ingestion |
| `src/veriformis/ir/` | Canonical document model and JSON serialization |
| `src/veriformis/rules/` | Deterministic cleaning rules and transform records |
| `src/veriformis/chunkers/` | Paragraph, fixed, sliding, sentence, and structure chunking |
| `src/veriformis/serializers/` | Completion, instruction, and rendered chat records |
| `src/veriformis/validate/` | Schema, encoding, and provenance gates |
| `src/veriformis/bundle/` | Bundle manifest, writer, and programmatic verification |

The domain modules are callable from Python, but the package does not yet expose a stable end-to-end application API. The CLI composes these modules directly.

## Canonical document model

Every supported parser emits the same document IR. It contains block nodes such as headings, paragraphs, lists, tables, code blocks, blockquotes, images, and math. It also represents links, citations, notes, and rich inline marks.

Each top-level block can carry a `Span` and `block_index`. A span indexes a canonical extracted-text stream assembled from the parsed blocks. It does not index the original file bytes or raw source characters.

`SourceRef` records:

- a content-derived source ID;
- the original path, SHA-256, and byte size;
- the parser name;
- the canonical extracted text used by provenance checks.

DOCX has no page mapping in `0.1.0`, so its span page is always `None`. Sentence chunks may also have no character span.

## Workspace protocol

The workspace is both persistence and the current inter-stage protocol.

| Stage | Current artifacts |
|---|---|
| Parse | `registry.json`, `<stem>.ir.json`, `<stem>.extracted.txt` |
| Clean | Updated IR files, `transforms.json` |
| Chunk | `chunks.json` |
| Format | `records.jsonl`, `records.meta.json` |
| Validate | `validations.json` |
| Seal | A new bundle directory |

Each later stage loads files written by earlier stages. There is no workspace revision, lock, dependency graph, atomic stage commit, or stale-output invalidation.

## Cleaning and chunking

Cleaning operates deterministically. A transform record reports the rule, parameters, block index, edit count, removed characters, and whether the safety threshold blocked the change. A rule that would remove more than 30 percent of a block is skipped.

Cleaning is not structurally lossless after an edit. Replacing text in a rich block flattens that block's inline structure. Transform records also lack `source_id` in `0.1.0`.

Chunkers carry source ID, block index, optional span, heading path, estimated tokens, and a transformed flag. Token counts are estimates based on one token per four characters.

## Record construction and serialization

The current format stage maps chunks directly into records:

- completion: `{"text": "..."}`;
- instruction: `{"instruction": "...", "input": "...", "output": "..."}`;
- chat: a model-template-rendered `{"text": "..."}` row.

Serializers do not preserve chunk identity or record-level provenance. The current CLI chat path attaches the generic instruction `Summarize the following.` and copies the source chunk unchanged as the assistant response. That is not a truthful summarization operation. Pre-rendering chat into `text` also removes the prompt and assistant boundary needed for completion-only masking in downstream trainers.

These are current defects, not intended product constraints. The target architecture introduces declared training objectives, `DatasetRecipe`, ordered `ConstructionPass` operations, evidence-bound candidate records, and structured training rows. See roadmap steps 7 through 15.

## Validation

`0.1.0` runs three gates:

1. `schema` requires the exact key set and string values for the selected format.
2. `encoding` detects selected mojibake markers and disallowed control characters in `text`, or in `output` for instruction rows. It does not inspect instruction or input fields.
3. `provenance` checks source registration, block indexes, span bounds, and unchanged span content where available.

Validation does not yet cover construction semantics, record-to-chunk cardinality, duplicates, PII, coverage, balancing, split leakage, or a complete immutable dataset snapshot. The exact-key schema also prevents records from carrying extra provenance metadata.

## Bundle boundary

The current bundle contains:

```text
name.vfbundle/
├── dataset.jsonl
└── manifest.json
```

The manifest records bundle identity, creation time, Veriformis version, source metadata, transforms, chunk metadata, dataset counts, validation results, and file hashes.

Sealing refuses persisted failed gate results. It does not rerun the gates against the exact records being sealed. The CLI also does not call `verify_bundle` after writing. Programmatic verification checks declared files, skips the manifest self-hash, and ignores undeclared extra files. Original inputs are not copied into the bundle.

## High-impact current limitations

- Same-stem inputs can overwrite each other's workspace artifacts.
- Chunk IDs restart for each document and can collide in a multi-source workspace.
- Transform state is keyed only by block index and can cross source boundaries.
- Upstream reruns can leave stale chunks, records, validations, or bundles.
- Markdown can silently drop unsupported tokens.
- Note bodies are stored in the IR but are not included in the current chunk flow.
- Citation markers, note references, and inline images do not contribute text to the canonical training projection.
- Record rows do not retain source evidence or chunk identity.
- Current chat rows have false summary semantics and incompatible masking boundaries.
- Sealing is not an atomic validation and commit of one immutable snapshot.

## Planned target architecture

The target remains one local Python core with thin adapters. Planned work includes:

1. versioned transactional workspaces and source-scoped identities;
2. explicit parser-loss diagnostics and immutable source evidence;
3. replayable cleaning plans shared by preview and apply;
4. training objectives, dataset recipes, construction passes, and record lifecycle states;
5. curation, leakage-safe splitting, exact validation, and atomic sealing;
6. a typed `PipelineService` used by CLI, MCP, and SwiftUI adapters;
7. structured downstream rows with masking and provenance metadata;
8. expanded ingest, integrations, and governed model-assisted construction after the deterministic core is complete.

These items are proposals, not `0.1.0` behavior. Their order and exit gates are authoritative in the [build roadmap](plans/2026-07-29-veriformis-roadmap.md).

## Related documentation

- [Product contract](product-contract.md)
- [Current implementation status](current-status.md)
- [CLI reference](cli.md)
- [Development guide](development.md)
- [Build roadmap](plans/2026-07-29-veriformis-roadmap.md)
