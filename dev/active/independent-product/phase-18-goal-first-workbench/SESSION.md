# Phase 18 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-29

**Local branch:** `phase18/06-prepublication-samples`

**Completed:** Item 18.5, PR #164 at `2faad0d`.

**Current item:** 18.6 pre-publication samples. ResultView shows recovery,
mapping, supervised region, preview-only quality, exclusions, and split
facts. Dry-run destination tree waits until a container is selected.
No renderer. No destination write. Quality does not block seal.

**Next gate:** Publish the 18.6 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 18.7.

**Decision:** ADR-0019 Decision A. Swift is a process adapter.
