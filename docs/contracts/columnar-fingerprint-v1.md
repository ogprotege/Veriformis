# Columnar Semantic Fingerprint v1

**Contract ID:** `veriformis.columnar-semantic-fingerprint`

**Contract version:** `1`

**Schema identifier:** `veriformis.columnar-semantic-fingerprint/v1`

**Status:** Implemented algorithm pin. Receipts still bind exact emitted
bytes of this run.

**Last reviewed:** 2026-08-24

## Purpose

Give Parquet, Arrow, and local Hugging Face Dataset exports a semantic
identity that does not depend on library-specific metadata. PyArrow and
Hugging Face Datasets may change compression, statistics, `created_by`,
dictionary encoding, or store logical UTF-8 as `large_utf8`. Those bytes
are not the identity.

The fingerprint is the SHA-256 of a lossless canonical JSON preimage of
one train or evaluation partition. Generic JSONL, JSON, and constrained
CSV keep `portable_exact_bytes`. Columnar v1 uses
`semantic_content_only`.

## Preimage

The preimage contains exactly:

| Field | Meaning |
| --- | --- |
| `schema_id` | `veriformis.columnar-semantic-fingerprint/v1` |
| `schema_pin_digest` | SHA-256 of the item 9.2 Arrow/feature catalog |
| `row_schema` | One v1 product row schema |
| `partition` | `train` or `evaluation` |
| `record_count` | Exact payload count, including zero |
| `payloads` | Ordered product payloads with exact Unicode strings |

Container identity is not in the preimage. The same rows and partition
fingerprint identically for `parquet`, `arrow`, and
`hugging-face-dataset`.

Serialization is `lossless_json_bytes`: exact strings, sorted object
keys, compact separators, UTF-8. Combining characters are not folded to
NFC.

## Excluded from the fingerprint

`arrow_endianness`, `compression`, `created_by`, `dictionary_encoding`,
`large_utf8_vs_utf8`, `parquet_key_value_metadata`, `row_group_layout`,
and `statistics`.

## Receipts

The export receipt still records the SHA-256 and byte size of each
emitted file for this pinned extra. That is instance identity, not a
portable exact-bytes claim.

## Nulls and nesting

Null product fields are unrepresentable and fail before hashing.
`messages` remains exactly two turns, user then assistant, with `role`
and `content`. Empty evaluation partitions have a defined fingerprint
over zero payloads.

## Non-goals

Emission. Hub upload. Portable exact bytes across library versions.
Changing JSONL/JSON/CSV determinism.

## Isolation

Core pytest and this pin must not import PyArrow, Hugging Face Datasets,
or pandas. Extra `columnar` stays empty.
