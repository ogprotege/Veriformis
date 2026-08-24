# Phase 9 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-23

**Local branch:** `phase9/07-columnar-import` from `main`

**Predecessor:** Phase 9.6 merged as PR #94 at
`49b3901e177c15d7356d4ffc998b2c711e9137e2`. Local `main` equals
`origin/main`.

**Completed:** 9.1–9.6

**Current item:** 9.7 Map Parquet and Arrow into Phase 7

**Not started:** 9.8. Do not start Phase 10 or 13.

**9.7 design:** Dataset-row capture admits `.parquet` and `.arrow`.
Document-source parse of those suffixes stays unsupported. Extra
`columnar` stays empty; capture imports PyArrow only when those files
are read and fails closed if it is absent. Confirmed mapping plans and
`mapped_value` evidence are unchanged.
