# Phase 18 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-28

**Local branch:** `phase18/02-thin-adapter-contract`

**Completed:** Item 18.1, PR #160 at
`73bf306bf53a650452f5d5dba5082ef842ced732`.

**Current item:** 18.2 pin the thin-adapter workbench contract. ADR-0019
and `veriformis.workbench-adapter/v1`. No Review, Exports, or dataset-row
UI.

**Next gate:** Publish the 18.2 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 18.3.

**Decision:** ADR-0019 Decision A. Swift is a process adapter.
PipelineService owns policy.
