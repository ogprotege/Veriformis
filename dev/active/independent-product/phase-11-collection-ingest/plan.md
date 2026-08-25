# Phase 11 Execution Plan

**Status:** Complete

**Last updated:** 2026-08-25

**Authority:** Independent Product Roadmap Phase 11; ADR-0015; ADR-0008.

**Predecessor:** Phase 10 completed. Homepage PR #103 at `0b0e188`.

Items 11.1–11.8 land as one pull request by operator instruction 2026-08-25.

## Goal

Make a mixed directory a deterministic, fail-closed ingest unit without
claiming any-input behavior.

## Checklist

### 11.1 Open the collection-ingest packet

- [x] Packet, program ledger, ADR-0015.

### 11.2 Add the collection plan

- [x] `veriformis.collection-plan/v1`; PipelineService/CLI/MCP/Mac share it.

### 11.3 Add collection preflight inventory

- [x] `collect` prints accepted/ignored/refused/duplicate counts; parse and
  compile preflight expand through the same plan.

### 11.4 Decide archive expansion

- [x] Skipped. Zip remains export transport.

### 11.5 Build per-parser hardening corpora

- [x] `tests/parsers/test_hardening_matrix.py`.

### 11.6 Isolate crash-prone parsers only if needed

- [x] Skipped. In-process fail-closed remains the v1 boundary.

### 11.7 Record parser versions and recovery quality

- [x] `veriformis.parsers.identity`; parse-report status unchanged.

### 11.8 Rank new types, admit none without evidence, and close

- [x] Owner-corpus still unranked. No new families. Closeout.

## Usability criteria

| ID | Criterion |
| --- | --- |
| U1 | Folder to Mac and CLI `parse` produce the same source ids and order |
| U2 | Unsupported, hidden, and duplicate members are counted |
| U3 | Limits fail closed |
| U4 | Symlinks fail closed |
| U5 | Explicit file-list compile is unchanged |
| U6 | Discovery does not name unimplemented families |
| U7 | Image-only PDF still refuses as ocr-image |

## Exit gate

A mixed directory fixture produces a deterministic inventory and source order;
malicious collection fixtures fail safely; documentation matches dispatch.
