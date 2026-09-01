# Phase 20 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-09-01

**Local branch:** `phase20/08-profile-freeze`

**Completed:** Item 20.7, PR #187 at
`1d4ee9398763bb61f4d8cd5f45d360c5fbf3daab`.

**Current item:** 20.8 freeze optional profiles. Extras stay empty.
Unsloth is not executable. Version stays `0.1.0`.

**Next gate:** Run the 20.8 local gates, publish the pull request, require
every GitHub check, merge, and synchronize clean `main`.

**Decision:** Honest 1.0 is CLI-first. Public signed Mac is not in the
matrix unless 20.6 produces owner-signed evidence (default skip).
Operator asked to plan and execute Phase 20 the same sequential-green-PR
way as Phase 19 on 2026-08-31.
