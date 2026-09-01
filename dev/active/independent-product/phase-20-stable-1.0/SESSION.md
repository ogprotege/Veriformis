# Phase 20 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-09-01

**Local branch:** `phase20/04-security-review`

**Completed:** Item 20.3, PR #183 at
`0d9919af31d1dfdd7e13baafacf4420cac9b9f55`.

**Current item:** 20.4 license, parser-threat, secret, and provenance
review. Version stays `0.1.0`. No pip-audit CI job. No signed Mac.

**Next gate:** Run the 20.4 local gates, publish the pull request, require
every GitHub check, merge, and synchronize clean `main`.

**Decision:** Honest 1.0 is CLI-first. Public signed Mac is not in the
matrix unless 20.6 produces owner-signed evidence (default skip).
Operator asked to plan and execute Phase 20 the same sequential-green-PR
way as Phase 19 on 2026-08-31.
