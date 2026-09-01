# Phase 20 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-09-01

**Local branch:** `phase20/06-signed-mac-skip`

**Completed:** Item 20.5, PR #185 at
`f47afdf35d2520d8a76bd0a2de91303dec6150e3`.

**Current item:** 20.6 skip signed Mac with a record. No xcodebuild.
Version stays `0.1.0`.

**Next gate:** Run the 20.6 local gates, publish the pull request, require
every GitHub check, merge, and synchronize clean `main`.

**Decision:** Honest 1.0 is CLI-first. Public signed Mac is not in the
matrix unless 20.6 produces owner-signed evidence (default skip).
Operator asked to plan and execute Phase 20 the same sequential-green-PR
way as Phase 19 on 2026-08-31.
