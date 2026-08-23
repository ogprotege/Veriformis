# Phase 9 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-23

**Local branch:** `phase9/04-parquet-export` from `main`

**Predecessor:** Phase 9.3 merged as PR #91 at
`f4c35e12fcc4453e65e30e87266583727d5f6cd2`. Local `main` equals
`origin/main`.

**Completed:** 9.1, 9.2, 9.3

**Current item:** 9.4 Emit Parquet

**Not started:** 9.5–9.8. Do not start Phase 10 or 13.

**9.4 design:** Selector `parquet` v1, `consumer_id` null,
`semantic_content_only`. Dry-run plans fingerprints without PyArrow.
Execute imports PyArrow only at render time and fails closed if it is
absent. Extra `columnar` stays empty. Taxonomy stays planned.
