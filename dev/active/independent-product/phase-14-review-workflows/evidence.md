# Phase 14 Evidence

**Status:** Open — item 14.4 corrections as transforms or mapping revisions

**Opened:** 2026-08-26

## Predecessor evidence

Phase 13 completed. Closeout merged as PR #122 at
`ef31559c9184b553209a3c45eca5d943fbb9a680`, then stamped as PR #123 at
`4d7b00fca9b685df95aa2a19349604f2b40d2406`.

Operator compile of Pius X *Pascendi Dominici Gregis* at
`/Users/biscuit/Documents/Veriformis` (`2026-08-24T13-54-52Z`): `full_text`
/`text`, 31 train / 0 evaluation, manifest
`94b63232166aeedc9db797fdc0ec0167b2135d8c01bd3934635250a0a2245ace`. Seal
`self_consistent`; zip `external_digest`. Recorded in
[operator-compile-2026-08-24-pascendi.md](../operator-compile-2026-08-24-pascendi.md).

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| Construction `review_policy` defaults to `none` | `source-verified` | `src/veriformis/construction/models.py` `DatasetRecipe` |
| `ReviewEvidence` has `reviewer_id`, `verdict`, `rationale`; no signature | `source-verified` | `src/veriformis/construction/models.py` `ReviewEvidence` |
| CLI `construct` has `--require-review` and no reviews payload | `source-verified` | `src/veriformis/cli.py` `construct` |
| `PipelineService.construct` accepts no `reviews` argument | `source-verified` | `src/veriformis/pipeline/service.py` |
| OCR preview records `pending_review` hooks, not a queue | `source-verified` | `src/veriformis/ocr/preview.py` |
| No quality heuristic is admitted to block seal | `source-verified` | `src/veriformis/quality/gates.py` `V1_QUALITY_GATES` |
| Seventeen finished-dataset gates unchanged | `source-verified` | `src/veriformis/contracts.py` `V1_FINISHED_DATASET_GATES` |

## Required item 14.1 evidence

- [x] Packet opened; Phase 14 `in_progress`; Phase 13 merge cited; six locks recorded.
- [x] Construction `review_policy` defaults to `none`.
- [x] `ReviewEvidence` is an unsigned local attestation.
- [x] CLI, MCP, and `PipelineService` cannot submit completed review evidence.
- [x] OCR preview and quality findings are not review queues.
- [x] No Phase 13 heuristic is admitted to block seal.
- [x] Focused isolation tests, tracking, Ruff, lock, and diff check.

## Required item 14.2 evidence

- [x] `veriformis.review-bundle/v1` binds to a finished-dataset plan.
- [x] Closed queue-kind set. Core, opt-in, and sampling kinds are named.
- [x] Waiver cannot change bytes. Correction kind is transform or mapping-revision.
- [x] `blocks_seal` is false. CLI still has no submit command.

## Required item 14.3 evidence

- [x] Core queue kinds are listed on every report.
- [x] Required-review construction fills `construction-pending` items.
- [x] Default `none` construction has no pending items.
- [x] Opt-in near-duplicate and detector kinds stay off unless requested.

## Required item 14.4 evidence

- [x] Transform correction binds a new `trn` identity and requires a byte change.
- [x] Mapping revision binds a new `mpl` identity.
- [x] Unchanged mapping or identical-byte transform fails closed.
- [x] In-place mutation of accepted records fails closed.
- [x] Waiver `changes_bytes` stays false.
