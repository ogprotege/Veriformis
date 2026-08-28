# Phase 17 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-28

**Local branch:** `phase17/08-admit-stepwise`

**Completed:** Item 17.7, PR #156 at
`132fd478bdd9f65518450a5ce3c8a93da5a6dad0`.

**Current item:** 17.8 admit `stepwise-supervision`. Prompt plus ordered
user-provided steps. Last step is the target. Profiles refuse the new
schema. Constrained CSV refuses it.

**Next gate:** Publish the 17.8 pull request, require every GitHub check,
merge, and synchronize clean `main` before item 17.9.

**Decision:** Steps are user-provided `mapped_value` fields. The compiler
does not invent chain-of-thought. Synthetic JSONL is the retained
fixture.
