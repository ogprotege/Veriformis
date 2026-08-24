# Phase 10 — Expand Consumer Profiles under Evidence Gates

**Status:** Complete

**Started:** 2026-08-24

**Completed:** 2026-08-24

**Roadmap phase:** [Phase 10](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-10--expand-consumer-profiles-under-evidence-gates)

**Predecessor:** [Phase 9 closeout](../phase-09-columnar-containers/closeout.md),
merged as PR #96 at `abdcce6474aadd33fcf38a5360b63a4f8d293a5c` after all 18
GitHub checks passed. Clean local `main` equals `origin/main` there.

## Purpose

Add high-value training-system profiles without coupling the product to any
one ecosystem. Each candidate is admitted independently. Profiles remain
optional adapters over an already-verified bundle (ADR-0012, ADR-0014).

## Phase boundary

Phase 10 owns admission pins, isolated extras, independently admitted
emissions, Aptus-as-profile migration, conformance harnesses, sidecars,
deprecation policy, and discovery truthfulness. It adds no new row schema,
no Hub upload, no hosted OpenAI profile, and no training launcher.

Item 10.1 opens the packet, publishes ADR-0014, keeps `axolotl`,
`llama-factory`, and `unsloth` as candidates, refuses those `consumer_id`
values as Phase 10, and declares empty extras. Aptus remains the existing
sibling handoff until item 10.6.

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

Items 10.3–10.8 emit Axolotl and LLaMA-Factory, skip Unsloth, move Aptus
onto `ExportService`, add official-schema harnesses, and close the
phase. Extras stay empty. The exporter does not train. Do not start
Phase 11 or 13 from this packet.
