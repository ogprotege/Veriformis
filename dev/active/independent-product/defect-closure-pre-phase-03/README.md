# Defect Closure — Pre-Phase-3 Hardening

**Status:** Completed

**Started:** 2026-08-12

**Kind:** Interstitial defect-closure packet (not a numbered roadmap phase)

**Precedes:** [Phase 3 — Taxonomy](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-3--formalize-the-goal-schema-container-and-profile-taxonomy)

## Purpose

Close the correctness, fail-closed, and adapter-parity defects surfaced by the
2026-08-12 full-repository review before taxonomy work begins on Phase 3. The
green 675-test baseline hid every one of these because they live in paths unit
fixtures did not cross: Unicode edges, interruption windows, mixed-input seams,
untrusted-input handling, and surface plumbing.

This packet follows the Phase 2 pattern — pinned regression tests first, one
reviewable pull request — but it is **not** a numbered phase. It changes no
persisted schema and no durable identity derivation, so it neither advances the
program ledger nor requires a workspace revision migration. Parser fixes change
canonical streams and diagnostics for **new** runs only; that is corrected
recovery behavior, not a migration.

## Scope

Two critical and ten major defects, plus directly adjacent minors in the same
functions, grouped into seven independently developed clusters:

| Cluster | Defects closed |
| --- | --- |
| Workspace | Commit no-op/transition guard (critical) |
| Parsers | HTML residual-text loss (critical); DOCX table-wrapper and code-run drops; Markdown blockquote footnote refusal |
| Datasets | RecursionError containment across loaders, validator, and bundle verifier; iterative disjoint-set; reachable `primary-source-cap` |
| Transport / handoff | Post-publication warning guard; handoff `\n`-framed JSONL; descriptor path pinning and manifest cross-check; `SealPartialPublicationError` surfacing in `run` and MCP |
| Cleaning / YAML | `special-chars` combining-mark preservation; `chunk_sentence` evidence alignment; strict pipeline-spec key and recipe-id validation |
| Review lifecycle | Reviewed construction results replay with their review evidence through every downstream stage |
| Workbench | Fail-closed evaluation-gate and CLI split-ratio defaults |

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Cluster list, gates, and integration order |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted scope and non-scope decisions |
| [risks.md](risks.md) | Active risks and controls |
| [evidence.md](evidence.md) | Review provenance and verification proof |
| [closeout.md](closeout.md) | Exit-gate judgment |

## Non-goals

No taxonomy work, no new objectives/row schemas/containers, no persisted-schema
or identity change, no signing/notarization, no public-ready claim. Remaining
lower-severity findings from the review are carried forward to `risks.md` for
Phase 3+ scheduling rather than forced into this packet.
