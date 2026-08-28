# Phase 17 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-28

**Local branch:** `phase17/07-admit-tool-calls`

**Completed:** Item 17.6, PR #155 at
`4496d0ebc851af20b2a94316a7520b9d3f20b096`.

**Current item:** 17.7 admit `tool-call-conversations`. New conversation
schema with user-provided tool traces. Two-turn `messages` stays exactly
two turns. Profiles refuse the new schema. Constrained CSV refuses it.

**Next gate:** Publish the 17.7 pull request, require every GitHub check,
merge, and synchronize clean `main` before item 17.8.

**Decision:** Tool traces are user-provided `mapped_value` fields. The
compiler does not call tools or invent traces. Conversation leakage
keeps one thread in one partition. Synthetic JSONL is the retained
fixture.
