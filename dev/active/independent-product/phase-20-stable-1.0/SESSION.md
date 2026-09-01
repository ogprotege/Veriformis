# Phase 20 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-31

**Local branch:** `phase20/02-support-matrix`

**Completed:** Item 20.1, PR #181 at
`1f6660944fccd3bdcfdfe1ac88270866211bd613`.

**Current item:** 20.2 freeze the CLI-first 1.0 support matrix. Version
stays `0.1.0`. No signed Mac, Hub execute, or version bump.

**Next gate:** Run the 20.2 local gates, publish the pull request, require
every GitHub check, merge, and synchronize clean `main`.

**Decision:** Honest 1.0 is CLI-first. Public signed Mac is not in the
matrix unless 20.6 produces owner-signed evidence (default skip).
Operator asked to plan and execute Phase 20 the same sequential-green-PR
way as Phase 19 on 2026-08-31.
