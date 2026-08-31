# Phase 19 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-31

**Local branch:** `phase19/05-mcp-parity`

**Completed:** Item 19.4, PR #174 at
`f80bab4ffd714bec6dfcf354050b4aa71735bb0a`.

**Current item:** 19.5 MCP parity. Wrap project-spec packets. Skip
`package` / `package-verify` with a record. `run_pipeline` stays
pipeline/v1. No Hub. No quality-report.

**Next gate:** Publish the 19.5 pull request, require every GitHub check,
merge, and synchronize clean `main` before item 19.6.

**Decision:** ADR-0020 Decision A (pin only; no Hub execute). Operator
approved the Phase 19 plan as written on 2026-08-31.
