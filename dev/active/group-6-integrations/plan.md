# Group 6 Integrations Plan

**Status:** Complete

**Roadmap scope:** Steps 22 through 23

**Starting point:** Groups 1 through 5 at version `0.1.0`

## Outcome

1. Constrained local MCP adapter exposes recipe, preview, construction,
   validation, sealing, and verification through `PipelineService` only.
2. Versioned Aptus handoff descriptor binds sealed partitions, assignment
   projection digest, row semantics, masking expectations, and backend
   capability claims without changing the closed `minimal-v1` six-file set.

## Fixed decisions

- MCP is local stdio only; no remote tools, no generation.
- Tool handlers call `PipelineService` and return structured JSON outcomes.
- Aptus handoff is a sibling artifact (`*.aptus-handoff.json`), not an extra
  sealed bundle file (preserves minimal-v1 closed set).
- Assignment digest for handoff is a portable projection over sealed
  provenance rows so consumers can recompute without workspace state.
- Current MLX capability rejects plain `text` rows; handoff records that.
- Exit gate: service/CLI/MCP parity digests; handoff consumer verifies
  external_digest, partition bytes, rows, and assignment projection.

## Exit gate

Python, CLI, and MCP produce identical results for the same stage inputs.
Aptus-side consumption is proven by a Veriformis consumer that verifies the
handoff against a sealed bundle without mutating partitions.
