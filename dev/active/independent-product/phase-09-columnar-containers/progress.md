# Phase 9 Progress

Append-only. Corrections add a later entry.

## 2026-08-23 — Phase 9 opened; item 9.1 in progress

**Status:** Packet created from clean `main` at
`199e16eeabd8c624b571add9d28034830b3b92da` (PR #88).

Item 9.1 publishes ADR-0013 and keeps `parquet`, `arrow`, and
`hugging-face-dataset` planned. Selecting those container identifiers
refuses with the later item. Extra `columnar` is an empty list. Do not
emit Parquet, Arrow, or Hugging Face Dataset files.

Focused isolation tests passed (15 including Phase 8 isolation). Tracking,
Ruff, lock, and diff check passed. Core pytest passed 2009 with 3
deselected and the intentional transport durability warning.

**Next action:** Publish the item 9.1 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 9.2.

## 2026-08-23 — Item 9.1 merged; item 9.2 in progress

**Status:** Item 9.1 merged as PR #89 at
`719c961da3346c3102f26ebd03ddf7af01fded54` after all 16 GitHub checks
passed. Clean local `main` equals `origin/main`.

Item 9.2 packages exact Arrow types and Hugging Face features for
`text`, `prompt_completion`, `instruction_output`, and nested `messages`.
Official docs reviewed 2026-08-23. Version ranges live in
`columnar_schemas-v1.json`. Extra `columnar` stays empty. Taxonomy stays
planned. Do not emit Parquet, Arrow, or Hugging Face Dataset files.

**Next action:** Publish the item 9.2 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 9.3.

## 2026-08-23 — Item 9.2 merged; item 9.3 in progress

**Status:** Item 9.2 merged as PR #90 at
`2f31526e15f1fe3d2df394d959a92a124b909258` after all 16 GitHub checks
passed. Clean local `main` equals `origin/main`.

Item 9.3 packages the semantic fingerprint preimage: ordered product
payloads, partition, row schema, and the 9.2 schema-pin digest.
`determinism_claim` is `semantic_content_only`. Container identity and
library metadata are excluded. Receipts still bind exact emitted bytes.
Extra `columnar` stays empty. Taxonomy stays planned.

**Next action:** Publish the item 9.3 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 9.4.

## 2026-08-23 — Item 9.3 merged; item 9.4 in progress

**Status:** Item 9.3 merged as PR #91 at
`f4c35e12fcc4453e65e30e87266583727d5f6cd2` after all 16 GitHub checks
passed. Clean local `main` equals `origin/main`.

Item 9.4 emits generic Parquet v1 with `consumer_id` null and
`semantic_content_only`. Dry-run plans fingerprints without PyArrow.
Execute fails closed if PyArrow is absent. Extra `columnar` stays empty.
Taxonomy stays planned.

**Next action:** Publish the item 9.4 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 9.5.

## 2026-08-23 — Item 9.4 merged; item 9.5 in progress

**Status:** Item 9.4 merged as PR #92 at
`7af0a28fe2b4bf015c7bacffaf438cbc94ff047a` after all 16 GitHub checks
passed. Clean local `main` equals `origin/main`.

Item 9.5 emits generic Arrow IPC v1 with `consumer_id` null and
`semantic_content_only`. Dry-run plans fingerprints without PyArrow.
Execute fails closed if PyArrow is absent. Extra `columnar` stays empty.
Taxonomy stays planned. Hugging Face Dataset still refuses with item 9.6.

**Next action:** Publish the item 9.5 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 9.6.

## 2026-08-23 — Item 9.5 merged; item 9.6 in progress

**Status:** Item 9.5 merged as PR #93 at
`df88c5c576df2aef4289b19cc1dc6e63fbb4b60d` after all 16 GitHub checks
passed. Clean local `main` equals `origin/main`.

Item 9.6 emits a local Hugging Face DatasetDict v1 with `consumer_id`
null and `semantic_content_only`. Dry-run plans fingerprints without
Datasets. Execute fails closed if Datasets is absent. Extra `columnar`
stays empty. Taxonomy stays planned. There is no Hub upload.

**Next action:** Publish the item 9.6 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 9.7.

## 2026-08-23 — Item 9.6 merged; item 9.7 in progress

**Status:** Item 9.6 merged as PR #94 at
`49b3901e177c15d7356d4ffc998b2c711e9137e2` after all 16 GitHub checks
passed. Clean local `main` equals `origin/main`.

Item 9.7 admits Parquet and Arrow into Phase 7 dataset-row capture.
Suffix does not switch modes. Extra `columnar` stays empty. Capture
imports PyArrow only when those files are read.

**Next action:** Publish the item 9.7 pull request. Require green GitHub
checks, merge, and synchronize clean main before item 9.8.

## 2026-08-24 — Item 9.7 merged; item 9.8 in progress

**Status:** Item 9.7 merged as PR #95 at
`d452df35a52577852a0c1ccc9ad6e46f28983778` after all 16 GitHub checks
passed. Clean local `main` equals `origin/main`.

Item 9.8 adds isolated library-reload harnesses and optional
`columnar-integration` CI that installs pin-range PyArrow and Datasets
with `uv run --with`. It measures JSONL versus columnar tree sizes,
promotes `parquet`, `arrow`, and `hugging-face-dataset` to implemented,
and closes Phase 9. Extra `columnar` stays empty. Do not start Phase 10
or 13.

**Next action:** Publish the item 9.8 pull request. Require green GitHub
checks, merge, and synchronize clean main.

## 2026-08-24 — Phase 9 closed; operator compile observed

**Status:** Item 9.8 merged as PR #96 at
`abdcce6474aadd33fcf38a5360b63a4f8d293a5c` after all 18 GitHub checks
passed. Clean local `main` equals `origin/main`.

Operator compile at `/Users/biscuit/Documents/Veriformis` (timestamp
`2026-08-24T13-54-52Z`): one Markdown source, Pius X *Pascendi Dominici
Gregis* (`1907-09-08_pascendi-dominici-gregis.md`), parser `markdown`.
Recipe `full_text` / target row `text`. 31 chunks, 31 accepted, 31
curated in, 0 excluded. Split: 31 train, 0 evaluation, 1 leakage group
(expected for a single source). All 17 dataset gates passed. Bundle
manifest SHA-256
`94b63232166aeedc9db797fdc0ec0167b2135d8c01bd3934635250a0a2245ace`.
Seal grade `self_consistent`; transport zip archive SHA-256
`ab51ba97a960c6f15acb07a9706839060c914da3f41ffab6fa24d1d304ba7928`
verified `external_digest`. One train row is scrape front matter, not
encyclical prose. No generic columnar or trainer-profile export in this
run.

Phase 9 is complete. 
