# Phase 20 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-09-01

**Local branch:** `phase20/10-version-and-closeout`

**Completed:** Item 20.9, PR #189 at
`eff1bfa962d438863814f1449330fe12fa660a9d`.

**Current item:** 20.10 retain `0.1.0` and close Phase 20. Sealed
manifests bind `veriformis_version`. Goldens stay byte-identical.
Do not invent a Phase 21.

**Next gate:** Run the 20.10 local gates, publish the pull request, require
every GitHub check, merge, and synchronize clean `main`.

**Decision:** Honest 1.0 is CLI-first. Public signed Mac is not in the
matrix unless 20.6 produces owner-signed evidence (default skip).
Operator asked to plan and execute Phase 20 the same sequential-green-PR
way as Phase 19 on 2026-08-31.
