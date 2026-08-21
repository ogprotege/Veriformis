# Project Tracking and Evidence Policy

**Status:** Active

**Policy version:** `veriformis.project-tracking/v1`

**Last reviewed:** 2026-08-21 (independent-product Phase 4.3 source trust)

**Next review:** Independent-product Phase 4.3 state transition or any
program-state, evidence-grade, or completion-rule change

## Purpose

This policy ensures that Veriformis progress is continuously recorded and that
implemented claims are based on inspectable evidence rather than assertion.
It applies to the independent-product roadmap and all later product programs.

## Authority order

When records conflict, use this order:

1. Versioned runtime contracts and verified code behavior.
2. [Current implementation status](../current-status.md) for human-readable
   present capability claims.
3. [Support registry](support-registry.json) for machine-readable capability
   state.
4. [Independent product roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md)
   for future work, dependencies, and exit gates.
5. [Program ledger](../../dev/active/independent-product/program.json) for the
   current execution state of each roadmap phase.
6. Root [WIP](../../WIP.md) as a convenient human-readable mirror.
7. Phase packets and historical plans as implementation and decision history.

Lower records must not override higher records. Plans are never proof that a
capability exists.

## Allowed phase states

| State | Meaning | Required record |
| --- | --- | --- |
| `planned` | Authorized by the roadmap but not started | Roadmap phase and next gate |
| `in_progress` | Work has begun and has an active packet | Packet, dated progress entry, open checklist |
| `blocked` | Exit cannot advance without a named external or owner dependency | Blocker, attempted alternatives, resumption condition |
| `deferred` | Intentionally excluded from the active release or milestone | Decision, reason, reconsideration trigger |
| `completed` | All work and exit evidence passed | Closeout, tests, evidence links, status/support updates |

Only one sequential critical-path phase may be `in_progress` unless the
roadmap explicitly permits parallel work and each active phase has its own
packet.

## Standard phase packet

Every `in_progress` or `completed` phase directory contains:

```text
README.md
plan.md
progress.md
decisions.md
risks.md
evidence.md
closeout.md
```

The packet is created before implementation begins. `progress.md` is
append-only by dated entry: corrections add a later entry rather than rewriting
history. Evidence summaries may be updated when checks are rerun, but the
previous result remains visible.

## Step completion rule

A checklist step may be marked complete only when:

1. Its deliverable exists.
2. Its stated verification has passed.
3. Evidence is linked from the phase packet.
4. Relevant decisions, risks, support claims, and documentation are updated.
5. Remaining limitations are explicit.

## Phase completion rule

A phase moves to `completed` only when:

1. Every required checklist item is complete or explicitly deferred by an
   accepted decision that the roadmap permits.
2. The roadmap exit gate passes.
3. Tests and other affected verification gates pass.
4. `closeout.md` states delivered scope, evidence, exclusions, remaining debt,
   and migration or release consequences.
5. `program.json`, `WIP.md`, `current-status.md`, `support-registry.json`, and
   the evidence index agree.
6. `scripts/check_project_tracking.py` and the full required suite pass.

Green tests alone do not complete a phase. Conversely, prose cannot mark a
phase complete when executable checks fail.

## Evidence grades

The machine evidence index defines these grades:

- `source-verified`
- `test-verified`
- `recorded-local`
- `retained-artifact`
- `external-primary`
- `planned`

Claims must state the strongest grade they actually possess. A dated local
summary is not represented as a retained log; an official external document is
not represented as proof that Veriformis implemented its contract.

## Required update protocol

Every change that alters a tracked capability or phase state must update, in
the same change:

1. The active phase checklist and progress entry.
2. The program ledger when phase state or next gate changes.
3. The support registry when capability state changes.
4. Current status and WIP when user-visible truth changes.
5. The evidence index and phase evidence when a gate is run or superseded.
6. An ADR when architecture, product meaning, compatibility, or evidence policy
   changes materially.
7. Documentation debt when work is consciously left incomplete.

The tracking regression test prevents many structural mismatches. Review is
still required for semantic accuracy that code cannot infer.

## Claim discipline

- Use `implemented` only for behavior present in current code with passing
  evidence.
- Use `planned` for roadmap commitments not yet present.
- Use `candidate` for researched possibilities that have not passed admission.
- Use `unsupported` or `explicitly_unsupported` for known refusal boundaries.
- Bind consumer compatibility to a named profile and tested version range.
- Do not describe a test count, green build, or signed artifact as product
  suitability beyond the gate it actually proves.
- Preserve historical records, but label them historical when superseded.

## Review cadence

- Phase packet: every work session that changes state or evidence.
- WIP and program ledger: every phase/step state transition.
- Current status and support registry: every user-visible capability change.
- Evidence index: every verification run used to support a claim.
- ADRs: at decision time and at their stated review triggers.
- Documentation debt: every phase closeout.
