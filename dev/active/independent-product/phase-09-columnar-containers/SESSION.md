# Phase 9 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-23

**Local branch:** `phase9/06-hf-dataset-export` from `main`

**Predecessor:** Phase 9.5 merged as PR #93 at
`df88c5c576df2aef4289b19cc1dc6e63fbb4b60d`. Local `main` equals
`origin/main`.

**Completed:** 9.1, 9.2, 9.3, 9.4, 9.5

**Current item:** 9.6 Emit a local Hugging Face dataset

**Not started:** 9.7–9.8. Do not start Phase 10 or 13.

**9.6 design:** Selector `hugging-face-dataset` v1, `consumer_id` null,
`semantic_content_only`. Dry-run plans fingerprints without Datasets or
PyArrow. Execute imports Hugging Face Datasets only at render time and
fails closed if it is absent. Extra `columnar` stays empty. Taxonomy
stays planned. No Hub upload.
