# Phase 18 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-29

**Local branch:** `phase18/04-input-modes-and-mapping`

**Completed:** Item 18.3, PR #162 at
`acf8ee405616d3b6ae8fa443cc3eb49f77bc790a`.

**Current item:** 18.4 input modes and mapping preview. Mode picker is
`document-source`, `dataset-row`, and `mixed`. Dataset-row wraps
mapping-detect, operator confirm, mapping-preview, then parse and map.
Unconfirmed plans cannot compile. Family goals wait for a confirmed
mapping plan.

**Next gate:** Publish the 18.4 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 18.5.

**Decision:** ADR-0019 Decision A. Swift is a process adapter.
PipelineService owns policy. Mapping is confirm-then-map.
