# Phase 9 Evidence

**Status:** Open — item 9.8 closeout

**Opened:** 2026-08-23

## Predecessor evidence

Phase 8 completed. Item 8.7 merged as PR #88 at
`199e16eeabd8c624b571add9d28034830b3b92da` after all 16 GitHub checks
passed.

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| `parquet`, `arrow`, and `hugging-face-dataset` are planned taxonomy identifiers | `source-verified` | `src/veriformis/taxonomy.py`; `docs/governance/support-registry.json` |
| Production discovery has no those container selectors | `source-verified` | `ExportService.discover_exports()` |
| Core optional extras are `test`, `trl`, and `mlx-lm` | `source-verified` | `pyproject.toml` |
| Generic JSONL, JSON, and constrained CSV are implemented | `source-verified` | Phase 5 closeout |

## Required item 9.1 evidence

- [x] Packet opened; Phase 9 `in_progress`; Phase 8 merge cited.
- [x] ADR-0013 published and indexed.
- [x] Planned containers refuse export with items 9.4, 9.5, and 9.6.
- [x] Existing generic and profile selectors remain executable.
- [x] Extra `columnar` is an empty list; lock has no PyArrow or datasets packages.
- [x] Focused isolation tests passed (15 including Phase 8 isolation). Tracking,
      Ruff, lock, and diff check passed. Core pytest: 2009 passed, 3
      deselected, expected transport warning.
- [x] Item 9.1 merged as PR #89 at
      `719c961da3346c3102f26ebd03ddf7af01fded54` after all 16 GitHub checks
      passed.

## Required item 9.2 evidence

- [x] Packaged Arrow and Hugging Face feature pins cover all four row schemas,
      including nested `messages` with role then content.
- [x] Official-doc URLs and 2026-08-23 review dates on `pyarrow` and `datasets`.
- [x] Version ranges live in data. Extra `columnar` remains empty. Lock has no
      PyArrow, datasets, or pandas.
- [x] Python, CLI `columnar-schemas`, and MCP `columnar_schemas` emit the same
      canonical JSON. Importing pins does not import columnar libraries.
- [x] Planned containers still refuse. Taxonomy stays planned.
- [x] Focused pin and isolation tests passed (15). Tracking, Ruff, lock, and
      diff check passed. Core pytest: 2016 passed, 3 deselected, expected
      transport warning.
- [x] Item 9.2 merged as PR #90 at
      `2f31526e15f1fe3d2df394d959a92a124b909258` after all 16 GitHub checks
      passed.

## Required item 9.3 evidence

- [x] Packaged fingerprint contract names `semantic_content_only` and
      `receipt_binds=exact_emitted_bytes`.
- [x] Preimage is ordered payloads plus partition, row schema, and schema-pin
      digest. Container id and library metadata are excluded.
- [x] Unicode is lossless, not NFC-folded. Null, extra keys, and malformed
      messages fail closed. Empty evaluation has a defined fingerprint.
- [x] Same rows fingerprint identically regardless of later container choice.
- [x] Importing the pin does not import PyArrow, datasets, or pandas.
- [x] Focused fingerprint, schema, and isolation tests passed (26). Tracking,
      Ruff, lock, and diff check passed. Core pytest: 2027 passed, 3
      deselected, expected transport warning.
- [x] Item 9.3 merged as PR #91 at
      `f4c35e12fcc4453e65e30e87266583727d5f6cd2` after all 16 GitHub checks
      passed.

## Required item 9.4 evidence

- [x] Selector `parquet` v1, `consumer_id` null, `semantic_content_only`.
- [x] Dry-run plans train/evaluation Parquet fingerprints without importing
      PyArrow. Execute fails closed naming extra `columnar` when PyArrow is
      absent.
- [x] Nested `messages` is in the supported schema list. Taxonomy stays
      planned. Extra `columnar` stays empty.
- [x] Core pytest: 2030 passed, 3 deselected, expected transport warning.
- [x] Item 9.4 merged as PR #92 at
      `7af0a28fe2b4bf015c7bacffaf438cbc94ff047a` after all 16 GitHub checks
      passed.

## Required item 9.5 evidence

- [x] Selector `arrow` v1, `consumer_id` null, `semantic_content_only`.
- [x] Dry-run plans train/evaluation Arrow IPC fingerprints without importing
      PyArrow. Execute fails closed naming extra `columnar` when PyArrow is
      absent.
- [x] Nested `messages` is in the supported schema list. Taxonomy stays
      planned. Extra `columnar` stays empty. Hugging Face Dataset still
      refuses with item 9.6.
- [x] Core pytest: 2033 passed, 3 deselected, expected transport warning.
- [x] Item 9.5 merged as PR #93 at
      `df88c5c576df2aef4289b19cc1dc6e63fbb4b60d` after all 16 GitHub checks
      passed.

## Required item 9.6 evidence

- [x] Selector `hugging-face-dataset` v1, `consumer_id` null,
      `semantic_content_only`. Local DatasetDict layout. No Hub upload.
- [x] Dry-run plans train/evaluation fingerprints without importing Datasets
      or PyArrow. Execute fails closed naming extra `columnar` when Datasets
      is absent.
- [x] Nested `messages` is in the supported schema list. Taxonomy stays
      planned. Extra `columnar` stays empty.
- [x] Core pytest: 2038 passed, 3 deselected, expected transport warning.
- [x] Item 9.6 merged as PR #94 at
      `49b3901e177c15d7356d4ffc998b2c711e9137e2` after all 16 GitHub checks
      passed.

## Required item 9.7 evidence

- [x] Dataset-row mapping admits `parquet` and `arrow`. Nested `messages`
      is in scope. Suffix does not switch document-source to dataset-row.
- [x] Capture fails closed naming extra `columnar` when PyArrow is absent.
      Extra `columnar` stays empty. Confirmed mapping plans and
      `mapped_value` evidence remain the Phase 7 path.
- [x] Core pytest: 2043 passed before mixed-mode nits; focused mapping tests
      passed after operator-guide and capture review fixes.
- [x] Item 9.7 merged as PR #95 at
      `d452df35a52577852a0c1ccc9ad6e46f28983778` after all 16 GitHub checks
      passed.

## Required item 9.8 evidence

- [x] Isolated `columnar_integration` harnesses reload Parquet, Arrow, and
      DatasetDict through PyArrow and Hugging Face Datasets. Large values,
      nested roles, null refusal, Unicode, shard extra files, empty
      evaluation, and schema evolution fail closed or round-trip as
      specified. Focused optional tests: 12 passed.
- [x] Optional CI job `columnar-integration` uses `continue-on-error` and
      `uv run --with` pin ranges, plus Hub-offline flags. Extra `columnar`
      stays empty. Lock has no PyArrow, datasets, or pandas.
- [x] JSONL versus columnar tree sizes on the Phase 3 full-text fixture:
      split JSONL 24,073 bytes, Parquet 25,162, Arrow 25,386, DatasetDict
      31,733. Recorded as this-run sizes, not a recommendation.
- [x] Taxonomy, support registry, and goal catalog list the three containers
      as implemented. Core pytest: 2043 passed, 15 deselected, expected
      transport warning.
- [x] Library reload required two renderer fixes: DatasetDict `num_shards`
      is a per-split dict; list-of-struct Features uses `[struct]`; empty
      evaluation uses `Dataset.from_dict` so the pinned shard remains.
