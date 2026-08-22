# Phase 5 Closeout

**Status:** Incomplete

**Last reviewed:** 2026-08-22

## Judgment

Phase 5 is in progress. Items 5.1–5.3 implement and admit the
`split-jsonl-directory`, `json`, and `constrained-csv` v1 containers; item 5.3
merged as PR #55 at `c6d7fc13a09a`. Those three containers do not satisfy the
phase-wide roadmap exit gate. Item 5.4 is locally admitted after its required
evidence and corrected independent reviews passed; pull-request publication,
GitHub evidence, and merge remain pending. Items 5.5–5.7 also remain open, so
Phase 5 is not complete.

## Required before completion

- [ ] Items 5.1–5.7 are complete or explicitly deferred by an accepted
      roadmap-permitted decision.
- [ ] Every compatible schema/container pairing round-trips to identical rows
      and logical partitions.
- [ ] Tamper detection passes and nested CSV fails before publication with an
      actionable alternative.
- [ ] Focused, full, release, tracking, parity, Mac, lint, and diff gates pass
      and are recorded in `evidence.md`.
- [ ] Program, WIP, current status, support registry, evidence index,
      documentation, and this packet agree.
- [ ] Delivered scope, exclusions, remaining debt, and migration or release
      consequences are recorded here.

## Current exclusions and boundaries

- Split JSONL, canonical JSON, and constrained CSV are implemented in items
  5.1–5.3. Constrained CSV supports only the three flat row schemas and refuses
  nested `messages` with a JSON alternative before publication.
- Item 5.4's local `deterministic-export-pack-zip-v1` integration is an
  optional receipt-anchored `.vfexport.zip` wrapper around one unchanged
  published directory. It is not a fourth renderer, trainer format,
  source-bound export verification, persisted receipt change, MCP operation,
  or Mac UI action. Its local admission gates are complete; publication,
  GitHub evidence, and merge remain open.
- Phase-wide round trips, previews, and final guidance remain later Phase 5
  work.
- Generic output is not evidence of Aptus, MLX-LM, TRL, or any other trainer
  compatibility.
- Phase 5 does not add construction, curation, balancing, splitting, public
  plugins, network publication, force replacement, signing, notarization, or
  maturity promotion.
