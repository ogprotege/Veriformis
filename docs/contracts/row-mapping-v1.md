# Row Mapping Contract v1

**Contract ID:** `veriformis.row-mapping`

**Contract version:** `1`

**Discovery schema:** `veriformis.mapping-contract-discovery/v1`

**Status:** Models, discovery, JSONL/JSON/CSV/Parquet/Arrow capture, mapping
execution, detection, preview, membership policy, mixed mode, and the
dataset-row seal path are implemented through Phase 7.10 and item 9.7,
including packaged mapping templates.

**Last reviewed:** 2026-08-24 (independent-product Phase 9 closeout)

## Purpose

Define the persisted shapes for existing-dataset row sources, field mappings,
mapping plans, imported records, and `mapped_value` evidence. JSONL, JSON,
compatible CSV, Parquet, and Arrow IPC capture apply a confirmed
`mapping-plan/v1` into the four Finished Dataset v1 payload shapes. Suffix
does not switch compiler mode: `.parquet` and `.arrow` remain unsupported
in document-source parse. Dataset-row workspaces use revision schema 4 with
stages `parse → map → curate → split → format → validate → seal`. Format
emits ordinary `ProductRow` v1. Provenance lists mapping-rule ids instead of
construction chunk ids. Extra `columnar` lists the pins; Parquet and Arrow
capture import PyArrow only when those files are read.

## Closed vocabularies

| Vocabulary | v1 values |
| --- | --- |
| Admitted containers | `jsonl`, `json`, `csv`, `parquet`, `arrow` |
| Reserved containers | none |
| CSV dialect | header required, comma, UTF-8, no trim, no pad |
| Membership policy | `authoritative`, `advisory`, `replaced` |
| Coercion / missing / invalid-row | `refuse` |
| Review policy | `none` executes; `required` is representable but refuses execution because v1 has no durable review receipt |

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

Hub upload. Portable exact bytes for Parquet/Arrow. CSV `messages` rows.
Constrained CSV cannot represent nested `messages`; import refuses that
pair and names `split-jsonl-directory` or `json`. Parquet and Arrow admit
nested `messages`. Suffix never selects document-source versus dataset-row.

Rejected rows are recorded in `veriformis.mapping-rejection-report/v1`. That
report is a content-addressed project artifact, not a verified export. Accepted
rows may still seal; rejected rows never appear in the row set.

## Validation evidence

The imported validator receives exact captured raw sources. It recaptures
rows, verifies mapping confirmation, reconstructs the mapping recipe and
records, and derives split digests from the raw bytes. Split declarations
are not their own source evidence. Named gates also check lifecycle,
curation membership, exact deduplication, target length and source caps,
coverage, partition assignment, leakage groups, row payloads, schema,
canonical encoding, required partitions, and snapshot files.

A report must contain every ordered imported gate bound to its snapshot.
Passing gates carry no findings; failed gates require findings. Snapshot
files and row counts must agree. These checks do not change the v1 schema.
