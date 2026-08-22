# Phase 5 Closeout

**Status:** Incomplete

**Last reviewed:** 2026-08-22

## Judgment

Phase 5 is in progress. Items 5.1–5.5 are merged; item 5.5 merged as PR #57 at
`c72b8e9ec7bc2746d74404226aa086d497e15db1`. Item 5.6's runtime preview is
implemented and locally admitted, but publication, GitHub evidence, merge, and
clean-main synchronization remain pending. Item 5.7 also remains open, so
Phase 5 is not complete.

## Required before completion

- [ ] Items 5.1–5.7 are complete or explicitly deferred by an accepted
      roadmap-permitted decision.
- [x] Every compatible schema/container pairing round-trips to identical rows
      and logical partitions.
- [x] Tamper detection passes and nested CSV fails before publication with an
      actionable alternative.
- [x] Focused, full, release, tracking, parity, Mac, lint, and diff gates pass
      and are recorded in `evidence.md`.
- [ ] Program, WIP, current status, support registry, evidence index,
      documentation, and this packet agree.
- [ ] Delivered scope, exclusions, remaining debt, and migration or release
      consequences are recorded here.

## Current exclusions and boundaries

- Split JSONL, canonical JSON, and constrained CSV are implemented in items
  5.1–5.3. Constrained CSV supports only the three flat row schemas and refuses
  nested `messages` with a JSON alternative before publication.
- Item 5.4's merged `deterministic-export-pack-zip-v1` integration is an
  optional receipt-anchored `.vfexport.zip` wrapper around one unchanged
  published directory. It is not a fourth renderer, trainer format,
  source-bound export verification, persisted receipt change, MCP operation,
  or Mac UI action.
- Item 5.5 is a merged, discovery-closed fixture proving all 11
  compatible current container/schema pairs, actionable nested-CSV refusal,
  and semantic tampering. It is not a production importer or replayer.
- Item 5.6 previews are runtime-only bounded response evidence: exact
  ordinal-zero partition samples and one normalized plan-derived tree, with
  whole-row omission rather than truncation. Its implementation and local
  admission evidence passed; publication and merge remain open. Final guidance
  remains item 5.7 work.
- Generic output is not evidence of Aptus, MLX-LM, TRL, or any other trainer
  compatibility.
- Phase 5 does not add construction, curation, balancing, splitting, public
  plugins, network publication, force replacement, signing, notarization, or
  maturity promotion.
