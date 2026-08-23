# Phase 9 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-23

**Local branch:** `phase9/03-semantic-fingerprints` from `main`

**Predecessor:** Phase 9.2 merged as PR #90 at
`2f31526e15f1fe3d2df394d959a92a124b909258`. Local `main` equals
`origin/main`.

**Completed:** 9.1, 9.2

**Current item:** 9.3 Define semantic fingerprints

**Not started:** 9.4–9.8. Do not start Phase 10 or 13.

**9.3 design:** Versioned lossless preimage over ordered product payloads
and the 9.2 schema-pin digest. `semantic_content_only`. Container id is
not in the preimage. Receipts still bind exact emitted bytes. Extra
`columnar` stays empty. No files emitted.
