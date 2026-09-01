# Phase 20 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-09-01

**Local branch:** `phase20/09-support-lifecycle`

**Completed:** Item 20.8, PR #188 at
`c914106ddfeb2495072bda1f1e07bb34f2d9d66d`.

**Current item:** 20.9 support-lifecycle documentation. Version stays
`0.1.0`. This item is not a version bump.

**Next gate:** Run the 20.9 local gates, publish the pull request, require
every GitHub check, merge, and synchronize clean `main`.

**Decision:** Honest 1.0 is CLI-first. Public signed Mac is not in the
matrix unless 20.6 produces owner-signed evidence (default skip).
Operator asked to plan and execute Phase 20 the same sequential-green-PR
way as Phase 19 on 2026-08-31.
