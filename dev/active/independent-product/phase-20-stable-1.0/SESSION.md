# Phase 20 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-31

**Local branch:** `phase20/01-stable-packet`

**Completed:** Phase 19 closeout, PR #180 at
`084e504a799b6c1c1cc130c8ee819b13de5d6bbe`.

**Current item:** 20.1 packet and honesty locks. Version stays `0.1.0`.
No matrix freeze, version bump, signed Mac, or Hub execute.

**Next gate:** Run the 20.1 local gates, publish the pull request, require
every GitHub check, merge, and synchronize clean `main`.

**Decision:** Honest 1.0 is CLI-first. Public signed Mac is not in the
matrix unless 20.6 produces owner-signed evidence (default skip).
Operator asked to plan and execute Phase 20 the same sequential-green-PR
way as Phase 19 on 2026-08-31.
