# Phase 19 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-31

**Local branch:** `phase19/08-credential-isolation`

**Completed:** Item 19.7, PR #177 at
`f9ec2e4a4857d9286b48a91de31e2650ac9cc3ab`.

**Current item:** 19.8 credential isolation. Specs and locks refuse
credential-shaped fields. Injected env secrets must not persist.

**Next gate:** Publish the 19.8 pull request, require every GitHub check,
merge, and synchronize clean `main` before item 19.9.

**Decision:** ADR-0020 Decision A (pin only; no Hub execute). Operator
approved the Phase 19 plan as written on 2026-08-31.
