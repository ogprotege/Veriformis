# Phase 10 Evidence

**Status:** Open — item 10.2 pins

**Opened:** 2026-08-24

## Predecessor evidence

Phase 9 completed. Item 9.8 merged as PR #96 at
`abdcce6474aadd33fcf38a5360b63a4f8d293a5c` after all 18 GitHub checks
passed.

Operator compile of Pius X *Pascendi Dominici Gregis* at
`/Users/biscuit/Documents/Veriformis` (`2026-08-24T13-54-52Z`): `full_text`
/`text`, 31 train / 0 evaluation, manifest
`94b63232166aeedc9db797fdc0ec0167b2135d8c01bd3934635250a0a2245ace`. Seal
`self_consistent`; zip `external_digest`. Recorded in
[operator-compile-2026-08-24-pascendi.md](../operator-compile-2026-08-24-pascendi.md).

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| `trl` and `mlx-lm` are implemented export consumer profiles | `source-verified` | `src/veriformis/taxonomy.py` |
| `axolotl`, `llama-factory`, and `unsloth` are candidate identifiers | `source-verified` | `src/veriformis/taxonomy.py`; support registry |
| Selecting those candidate `consumer_id` values refuses as Phase 10 | `source-verified` | `ExportService._refuse_unexecutable_consumer_id` |
| Aptus is an optional sibling handoff, not an export consumer_id | `source-verified` | `docs/contracts/aptus-handoff-v1.md` |
| Extra `columnar` is empty; Parquet/Arrow/HF Dataset are implemented generics | `source-verified` | Phase 9 closeout |

## Required item 10.1 evidence

- [x] Packet opened; Phase 10 `in_progress`; Phase 9 merge cited.
- [x] ADR-0014 published and indexed.
- [x] Candidate profiles refuse export as Phase 10.
- [x] Existing generic and Phase 8 profile selectors remain executable.
- [x] Extras `axolotl`, `llama-factory`, and `unsloth` are empty lists; lock
      has no those trainer packages.
- [x] Focused isolation tests, tracking, Ruff, lock, and diff check.
