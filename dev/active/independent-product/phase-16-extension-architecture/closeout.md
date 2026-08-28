# Phase 16 Closeout

**Status:** Complete

**Last reviewed:** 2026-08-27

## Exit-gate judgment

Passed. The internal extension protocol is implemented. The text parser
and generic `split-jsonl-directory` exporter are selected through that
protocol with identical goldens. A missing or broken optional extra fails
in isolation; core CLI, MCP, and `PipelineService` still start. Compatibility
errors name exact contract versions. ADR-0017 Decision A: no untrusted
loader. Public plugin loading is skipped with a record. No in-process
project plugins. No Mac UI. Do not start Phase 17 from this packet.

## Usability criteria

| ID | Judgment | Evidence |
| --- | --- | --- |
| Internal protocol | Pass | `veriformis.extension-protocol/v1`; six kinds; builtin vs third-party origin |
| Two exemplars | Pass | `.txt` and generic `split-jsonl-directory` through the protocol; kit goldens |
| Isolation | Pass | Empty extras; broken extra=ocr fixture cannot advance `HEAD` or write a bundle |
| Compatibility diagnostics | Pass | Unknown versions name requested versus supported identity |
| No public plugin API | Pass | ADR-0017 Decision A; public loader skipped with a record |
| No Phase 17 | Pass | Packet and ledger forbid starting Phase 17 |

## Delivered scope

- 16.1 packet and pre-extension isolation.
- 16.2 `veriformis.extension-protocol/v1`.
- 16.3 built-in-only registry over existing bindings.
- 16.4 read-only capability declarations and discovery.
- 16.5 text parser migration.
- 16.6 generic `split-jsonl-directory` migration.
- 16.7 test-only compatibility kit.
- 16.8 ADR-0017 Decision A.
- 16.9 missing and broken extra isolation.
- 16.10 adversarial refusals and closeout. Public plugin loading skipped.

## Exclusions

Untrusted loader. Public plugin API. Workspace `plugins/` path. In-process
dataset-project Python. Mac plugin UI (Phase 18). New parsers, families,
containers, or profiles (Phase 17). Migrating every remaining suffix or
exporter; two exemplars satisfy the exit gate.

## Remaining debt

A later phase may propose Decision B (narrow sandbox) only with a new ADR
that supersedes ADR-0017. Until then third-party origin is a declaration
token, not an executable binding.

## Skip record

Public plugin loading in 16.9/16.10 is skipped with a record because
ADR-0017 selected Decision A. Same honesty as Phase 15.5–15.8.
