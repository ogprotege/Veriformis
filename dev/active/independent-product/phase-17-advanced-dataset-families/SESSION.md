# Phase 17 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-28

**Local branch:** `phase17/05-admit-classification`

**Completed:** Item 17.4, PR #153 at
`07bb0d0fc7ca427db297bf55d1c5ed9d26627c95`.

**Current item:** 17.5 admit `explicit-label-classification`. Local gates
are green. Dataset-row mapping with user-provided context, label, and
annotator. Profiles refuse the new schema. Constrained CSV refuses it.

**Next gate:** Publish the 17.5 pull request, require every GitHub check,
merge, and synchronize clean `main` before item 17.6.

**Decision:** Labels are user-provided `mapped_value` fields. Document-source
construction cannot invent them.
