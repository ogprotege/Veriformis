# Scale Baseline Report Contract v1

**Contract ID:** `veriformis.scale-corpus` (baseline report)

**Contract version:** `1`

**Schema:** `veriformis.scale-baseline-report/v1`

**Status:** Implemented harness in independent-product Phase 15.3. Reports
are named-hardware evidence. They are not a product SLA and do not
publish a support tier.

**Last reviewed:** 2026-08-27

**Authority:** [Independent Product Roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 15.

## Purpose

Record wall time, CPU, peak RSS, disk amplification, object count,
startup, between-stage cancel, and resume for one packaged document-
source corpus on named hardware. Exact targets wait for operator
review of these reports.

## Report

Identity is `derive_id("sbr", …)` over the payload excluding
`report_id`. `sla_claim` and `statistical_meaning` are false. Hardware
fields name the interpreter and machine; they are not a guarantee that
another machine will match.

v1 compiles `document-source` corpora only. Dataset-row specs fail
closed. Cancellation is cooperative between stages, not mid-stage.
Peak RSS is process-wide `ru_maxrss`, not a delta.

Packaged measurement-point specs (`measure-markdown-*`, `measure-pdf-2-8`)
are a ladder, not a support table. A modest fig-leaf tier from an
unrepresentative fixture is forbidden.

## Surfaces

Python `PipelineService.run_scale_baseline`, CLI `scale-baseline`, and
MCP `scale_baseline` emit the same schema. Tiny CI smoke runs in the
ordinary suite. Named-hardware dumps use the excluded `scale_benchmark`
marker.

## Non-goals

Published support tiers. Throughput SLAs. Streaming or sharding. Mac
progress chrome. Mid-stage compile cancellation. Dataset-row mapping
compile in this report version. An operator CLI compile of a two-row
JSONL fixture is packet evidence, not this report schema.
