# Phase 15 Execution Plan

**Status:** In progress — item 15.4

**Last updated:** 2026-08-27

**Authority:** [Independent Product Roadmap](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 15; [program.json](../program.json); [Finished Dataset Contract v1](../../../../docs/contracts/finished-dataset-v1.md); [Verified Export Contract v1](../../../../docs/contracts/verified-export-v1.md).

**Predecessor:** Phase 14 closeout merged as PR #131 at
`44a1a94150171d9bca4049f5d8069885494e4192`. Clean local `main` equals
`origin/main` there.

Each numbered work item is one sequential pull request on branch
`phase15/0N-<slug>` titled `Phase 15.N: <imperative>`. A pull request must
pass its focused and required repository gates, pass every GitHub check,
merge, and leave clean local `main` equal to `origin/main` before the next
item begins. The repository is public; sequential PRs are the operator
instruction of 2026-08-25.

Stop after 15.3 and show the baseline report before 15.4 publishes
tiers and before 15.5–15.8 engineer anything. Closeout is folded into
15.9. Do not start Phase 16 from this packet.

## Goal

Replace unknown scale behavior with named, reproducible support tiers
and bounded-resource execution.

## Architecture

`PipelineService` remains the composition root. CLI, MCP, and later Mac
progress screens are adapters. The sealed bundle is the oracle. Exports
may shard; the compiler workspace does not become a distributed job.
Streaming and external sort land only if they preserve deterministic
ordering, identity, curation, and leakage grouping. Small-corpus
ergonomics stay the default.

## Standing constraints

- Measure before targets. 15.4 is the first public number.
- Oracle is the sealed bundle. Speed never licenses a different dataset.
- Synthetic retained corpora only. Owner library bytes never enter the
  repo or CI.
- Named hardware is evidence, not a product SLA.
- 15.5–15.8 fire only against measured, named bottlenecks. A modest
  fig-leaf tier is forbidden. Keep measuring until a claim has evidence.
- Sharding is export, not a second compiler. Canonical JSON v1 keeps
  its no-scale claim.
- Small-corpus golden path stays the default unless a versioned
  migration is named.
- Surfaces: `PipelineService` plus CLI/MCP. Mac scale UX is Phase 18.
- Disk preflight must not guess.
- Phase 13 quality and Phase 14 review stay orthogonal.
- Do not start Phase 16 from this packet.

## Key decisions (lock at 15.1)

| Decision | Recommendation | Why |
| --- | --- | --- |
| Sequential PRs | 15.1 then 15.2 through 15.9, one green merge at a time. | Operator instruction; same as Phases 12–14. |
| Packet first | 15.1 opens tracking and proves current scale facts. | Honesty pattern of 13.1 and 14.1. |
| No generators in 15.1 | Do not add corpora, harness, tiers, streaming, or sharding. | Declaring those implies later public numbers. 15.2 owns generators. |
| Ten operator locks | Measure first; sealed-bundle oracle; synthetic corpora; named hardware is evidence; no speculative rewrite; sharding is export; small-corpus default; CLI/MCP not Mac; no guessed preflight; 13/14 orthogonal. | Operator accepted 2026-08-26 against the product mission. |
| Gate after 15.3 | Operator reviews baselines before 15.4. 15.5–15.8 may shrink. | Lock 1 and lock 5. |
| Closeout in 15.9 | Adversarial tests, small-corpus invariant, and exit evidence close the phase. | Same fold as Phase 14.8. |

## Likely files (created across the phase)

- Create: `dev/active/independent-product/phase-15-scale/` packet (15.1)
- Create later: corpus generators, baseline harness, tier table, streaming
  or sharding only if 15.3/15.4 name them
- Do not modify in 15.1: validation gates, export renderers, review
  queues, quality admission, Mac UI

---

## Checklist

### 15.1 Open the scale packet

**Branch:** `phase15/01-scale-packet`
**Title:** `Phase 15.1: Open the scale packet`

- [x] Confirm the predecessor gate: Phase 14 completed, `HEAD == origin/main`.
- [x] Create the standard Phase 15 packet. Mark Phase 15 `in_progress` in
      `program.json`. Reconcile active tracking documents. Cite the Phase 14
      closeout merge. Record the ten operator locks.
- [x] Prove `gap-retained-scale-benchmarks` is `verified-open`.
- [x] Prove corpus-demand `representative-scale` is still an evidence gap.
- [x] Prove the support registry publishes no corpus tiers.
- [x] Prove canonical JSON v1 makes no scale, streaming, or memory claim.
- [x] Prove Hugging Face Dataset export pins one shard per split.
- [x] Prove CLI, MCP, and `PipelineService` have no scale-benchmark,
      stream-compile, or shard-export operations.
- [x] Prove there is no `veriformis.scale` module and no `scale_benchmark`
      pytest marker.
- [x] Record focused, tracking, lint, lock, and diff evidence. Do not claim
      targets.

### 15.2 Add deterministic benchmark corpora

**Branch:** `phase15/02-benchmark-corpora`
**Title:** `Phase 15.2: Add deterministic benchmark corpora`

- [x] Versioned generators and tiny CI fixtures covering file count, bytes,
      records, row length, nesting, PDF pages, duplicate rate, container,
      and both compile paths. Seeds make them bit-stable. No owner library.
      No committed large blobs.

### 15.3 Record named-hardware baselines

**Branch:** `phase15/03-baseline-harness`
**Title:** `Phase 15.3: Record named-hardware baselines`

- [x] Harness records wall, CPU, peak RSS, disk amplification, object
      count, startup, cancel, and resume on named hardware. Reports are
      evidence, not SLAs. CI smoke only under an excluded marker. No
      published tiers.

### 15.3b Expand the named-hardware measurement ladder

**Branch:** `phase15/03b-measurement-ladder`
**Title:** `Phase 15.3b: Expand the named-hardware measurement ladder`

- [x] Record the operator lock: never publish a modest fig-leaf tier;
      keep measuring until a claim has evidence.
- [x] Packaged measurement-point specs (not support tiers) covering
      10×40, 25×100, 50×400, 100×1000 markdown, PDF pages, and
      duplicates.
- [x] Named-hardware reports retained as evidence. `sla_claim` stays
      false. Dataset-row compile remains unmeasured in 15.3b.
- [x] Core pytest materializes the ladder; it does not compile the
      large points. No published tier.

### 15.3c Record dataset-row CLI compile evidence

**Branch:** `phase15/03c-dataset-row-cli-compile`
**Title:** `Phase 15.3c: Record dataset-row CLI compile evidence`

- [x] `scale-baseline --corpus-id ci-tiny-jsonl` refuses; retain that
      as a refusal, not a passing baseline.
- [x] Operator CLI compile of the two-row `text.jsonl` fixture through
      seal/verify, with confirmed mapping plan, wall, RSS, workspace,
      and bundle sizes. `sla_claim` stays false.
- [x] Peak RSS is the max of separate CLI processes, not the 15.3b
      single-process number. Amplification is overhead. Not a support
      tier. Item 15.4 stays closed.

### 15.4 Publish operator-reviewed support tiers

**Branch:** `phase15/04-support-tiers`
**Title:** `Phase 15.4: Publish operator-reviewed support tiers`

- [x] Operator reviews the measurement ladder. Publish named tiers
      only from evidenced ceilings. A modest fig-leaf tier is
      forbidden. Unmet sizes stay unmeasured, not "supported small".
      No rewrite. `published_tiers` is empty. Observations and
      refusals are discovery, not an SLA.

### 15.5 Profile and optimize measured bottlenecks

**Branch:** `phase15/05-measured-optimize`
**Title:** `Phase 15.5: Profile and optimize measured bottlenecks`

- [ ] Only hot paths 15.3 measured and 15.4 named. Profiler evidence in
      the packet. Sealed-bundle oracle on shared fixtures. Small-corpus
      results unchanged. Skip this item if 15.4 declared the current
      path sufficient.

### 15.6 Add streaming only where the oracle allows

**Branch:** `phase15/06-streaming`
**Title:** `Phase 15.6: Add streaming only where the oracle allows`

- [ ] Iterator APIs and external sort only if compatible with ordering,
      identity, curation, and leakage grouping, and only if 15.3/15.4
      named them. Streaming output matches the non-streaming oracle. Not
      for canonical JSON v1.

### 15.7 Add bounded-resource execution

**Branch:** `phase15/07-bounded-execution`
**Title:** `Phase 15.7: Add bounded-resource execution`

- [ ] Incremental parse/clean reuse, bounded queues, backpressure,
      progress facts, checkpoint/resume, and measured disk-space
      preflight. Build on Phase 2 cancel/workspace. No guessed preflight.
      No Mac UI.

### 15.8 Add deterministic JSONL and Parquet sharding

**Branch:** `phase15/08-deterministic-sharding`
**Title:** `Phase 15.8: Add deterministic JSONL and Parquet sharding`

- [ ] Shard plans with shard receipts and existing global semantic
      fingerprints. Hugging Face `num_shards` only if 15.3 showed
      one-shard export as the bottleneck. No workspace sharding. Canonical
      JSON stays unsharded.

### 15.9 Add adversarial scale tests and close Phase 15

**Branch:** `phase15/09-adversarial-closeout`
**Title:** `Phase 15.9: Add adversarial scale tests and close Phase 15`

- [ ] Crash, cancel, disk exhaustion, file-descriptor limits, large
      individual records, and cross-platform reproducibility. Small-corpus
      invariant proven. Closeout. Do not start Phase 16 from this packet.

## Usability criteria

| ID | Criterion |
| --- | --- |
| U1 | `PipelineService` owns scale policy. CLI and MCP are adapters. Mac scale UX is Phase 18. |
| U2 | After any scale change, the same sources and recipe produce the same sealed-bundle identities. |
| U3 | Retained corpora are synthetic. Owner library bytes never enter the repo or CI. |
| U4 | Public numbers cite named hardware and corpus identity. They are not unbounded SLAs. |
| U5 | 15.5–15.8 run only against measured, named bottlenecks, or are skipped with a record. A modest unpublished-as-tier fig leaf is forbidden. |
| U6 | Sharding is a derivative. The workspace remains one machine and one identity. |
| U7 | Small-corpus fixtures, seventeen gates, and default recipes stay unchanged unless a versioned migration is named. |
| U8 | Disk preflight and bounded queues refuse to guess. |
| U9 | Quality reports and review queues are not a default compile tax at scale. |
| U10 | Phase 16 does not start from this packet. |

## Exit gate

All declared tiers meet targets set before optimization acceptance;
benchmark regressions fail CI or release gates at documented
thresholds; semantic outputs match the non-streaming oracle on shared
fixtures.

**Result:** Pending. See [closeout.md](closeout.md). Do not start Phase 16.
