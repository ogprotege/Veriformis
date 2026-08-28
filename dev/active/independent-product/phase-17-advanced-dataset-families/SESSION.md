# Phase 17 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-28

**Local branch:** `phase17/09-generator-boundary`

**Completed:** Item 17.8, PR #157 at
`d4070236512dbf4f1827de1500360bb2d41c535b`.

**Current item:** 17.9 threat-model governed generation. ADR-0018
Decision A: no compile-path generator. This PR adds no `GeneratorPass`.

**Next gate:** Publish the 17.9 pull request, require every GitHub
check, merge, and synchronize clean `main` before item 17.10.

**Decision:** Decision A. Phase 17 does not install a generator.
Generated data is not source truth. ADR-0017 Decision A still holds.
