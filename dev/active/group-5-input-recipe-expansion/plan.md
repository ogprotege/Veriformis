# Group 5 Input and Recipe Expansion Plan

**Status:** Complete

**Roadmap scope:** Steps 20 through 21

**Starting point:** Groups 1 through 4 at version `0.1.0`

**Last reviewed:** 2026-08-05

## Outcome

Every declared v1 input either compiles with explicit extraction-loss
diagnostics or fails with a named limitation (including OCR refusal). Multiple
deterministic recipes and a versioned YAML pipeline produce measurable,
repeatable datasets from supported formats.

## Fixed decisions

1. **HTML:** deterministic `lxml` body extraction (no network). Scripts, styles,
   and non-body chrome are omitted with explicit diagnostics.
2. **PDF:** `pypdfium2` text-layer extraction with page-region blocks. Empty or
   image-only PDFs refuse with a named OCR limitation.
3. **CSV / JSON / JSONL:** UTF-8 structured recovery into canonical IR tables or
   paragraphs with source-text evidence, never silent schema invention.
4. **OCR:** unsupported. Named refusal only; no image decoding path.
5. **Recipe library:** named deterministic builders for the five objectives plus
   finished-plan defaults; pure functions over existing contracts.
6. **YAML pipelines:** versioned `veriformis.pipeline/v1` documents executed only
   through `PipelineService` (no second orchestration root).
7. **Statistics:** deterministic, offline counts and length summaries over
   construction and finished-stage artifacts; estimates only (no tokenizer extra).

## Exit gate

- Declared formats parse, refuse, or diagnose as specified.
- At least two named recipes produce sealed, verifiable datasets from mixed
  supported sources with identical digests on replay.
- YAML pipeline run matches equivalent stage-command service calls.
