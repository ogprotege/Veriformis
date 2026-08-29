# Phase 18 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-29

**Local branch:** `phase18/08-review-flows`

**Completed:** Item 18.7, PR #166 at `259412d`.

**Current item:** 18.8 review flows. Sidebar adds Review. Wrap
review-export, review-import, and operator-confirmed review-submit.
Default `review_policy` stays `none`. Corrections are new identities.
Required unresolved reviews still block seal.

**Next gate:** Publish the 18.8 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 18.9.

**Decision:** ADR-0019 Decision A. Swift is a process adapter.
