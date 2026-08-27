# Phase 15 Evidence

**Status:** Open — item 15.5

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

## Required item 15.3 evidence

- [x] `veriformis.scale-baseline-report/v1` records wall, CPU, peak RSS,
      disk amplification, object count, startup, cancel, and resume.
- [x] `sla_claim` and `statistical_meaning` are false.
- [x] Document-source tiny markdown compiles. Dataset-row specs fail closed.
- [x] Between-stage cancel stops after parse. Resume continues from that workspace.
- [x] Python, CLI `scale-baseline`, and MCP `scale_baseline` agree on schema.
- [x] `scale_benchmark` marker exists and is excluded from core pytest.
- [x] No published corpus tier.
- [x] Recorded-local tiny-markdown report at
      [baselines/2026-08-26-ci-tiny-markdown.json](baselines/2026-08-26-ci-tiny-markdown.json);
      `sla_claim` is false.

## Required item 15.3b evidence

- [x] Operator lock recorded: never publish a modest fig-leaf tier.
- [x] Measurement ladder specs packaged; they are not support tiers.
- [x] Named-hardware reports for markdown 10×40, 25×100, 50×400,
      100×1000, PDF 2×8, plus tiny PDF and tiny duplicates.
- [x] `measure-markdown-duplicates-10-40` compile refused:
      coverage `coverage-blocker-present`.
- [x] Dataset-row compile remains unmeasured in 15.3b.
- [x] Core pytest materializes the ladder and does not compile 100×1000.

## Required item 15.3c evidence

- [x] `scale-baseline --corpus-id ci-tiny-jsonl` refused:
      `error[scale-invalid]: scale baseline v1 compiles document-source corpora only`,
      exit 2. Retained at
      [baselines/2026-08-27-scale-baseline-ci-tiny-jsonl.refused.json](baselines/2026-08-27-scale-baseline-ci-tiny-jsonl.refused.json).
- [x] Operator CLI compile of `tests/regressions/fixtures/phase7/text.jsonl`
      (55 bytes, two rows) through parse → map → curate → split → format →
      validate → seal → verify. Confirmed plan
      `mpl-v1-99155c717e9729d19f8cd3032fa4d58ce8dc719f06070f2294644a43b039668c`.
      Seal passed. Verify grade `external_digest` on manifest
      `d55fbddb01359dbb958b7b09bdd5110dd3e48ed53c1d8b81c17f5844028e2a0f`.
- [x] Compile wall parse→verify 3.24 s. Peak RSS 74,399,744 bytes as the
      max of separate CLI processes (~71.0 MiB). Workspace 114,954 bytes.
      Bundle 12,052 bytes. Amplification is overhead. Not a support tier.
      Recorded at
      [baselines/2026-08-27-dataset-row-text-jsonl-cli.json](baselines/2026-08-27-dataset-row-text-jsonl-cli.json).
- [x] Ollama was stopped. No oracle module. No new extra. `sla_claim`
      false. Item 15.4 stays closed.

## Required item 15.4 evidence

- [x] Operator reviewed the ladder. `published_tiers` is empty. A modest
      fig-leaf tier is forbidden.
- [x] `veriformis.scale-support-discovery/v1` names observed reports,
      retained refusals, and unmeasured work. `sla_claim` is false.
- [x] Python, CLI `scale-support`, and MCP `scale_support` agree.
- [x] `gap-retained-scale-benchmarks` closes; retained reports exist.
      No published corpus support tier.
- [x] No rewrite. Item 15.5 may skip if no named bottleneck.

## Required item 15.5 evidence

- [x] Skipped with a record. 15.4 published no tier and named no
      bottleneck. No profiler. No stage rewrite. Small-corpus path
      unchanged.
