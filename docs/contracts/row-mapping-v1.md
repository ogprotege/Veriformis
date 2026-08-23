# Row Mapping Contract v1

**Contract ID:** `veriformis.row-mapping`

**Contract version:** `1`

**Discovery schema:** `veriformis.mapping-contract-discovery/v1`

**Status:** Models and discovery implemented in Phase 7.2. Capture and
execution remain item 7.3.

**Last reviewed:** 2026-08-23

## Purpose

Define the persisted shapes for existing-dataset row sources, field mappings,
mapping plans, imported records, and `mapped_value` evidence. Discovery is
read-only. No file is captured and no workspace is mutated by this contract
item.

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

## Non-goals

Capture, mapping execution, detection, preview, JSON/CSV admission, mixed
mode, and Parquet/Arrow.
