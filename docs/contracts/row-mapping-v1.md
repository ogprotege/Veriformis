# Row Mapping Contract v1

**Contract ID:** `veriformis.row-mapping`

**Contract version:** `1`

**Discovery schema:** `veriformis.mapping-contract-discovery/v1`

**Status:** Models, discovery, JSONL capture, mapping execution, and the
dataset-row seal path are implemented in Phase 7.3. Detection, preview,
JSON/CSV admission, mixed mode, and templates remain later items.

**Last reviewed:** 2026-08-23

## Purpose

Define the persisted shapes for existing-dataset row sources, field mappings,
mapping plans, imported records, and `mapped_value` evidence. JSONL capture
and mapping execution apply a confirmed `mapping-plan/v1` into the four
Finished Dataset v1 payload shapes. Dataset-row workspaces use revision
schema 4 with stages `parse → map → curate → split → format → validate →
seal`. Format emits ordinary `ProductRow` v1. Provenance lists mapping-rule
ids instead of construction chunk ids.

## Closed vocabularies

| Vocabulary | v1 values |
| --- | --- |
| Admitted containers | `jsonl` |
| Reserved containers | `json`, `csv` (item 7.8) |
| Membership policy | `replaced` |
| Coercion / missing / invalid-row | `refuse` |
| Review policy | `none`, `required` |

Payload keys are exactly the Finished Dataset v1 keys: `text`; `prompt` and
`completion`; `instruction`, `input`, and `output`; `messages`.

## Identities

Every persisted object recomputes its identity on load. Extra or missing
fields fail closed. Field values must match `mapped_value.output_sha256`.
The mapping recipe identity includes the mapping-plan id, every mapping-rule
id, the goal catalog SHA-256, and the selected sources, so a silent mapping
edit cannot reuse a prior seal. Imported row provenance names file, index,
JSON pointer, and mapping-rule ids. It does not claim construction chunks.

## Non-goals

Detection, preview, JSON/CSV admission, mixed mode, partition honor, mapping
templates, and Parquet/Arrow.
