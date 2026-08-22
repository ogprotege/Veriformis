# Phase 5 Closeout

**Status:** Incomplete

**Last reviewed:** 2026-08-22

## Judgment

Phase 5 is in progress. Items 5.1 and 5.2 implement and admit the
`split-jsonl-directory` v1 and `json` v1 containers, but two completed
containers do not satisfy the phase-wide roadmap exit gate. Items 5.3–5.7
remain open.

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

- Split JSONL and canonical JSON are implemented in items 5.1 and 5.2. CSV,
  generic export-pack archives, phase-wide round trips, previews, and final
  guidance remain later Phase 5 work.
- Generic output is not evidence of Aptus, MLX-LM, TRL, or any other trainer
  compatibility.
- Phase 5 does not add construction, curation, balancing, splitting, public
  plugins, network publication, force replacement, signing, notarization, or
  maturity promotion.
