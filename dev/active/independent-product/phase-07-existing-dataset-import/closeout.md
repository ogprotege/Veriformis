# Phase 7 Closeout

**Status:** Complete

**Last reviewed:** 2026-08-23

## Exit-gate judgment

Passed. Representative `text`, prompt/completion, instruction/input/output,
and two-turn message datasets import under explicit confirmed mappings,
validate, seal, generically export, and semantically round-trip. Ambiguous or
lossy mappings do not auto-publish. Document-source compilation remains the
default and does not switch on suffix.

Closeout first merged on local admission evidence while GitHub Actions was
budget-blocked. After the spending limit was increased, PR #80 at
`b7bb7f0c2046fba87fd7c9da12f7d2ccb5c2c88f` passed all 14 GitHub checks and
the `main` `ci` run 32617948069 succeeded. Intermediate PRs #71–#79 remain
historically budget-failed on GitHub; the current tree is the closeout SHA.

## Usability criteria

| ID | Judgment | Current-tree evidence |
| --- | --- | --- |
| U1 | Pass | `tests/mapping/test_input_modes.py` — document-source default; dataset-row is explicit; suffix does not switch paths |
| U2 | Pass | `tests/mapping/test_mapping_detect.py` — unique and ambiguous files require confirmation |
| U3 | Pass | `tests/mapping/test_mapping_preview.py` — full-file preview reports later rejects |
| U4 | Pass | `tests/mapping/test_mapping_provenance.py` — mapped_value replay and tamper refusals |
| U5 | Pass | `tests/mapping/test_jsonl_row_mapping.py` — Python / CLI / MCP identity parity |
| U6 | Pass | `tests/mapping/test_membership.py` — authoritative leakage fails closed |
| U7 | Pass | `tests/mapping/test_json_csv_roundtrip.py` — JSONL × 4, JSON × 4, CSV × 3 map → seal → generic export |

Mac detect decode is present on the CLI bridge
(`macos/Sources/Services/VeriformisCLI.swift`). Full XCTest mapping
walkthroughs were not re-run in this closeout. The GitHub macOS pytest job
(`test (py3.12, macos-latest)`) passed on the closeout SHA.

## Delivered scope

- 7.1 named `document-source`, `dataset-row`, and `mixed` (PR #71).
- 7.2 froze row-mapping contracts (PR #72).
- 7.3 mapped JSONL into the four semantic rows on workspace revision v4 (PR #73).
- 7.4 required confirmation of detector proposals (PR #74).
- 7.5 bound mapping provenance and replay (PR #75).
- 7.6 previewed mapping across the full file (PR #76).
- 7.7 honored imported partitions and admitted mixed mode with distinct provenances (PR #77).
- 7.8 admitted JSON and compatible CSV and proved production round trips (PR #78).
- 7.9 exported row-level rejections as a content-addressed project artifact (PR #79).
- 7.10 shipped mapping templates, the operator guide, U1–U7 judgment, and this closeout.

## Remaining bounds (not Phase 7 gaps)

- Parquet / Arrow / Hugging Face Dataset import remains Phase 9.
- Consumer profiles remain Phase 8.
- Quality heuristics remain Phase 13.
- A full Mac mapping spreadsheet remains Phase 18.
- CSV cannot represent nested `messages`.
- No trainer, spreadsheet, or Hub compatibility claim.

`gap-existing-dataset-row-mapping` is closed. Those later phases are new work,
not an open Phase 7 gap.

## Verification summary

Local core gates for item 7.10 and the subsequent GitHub `ci` results are
recorded in `evidence.md`. Phase 8 may begin under its own packet when the
operator asks. Do not start Phase 9 or 13 from this closeout.
