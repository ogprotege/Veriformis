# Hugging Face Dataset Export v1

**Container ID:** `hugging-face-dataset`

**Container version:** `1`

**Determinism claim:** `semantic_content_only`

**Status:** Implemented generic export. Extra `columnar` remains empty.
There is no Hub upload.

**Last reviewed:** 2026-08-24

## Purpose

Emit a local Hugging Face `DatasetDict` directory from a verified bundle
without changing membership. Nested `messages` is in scope. `consumer_id`
is null. There is no Hub upload.

Semantic identity is the item 9.3 fingerprint over ordered product
payloads. The export receipt binds the exact emitted bytes of this run.
This is not portable exact bytes across Datasets versions.

## Layout

| Path | Role |
| --- | --- |
| `dataset/dataset_dict.json` | DatasetDict split index |
| `dataset/train/data-00000-of-00001.arrow` | Train payloads |
| `dataset/train/dataset_info.json` | Library split info |
| `dataset/train/state.json` | Library split state |
| `dataset/evaluation/data-00000-of-00001.arrow` | Evaluation payloads, including empty |
| `dataset/evaluation/dataset_info.json` | Library split info |
| `dataset/evaluation/state.json` | Library split state |
| `metadata/dataset-card.json` | Machine-readable layout |
| `metadata/row-provenance.jsonl` | Aligned provenance |
| `README.md` | Human-readable description |
| `export-receipt.json` | Receipt |

Features come from the item 9.2 pins. Null product fields fail in
Veriformis. Render and replay import Hugging Face Datasets only when those
operations run. Dry-run plans fingerprints without importing Datasets or
PyArrow. If Datasets is absent, execute fails closed naming extra
`columnar`.

## Non-goals

Hub upload. Portable exact bytes. Trainer profiles. Remote `load_dataset`.
