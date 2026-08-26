# Scale Corpus Contract v1

**Contract ID:** `veriformis.scale-corpus`

**Contract version:** `1`

**Schemas:** `veriformis.scale-corpus-spec/v1`, `veriformis.scale-corpus/v1`

**Status:** Implemented generators in independent-product Phase 15.2. No
published support tier, baseline harness, streaming API, or shard plan.

**Last reviewed:** 2026-08-26

**Authority:** [Independent Product Roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 15.

## Purpose

Generate deterministic, synthetic benchmark corpora from named dimensions.
The generator is not a second compiler. It does not compile, export, or
publish a throughput claim.

## Spec

A `ScaleCorpusSpec` binds `corpus_id`, `input_mode`
(`document-source` or `dataset-row`), `file_count`, `record_count`,
`row_length`, `nesting_depth`, `pdf_pages`, `duplicate_rate_ppm`, a
generic export `container` label, and a lowercase `seed`. Identity is
`derive_id("scs", …)` over the payload excluding `spec_id`.

PDF corpora require `record_count == file_count * pdf_pages`. Dataset-row
corpora cannot set `pdf_pages`. Constrained CSV cannot nest. Duplicate
rates that copy no record fail closed.

## Materialization

`materialize_scale_corpus` writes an empty destination and returns a
`ScaleCorpus` whose `total_bytes` and per-file SHA-256 are measured.
The same spec replays the same bytes. Owner library bytes never enter
the corpus. Large runs stay local; CI uses the packaged tiny specs.

Record payloads are HMAC-SHA256 of the seed and `record:{index}`, then
expanded to exact `row_length` Unicode characters, including `café`.

## Non-goals

Published support tiers. Named-hardware SLAs. Streaming or sharding.
Mac scale UX. Checking in generated blobs. Using Pascendi, Aquinas, or
Magisterium bytes as retained fixtures.
