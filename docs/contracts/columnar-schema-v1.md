# Columnar Schema Pins v1

**Contract ID:** `veriformis.columnar-schema-pin`

**Contract version:** `1`

**Discovery schema:** `veriformis.columnar-schema-discovery/v1`

**Status:** Implemented Arrow and Hugging Face feature pins for the three
columnar generic containers. Extra `columnar` remains empty.

**Last reviewed:** 2026-08-24

## Purpose

Pin exact Arrow types and Hugging Face `Features` for every v1 product
row schema, including nested `messages`. A pin records official-doc URLs,
review dates, licenses, the empty extra name, and version ranges. Version
ranges live in this catalog. They are not core lock pins.

Taxonomy lists `parquet`, `arrow`, and `hugging-face-dataset` as
implemented. Selecting those identifiers plans and can emit those
containers. TRL and MLX-LM remain split-JSONL adapters.

## Closed vocabularies

| Vocabulary | v1 values |
| --- | --- |
| State | `implemented` |
| Extra | `columnar` |
| Null policy | `unrepresentable` |
| Round-trip | `false` |
| Packages | `datasets`, `pyarrow` in that order |
| Row schemas | `instruction_output`, `messages`, `prompt_completion`, `text` |
| Arrow kinds | `utf8`, `list`, `struct` |
| Hugging Face kinds | `value` with `dtype=string`, `list`, `struct` |
| Messages | exactly two turns, `user` then `assistant`; struct fields `role` then `content` |

Column order is product payload order, not alphabetical:

- `text`: `text`
- `prompt_completion`: `prompt`, `completion`
- `instruction_output`: `instruction`, `input`, `output`
- `messages`: `messages`

Every column and nested field is non-null. Empty strings remain product
strings; JSON `null` is refused later in Veriformis before a library sees
the row.

Hugging Face Datasets may physically store `large_utf8` for a logical
string. Semantic identity across library encodings is item 9.3. Receipts
still bind the exact emitted bytes of a pinned extra.

## Isolation

Optional extra `columnar` remains an empty list. Core install, compile,
seal, generic JSONL/JSON/CSV export, TRL/MLX-LM adapters, and core pytest
must not import PyArrow, Hugging Face Datasets, or pandas.

## Non-goals

Hub upload. Portable exact bytes across library versions. Phase 10
trainer profiles.

## Discovery

Python `PipelineService.discover_columnar_schemas()`, CLI
`veriformis columnar-schemas`, and MCP `columnar_schemas` emit the same
canonical JSON as `src/veriformis/exports/columnar_schemas-v1.json`.
