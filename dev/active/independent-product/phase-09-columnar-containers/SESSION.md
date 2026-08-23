# Phase 9 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-23

**Local branch:** `phase9/05-arrow-export` from `main`

**Predecessor:** Phase 9.4 merged as PR #92 at
`7af0a28fe2b4bf015c7bacffaf438cbc94ff047a`. Local `main` equals
`origin/main`.

**Completed:** 9.1, 9.2, 9.3, 9.4

**Current item:** 9.5 Emit Arrow

**Not started:** 9.6–9.8. Do not start Phase 10 or 13.

**9.5 design:** Selector `arrow` v1, `consumer_id` null,
`semantic_content_only`. Dry-run plans fingerprints without PyArrow.
Execute imports PyArrow only at render time and fails closed if it is
absent. Extra `columnar` stays empty. Taxonomy stays planned. Hugging
Face Dataset still refuses with item 9.6.
