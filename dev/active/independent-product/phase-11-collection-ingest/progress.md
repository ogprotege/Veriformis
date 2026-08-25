# Phase 11 Progress

**Status:** Append-only

## 2026-08-25 — Combined 11.1–11.8

Opened the packet and published ADR-0015. Implemented collection plan v1
behind `PipelineService`, CLI `collect`, MCP `collect`, and automatic
expansion in `parse` / compile `preflight`. Replaced the Mac folder walk.
Skipped archive ingest, parser subprocess isolation, and new input families
with explicit records. Added parser identity pins and per-parser hardening
fixtures. Closeout is this pull request. Do not start Phase 12 or 13.
