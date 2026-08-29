# Phase 18 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-28

**Local branch:** `phase18/01-workbench-packet`

**Completed:** Item 17.10, PR #159 at
`7d851c8a531eac7217051effe000048403a3b866`.

**Current item:** 18.1 open the goal-first-workbench packet. Honesty
records and isolation tests only. No new screen, mode, or CLI wrap.

**Next gate:** Publish the 18.1 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 18.2.

**Decision:** Swift remains a thin CLI adapter. PipelineService owns
policy.
