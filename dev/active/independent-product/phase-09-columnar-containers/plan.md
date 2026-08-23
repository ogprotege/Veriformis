# Phase 9 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-23

**Authority:** [Independent Product Roadmap](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 9; [program.json](../program.json); [ADR-0013](../../../../docs/adr/0013-columnar-containers-as-optional-generic-exports.md).

**Predecessor:** Phase 8 closeout merged as PR #88 at
`199e16eeabd8c624b571add9d28034830b3b92da` after all 16 GitHub checks
passed. Clean local `main` equals `origin/main` there.

Each numbered roadmap work item is one sequential pull request on branch
`phase9/0N-<slug>` titled `Phase 9.N: <imperative>`. A pull request must pass
its focused and required repository gates, pass every GitHub check, merge, and
leave clean local `main` equal to `origin/main` before the next item begins.

The plan below is the roadmap's eight work items, reordered so isolation,
schema pins, and semantic fingerprints land before emission. Closeout is
folded into 9.8, matching Phase 6, 7, and 8.

## Goal

Ship Parquet, Arrow, and local Hugging Face Dataset/DatasetDict as optional
generic containers with pinned schemas, semantic fingerprints, isolated
extras, library-reload harnesses, and mapping import, without pulling
columnar libraries into core.

## Architecture

`ExportService` remains the only export composition boundary.
`PipelineService`, CLI, MCP, and the Mac bridge are adapters. Columnar
containers are generic: `consumer_profile: null`. They are not trainer
profiles. TRL and MLX-LM stay split-JSONL adapters. Mapping import extends
the Phase 7 dataset-row path; suffix never switches modes.

## Standing constraints

- Core install, compile, seal, JSONL/JSON/CSV export, TRL/MLX-LM adapters,
  and core pytest never import PyArrow, Hugging Face Datasets, pandas, or
  another columnar library.
- Optional extra `columnar` and optional CI jobs, same isolation as Aptus
  and profile extras (`continue-on-error`, separate evidence).
- The verified six-file bundle remains canonical (ADR-0004). Columnar
  output may not curate, resplit, or change membership or loss-policy IDs.
- `messages` is in scope. Null product fields remain unrepresentable.
- Semantic fingerprints must be independent of library-specific metadata
  that can drift across PyArrow or datasets versions. Receipts still bind
  the exact emitted bytes of this pinned extra.
- No Hub upload, no network, no training launch.
- Python / CLI / MCP / Mac bridge agree on selector and produced files.
- Do not start Phase 10 or 13 from this packet.

## Key decisions (lock at 9.1)

| Decision | Recommendation | Why |
| --- | --- | --- |
| Generic containers, not profiles | `parquet`, `arrow`, and `hugging-face-dataset` are physical containers with `consumer_id` null. ADR-0013. | ADR-0003 already separates container from profile. |
| Isolation | Columnar libraries live in optional extra `columnar` and optional CI. Extra is empty until 9.2 pins versions. | Standalone release gates (ADR-0002). |
| Planned refusal | `parquet` refuses naming item 9.4; `arrow` refuses naming item 9.5; `hugging-face-dataset` refuses naming item 9.6. | Same honesty pattern as Phase 8.1. |
| Semantic vs exact bytes | Semantic fingerprint is the cross-version identity. Receipt SHA-256 is this-run exact bytes. Not `portable_exact_bytes` across library versions. | Roadmap item 5; Parquet is not JSONL. |
| Closeout | Folded into 9.8 with harnesses, benchmarks, and taxonomy promotion. | Phase 6, 7, and 8 precedent. |

## Likely files (created across the phase)

- Create: `dev/active/independent-product/phase-09-columnar-containers/` packet (9.1)
- Create: `docs/adr/0013-columnar-containers-as-optional-generic-exports.md` (9.1)
- Modify: `src/veriformis/exports/service.py` planned-container refusal (9.1)
- Create later: schema pins, fingerprint contract, renderers, mapping import, optional CI
- Do not modify in 9.1: production JSONL/JSON/CSV renderers, TRL/MLX-LM adapters, taxonomy implemented lists

---

## Checklist

### 9.1 Open the columnar-container packet

**Branch:** `phase9/01-columnar-packet`
**Title:** `Phase 9.1: Open the columnar-container packet`

- [x] Confirm the predecessor gate: Phase 8 completed, `HEAD == origin/main`.
- [x] Create the standard Phase 9 packet. Mark Phase 9 `in_progress` in `program.json`. Reconcile active tracking documents. Cite the Phase 8 closeout merge.
- [x] Publish ADR-0013.
- [x] Keep `parquet`, `arrow`, and `hugging-face-dataset` planned. Refuse those `container_id` values with the named later item.
- [x] Prove generic JSONL, JSON, CSV, TRL, and MLX-LM discovery still executable.
- [x] Declare empty extra `columnar` so `uv lock` does not pull PyArrow.
- [x] Record focused, tracking, lint, lock, and diff evidence. Do not claim Parquet, Arrow, or Hugging Face Dataset support.

### 9.2 Pin Arrow schemas for every row

**Branch:** `phase9/02-arrow-schema-pins`
**Title:** `Phase 9.2: Pin Arrow schemas for every row`

- [x] Packaged exact Arrow/feature schemas for all four row schemas, including nested messages. Official-doc review dates. Version ranges in data, not core lock.

### 9.3 Define semantic fingerprints

**Branch:** `phase9/03-semantic-fingerprints`
**Title:** `Phase 9.3: Define semantic fingerprints`

- [x] Versioned fingerprint independent of library metadata. Receipts still bind exact emitted bytes.

### 9.4 Emit Parquet

**Branch:** `phase9/04-parquet-export`
**Title:** `Phase 9.4: Emit Parquet`

- [x] Selector `parquet` v1, `consumer_id` null. Splits preserved. Nested `messages` admitted. Taxonomy remains planned.

### 9.5 Emit Arrow

**Branch:** `phase9/05-arrow-export`
**Title:** `Phase 9.5: Emit Arrow`

- [ ] Arrow IPC layout from the 9.2 pins. Split preservation, data card, receipt. Taxonomy remains planned.

### 9.6 Emit a local Hugging Face dataset

**Branch:** `phase9/06-hf-dataset-export`
**Title:** `Phase 9.6: Emit a local Hugging Face dataset`

- [ ] Local Dataset/DatasetDict directory with splits, features, and data card. Not Hub publish. Taxonomy remains planned.

### 9.7 Map Parquet and Arrow into Phase 7

**Branch:** `phase9/07-columnar-import`
**Title:** `Phase 9.7: Map Parquet and Arrow into Phase 7`

- [ ] Dataset-row mapping admits Parquet/Arrow. Suffix does not switch modes. Confirmed mapping and `mapped_value` evidence.

### 9.8 Load through the real libraries and close Phase 9

**Branch:** `phase9/08-harness-benchmarks-closeout`
**Title:** `Phase 9.8: Load through the real libraries and close Phase 9`

- [ ] Isolated harnesses and optional CI. Large values, nested roles, null refusal, Unicode, shard boundaries, empty eval, schema evolution, library reload.
- [ ] Measure JSONL versus columnar before any storage or speed claim.
- [ ] Promote the three containers to implemented. Closeout. Do not start Phase 10 or 13.

## Usability criteria

| ID | Criterion |
| --- | --- |
| U1 | Discovery does not imply implemented Parquet, Arrow, or Hugging Face Dataset containers. |
| U2 | Selecting a planned container fails in Veriformis with the later item, before PyArrow or datasets is imported. |
| U3 | A columnar export never changes membership or targets relative to the source bundle. |
| U4 | Null, nested-CSV-style, and incompatible rows fail in Veriformis before the library sees them. |
| U5 | Python, CLI, and MCP agree on container identity. |
| U6 | Core pytest passes without the columnar extra. |
| U7 | Compatible row schemas round-trip through each container with identical semantic fingerprints and partitions. |

## Exit gate

All current compatible row schemas round-trip through each new container with
identical semantic fingerprints and partitions. Core tests still pass without
the columnar extra. Version-drift tests fail clearly.

**Result:** Pending. See [closeout.md](closeout.md).
