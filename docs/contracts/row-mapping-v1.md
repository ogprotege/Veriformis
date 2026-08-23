# Row Mapping Contract v1

**Contract ID:** `veriformis.row-mapping`

**Contract version:** `1`

**Discovery schema:** `veriformis.mapping-contract-discovery/v1`

**Status:** Models, discovery, JSONL/JSON/CSV capture, mapping execution,
detection, preview, membership policy, mixed mode, and the dataset-row seal
path are implemented through Phase 7.8. Mapping templates remain item 7.10.

**Last reviewed:** 2026-08-23

## Purpose

Define the persisted shapes for existing-dataset row sources, field mappings,
mapping plans, imported records, and `mapped_value` evidence. JSONL, JSON,
and compatible CSV capture apply a confirmed `mapping-plan/v1` into the four
Finished Dataset v1 payload shapes. Dataset-row workspaces use revision
schema 4 with stages `parse → map → curate → split → format → validate →
seal`. Format emits ordinary `ProductRow` v1. Provenance lists mapping-rule
ids instead of construction chunk ids.

## Closed vocabularies

| Vocabulary | v1 values |
| --- | --- |
| Admitted containers | `jsonl`, `json`, `csv` |
| Reserved containers | none |
| CSV dialect | header required, comma, UTF-8, no trim, no pad |
| Membership policy | `authoritative`, `advisory`, `replaced` |
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

Mapping templates, Parquet/Arrow, and CSV `messages` rows. Constrained CSV
cannot represent nested `messages`; import refuses that pair and names
`split-jsonl-directory` or `json`.
