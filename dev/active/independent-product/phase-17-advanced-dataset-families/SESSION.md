# Phase 17 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-28

**Local branch:** `phase17/06-admit-preference`

**Completed:** Item 17.5, PR #154 at
`301d1a6c4477480a12bfcba66a9246f5a4607f61`.

**Current item:** 17.6 admit `preference-and-ranking`. Pair schema with
user-provided prompt, chosen, and rejected. Unpaired feedback and
ranking-order schemas skipped with a record. Profiles refuse the new
schema. Constrained CSV refuses it.

**Next gate:** Publish the 17.6 pull request, require every GitHub check,
merge, and synchronize clean `main` before item 17.7.

**Decision:** Chosen and rejected are user-provided `mapped_value`
fields. Document-source construction cannot invent them. Shared-prompt
leakage keeps one prompt in one partition.
