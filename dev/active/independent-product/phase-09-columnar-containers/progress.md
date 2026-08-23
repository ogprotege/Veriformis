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
