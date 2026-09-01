# Phase 20 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-31

**Local branch:** `phase20/03-migration-completeness`

**Completed:** Item 20.2, PR #182 at
`aa91d49331ab5fec264593287baf89d3fbb116e1`.

**Current item:** 20.3 migration completeness and operator guide. Version
stays `0.1.0`. Unknown versions fail closed.

**Next gate:** Run the 20.3 local gates, publish the pull request, require
every GitHub check, merge, and synchronize clean `main`.

**Decision:** Honest 1.0 is CLI-first. Public signed Mac is not in the
matrix unless 20.6 produces owner-signed evidence (default skip).
Operator asked to plan and execute Phase 20 the same sequential-green-PR
way as Phase 19 on 2026-08-31.
