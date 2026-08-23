# ADR-0010 — Input Mode as a Compiler Path

**Status:** Accepted

**Date:** 2026-08-23

**Decider:** Phase 7.1 opening; independent-product roadmap Phase 7

## Context and evidence

CSV, JSON, and JSONL are already recovered as document or table sources.
Phase 7 must admit datasets that already contain training rows without
collapsing that path into a suffix or a taxonomy axis. The support registry
already distinguishes implemented and planned *modes*. Taxonomy v1 already has
seven axes; adding an eighth would mix “what is learned” with “which compiler
graph runs.”

## Decision

1. Input **mode** is a compiler path, not a taxonomy axis and not a collapsed
   “format” field. The closed identifiers are `document-source`,
   `dataset-row`, and `mixed`.
2. `document-source` remains the default and the only executable mode in item
   7.1. Omitting `--mode` is document-source. Suffix `.jsonl` does not select
   import.
3. `dataset-row` and `mixed` are discoverable and planned. Execution refuses
   with an actionable reason that names the later item (7.3 and 7.7).
4. Mode identifiers are packaged versioned data
   (`veriformis.input-mode-discovery/v1`). CLI, MCP, and `PipelineService`
   consume discovery rather than duplicated constants. The support registry
   lists the same implemented and planned identifiers, bound by the tracking
   checker.
5. Dataset-row capture must not reuse document recovery in
   `parsers/structured.py`. That path remains document-source only.

## Consequences

- Existing compiles stay byte-compatible.
- Later mapping, preview, partition, and mixed work have a named gate to open.
- Advertising a planned mode as implemented fails tracking.

## Alternatives considered

- An eighth taxonomy axis: rejected; mode is a stage graph, not a learning
  meaning.
- Silent suffix dispatch into import: rejected; the same `.jsonl` file is
  valid document-source material.
- Reusing CSV/JSON recovery for mapping: rejected; recovery trims, pads, and
  flattens, which Phase 5.3 already refused as round-trip evidence.

## Review triggers

Item 7.3 executable dataset-row mapping; item 7.7 mixed projects; any new
compiler path; any attempt to infer mode from suffix.
