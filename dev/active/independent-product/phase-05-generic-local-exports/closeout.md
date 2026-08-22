# Phase 5 Closeout

**Status:** Incomplete

**Last reviewed:** 2026-08-22

## Judgment

Phase 5 is in progress. Items 5.1–5.3 implement and admit the
`split-jsonl-directory`, `json`, and `constrained-csv` v1 containers, but these
three containers do not satisfy the phase-wide roadmap exit gate. Items
5.4–5.7 remain open, and item 5.3 still requires its remote-green merge gate.

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
  nested `messages` with a JSON alternative before publication. Generic
  export-pack archives, phase-wide round trips, previews, and final guidance
  remain later Phase 5 work.
- Generic output is not evidence of Aptus, MLX-LM, TRL, or any other trainer
  compatibility.
- Phase 5 does not add construction, curation, balancing, splitting, public
  plugins, network publication, force replacement, signing, notarization, or
  maturity promotion.
