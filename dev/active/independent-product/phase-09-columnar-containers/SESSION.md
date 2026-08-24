# Phase 9 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-24

**Local branch:** `phase9/08-harness-benchmarks-closeout` from `main`

**Predecessor:** Phase 9.7 merged as PR #95 at
`d452df35a52577852a0c1ccc9ad6e46f28983778`. Local `main` equals
`origin/main` there.

**Completed:** 9.1–9.7

**Current item:** 9.8 Harness, benchmarks, and Phase 9 closeout

**Not started:** Phase 10. Do not start Phase 10 or 13.

**9.8 design:** Optional `columnar_integration` CI installs pin-range
PyArrow and Datasets with `uv run --with` so the lock stays empty.
Harnesses reload Parquet, Arrow, and DatasetDict through those
libraries. Taxonomy promotion lands in this item.
