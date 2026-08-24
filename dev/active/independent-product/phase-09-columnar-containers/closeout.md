# Phase 9 Closeout

**Status:** Complete

**Last reviewed:** 2026-08-24

## Exit-gate judgment

Passed. Parquet, Arrow IPC, and local Hugging Face DatasetDict v1 are
implemented optional generic containers over a verified bundle. Semantic
fingerprints are independent of library metadata. Receipts bind this-run
bytes. Core pytest still passes without PyArrow or Datasets. Optional
CI loads the artifacts through those libraries. Mapping admits Parquet
and Arrow without letting suffix switch modes. Hub upload remains out of
scope.

Item 9.8 is this closeout pull request. Do not start Phase 10 or 13 from
this packet.

## Usability criteria

| ID | Judgment | Current-tree evidence |
| --- | --- | --- |
| U1 | Pass | Discovery lists the three containers as implemented generic selectors with `consumer_id` null |
| U2 | Pass | Extra `columnar` stays empty; execute and capture fail closed naming the extra when libraries are absent |
| U3 | Pass | Library-reload tests keep train/evaluation membership and payload order |
| U4 | Pass | Null, extra columns, and mixed document/row parses fail in Veriformis |
| U5 | Pass | Python, CLI, and MCP share taxonomy, schema-pin, and export discovery identity |
| U6 | Pass | Core pytest excludes `columnar_integration`; lock has no PyArrow, datasets, or pandas |
| U7 | Pass | All four row schemas fingerprint identically across Parquet, Arrow, and DatasetDict after library reload |

## Delivered scope

- 9.1 opened the packet and published ADR-0013 (PR #89).
- 9.2 pinned Arrow types and Hugging Face features (PR #90).
- 9.3 defined `semantic_content_only` fingerprints (PR #91).
- 9.4 emitted generic Parquet v1 (PR #92).
- 9.5 emitted generic Arrow IPC v1 (PR #93).
- 9.6 emitted a local Hugging Face DatasetDict v1 (PR #94).
- 9.7 mapped Parquet and Arrow into Phase 7 dataset-row capture (PR #95).
- 9.8 added isolated library-reload harnesses, optional CI, measured JSONL versus columnar tree sizes, promoted the three containers, and closed the phase.

## Remaining bounds (not Phase 9 gaps)

- Extra `columnar` stays empty. Optional CI installs pin-range wheels only in that job.
- Columnar v1 does not claim portable exact bytes across PyArrow or Datasets versions.
- There is no Hub upload.
- Axolotl, LLaMA-Factory, Unsloth, and Aptus-as-profile remain Phase 10.
- Quality heuristics remain Phase 13.

## Verification summary

Local core gates for item 9.8 and the subsequent GitHub `ci` results are
recorded in `evidence.md`. Phase 10 may begin under its own packet when
the operator asks. Do not start Phase 10 or 13 from this closeout.
