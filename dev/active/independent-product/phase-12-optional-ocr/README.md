# Phase 12 — Add Optional Local OCR with Accountable Recovery

**Status:** In progress

**Started:** 2026-08-25

**Completed:**

**Roadmap phase:** [Phase 12](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-12--add-optional-local-ocr-with-accountable-recovery)

**Predecessor:** [Phase 11 closeout](../phase-11-collection-ingest/closeout.md),
merged as PR #104 at `e856af96043c9876affa275b5246e83541254d9d`. Clean local
`main` equals `origin/main` there.

## Purpose

Recover image-only and mixed PDFs without weakening source evidence. OCR is
optional, local, and accountable. It never silently replaces a recoverable
digital text layer.

## Phase boundary

Phase 12 owns the OCR evaluation, the owner-approved OCR ADR or an explicit
deferral, and — only after that ADR is accepted — parser identities, recovery
paths, thresholds, review hooks, the isolated `ocr` extra, and the no-network
harness.

Item 12.1 opens the packet. `ocr-image` stays `explicitly_unsupported`. There
is no `ocr` extra. Image-only and empty-text PDFs still refuse with
`pdf.ocr-required` / `ocr-unsupported`. Items 12.3–12.8 wait on the
12.2 evaluation and an owner ADR or deferral. Do not start Phase 13 from
this packet.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Eight-item execution sequence, usability criteria, and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted scope decisions |
| [risks.md](risks.md) | Risk register and controls |
| [evidence.md](evidence.md) | Starting facts and observed proof |
| [closeout.md](closeout.md) | Exit-gate judgment |
| [SESSION.md](SESSION.md) | Crash-recovery pointer for the current item |

## Current state

Item 12.1 is opening the packet. OCR is not implemented. Do not start
Phase 13 from this packet.
