# Phase 15 Evidence

**Status:** Open — item 15.2

**Opened:** 2026-08-26

## Predecessor evidence

Phase 14 completed. Closeout merged as PR #131 at
`44a1a94150171d9bca4049f5d8069885494e4192`. Clean local `main` equals
`origin/main` there.

Operator compile of Pius X *Pascendi Dominici Gregis* at
`/Users/biscuit/Documents/Veriformis` (`2026-08-24T13-54-52Z`): `full_text`
/`text`, 31 train / 0 evaluation, manifest
`94b63232166aeedc9db797fdc0ec0167b2135d8c01bd3934635250a0a2245ace`. Seal
`self_consistent`; zip `external_digest`. Recorded in
[operator-compile-2026-08-24-pascendi.md](../operator-compile-2026-08-24-pascendi.md).
That run is not a retained scale benchmark.

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| Support gap `gap-retained-scale-benchmarks` is `verified-open` | `source-verified` | `docs/governance/support-registry.json` |
| Corpus-demand gap `representative-scale` is open | `source-verified` | `docs/governance/corpus-demand-matrix.json` |
| Support registry publishes no corpus tiers | `source-verified` | `docs/governance/support-registry.json` |
| Canonical JSON v1 makes no scale, streaming, or memory claim | `source-verified` | `docs/generic-exports.md`; `docs/contracts/canonical-json-export-v1.md` |
| Hugging Face Dataset export pins `num_shards` train/eval = 1 | `source-verified` | `src/veriformis/exports/hugging_face_dataset.py` |
| Phase 9.8 JSONL-versus-columnar sizes are a tiny fixture, not a recommendation | `source-verified` | Phase 9 evidence; split JSONL 24,073 bytes |
| No `veriformis.scale` module at 15.1 open | `source-verified` | package layout; 15.2 adds generators |
| CLI, MCP, and `PipelineService` have no scale-benchmark, stream-compile, or shard-export operations | `source-verified` | `src/veriformis/cli.py`; MCP server; `PipelineService` |
| Seventeen finished-dataset gates unchanged | `source-verified` | `src/veriformis/contracts.py` `V1_FINISHED_DATASET_GATES` |
| Pytest has no `scale_benchmark` marker | `source-verified` | `pyproject.toml` |

## Required item 15.1 evidence

- [x] Packet opened; Phase 15 `in_progress`; Phase 14 merge cited; ten locks recorded.
- [x] No retained scale benchmark. Gap `gap-retained-scale-benchmarks` stays `verified-open`.
- [x] No published corpus tier or public scale guarantee.
- [x] Canonical JSON v1 still makes no scale, streaming, or memory claim.
- [x] Hugging Face Dataset export still pins one shard per split.
- [x] CLI, MCP, and `PipelineService` have no scale, stream-compile, or shard-export operations.
- [x] No `veriformis.scale` module and no `scale_benchmark` pytest marker.
- [x] Focused isolation tests, tracking, Ruff, lock, and diff check.

## Required item 15.2 evidence

- [x] `veriformis.scale-corpus-spec/v1` and `veriformis.scale-corpus/v1`.
- [x] Named seed replays the same bytes; a different seed changes bytes.
- [x] Unicode payloads are exact. Nested JSONL depth is exact.
- [x] PDF page count matches the spec. Duplicate ppm copies later records.
- [x] Tiny CI specs cover both compile paths and the roadmap dimensions.
- [x] Invalid specs and a non-empty destination fail closed.
- [x] No published tier, harness, CLI scale command, or committed blobs.
