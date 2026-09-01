# Phase 20 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-09-01

**Local branch:** `phase20/05-clean-machine-cli`

**Completed:** Item 20.4, PR #184 at
`484b6ff69682a64e4deb5b14d5bfd380236061c3`.

**Current item:** 20.5 clean-machine CLI evidence. Isolated wheel install
then golden compile. No Aptus. Version stays `0.1.0`.

**Next gate:** Run the 20.5 local gates, publish the pull request, require
every GitHub check, merge, and synchronize clean `main`.

**Decision:** Honest 1.0 is CLI-first. Public signed Mac is not in the
matrix unless 20.6 produces owner-signed evidence (default skip).
Operator asked to plan and execute Phase 20 the same sequential-green-PR
way as Phase 19 on 2026-08-31.
