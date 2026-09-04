# Arrow Export v1

**Container ID:** `arrow`

**Container version:** `1`

**Determinism claim:** `semantic_content_only`

**Status:** Implemented generic export. Extra `columnar` lists the pins.

**Last reviewed:** 2026-08-24

## Purpose

Emit train and evaluation Arrow IPC files from a verified bundle without
changing membership. Nested `messages` is in scope. `consumer_id` is
null.

Semantic identity is the item 9.3 fingerprint over ordered product
payloads. The export receipt binds the exact emitted bytes of this run.
This is not portable exact bytes across PyArrow versions.

## Layout

| Path | Role |
| --- | --- |
| `data/train.arrow` | Train payloads (Arrow IPC file) |
| `data/evaluation.arrow` | Evaluation payloads, including empty |
| `metadata/dataset-card.json` | Machine-readable layout |
| `metadata/row-provenance.jsonl` | Aligned provenance |
| `README.md` | Human-readable description |
| `export-receipt.json` | Receipt |

Arrow types come from the item 9.2 pins. Null product fields fail in
Veriformis. Render and replay import PyArrow only when those operations
run. Dry-run plans fingerprints without importing PyArrow. If PyArrow is
absent, execute fails closed naming extra `columnar`.

## Non-goals

Hub upload. Portable exact bytes. Trainer profiles. Parquet and
Hugging Face DatasetDict are separate generic containers.
