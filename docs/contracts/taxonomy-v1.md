# Dataset Taxonomy Contract v1

**Contract ID:** `veriformis.taxonomy`

**Contract version:** `1`

**Schema identifier:** `veriformis.taxonomy/v1`

**Execution profile:** `offline-deterministic-v1`

**Implementation status:** Implemented in completed independent-product Phase 3.
This contract defines vocabulary and compatibility. Its family labels and
canonical profile classify behavior already shipped under the construction and
finished-dataset contracts; it adds no new learning behavior, export adaptation
or container, or trainer-specific destination profile.

**Last reviewed:** 2026-08-23 (independent-product Phase 9.6: parquet, arrow, and hugging-face-dataset are export-executable; taxonomy still planned)

**Next review:** Any taxonomy, input-family, loss-policy, or
compatibility-matrix change

## Purpose

This contract gives every later input and output feature a truthful semantic
home. It defines seven independent axes:

1. training family;
2. training objective;
3. semantic row schema;
4. physical container;
5. consumer profile;
6. loss policy;
7. input family (added additively by Phase 6.2 under
   [ADR-0008](../adr/0008-input-family-taxonomy-axis.md)).

UI, APIs, recipes, and docs MUST NOT collapse more than one axis into a single
“format” value. A physical container such as JSONL does not state what is
learned. A consumer profile does not invent an objective.

This contract reuses existing v1 identifiers from Dataset Construction,
Finished Dataset, Bundle Transport, and Aptus Handoff. It MUST NOT
reinterpret sealed artifacts. An incompatible meaning change requires a
versioned migration.

## Normative language

`MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, and `MAY` are normative terms.
Human-readable aliases are not persisted identifiers.

## Authority

| Axis | Existing authority reused here |
| --- | --- |
| Objective | [Dataset Construction Contract v1](dataset-construction-v1.md) `TrainingObjective` |
| Semantic row | Construction recipe `target_row_schema`; [Finished Dataset Contract v1](finished-dataset-v1.md) product rows |
| Canonical container | Finished-dataset `minimal-v1` bundle |
| Transport container | [Bundle Transport Contract v1](bundle-transport-v1.md) |
| Optional Aptus profile | [Aptus Handoff Contract v1](aptus-handoff-v1.md) |
| Four-axis product model | [ADR-0003](../adr/0003-four-axis-dataset-model.md) |

## Axis definitions

### Training family

A training family is the coarse learning kind. It is not a row schema, file
type, or trainer name.

Implemented v1 families are conservative:

| Family ID | State | What is learned |
| --- | --- | --- |
| `source-grounded-language-modeling` | implemented | The model continues or memorizes source-grounded text. The only current objective is `full_text`. |
| `source-grounded-supervised-fine-tuning` | implemented | The model produces a source-grounded target from an explicit context. Current objectives are `continuation`, `section_reconstruction`, `before_after_transformation`, and `structured_field`. |

Future-only families MAY be named. They MUST be recorded as `planned` or
`explicitly_unsupported` and MUST NOT appear in discovery as implemented:

| Family ID | State | Reason it is not implemented |
| --- | --- | --- |
| `preference-and-ranking` | planned | No preference objective, pair schema, or ranking loss |
| `explicit-label-classification` | planned | No explicit label objective or label-set contract |
| `tool-call-conversations` | planned | No tool/function-call row contract |
| `stepwise-supervision` | planned | No stepwise or process-supervision schema |
| `pre-tokenized-training` | planned | Tokenizer-bound rows require a named consumer/model profile |
| `governed-generated-candidates` | planned | Owner-gated Group 8; not deterministic v1 |
| `multimodal-training` | explicitly_unsupported | No multimodal recovery or row contract |

`summary` is not a family, objective, or alias.

### Training objective

A `TrainingObjective` states what the model should learn and which constructed
fields are context or target. Persisted kinds remain exactly:

- `full_text`
- `continuation`
- `section_reconstruction`
- `before_after_transformation`
- `structured_field`

Field roles remain those in the construction contract. This taxonomy MUST NOT
add, rename, or drop those kinds.

Learning reading of the current kinds:

| Objective | Family | Learning reading |
| --- | --- | --- |
| `full_text` | `source-grounded-language-modeling` | The retained source text is the supervised sequence. This is continued pretraining / language-modeling data, not a summary. |
| `continuation` | `source-grounded-supervised-fine-tuning` | Complete the source unit after an exact prompt span. |
| `section_reconstruction` | `source-grounded-supervised-fine-tuning` | Recover the exact section body from its heading. |
| `before_after_transformation` | `source-grounded-supervised-fine-tuning` | Reproduce the named deterministic transform. |
| `structured_field` | `source-grounded-supervised-fine-tuning` | Emit one explicit IR scalar as the target. |

### Semantic row schema

A semantic row schema states field roles in the sealed product row. Persisted
values remain exactly `text`, `prompt_completion`, `instruction_output`, and
`messages`. Payload shapes remain those in the finished-dataset contract.

Legacy CLI names `completion`, `instruction`, and `chat` are UI aliases only.
They MUST NOT appear in a `DatasetRecipe`, sealed row set, or taxonomy
discovery identifier.

### Physical container

A physical container stores rows, partitions, metadata, and sidecars. It does
not determine the objective or loss.

| Container ID | State | Role |
| --- | --- | --- |
| `minimal-v1` | implemented | Canonical six-file Veriformis bundle |
| `deterministic-vfbundle-zip-v1` | implemented | Finder-safe transport of that bundle; not a trainer export |
| `deterministic-export-pack-zip-v1` | implemented | Receipt-anchored transport of one unchanged generic export pack; not a renderer or trainer export |
| `split-jsonl-directory` | implemented | Phase 5 consumer-neutral generic export; contract v1 |
| `json` | implemented | Phase 5 consumer-neutral canonical JSON export; contract v1 |
| `constrained-csv` | implemented | Phase 5 consumer-neutral constrained CSV export for the three flat row schemas; contract v1 |
| `parquet` | planned | Phase 9 |
| `arrow` | planned | Phase 9 |
| `hugging-face-dataset` | planned | Phase 9 |

Phase 5.6's `veriformis.export-dry-run-preview/v1` is a runtime view of one
already-selected physical container and immutable export plan. It is not a
physical container, semantic row schema, training objective, consumer profile,
or loss policy, and it changes no taxonomy or support-registry state.

### Consumer profile

A consumer profile applies a named destination’s filenames, mappings,
templates, masking constraints, and sidecars. It MUST NOT curate, resplit, or
change record membership.

| Profile ID | State | Role |
| --- | --- | --- |
| `veriformis-canonical-v1` | implemented | No destination adaptation; the verified bundle is the product |
| `aptus-handoff-v1` | implemented | Optional sibling descriptor; default surfaces do not write it |
| `trl` | implemented | Optional SFT export adapter over split JSONL |
| `mlx-lm` | implemented | Optional LoRA export adapter over split JSONL |
| `axolotl` | candidate | Phase 10 |
| `llama-factory` | candidate | Phase 10 |
| `unsloth` | candidate | Phase 10 |

The persisted validation gate ID `aptus-row-shape` remains a generic row-shape
check. It is not a consumer profile and imports no Aptus code.

### Loss policy

A loss policy states which row bytes are supervised. Every implemented
semantic row has exactly one:

| Row schema | Loss policy ID | Supervised boundary |
| --- | --- | --- |
| `text` | `full-sequence` | The entire `text` value is supervised. |
| `prompt_completion` | `completion-only` | `prompt` is context; `completion` is the supervised target. |
| `instruction_output` | `output-only` | `instruction` and `input` are context; `output` is the supervised target. |
| `messages` | `final-assistant-suffix` | Only the final assistant message is supervised. |

A consumer profile MAY refuse a row schema or add a stricter masking
expectation. It MUST NOT silently change the loss policy ID of an accepted
row. The Aptus profile’s refusal of plain `text` is such a constraint.

### Input family

An input family is the recovery-side kind of a raw source. It classifies what
a parser recovers; it never states what is learned, which row schema applies,
or which container is produced. Each declared v1 suffix belongs to exactly one
implemented family, and each family names the parser kinds that produce its
sources.

| Family ID | State | Suffixes | Parser kinds | What recovery supplies |
| --- | --- | --- | --- | --- |
| `plain-text` | implemented | `.txt` | `text` | Paragraph text only |
| `source-code` | implemented | `.c`, `.cpp`, `.go`, `.java`, `.js`, `.py`, `.rb`, `.rs`, `.sh`, `.ts` | `text` | One code block carrying its language |
| `markdown` | implemented | `.markdown`, `.md` | `markdown` | Headings, paragraphs, code blocks, links, images, lists, tables, math, citations |
| `word-document` | implemented | `.docx` | `docx` | Headings, paragraphs, code blocks, links, images, lists, tables, math, citations |
| `html` | implemented | `.htm`, `.html` | `html` | Headings and paragraphs |
| `pdf-text` | implemented | `.pdf` | `pdf` | Paragraphs from the embedded text layer under synthetic per-page labels (`Page N` headings); image-only pages refuse |
| `delimited-table` | implemented | `.csv` | `csv` | One table without alignment attributes |
| `json-records` | implemented | `.json`, `.jsonl` | `json`, `jsonl` | Paragraph text per flattened textual field |
| `ocr-image` | explicitly_unsupported | — | — | No OCR recovery exists; image-only PDFs fail closed |

Goal eligibility per family is bound in the
[Goal Catalog Contract v1](goal-catalog-v1.md). Adding a family, moving a
suffix between families, or promoting `ocr-image` requires a roadmap step
(Phases 11 and 12) and a support-registry change in the same pull request.

## Compatibility

The following objective/row pairs are the only valid v1 combinations:

| Objective | Allowed row schemas |
| --- | --- |
| `full_text` | `text` |
| `continuation` | `prompt_completion`, `instruction_output`, `messages` |
| `section_reconstruction` | `prompt_completion`, `instruction_output`, `messages` |
| `before_after_transformation` | `prompt_completion`, `instruction_output`, `messages` |
| `structured_field` | `prompt_completion`, `instruction_output`, `messages` |

Any other pair is invalid. Loaders, `PipelineService.construct`, recipes, and
discovery MUST fail closed before compile.

Default row schema when the caller omits one:

| Objective | Default row schema |
| --- | --- |
| `full_text` | `text` |
| every other implemented objective | `prompt_completion` |

`veriformis-canonical-v1` accepts every valid objective/row pair.
`aptus-handoff-v1` accepts those pairs except `text`.
`trl` and `mlx-lm` accept every valid objective/row pair as optional export
adapters. `instruction_output` is transformed to prompt/completion columns.
They refuse preference, tools, and vision types.

Unknown family, objective, row, container, profile, loss-policy, or
input-family identifiers MUST fail closed. Planned and explicitly unsupported
identifiers MUST NOT be selected for compile.

## Discovery and vocabulary

One registry is the source of discovery for `PipelineService`, CLI, MCP, and
workbench help. Discovery listings MUST name each axis separately. They MUST
NOT emit a field named `format` whose value could be an objective, row
schema, container, or profile.

Persisted identifiers are the vocabulary of recipes, rows, and seals. UI
labels MAY be friendlier if they remain bound to those identifiers.

## Version and migration

The taxonomy catalog uses schema `veriformis.taxonomy/v1`. Adding a planned
name, promoting an admitted identifier from planned to implemented, or adding
an independent axis whose identifiers are never persisted in a recipe, row, or
seal (as Phase 6.2 did for `input_family`) does not by itself change the schema
version; discovery consumers MUST be updated in the same change. Changing the
meaning of an existing identifier, allowed combination, or loss boundary
requires a new taxonomy schema version and a migration test.

Historical construction, finished-dataset, bundle, and handoff schemas remain
readable through their own loaders. This contract does not replace them.

## Non-goals

- Implementing preference, classification, tool-use, multimodal, pre-tokenized,
  or generated-data families.
- Adding consumer-specific trainer profiles or changing container semantics.
- Renaming `aptus-row-shape` without a versioned report migration.
- Declaring beta or public-ready maturity.
