# Scale Support Contract v1

**Contract ID:** `veriformis.scale-support`

**Contract version:** `1`

**Schema:** `veriformis.scale-support-discovery/v1`

**Status:** Implemented discovery in independent-product Phase 15.4.
Published support tiers are empty. Observed measurements are evidence,
not an SLA.

**Last reviewed:** 2026-08-27

**Authority:** [Independent Product Roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 15.

## Purpose

Record the operator review of the Phase 15 measurement ladder and name
what is published, observed, refused, and unmeasured. A modest fig-leaf
tier is forbidden. Unmet sizes stay unmeasured, not "supported small".

## Catalog

`published_tiers` is the empty list. `sla_claim` and
`statistical_meaning` are false. Observations cite retained packet
reports and exact source, RSS, and wall figures. Refusals stay refusals.
Unmeasured identifiers are sorted unique tokens.

Identity of this catalog is the packaged canonical JSON. Surfaces must
not invent a supported corpus size.

## Surfaces

Python `PipelineService.discover_scale_support`, CLI `scale-support`,
and MCP `scale_support` emit the same schema.

## Non-goals

A published corpus support tier. Throughput SLAs. Streaming compile.
Export sharding. Dataset-row compile inside `scale-baseline` v1.
Guessed disk preflight from these observations.
