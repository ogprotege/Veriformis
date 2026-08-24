# Phase 9 — Columnar and Hugging Face Dataset Containers

**Status:** In progress

**Started:** 2026-08-23

**Completed:**

**Roadmap phase:** [Phase 9](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-9--add-columnar-and-hugging-face-dataset-containers)

**Predecessor:** [Phase 8 closeout](../phase-08-consumer-profiles/closeout.md),
merged as PR #88 at `199e16eeabd8c624b571add9d28034830b3b92da` after all 16
GitHub checks passed. Clean local `main` equals `origin/main` there.

## Purpose

Add Parquet, Arrow, and local Hugging Face Dataset/DatasetDict as optional
generic containers over an already-verified bundle, plus Parquet/Arrow
import into the Phase 7 mapping path. Keep PyArrow and Hugging Face Datasets
out of core install, compile, seal, generic JSONL/JSON/CSV export, and core
pytest.

## Phase boundary

Phase 9 owns isolation extras, Arrow schema pins, semantic fingerprints,
three columnar renderers, mapping import, library reload harnesses, and
measured JSONL-versus-columnar benchmarks. It adds no trainer profile, no
Hub upload, no fourth row schema, and no claim of byte-identical files
across arbitrary third-party library versions.

Item 9.1 opens the packet, publishes ADR-0013, keeps the three containers
planned, and refuses those `container_id` values with the named later item.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Eight-item execution sequence, usability criteria, and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted scope decisions |
| [risks.md](risks.md) | Risk register and controls |
| [evidence.md](evidence.md) | Starting facts and observed proof |
| [closeout.md](closeout.md) | Exit-gate judgment |
| [SESSION.md](SESSION.md) | Crash-recovery pointer for the current item |

## Current state

Items 9.1–9.6 merged as PR #89–#94. Item 9.7 maps Parquet and Arrow into
Phase 7 dataset-row capture. Suffix does not switch modes. Taxonomy
`parquet`, `arrow`, and `hugging-face-dataset` remain planned. Extra
`columnar` stays empty. There is no Hub upload.
