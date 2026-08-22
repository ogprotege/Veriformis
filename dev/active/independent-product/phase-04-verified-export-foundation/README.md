# Phase 4 — Verified Export Foundation

**Status:** Completed

**Started:** 2026-08-21

**Completed:** 2026-08-21

**Roadmap phase:** [Phase 4](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-4--build-the-verified-export-foundation)

**Predecessor:** [Phase 3 closeout](../phase-03-taxonomy/closeout.md)

## Purpose

Build one consumer-neutral, verified-bundle-only export foundation. Export
plans, receipts, publication, and verification remain derivatives of the
canonical `minimal-v1` bundle. They do not become a second construction,
curation, balancing, or splitting pipeline.

CLI, MCP, and the CLI-backed Mac workbench must use the shared Python
composition root. No adapter may copy, rewrite, or reinterpret bundle payloads
on its own.

## Phase boundary

Phase 4 establishes contracts, services, safety, evidence, and surfaces. Its
exit proof uses an injected conformance exporter that is not a supported
product container. Generic JSONL, JSON, and CSV exports remain Phase 5 work;
trainer-specific profiles remain later work.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Nine-PR execution sequence and exit gate |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Accepted architectural and evidence decisions |
| [risks.md](risks.md) | Active risk register and controls |
| [evidence.md](evidence.md) | Starting facts and observed proof |
| [closeout.md](closeout.md) | Exit-gate judgment |

## Outcome

Phase 4 delivered one consumer-neutral verified-export foundation beneath
`PipelineService`: strict versioned plans, profiles, dependencies, membership,
file bindings, receipts, and verification; trusted-by-default source admission;
source-derived planning; exact derivative-membership enforcement; atomic
no-replace publication; exact-byte and semantic-content evidence limits; and
strict discovery, dry-run, inspect, execute, and verify operations across
Python, CLI, MCP, and the CLI-backed Mac bridge.

Items 4.1–4.7 merged sequentially as PRs #43–#49. The Phase 4.8 surface
implementation merged as PR #50 at
`fb0a13d7cab1e456b6ff3b3dc6ebab13b9898edb`; its review corrections merged as
PR #51 at `d91542fe12c5a492de578ad060836a7d65999e42`. Clean local `main` was
synchronized to that commit before the Phase 4.9 closeout branch began.

The Phase 4.9 harness consolidates contract and identity replay, tamper and
unexpected-file refusal, traversal and Unicode/case-alias rejection, link and
special-file refusal, source-digest failure, complete membership-mutation
failure, publication races, cancellation ordering, and honest visible-partial
reporting. The packet, program ledger, WIP, current status, architecture,
support-gap record, evidence index, and active documentation are reconciled by
the closeout change.

The default service still has no renderer or semantic replayer. Production
discovery remains empty. There is no public registration API, supported generic
container, new consumer profile, force or replacement control, or support
promotion. Generic containers remain Phase 5 work, and named trainer profiles
remain later work.
